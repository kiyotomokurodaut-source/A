"""画像の審査（R18 の自動判定・形式の検査・EXIF 除去）。

判定は三値で返す:

  approved  そのまま公開してよい
  pending   公開せず、管理者の確認待ちにする（疑わしいもの、自動判定ができないもの）
  blocked   保存も公開もしない

内蔵の判定器は肌色領域のヒューリスティックで、機械学習の分類器ではない。
水着・裸・露出の多い写真をだいたい拾う程度で、取りこぼしも誤爆もある。
だから「疑わしい」は公開ではなく保留に倒し、通報と管理キューを併用する。
本番で精度が要るなら BBS_NSFW_ENDPOINT に分類器を立て、そちらを使う
（{"score": 0..1} を返す HTTP エンドポイント。詳細は README）。
"""

from __future__ import annotations

import hashlib
import json
import urllib.error
import urllib.request
from dataclasses import dataclass, field

from . import config

try:  # 任意の依存。無くても動くが、その場合は自動判定ができない。
    from PIL import Image, ImageFile

    ImageFile.LOAD_TRUNCATED_IMAGES = False
    PILLOW = True
except Exception:  # pragma: no cover - Pillow が無い環境用
    PILLOW = False

APPROVED = "approved"
PENDING = "pending"
BLOCKED = "blocked"

_MAGIC = (
    (b"\xff\xd8\xff", "image/jpeg"),
    (b"\x89PNG\r\n\x1a\n", "image/png"),
    (b"GIF87a", "image/gif"),
    (b"GIF89a", "image/gif"),
)


@dataclass
class Verdict:
    status: str
    score: float = 0.0
    reason: str = ""
    mime: str = ""
    width: int = 0
    height: int = 0
    data: bytes = b""
    details: dict = field(default_factory=dict)


def sniff_mime(data: bytes) -> str | None:
    """宣言された Content-Type ではなく中身で判定する。"""
    for magic, mime in _MAGIC:
        if data.startswith(magic):
            return mime
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return None


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def inspect(data: bytes) -> Verdict:
    """アップロードされたバイト列を検査し、保存すべき正規化済みデータを返す。"""
    if not data:
        return Verdict(BLOCKED, 1.0, "空のファイルです。")
    if len(data) > config.MEDIA_MAX_BYTES:
        limit = config.MEDIA_MAX_BYTES // (1024 * 1024)
        return Verdict(BLOCKED, 1.0, f"画像は {limit}MB までです。")

    mime = sniff_mime(data)
    if mime is None or mime not in config.ALLOWED_MIME:
        return Verdict(BLOCKED, 1.0, "対応していない形式です（JPEG・PNG・WebP・GIF のみ）。")

    if not PILLOW:
        return Verdict(
            PENDING, 0.0,
            "自動審査が使えない環境のため、公開前に管理者が確認します。",
            mime=mime, data=data, details={"engine": "none"},
        )

    try:
        normalized, width, height, animated = _normalize(data, mime)
    except Exception as exc:  # 壊れた画像、爆弾的な圧縮率など
        return Verdict(BLOCKED, 1.0, f"画像として読めませんでした（{type(exc).__name__}）。")

    score, details = _nsfw_score(normalized)
    details["animated"] = animated

    if score >= config.NSFW_BLOCK_SCORE:
        return Verdict(
            BLOCKED, score,
            "露出の多い画像と判定されました。R18 相当の画像は投稿できません。",
            mime=mime, width=width, height=height, details=details,
        )
    if animated or score >= config.NSFW_REVIEW_SCORE:
        reason = (
            "動画形式（アニメーション）は全フレームを自動判定できないため、確認待ちにしました。"
            if animated else
            "露出の判定が微妙だったため、公開前に管理者が確認します。"
        )
        return Verdict(
            PENDING, score, reason,
            mime=normalized.mime, width=width, height=height,
            data=normalized.data, details=details,
        )
    return Verdict(
        APPROVED, score, "", mime=normalized.mime, width=width, height=height,
        data=normalized.data, details=details,
    )


# --- 正規化 -----------------------------------------------------------------

@dataclass
class _Normalized:
    data: bytes
    mime: str
    image: "Image.Image"


def _normalize(data: bytes, mime: str) -> tuple[_Normalized, int, int, bool]:
    """EXIF（位置情報を含む）を落とし、大きすぎる画像を縮めて詰め直す。

    アニメーションは詰め直すと壊れるので元データのまま保つ（どのみち保留になる）。
    """
    import io

    with Image.open(io.BytesIO(data)) as probe:
        probe.load()
        width, height = probe.size
        animated = bool(getattr(probe, "is_animated", False))
        frame = probe.convert("RGB")

    if width * height > 80_000_000:
        raise ValueError("画素数が大きすぎます")

    if animated:
        return _Normalized(data, mime, frame), width, height, True

    out = frame
    if max(out.size) > config.MEDIA_MAX_EDGE:
        ratio = config.MEDIA_MAX_EDGE / max(out.size)
        out = out.resize((max(1, int(out.width * ratio)), max(1, int(out.height * ratio))), Image.LANCZOS)

    buf = io.BytesIO()
    if mime == "image/png":
        out.save(buf, format="PNG", optimize=True)
        out_mime = "image/png"
    elif mime == "image/webp":
        out.save(buf, format="WEBP", quality=88, method=4)
        out_mime = "image/webp"
    else:
        out.save(buf, format="JPEG", quality=86, optimize=True, progressive=True)
        out_mime = "image/jpeg"
    return _Normalized(buf.getvalue(), out_mime, out), out.width, out.height, False


# --- 判定 -------------------------------------------------------------------

def _nsfw_score(normalized: _Normalized) -> tuple[float, dict]:
    if config.NSFW_ENDPOINT:
        score = _external_score(normalized.data, normalized.mime)
        if score is not None:
            return score, {"engine": "endpoint"}
        # 外部判定が落ちているときは内蔵に落とす（保留側に倒れる）。
    return _skin_score(normalized.image)


def _external_score(data: bytes, mime: str) -> float | None:
    req = urllib.request.Request(
        config.NSFW_ENDPOINT, data=data, method="POST",
        headers={"Content-Type": mime or "application/octet-stream"},
    )
    try:
        with urllib.request.urlopen(req, timeout=config.NSFW_ENDPOINT_TIMEOUT) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        return max(0.0, min(1.0, float(payload["score"])))
    except (urllib.error.URLError, OSError, ValueError, KeyError, TypeError):
        return None


_THUMB = 160


def _skin_score(image: "Image.Image") -> tuple[float, dict]:
    """肌色の面積と、その最大の連結領域から 0..1 のスコアを作る。

    面積だけだと木の幹や砂浜、ベージュの背景で誤爆する。
    「大きな一続きの肌」を重く見たうえで、写真らしさ（隣り合う画素の細かな
    ばらつき）が無いものは割り引く。ベタ塗りの背景やグラデーションは
    この段階でほぼ落ちる。
    """
    img = image.convert("RGB").resize((_THUMB, _THUMB), Image.BILINEAR)
    px = img.load()
    width = height = _THUMB
    total = width * height

    mask = bytearray(total)
    lum = bytearray(total)
    skin = 0
    skin_lum: list[int] = []
    for y in range(height):
        row = y * width
        for x in range(width):
            r, g, b = px[x, y]
            value = (r * 299 + g * 587 + b * 114) // 1000
            lum[row + x] = value
            if _is_skin(r, g, b):
                mask[row + x] = 1
                skin += 1
                skin_lum.append(value)

    if skin == 0:
        return 0.0, {"engine": "skin", "skin_ratio": 0.0, "largest_ratio": 0.0,
                     "texture": 0.0, "detail": 0.0}

    skin_ratio = skin / total
    largest = _largest_region(mask, width, height) / total
    texture = _stddev(skin_lum)
    detail = _detail(mask, lum, width, height)

    score = 0.65 * min(1.0, largest / 0.55) + 0.35 * min(1.0, skin_ratio / 0.60)
    # 写真なら隣接画素は細かく揺れる。揺れない面は塗りや無地の背景。
    if detail < 1.0:
        score *= 0.25
    elif detail < 2.0:
        score *= 0.60
    elif texture < 5.0:
        score *= 0.85
    score = max(0.0, min(1.0, score))
    return score, {
        "engine": "skin",
        "skin_ratio": round(skin_ratio, 4),
        "largest_ratio": round(largest, 4),
        "texture": round(texture, 2),
        "detail": round(detail, 2),
    }


def _detail(mask: bytearray, lum: bytearray, width: int, height: int) -> float:
    """肌と判定された画素の、隣どうしの明度差の平均。"""
    diffs = 0
    count = 0
    for y in range(height):
        row = y * width
        for x in range(width - 1):
            i = row + x
            if mask[i] and mask[i + 1]:
                diffs += abs(lum[i] - lum[i + 1])
                count += 1
    for y in range(height - 1):
        row = y * width
        for x in range(width):
            i = row + x
            if mask[i] and mask[i + width]:
                diffs += abs(lum[i] - lum[i + width])
                count += 1
    return diffs / count if count else 0.0


def _is_skin(r: int, g: int, b: int) -> bool:
    """RGB 則（Kovac ら）と YCbCr 則の両方を満たす画素だけを肌とみなす。"""
    mx, mn = max(r, g, b), min(r, g, b)
    if not (r > 95 and g > 40 and b > 20 and mx - mn > 15 and abs(r - g) > 15 and r > g and r > b):
        return False
    cb = 128 - 0.168736 * r - 0.331264 * g + 0.5 * b
    cr = 128 + 0.5 * r - 0.418688 * g - 0.081312 * b
    return 77 <= cb <= 127 and 133 <= cr <= 177


def _largest_region(mask: bytearray, width: int, height: int) -> int:
    """4 近傍の最大連結成分の画素数。幅優先で走査する。"""
    seen = bytearray(len(mask))
    best = 0
    for start in range(len(mask)):
        if not mask[start] or seen[start]:
            continue
        size = 0
        stack = [start]
        seen[start] = 1
        while stack:
            idx = stack.pop()
            size += 1
            x, y = idx % width, idx // width
            if x > 0 and mask[idx - 1] and not seen[idx - 1]:
                seen[idx - 1] = 1
                stack.append(idx - 1)
            if x + 1 < width and mask[idx + 1] and not seen[idx + 1]:
                seen[idx + 1] = 1
                stack.append(idx + 1)
            if y > 0 and mask[idx - width] and not seen[idx - width]:
                seen[idx - width] = 1
                stack.append(idx - width)
            if y + 1 < height and mask[idx + width] and not seen[idx + width]:
                seen[idx + width] = 1
                stack.append(idx + width)
        best = max(best, size)
    return best


def _stddev(values: list[int]) -> float:
    n = len(values)
    if n < 2:
        return 0.0
    mean = sum(values) / n
    var = sum((v - mean) ** 2 for v in values) / n
    return var ** 0.5
