"""認証・セッション・レート制限・匿名 ID。"""

from __future__ import annotations

import hashlib
import hmac
import re
import secrets
import threading
import time
from collections import defaultdict, deque

from . import config, db

HANDLE_RE = re.compile(r"^[A-Za-z0-9_]{3,20}$")
EMAIL_RE = re.compile(r"^[^@\s]+@([A-Za-z0-9.\-]+)$")

_SCRYPT = dict(n=2**14, r=8, p=1, dklen=32)


# --- パスワード -------------------------------------------------------------

def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    dk = hashlib.scrypt(password.encode("utf-8"), salt=salt, **_SCRYPT)
    return f"scrypt${_SCRYPT['n']}${_SCRYPT['r']}${_SCRYPT['p']}${salt.hex()}${dk.hex()}"


def verify_password(password: str, stored: str | None) -> bool:
    if not stored:
        return False
    try:
        scheme, n, r, p, salt_hex, dk_hex = stored.split("$")
        if scheme != "scrypt":
            return False
        dk = hashlib.scrypt(
            password.encode("utf-8"),
            salt=bytes.fromhex(salt_hex),
            n=int(n), r=int(r), p=int(p), dklen=len(dk_hex) // 2,
        )
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(dk.hex(), dk_hex)


def check_password_strength(password: str) -> str | None:
    if len(password) < 8:
        return "パスワードは8文字以上にしてください。"
    if len(password) > 200:
        return "パスワードが長すぎます。"
    if password.lower() in ("password", "12345678", "qwertyui"):
        return "推測されやすいパスワードです。"
    return None


# --- セッション -------------------------------------------------------------

def create_session(user_id: int) -> tuple[str, str]:
    token = secrets.token_urlsafe(32)
    csrf = secrets.token_urlsafe(24)
    now = db.now_ms()
    db.execute(
        "INSERT INTO sessions (token, user_id, csrf, created_at, expires_at) VALUES (?,?,?,?,?)",
        (token, user_id, csrf, now, now + config.SESSION_TTL_MS),
    )
    return token, csrf


def session_for(token: str | None):
    if not token:
        return None
    row = db.query_one(
        "SELECT s.token, s.csrf, s.expires_at, s.user_id, u.* FROM sessions s"
        " JOIN users u ON u.id = s.user_id WHERE s.token = ?",
        (token,),
    )
    if row is None:
        return None
    if row["expires_at"] < db.now_ms():
        db.execute("DELETE FROM sessions WHERE token = ?", (token,))
        return None
    return row


def destroy_session(token: str | None) -> None:
    if token:
        db.execute("DELETE FROM sessions WHERE token = ?", (token,))


def purge_expired_sessions() -> None:
    db.execute("DELETE FROM sessions WHERE expires_at < ?", (db.now_ms(),))


# --- 東大メールの確認 -------------------------------------------------------

def email_domain(email: str) -> str | None:
    m = EMAIL_RE.match(email.strip())
    if not m:
        return None
    return m.group(1).lower()


def is_utokyo_domain(domain: str) -> bool:
    return any(domain == d or domain.endswith("." + d) for d in config.UTOKYO_DOMAINS)


def hash_email(email: str) -> str:
    """生アドレスは保存しない。同一性の判定だけできればよい。"""
    return hmac.new(config.secret_key(), email.strip().lower().encode("utf-8"), "sha256").hexdigest()


def hash_code(code: str) -> str:
    return hmac.new(config.secret_key(), code.encode("utf-8"), "sha256").hexdigest()


# --- 匿名 ID ----------------------------------------------------------------

def anon_id(author_id: int, root_id: int, day: str) -> str:
    """スレッド内・その日限りで安定する匿名 ID。

    同じスレッドでの自演は見分けられるが、スレッドをまたぐ追跡はできない。
    鍵はサーバだけが持つので、外から逆算もできない。
    """
    msg = f"{author_id}:{root_id}:{day}".encode("utf-8")
    return hmac.new(config.secret_key(), msg, "sha256").hexdigest()[:8]


# --- レート制限（プロセス内） -----------------------------------------------

_buckets: dict[tuple[str, str], deque] = defaultdict(deque)
_bucket_lock = threading.Lock()


def rate_limit(name: str, key: str) -> bool:
    """許可するなら True。config.RATE_LIMITS に無い名前は素通し。"""
    limit = config.RATE_LIMITS.get(name)
    if not limit:
        return True
    count, window = limit
    now = time.monotonic()
    with _bucket_lock:
        bucket = _buckets[(name, key)]
        while bucket and now - bucket[0] > window:
            bucket.popleft()
        if len(bucket) >= count:
            return False
        bucket.append(now)
        return True


def reset_rate_limits() -> None:
    with _bucket_lock:
        _buckets.clear()
