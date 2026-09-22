#!/usr/bin/env python3
"""ページごとのSNSシェアカード（1200x630）を作る。

    pip install pillow
    python3 tools/make_og_cards.py

出力は ``public/og/<name>.jpg``。固定名なので ``/assets/`` には置きません
（あそこは1年 immutable で、作り直しても古い画像が返り続けるため）。
日本語は IPAゴシックで描きます。
"""

from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "public" / "og"
ART = ROOT / "art"
DATA = json.loads((ROOT / "site.json").read_text(encoding="utf-8"))
NAME = DATA["talent"]["name"]

W, H = 1200, 630

FONT_DIRS = [
    Path("/usr/share/fonts/opentype/ipafont-gothic"),
    Path("/usr/share/fonts/truetype/fonts-japanese-gothic.ttf").parent,
]
FONT_FILE = next(
    (d / n for d in FONT_DIRS for n in ("ipagp.ttf", "ipag.ttf") if (d / n).exists()),
    None,
)

CYAN = (112, 242, 247)
PINK = (242, 186, 221)
NIGHT = (5, 9, 28)

# name -> (見出し, そえ書き)
CARDS = {
    "index": (NAME, DATA["talent"]["catch"]),
    "profile": ("プロフィール", f"{NAME}のことを、もう少しだけ"),
    "schedule": ("配信スケジュール", "だいたい夜。だいたい起きています"),
    "guidelines": ("二次創作ガイドライン", "ファンアートと切り抜きについてのお願い"),
    "contact": ("お問い合わせ", "お仕事のご依頼・取材・許諾のご相談"),
}


def font(size: int) -> ImageFont.FreeTypeFont:
    if FONT_FILE is None:
        raise SystemExit(
            "日本語フォントが見つかりません。IPAゴシックを入れてください:\n"
            "  sudo apt-get install fonts-ipafont-gothic"
        )
    return ImageFont.truetype(str(FONT_FILE), size)


def wrap(text: str, per_line: int) -> list[str]:
    """日本語は単語で折れないので、文字数で折り返します。"""
    return [text[i : i + per_line] for i in range(0, len(text), per_line)] or [""]


def backdrop() -> Image.Image:
    """キービジュアルを暗くぼかした背景。文字が確実に読める濃さにします。"""
    kv = Image.open(ART / "keyvisual.png").convert("RGB")
    scale = max(W / kv.width, H / kv.height)
    kv = kv.resize((round(kv.width * scale), round(kv.height * scale)), Image.LANCZOS)
    left = (kv.width - W) // 2
    kv = kv.crop((left, 0, left + W, H)).filter(ImageFilter.GaussianBlur(4))

    # 左から右へ、濃い夜色をかぶせる。右側の立ち絵はうっすら残します。
    veil = Image.new("RGBA", (W, H))
    draw = ImageDraw.Draw(veil)
    for x in range(W):
        a = int(248 - 150 * min(1.0, max(0.0, (x - 430) / 700)))
        draw.line([(x, 0), (x, H)], fill=NIGHT + (a,))
    card = kv.convert("RGBA")
    card.alpha_composite(veil)
    return card.convert("RGB")


BASE = None


def make(name: str, title: str, sub: str) -> None:
    global BASE
    if BASE is None:
        BASE = backdrop()
    card = BASE.copy()
    d = ImageDraw.Draw(card)

    # 上下の細いアクセント
    d.rectangle([(0, 0), (W, 6)], fill=CYAN)
    d.rectangle([(0, H - 6), (W, H)], fill=(253, 84, 247))

    x, y = 72, 128

    # 肩書き
    d.text((x, y), DATA["talent"]["role"], font=font(28), fill=CYAN)
    y += 62

    # 見出し
    size = 92 if len(title) <= 8 else 72
    f = font(size)
    for line in wrap(title, 13 if size == 72 else 10):
        d.text((x, y), line, font=f, fill=(255, 255, 255))
        y += size + 14

    # そえ書き
    y += 14
    fs = font(30)
    for line in wrap(sub, 26):
        d.text((x, y), line, font=fs, fill=PINK)
        y += 46

    # 足もとのサイト名
    d.text((x, H - 78), DATA["site"]["host"].split("//")[-1], font=font(24), fill=(150, 162, 210))

    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f"{name}.jpg"
    card.save(path, "JPEG", quality=86, optimize=True, progressive=True)
    print(f"  og/{name}.jpg  {path.stat().st_size // 1024} KB")


def main() -> int:
    print("シェアカードを作ります")
    for name, (title, sub) in CARDS.items():
        make(name, title, sub)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
