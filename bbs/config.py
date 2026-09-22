"""設定値。すべて環境変数で上書きできる。

方針は既存サイトと同じで、標準ライブラリだけで動くこと。
Pillow は「あれば画像の自動審査と EXIF 除去が働く」任意の依存。
"""

from __future__ import annotations

import os
import pathlib
import secrets

BASE_DIR = pathlib.Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
DATA_DIR = pathlib.Path(os.environ.get("BBS_DATA_DIR") or (BASE_DIR / "data"))
MEDIA_DIR = DATA_DIR / "media"
DB_PATH = pathlib.Path(os.environ.get("BBS_DB_PATH") or (DATA_DIR / "board.db"))

# 開発モード。真のときだけメール確認コードを API 応答に含める（メール送信の代わり）。
DEV_MODE = (os.environ.get("BBS_DEV", "1") or "0").lower() not in ("0", "false", "no")

HOST = os.environ.get("BBS_HOST", "127.0.0.1")
PORT = int(os.environ.get("BBS_PORT", "8787"))

# 投稿
POST_MAX_CHARS = int(os.environ.get("BBS_POST_MAX_CHARS", "600"))
MEDIA_MAX_PER_POST = 4
DM_MAX_CHARS = 2000
BIO_MAX_CHARS = 300
DISPLAY_NAME_MAX_CHARS = 40

# 画像
MEDIA_MAX_BYTES = int(os.environ.get("BBS_MEDIA_MAX_BYTES", str(8 * 1024 * 1024)))
MEDIA_MAX_EDGE = 2048  # これを超える辺は縮小して保存（Pillow がある場合）
ALLOWED_MIME = ("image/jpeg", "image/png", "image/webp", "image/gif")

# R18 自動判定のしきい値。0..1 のスコア。
# 上を超えたら公開拒否、下を超えたら人の確認待ち（公開されない）。
NSFW_BLOCK_SCORE = float(os.environ.get("BBS_NSFW_BLOCK", "0.62"))
NSFW_REVIEW_SCORE = float(os.environ.get("BBS_NSFW_REVIEW", "0.38"))

# 外部の判定器を使う場合のフック（未設定なら内蔵ヒューリスティック）。
# 例: BBS_NSFW_ENDPOINT=http://127.0.0.1:9000/classify
NSFW_ENDPOINT = os.environ.get("BBS_NSFW_ENDPOINT", "").strip()
NSFW_ENDPOINT_TIMEOUT = float(os.environ.get("BBS_NSFW_TIMEOUT", "5"))

# 東大メールとして受け付けるドメイン
UTOKYO_DOMAINS = (
    "u-tokyo.ac.jp",
    "g.ecc.u-tokyo.ac.jp",
    "ecc.u-tokyo.ac.jp",
    "mail.u-tokyo.ac.jp",
)

SESSION_TTL_MS = 30 * 24 * 60 * 60 * 1000
EMAIL_CODE_TTL_MS = 30 * 60 * 1000

# レート制限: 名前 -> (回数, 窓の秒数)
RATE_LIMITS = {
    "register": (5, 3600),
    "login": (12, 900),
    "post": (30, 3600),
    "post_burst": (4, 10),
    "media": (24, 3600),
    "dm": (90, 3600),
    "report": (30, 3600),
    "email_code": (5, 3600),
}


def ensure_dirs() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    MEDIA_DIR.mkdir(parents=True, exist_ok=True)


def secret_key() -> bytes:
    """署名用の鍵。無ければ作る（0600）。環境変数 BBS_SECRET_KEY が優先。"""
    env = os.environ.get("BBS_SECRET_KEY")
    if env:
        return env.encode("utf-8")
    ensure_dirs()
    path = DATA_DIR / "secret.key"
    if not path.exists():
        tmp = path.with_suffix(".tmp")
        tmp.write_text(secrets.token_hex(32), encoding="utf-8")
        os.chmod(tmp, 0o600)
        tmp.replace(path)
    return path.read_text(encoding="utf-8").strip().encode("utf-8")


BOARDS_SEED = (
    ("zenpan", "全般", "東大まわりの雑談と情報交換。迷ったらここ。", 0, 10),
    ("jugyo", "授業・試験", "講義の感想、過去問、試験期の情報。", 0, 20),
    ("shinfuri", "進学選択", "進振りの点数、底点、内定後の話。", 1, 30),
    ("kenkyu", "研究室・院試", "研究室配属、院試、ラボの雰囲気。", 1, 40),
    ("circle", "サークル・部活", "新歓、活動報告、メンバー募集。", 0, 50),
    ("seikatsu", "生活・住まい", "食事、バイト、住まい、キャンパス周辺。", 0, 60),
    ("shukatsu", "就活・進路", "インターン、就活、進路相談。", 0, 70),
    ("ichiba", "売買・譲渡", "教科書や家具の譲渡。取引は当事者の自己責任。", 0, 80),
)
