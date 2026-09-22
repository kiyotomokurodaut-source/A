"""データ操作。SQL はここに閉じ込め、server.py は HTTP だけを扱う。"""

from __future__ import annotations

import datetime as _dt
import json
import secrets
import sqlite3

from . import auth, config, db

JST = _dt.timezone(_dt.timedelta(hours=9))


class Error(Exception):
    """利用者に見せてよいエラー。status は HTTP ステータス。"""

    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.message = message
        self.status = status


# --- ユーザ -----------------------------------------------------------------

def create_user(handle: str, display_name: str, password: str | None, *, is_guest: bool = False) -> sqlite3.Row:
    handle = handle.strip()
    if not auth.HANDLE_RE.match(handle):
        raise Error("ユーザ名は半角英数字とアンダースコア3〜20文字にしてください。")
    display_name = (display_name or handle).strip()[: config.DISPLAY_NAME_MAX_CHARS]
    password_hash = auth.hash_password(password) if password else None
    now = db.now_ms()
    try:
        cur = db.execute(
            "INSERT INTO users (handle, display_name, password_hash, is_guest, created_at)"
            " VALUES (?,?,?,?,?)",
            (handle, display_name, password_hash, 1 if is_guest else 0, now),
        )
    except sqlite3.IntegrityError:
        raise Error("そのユーザ名は使われています。", 409)
    return get_user(cur.lastrowid)


def get_user(user_id: int | None) -> sqlite3.Row | None:
    if user_id is None:
        return None
    return db.query_one("SELECT * FROM users WHERE id = ?", (user_id,))


def get_user_by_handle(handle: str) -> sqlite3.Row | None:
    return db.query_one("SELECT * FROM users WHERE handle = ? COLLATE NOCASE", (handle,))


def create_guest() -> sqlite3.Row:
    """登録せずに匿名で書き込むための一時アカウント。"""
    for _ in range(5):
        handle = "guest_" + secrets.token_hex(5)
        if get_user_by_handle(handle) is None:
            return create_user(handle, "ゲスト", None, is_guest=True)
    raise Error("ゲストを作成できませんでした。", 500)


def update_profile(user_id: int, display_name: str | None, bio: str | None) -> sqlite3.Row:
    user = get_user(user_id)
    if user is None:
        raise Error("ユーザが見つかりません。", 404)
    name = (display_name if display_name is not None else user["display_name"]).strip()
    if not name:
        raise Error("表示名を入力してください。")
    text = (bio if bio is not None else user["bio"]).strip()
    db.execute(
        "UPDATE users SET display_name = ?, bio = ? WHERE id = ?",
        (name[: config.DISPLAY_NAME_MAX_CHARS], text[: config.BIO_MAX_CHARS], user_id),
    )
    return get_user(user_id)


def user_counts(user_id: int) -> dict:
    row = db.query_one(
        "SELECT"
        " (SELECT COUNT(*) FROM posts WHERE author_id = ? AND deleted_at IS NULL) AS posts,"
        " (SELECT COUNT(*) FROM follows WHERE follower_id = ?) AS following,"
        " (SELECT COUNT(*) FROM follows WHERE followee_id = ?) AS followers",
        (user_id, user_id, user_id),
    )
    return {"posts": row["posts"], "following": row["following"], "followers": row["followers"]}


def serialize_user(user: sqlite3.Row, viewer_id: int | None = None, *, full: bool = False) -> dict:
    data = {
        "id": user["id"],
        "handle": user["handle"],
        "display_name": user["display_name"],
        "verified": bool(user["verified_at"]),
        "is_guest": bool(user["is_guest"]),
        "is_admin": bool(user["is_admin"]),
        "created_at": user["created_at"],
    }
    if full:
        data["bio"] = user["bio"]
        data["counts"] = user_counts(user["id"])
        data["following"] = is_following(viewer_id, user["id"]) if viewer_id else False
        data["followed_by"] = is_following(user["id"], viewer_id) if viewer_id else False
        data["is_self"] = viewer_id == user["id"]
    return data


# --- フォロー ---------------------------------------------------------------

def is_following(follower_id: int | None, followee_id: int | None) -> bool:
    if not follower_id or not followee_id:
        return False
    return db.query_one(
        "SELECT 1 FROM follows WHERE follower_id = ? AND followee_id = ?",
        (follower_id, followee_id),
    ) is not None


def follow(follower_id: int, followee_id: int) -> None:
    if follower_id == followee_id:
        raise Error("自分はフォローできません。")
    if get_user(followee_id) is None:
        raise Error("ユーザが見つかりません。", 404)
    db.execute(
        "INSERT OR IGNORE INTO follows (follower_id, followee_id, created_at) VALUES (?,?,?)",
        (follower_id, followee_id, db.now_ms()),
    )


def unfollow(follower_id: int, followee_id: int) -> None:
    db.execute(
        "DELETE FROM follows WHERE follower_id = ? AND followee_id = ?",
        (follower_id, followee_id),
    )


def follow_list(user_id: int, kind: str, viewer_id: int | None) -> list[dict]:
    if kind == "following":
        sql = ("SELECT u.* FROM follows f JOIN users u ON u.id = f.followee_id"
               " WHERE f.follower_id = ? ORDER BY f.created_at DESC LIMIT 200")
    else:
        sql = ("SELECT u.* FROM follows f JOIN users u ON u.id = f.follower_id"
               " WHERE f.followee_id = ? ORDER BY f.created_at DESC LIMIT 200")
    return [serialize_user(r, viewer_id, full=True) for r in db.query(sql, (user_id,))]


# --- 板 ---------------------------------------------------------------------

def boards() -> list[dict]:
    rows = db.query("SELECT * FROM boards ORDER BY position, slug")
    return [
        {
            "slug": r["slug"],
            "name": r["name"],
            "description": r["description"],
            "verified_only": bool(r["verified_only"]),
            "posts": db.query_one(
                "SELECT COUNT(*) AS c FROM posts WHERE board = ? AND deleted_at IS NULL", (r["slug"],)
            )["c"],
        }
        for r in rows
    ]


def get_board(slug: str) -> sqlite3.Row | None:
    return db.query_one("SELECT * FROM boards WHERE slug = ?", (slug,))


# --- 画像 -------------------------------------------------------------------

def insert_media(uploader_id: int | None, verdict, sha: str) -> str:
    media_id = secrets.token_hex(12)
    db.execute(
        "INSERT INTO media (id, uploader_id, mime, width, height, bytes, sha256, status,"
        " score, reason, details, created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        (media_id, uploader_id, verdict.mime, verdict.width, verdict.height,
         len(verdict.data), sha, verdict.status, verdict.score, verdict.reason,
         json.dumps(verdict.details, ensure_ascii=False), db.now_ms()),
    )
    return media_id


def get_media(media_id: str) -> sqlite3.Row | None:
    return db.query_one("SELECT * FROM media WHERE id = ?", (media_id,))


def hash_blocked(sha: str) -> sqlite3.Row | None:
    return db.query_one("SELECT * FROM blocked_hashes WHERE sha256 = ?", (sha,))


def block_hash(sha: str, reason: str) -> None:
    db.execute(
        "INSERT OR IGNORE INTO blocked_hashes (sha256, reason, created_at) VALUES (?,?,?)",
        (sha, reason, db.now_ms()),
    )


def set_media_status(media_id: str, status: str, reviewer_id: int, reason: str = "") -> None:
    media = get_media(media_id)
    if media is None:
        raise Error("画像が見つかりません。", 404)
    db.execute(
        "UPDATE media SET status = ?, reason = ?, reviewed_by = ?, reviewed_at = ? WHERE id = ?",
        (status, reason or media["reason"], reviewer_id, db.now_ms(), media_id),
    )
    if status == "blocked":
        block_hash(media["sha256"], reason or "管理者がブロック")


def serialize_media(row: sqlite3.Row, viewer_id: int | None, is_admin: bool = False) -> dict:
    visible = row["status"] == "approved" or is_admin or (viewer_id and row["uploader_id"] == viewer_id)
    return {
        "id": row["id"],
        "status": row["status"],
        "mime": row["mime"],
        "width": row["width"],
        "height": row["height"],
        "reason": row["reason"],
        "url": f"/media/{row['id']}" if visible else None,
    }


# --- 投稿 -------------------------------------------------------------------

def create_post(author: sqlite3.Row, body: str, *, board: str | None, anonymous: bool,
                parent_id: int | None, media_ids: list[str]) -> dict:
    body = (body or "").strip()
    if len(body) > config.POST_MAX_CHARS:
        raise Error(f"本文は{config.POST_MAX_CHARS}文字までです。")
    if not body and not media_ids:
        raise Error("本文か画像のどちらかは必要です。")
    if len(media_ids) > config.MEDIA_MAX_PER_POST:
        raise Error(f"画像は{config.MEDIA_MAX_PER_POST}枚までです。")

    parent = None
    if parent_id is not None:
        parent = get_post_row(parent_id)
        if parent is None or parent["deleted_at"]:
            raise Error("返信先の投稿が見つかりません。", 404)
        board = parent["board"]

    if board is not None:
        board_row = get_board(board)
        if board_row is None:
            raise Error("その板はありません。", 404)
        if board_row["verified_only"] and not author["verified_at"]:
            raise Error(f"「{board_row['name']}」は東大メールの確認が済んだ人だけが書けます。", 403)
    elif parent is None:
        board = "zenpan"

    attachments = []
    for media_id in media_ids:
        media = get_media(media_id)
        if media is None:
            raise Error("画像が見つかりません。", 404)
        if media["uploader_id"] != author["id"]:
            raise Error("他の人がアップロードした画像は使えません。", 403)
        if media["status"] == "blocked":
            raise Error("その画像は公開できません。", 403)
        attachments.append(media_id)

    now = db.now_ms()
    with db.transaction() as conn:
        cur = conn.execute(
            "INSERT INTO posts (author_id, board, body, anonymous, parent_id, root_id, created_at)"
            " VALUES (?,?,?,?,?,?,?)",
            (author["id"], board, body, 1 if anonymous else 0, parent_id,
             parent["root_id"] if parent else None, now),
        )
        post_id = cur.lastrowid
        if parent is None:
            conn.execute("UPDATE posts SET root_id = ? WHERE id = ?", (post_id, post_id))
        for position, media_id in enumerate(attachments):
            conn.execute(
                "INSERT INTO post_media (post_id, media_id, position) VALUES (?,?,?)",
                (post_id, media_id, position),
            )
    return serialize_post(get_post_row(post_id), author["id"], is_admin=bool(author["is_admin"]))


def get_post_row(post_id: int) -> sqlite3.Row | None:
    return db.query_one("SELECT * FROM posts WHERE id = ?", (post_id,))


def delete_post(post_id: int, actor: sqlite3.Row) -> None:
    post = get_post_row(post_id)
    if post is None or post["deleted_at"]:
        raise Error("投稿が見つかりません。", 404)
    if post["author_id"] != actor["id"] and not actor["is_admin"]:
        raise Error("自分の投稿だけ削除できます。", 403)
    db.execute(
        "UPDATE posts SET deleted_at = ?, deleted_by = ? WHERE id = ?",
        (db.now_ms(), "author" if post["author_id"] == actor["id"] else "moderator", post_id),
    )


def like(user_id: int, post_id: int, on: bool) -> dict:
    if get_post_row(post_id) is None:
        raise Error("投稿が見つかりません。", 404)
    if on:
        db.execute("INSERT OR IGNORE INTO likes (user_id, post_id, created_at) VALUES (?,?,?)",
                   (user_id, post_id, db.now_ms()))
    else:
        db.execute("DELETE FROM likes WHERE user_id = ? AND post_id = ?", (user_id, post_id))
    count = db.query_one("SELECT COUNT(*) AS c FROM likes WHERE post_id = ?", (post_id,))["c"]
    return {"post_id": post_id, "likes": count, "liked": on}


def repost(user_id: int, post_id: int, on: bool) -> dict:
    post = get_post_row(post_id)
    if post is None or post["deleted_at"]:
        raise Error("投稿が見つかりません。", 404)
    if on:
        db.execute("INSERT OR IGNORE INTO reposts (user_id, post_id, created_at) VALUES (?,?,?)",
                   (user_id, post_id, db.now_ms()))
    else:
        db.execute("DELETE FROM reposts WHERE user_id = ? AND post_id = ?", (user_id, post_id))
    count = db.query_one("SELECT COUNT(*) AS c FROM reposts WHERE post_id = ?", (post_id,))["c"]
    return {"post_id": post_id, "reposts": count, "reposted": on}


def serialize_post(post: sqlite3.Row, viewer_id: int | None, *, is_admin: bool = False,
                   reposted_by: sqlite3.Row | None = None) -> dict:
    counts = db.query_one(
        "SELECT (SELECT COUNT(*) FROM likes WHERE post_id = p.id) AS likes,"
        " (SELECT COUNT(*) FROM reposts WHERE post_id = p.id) AS reposts,"
        " (SELECT COUNT(*) FROM posts c WHERE c.parent_id = p.id AND c.deleted_at IS NULL) AS replies"
        " FROM posts p WHERE p.id = ?",
        (post["id"],),
    )
    deleted = post["deleted_at"] is not None
    author = get_user(post["author_id"])
    data = {
        "id": post["id"],
        "board": post["board"],
        "created_at": post["created_at"],
        "parent_id": post["parent_id"],
        "root_id": post["root_id"],
        "anonymous": bool(post["anonymous"]),
        "deleted": deleted,
        "body": "" if deleted else post["body"],
        "counts": {"likes": counts["likes"], "reposts": counts["reposts"], "replies": counts["replies"]},
        "viewer": {
            "liked": _has(viewer_id, "likes", post["id"]),
            "reposted": _has(viewer_id, "reposts", post["id"]),
            "can_delete": bool(viewer_id and (viewer_id == post["author_id"] or is_admin)),
            "is_author": bool(viewer_id and viewer_id == post["author_id"]),
        },
        "media": [],
        "author": _post_author(post, author, viewer_id, is_admin),
    }
    if reposted_by is not None:
        data["reposted_by"] = {"handle": reposted_by["handle"], "display_name": reposted_by["display_name"]}
    if not deleted:
        rows = db.query(
            "SELECT m.* FROM post_media pm JOIN media m ON m.id = pm.media_id"
            " WHERE pm.post_id = ? ORDER BY pm.position",
            (post["id"],),
        )
        data["media"] = [serialize_media(r, viewer_id, is_admin) for r in rows]
    return data


def _post_author(post: sqlite3.Row, author: sqlite3.Row | None, viewer_id: int | None,
                 is_admin: bool) -> dict:
    """匿名投稿では作者を出さない。同じスレッド・同じ日だけ安定する ID を添える。"""
    if author is None:
        return {"display_name": "退会済み", "handle": None, "verified": False, "anon": True}
    if not post["anonymous"]:
        return {
            "id": author["id"],
            "handle": author["handle"],
            "display_name": author["display_name"],
            "verified": bool(author["verified_at"]),
            "anon": False,
        }
    day = _dt.datetime.fromtimestamp(post["created_at"] / 1000, JST).strftime("%Y-%m-%d")
    return {
        "id": None,
        "handle": None,
        "display_name": "匿名",
        "verified": bool(author["verified_at"]),
        "anon": True,
        "anon_id": auth.anon_id(author["id"], post["root_id"] or post["id"], day),
        "is_you": bool(viewer_id and viewer_id == author["id"]),
    }


def _has(viewer_id: int | None, table: str, post_id: int) -> bool:
    if not viewer_id:
        return False
    return db.query_one(
        f"SELECT 1 FROM {table} WHERE user_id = ? AND post_id = ?", (viewer_id, post_id)
    ) is not None


# --- タイムライン -----------------------------------------------------------

def _decode_cursor(cursor: str | None) -> tuple[int, int] | None:
    if not cursor:
        return None
    try:
        at, pid = cursor.split(".")
        return int(at), int(pid)
    except (ValueError, AttributeError):
        return None


def _encode_cursor(sort_at: int, post_id: int) -> str:
    return f"{sort_at}.{post_id}"


def timeline(kind: str, viewer: sqlite3.Row | None, *, board: str | None = None,
             user_id: int | None = None, cursor: str | None = None, limit: int = 25) -> dict:
    limit = max(1, min(limit, 50))
    cur = _decode_cursor(cursor)
    viewer_id = viewer["id"] if viewer is not None else None
    is_admin = bool(viewer is not None and viewer["is_admin"])
    params: list = []
    where = ["p.deleted_at IS NULL"]

    if kind == "home":
        if viewer_id is None:
            raise Error("ログインが必要です。", 401)
        # フォロー中の人の投稿・リポストと、自分の投稿。
        sql = (
            "SELECT p.id AS post_id, p.created_at AS sort_at, NULL AS reposter_id FROM posts p"
            " WHERE p.deleted_at IS NULL AND p.parent_id IS NULL AND p.anonymous = 0"
            "   AND (p.author_id = ? OR p.author_id IN (SELECT followee_id FROM follows WHERE follower_id = ?))"
            " UNION ALL "
            "SELECT r.post_id, r.created_at, r.user_id FROM reposts r JOIN posts p ON p.id = r.post_id"
            " WHERE p.deleted_at IS NULL AND p.anonymous = 0"
            "   AND (r.user_id = ? OR r.user_id IN (SELECT followee_id FROM follows WHERE follower_id = ?))"
            " UNION ALL "
            "SELECT p.id, p.created_at, NULL FROM posts p"
            " WHERE p.deleted_at IS NULL AND p.parent_id IS NULL AND p.anonymous = 1 AND p.author_id = ?"
        )
        params = [viewer_id, viewer_id, viewer_id, viewer_id, viewer_id]
        inner = f"SELECT * FROM ({sql})"
    else:
        if kind == "board":
            where.append("p.board = ?")
            params.append(board)
            where.append("p.parent_id IS NULL")
        elif kind == "user":
            where.append("p.author_id = ?")
            params.append(user_id)
            # 他人のプロフィールでは匿名投稿を出さない（匿名の意味が無くなる）。
            if viewer_id != user_id:
                where.append("p.anonymous = 0")
        elif kind == "public":
            where.append("p.parent_id IS NULL")
        else:
            raise Error("不明なタイムラインです。", 404)
        inner = (
            "SELECT p.id AS post_id, p.created_at AS sort_at, NULL AS reposter_id"
            f" FROM posts p WHERE {' AND '.join(where)}"
        )

    sql = f"SELECT * FROM ({inner})"
    if cur:
        sql += " WHERE (sort_at < ? OR (sort_at = ? AND post_id < ?))"
        params += [cur[0], cur[0], cur[1]]
    sql += " ORDER BY sort_at DESC, post_id DESC LIMIT ?"
    params.append(limit + 1)

    rows = db.query(sql, params)
    has_more = len(rows) > limit
    rows = rows[:limit]
    items = []
    for row in rows:
        post = get_post_row(row["post_id"])
        if post is None:
            continue
        items.append(serialize_post(
            post, viewer_id, is_admin=is_admin,
            reposted_by=get_user(row["reposter_id"]) if row["reposter_id"] else None,
        ))
    return {
        "items": items,
        "next_cursor": _encode_cursor(rows[-1]["sort_at"], rows[-1]["post_id"]) if rows and has_more else None,
    }


def thread(post_id: int, viewer: sqlite3.Row | None) -> dict:
    root = get_post_row(post_id)
    if root is None:
        raise Error("投稿が見つかりません。", 404)
    viewer_id = viewer["id"] if viewer is not None else None
    is_admin = bool(viewer is not None and viewer["is_admin"])

    ancestors = []
    node = root
    while node["parent_id"]:
        node = get_post_row(node["parent_id"])
        if node is None:
            break
        ancestors.append(serialize_post(node, viewer_id, is_admin=is_admin))
    ancestors.reverse()

    replies = [
        serialize_post(r, viewer_id, is_admin=is_admin)
        for r in db.query(
            "SELECT * FROM posts WHERE parent_id = ? ORDER BY created_at, id LIMIT 200", (post_id,)
        )
        if r["deleted_at"] is None
    ]
    return {
        "ancestors": ancestors,
        "post": serialize_post(root, viewer_id, is_admin=is_admin),
        "replies": replies,
    }


def search(q: str, viewer: sqlite3.Row | None, limit: int = 30) -> list[dict]:
    q = (q or "").strip()
    if len(q) < 2:
        raise Error("検索語は2文字以上で。")
    viewer_id = viewer["id"] if viewer is not None else None
    escaped = q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    rows = db.query(
        "SELECT * FROM posts WHERE deleted_at IS NULL AND body LIKE ? ESCAPE '\\'"
        " ORDER BY created_at DESC LIMIT ?",
        ("%" + escaped + "%", limit),
    )
    return [serialize_post(r, viewer_id, is_admin=bool(viewer and viewer["is_admin"])) for r in rows]


# --- DM ---------------------------------------------------------------------

def dm_thread_for(user_a: int, user_b: int, *, create: bool = True) -> sqlite3.Row | None:
    lo, hi = sorted((user_a, user_b))
    row = db.query_one("SELECT * FROM dm_threads WHERE user_lo = ? AND user_hi = ?", (lo, hi))
    if row is not None or not create:
        return row
    now = db.now_ms()
    cur = db.execute(
        "INSERT INTO dm_threads (user_lo, user_hi, created_at, updated_at) VALUES (?,?,?,?)",
        (lo, hi, now, now),
    )
    return db.query_one("SELECT * FROM dm_threads WHERE id = ?", (cur.lastrowid,))


def dm_send(sender: sqlite3.Row, target_handle: str, body: str) -> dict:
    body = (body or "").strip()
    if not body:
        raise Error("本文を入力してください。")
    if len(body) > config.DM_MAX_CHARS:
        raise Error(f"DM は{config.DM_MAX_CHARS}文字までです。")
    if sender["is_guest"]:
        raise Error("DM を使うにはアカウント登録が必要です。", 403)
    target = get_user_by_handle(target_handle)
    if target is None:
        raise Error("相手が見つかりません。", 404)
    if target["id"] == sender["id"]:
        raise Error("自分には送れません。")
    if target["is_guest"]:
        raise Error("ゲストのアカウントには DM を送れません。", 403)
    # 受け取る側がフォローしていない相手からの DM も届くが、
    # 未フォローの相手には「リクエスト」として区別できるよう情報を持たせる。
    thread_row = dm_thread_for(sender["id"], target["id"])
    now = db.now_ms()
    cur = db.execute(
        "INSERT INTO dm_messages (thread_id, sender_id, body, created_at) VALUES (?,?,?,?)",
        (thread_row["id"], sender["id"], body, now),
    )
    db.execute("UPDATE dm_threads SET updated_at = ? WHERE id = ?", (now, thread_row["id"]))
    return {
        "id": cur.lastrowid,
        "thread_id": thread_row["id"],
        "sender": serialize_user(sender),
        "body": body,
        "created_at": now,
        "mine": True,
    }


def dm_threads(user_id: int) -> list[dict]:
    rows = db.query(
        "SELECT * FROM dm_threads WHERE user_lo = ? OR user_hi = ? ORDER BY updated_at DESC LIMIT 100",
        (user_id, user_id),
    )
    out = []
    for row in rows:
        other_id = row["user_hi"] if row["user_lo"] == user_id else row["user_lo"]
        other = get_user(other_id)
        last = db.query_one(
            "SELECT * FROM dm_messages WHERE thread_id = ? ORDER BY id DESC LIMIT 1", (row["id"],)
        )
        if last is None:
            continue
        unread = db.query_one(
            "SELECT COUNT(*) AS c FROM dm_messages WHERE thread_id = ? AND sender_id != ? AND read_at IS NULL",
            (row["id"], user_id),
        )["c"]
        out.append({
            "id": row["id"],
            "user": serialize_user(other) if other else {"display_name": "退会済み", "handle": None},
            "last_message": {"body": last["body"], "created_at": last["created_at"],
                             "mine": last["sender_id"] == user_id},
            "unread": unread,
            "updated_at": row["updated_at"],
            "request": not is_following(user_id, other_id),
        })
    return out


def dm_messages(user_id: int, thread_id: int, *, mark_read: bool = True) -> dict:
    row = db.query_one("SELECT * FROM dm_threads WHERE id = ?", (thread_id,))
    if row is None or user_id not in (row["user_lo"], row["user_hi"]):
        raise Error("その会話は見られません。", 404)
    other = get_user(row["user_hi"] if row["user_lo"] == user_id else row["user_lo"])
    messages = db.query(
        "SELECT * FROM dm_messages WHERE thread_id = ? ORDER BY id LIMIT 500", (thread_id,)
    )
    if mark_read:
        db.execute(
            "UPDATE dm_messages SET read_at = ? WHERE thread_id = ? AND sender_id != ? AND read_at IS NULL",
            (db.now_ms(), thread_id, user_id),
        )
    return {
        "id": thread_id,
        "user": serialize_user(other) if other else {"display_name": "退会済み", "handle": None},
        "messages": [
            {"id": m["id"], "body": m["body"], "created_at": m["created_at"],
             "mine": m["sender_id"] == user_id}
            for m in messages
        ],
    }


def dm_unread_total(user_id: int) -> int:
    return db.query_one(
        "SELECT COUNT(*) AS c FROM dm_messages m JOIN dm_threads t ON t.id = m.thread_id"
        " WHERE (t.user_lo = ? OR t.user_hi = ?) AND m.sender_id != ? AND m.read_at IS NULL",
        (user_id, user_id, user_id),
    )["c"]


# --- 通報とモデレーション ---------------------------------------------------

REPORT_REASONS = {
    "r18": "性的な画像・R18",
    "harassment": "誹謗中傷・晒し",
    "personal_info": "個人情報",
    "spam": "スパム・宣伝",
    "illegal": "違法・危険",
    "other": "その他",
}


def create_report(reporter_id: int | None, target_type: str, target_id: str, reason: str, note: str) -> dict:
    if target_type not in ("post", "media", "user"):
        raise Error("通報の対象が不正です。")
    if reason not in REPORT_REASONS:
        raise Error("理由を選んでください。")
    if target_type == "post" and get_post_row(int(target_id)) is None:
        raise Error("投稿が見つかりません。", 404)
    cur = db.execute(
        "INSERT INTO reports (reporter_id, target_type, target_id, reason, note, created_at)"
        " VALUES (?,?,?,?,?,?)",
        (reporter_id, target_type, str(target_id), reason, (note or "")[:500], db.now_ms()),
    )
    return {"id": cur.lastrowid, "ok": True}


def moderation_queue(viewer: sqlite3.Row) -> dict:
    media = [
        {**serialize_media(r, viewer["id"], True),
         "score": r["score"], "details": json.loads(r["details"] or "{}"),
         "created_at": r["created_at"],
         "uploader": serialize_user(get_user(r["uploader_id"])) if r["uploader_id"] else None}
        for r in db.query(
            "SELECT * FROM media WHERE status = 'pending' ORDER BY created_at LIMIT 100")
    ]
    reports = []
    for r in db.query("SELECT * FROM reports WHERE resolved_at IS NULL ORDER BY created_at DESC LIMIT 100"):
        item = {
            "id": r["id"], "target_type": r["target_type"], "target_id": r["target_id"],
            "reason": r["reason"], "reason_label": REPORT_REASONS.get(r["reason"], r["reason"]),
            "note": r["note"], "created_at": r["created_at"], "post": None,
        }
        if r["target_type"] == "post":
            post = get_post_row(int(r["target_id"])) if str(r["target_id"]).isdigit() else None
            if post is not None:
                item["post"] = serialize_post(post, viewer["id"], is_admin=True)
        reports.append(item)
    return {"media": media, "reports": reports}


def resolve_report(report_id: int, resolution: str, viewer: sqlite3.Row) -> None:
    row = db.query_one("SELECT * FROM reports WHERE id = ?", (report_id,))
    if row is None:
        raise Error("通報が見つかりません。", 404)
    if resolution == "delete_post" and row["target_type"] == "post":
        delete_post(int(row["target_id"]), viewer)
    db.execute(
        "UPDATE reports SET resolved_at = ?, resolution = ? WHERE id = ?",
        (db.now_ms(), resolution, report_id),
    )
