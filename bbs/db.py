"""SQLite への接続とスキーマ初期化。

スレッドごとに 1 接続（ThreadingHTTPServer 用）。WAL で読みと書きを並行させる。
"""

from __future__ import annotations

import sqlite3
import threading
import time
from typing import Any, Iterable, Sequence

from . import config

_local = threading.local()
_init_lock = threading.Lock()
_initialized = False


def now_ms() -> int:
    return int(time.time() * 1000)


def connect() -> sqlite3.Connection:
    conn = getattr(_local, "conn", None)
    if conn is not None:
        return conn
    config.ensure_dirs()
    conn = sqlite3.connect(str(config.DB_PATH), timeout=10, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA busy_timeout=10000")
    conn.execute("PRAGMA synchronous=NORMAL")
    _local.conn = conn
    return conn


def close() -> None:
    conn = getattr(_local, "conn", None)
    if conn is not None:
        conn.close()
        _local.conn = None


def init() -> None:
    """スキーマを作り、板を投入する。何度呼んでも同じ結果。"""
    global _initialized
    with _init_lock:
        conn = connect()
        schema = (config.BASE_DIR / "schema.sql").read_text(encoding="utf-8")
        conn.executescript(schema)
        for slug, name, desc, verified_only, position in config.BOARDS_SEED:
            conn.execute(
                "INSERT INTO boards (slug, name, description, verified_only, position)"
                " VALUES (?,?,?,?,?)"
                " ON CONFLICT(slug) DO UPDATE SET"
                "   name=excluded.name, description=excluded.description,"
                "   verified_only=excluded.verified_only, position=excluded.position",
                (slug, name, desc, verified_only, position),
            )
        _initialized = True


def query(sql: str, params: Sequence[Any] = ()) -> list[sqlite3.Row]:
    return connect().execute(sql, params).fetchall()


def query_one(sql: str, params: Sequence[Any] = ()) -> sqlite3.Row | None:
    return connect().execute(sql, params).fetchone()


def execute(sql: str, params: Sequence[Any] = ()) -> sqlite3.Cursor:
    return connect().execute(sql, params)


def executemany(sql: str, seq: Iterable[Sequence[Any]]) -> sqlite3.Cursor:
    return connect().executemany(sql, seq)


class transaction:
    """with 文で使う明示トランザクション（isolation_level=None のため自前）。"""

    def __enter__(self) -> sqlite3.Connection:
        self.conn = connect()
        self.conn.execute("BEGIN IMMEDIATE")
        return self.conn

    def __exit__(self, exc_type, exc, tb) -> bool:
        if exc_type is None:
            self.conn.execute("COMMIT")
        else:
            self.conn.execute("ROLLBACK")
        return False
