"""HTTP レイヤ。標準ライブラリの http.server だけで動く。

  python3 -m bbs.server --port 8787

本番に出すなら、前段に TLS 終端とリバースプロキシ（nginx / Caddy）を置くこと。
http.server は素の実装で、そのまま外に晒す前提の作りではない。
"""

from __future__ import annotations

import argparse
import json
import re
import socketserver
import sys
import traceback
import urllib.parse
from http import HTTPStatus
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from . import auth, config, db, models, moderation

MAX_JSON_BODY = 256 * 1024
SESSION_COOKIE = "bbs_session"

_routes: list[tuple[str, re.Pattern, str]] = []


def route(method: str, pattern: str):
    def wrap(func):
        _routes.append((method, re.compile(f"^{pattern}$"), func.__name__))
        return func
    return wrap


class HttpError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status
        self.message = message


class Handler(BaseHTTPRequestHandler):
    server_version = "utbbs"
    sys_version = ""
    protocol_version = "HTTP/1.1"

    # --- 入口 ---------------------------------------------------------------

    def do_GET(self): self._dispatch("GET")
    def do_POST(self): self._dispatch("POST")
    def do_PATCH(self): self._dispatch("PATCH")
    def do_DELETE(self): self._dispatch("DELETE")
    def do_HEAD(self): self._dispatch("GET", head_only=True)

    def _dispatch(self, method: str, head_only: bool = False) -> None:
        self._head_only = head_only
        self._body_read = False
        parsed = urllib.parse.urlparse(self.path)
        self.url_path = urllib.parse.unquote(parsed.path)
        self.query = urllib.parse.parse_qs(parsed.query)
        self.session = None
        try:
            for route_method, pattern, name in _routes:
                if route_method != method:
                    continue
                match = pattern.match(self.url_path)
                if match:
                    self.session = auth.session_for(self._cookie(SESSION_COOKIE))
                    if method != "GET":
                        self._check_csrf()
                    getattr(self, name)(*match.groups())
                    return
            if self.url_path.startswith("/api/"):
                self._json({"error": "そのエンドポイントはありません。"}, 404)
            else:
                self._serve_static("index.html")  # SPA のクライアント側ルーティング
        except models.Error as exc:
            self._fail(exc.message, exc.status)
        except HttpError as exc:
            self._fail(exc.message, exc.status)
        except (BrokenPipeError, ConnectionResetError):
            pass
        except Exception:
            traceback.print_exc()
            self._fail("サーバ側で問題が起きました。", 500)

    def _fail(self, message: str, status: int) -> None:
        """本文を読み切る前に失敗した場合は接続を閉じる（次の要求とずれないように）。"""
        if not self._body_read and int(self.headers.get("Content-Length") or 0) > 0:
            self.close_connection = True
        self._json({"error": message}, status)

    # --- 補助 ---------------------------------------------------------------

    def _cookie(self, name: str) -> str | None:
        raw = self.headers.get("Cookie")
        if not raw:
            return None
        try:
            jar = SimpleCookie(raw)
        except Exception:
            return None
        morsel = jar.get(name)
        return morsel.value if morsel else None

    def _check_csrf(self) -> None:
        """同一オリジンからの操作であることを二重に確かめる。"""
        origin = self.headers.get("Origin")
        if origin:
            host = self.headers.get("Host", "")
            if urllib.parse.urlparse(origin).netloc != host:
                raise HttpError(403, "別サイトからの操作は受け付けません。")
        if self.session is not None:
            token = self.headers.get("X-CSRF-Token", "")
            if token != self.session["csrf"]:
                raise HttpError(403, "画面を再読み込みしてからやり直してください。")

    def _body_bytes(self, limit: int) -> bytes:
        length = int(self.headers.get("Content-Length") or 0)
        if length > limit:
            raise HttpError(413, "送信されたデータが大きすぎます。")
        data = self.rfile.read(length) if length else b""
        self._body_read = True
        return data

    def _json_body(self) -> dict:
        raw = self._body_bytes(MAX_JSON_BODY)
        if not raw:
            return {}
        try:
            data = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise HttpError(400, "JSON を読み取れませんでした。")
        if not isinstance(data, dict):
            raise HttpError(400, "JSON オブジェクトを送ってください。")
        return data

    def _json(self, payload, status: int = 200, extra_headers: dict | None = None) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self._security_headers()
        for key, value in (extra_headers or {}).items():
            self.send_header(key, value)
        self.end_headers()
        if not getattr(self, "_head_only", False):
            self.wfile.write(body)

    def _security_headers(self) -> None:
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "same-origin")
        self.send_header("X-Frame-Options", "DENY")

    def _require_user(self, *, allow_guest: bool = True):
        if self.session is None:
            raise HttpError(401, "ログインが必要です。")
        if self.session["is_guest"] and not allow_guest:
            raise HttpError(403, "この操作にはアカウント登録が必要です。")
        return self.session

    def _require_admin(self):
        user = self._require_user(allow_guest=False)
        if not user["is_admin"]:
            raise HttpError(403, "管理者だけが使えます。")
        return user

    def _client_key(self) -> str:
        forwarded = self.headers.get("X-Forwarded-For", "")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return self.client_address[0]

    def _limit(self, name: str, key: str | None = None) -> None:
        if not auth.rate_limit(name, key or self._client_key()):
            raise HttpError(429, "操作が多すぎます。少し待ってからやり直してください。")

    def _session_cookie(self, token: str) -> dict:
        return {"Set-Cookie": (
            f"{SESSION_COOKIE}={token}; Path=/; HttpOnly; SameSite=Lax; Max-Age="
            f"{config.SESSION_TTL_MS // 1000}"
        )}

    def log_message(self, fmt: str, *args) -> None:  # 1リクエスト1行
        sys.stderr.write("%s - %s\n" % (self._client_key(), fmt % args))

    # --- 静的ファイル -------------------------------------------------------

    def _serve_static(self, relative: str) -> None:
        target = (config.STATIC_DIR / relative).resolve()
        if not str(target).startswith(str(config.STATIC_DIR.resolve())) or not target.is_file():
            self._json({"error": "見つかりません。"}, 404)
            return
        body = target.read_bytes()
        types = {".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8",
                 ".css": "text/css; charset=utf-8", ".svg": "image/svg+xml",
                 ".webmanifest": "application/manifest+json"}
        self.send_response(200)
        self.send_header("Content-Type", types.get(target.suffix, "application/octet-stream"))
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-cache")
        self._security_headers()
        if target.suffix == ".html":
            self.send_header("Content-Security-Policy",
                             "default-src 'self'; img-src 'self' data:; style-src 'self'; "
                             "script-src 'self'; connect-src 'self'; form-action 'none'; "
                             "base-uri 'none'; frame-ancestors 'none'")
        self.end_headers()
        if not getattr(self, "_head_only", False):
            self.wfile.write(body)

    @route("GET", r"/")
    def index(self):
        self._serve_static("index.html")

    @route("GET", r"/static/([A-Za-z0-9_.\-]+)")
    def static_file(self, name):
        self._serve_static(name)

    @route("GET", r"/healthz")
    def healthz(self):
        self._json({"ok": True, "moderation": "pillow" if moderation.PILLOW else "none"})

    # --- アカウント ---------------------------------------------------------

    @route("POST", r"/api/register")
    def register(self):
        self._limit("register")
        data = self._json_body()
        password = str(data.get("password") or "")
        problem = auth.check_password_strength(password)
        if problem:
            raise HttpError(400, problem)
        user = models.create_user(
            str(data.get("handle") or ""), str(data.get("display_name") or ""), password
        )
        token, csrf = auth.create_session(user["id"])
        self._json({"user": models.serialize_user(user, user["id"], full=True), "csrf": csrf},
                   201, self._session_cookie(token))

    @route("POST", r"/api/guest")
    def guest(self):
        """登録せずに匿名で書くための一時アカウント。読み書きは匿名投稿だけ。"""
        self._limit("register")
        user = models.create_guest()
        token, csrf = auth.create_session(user["id"])
        self._json({"user": models.serialize_user(user, user["id"], full=True), "csrf": csrf},
                   201, self._session_cookie(token))

    @route("POST", r"/api/login")
    def login(self):
        data = self._json_body()
        handle = str(data.get("handle") or "").strip()
        self._limit("login", f"{self._client_key()}:{handle.lower()}")
        user = models.get_user_by_handle(handle)
        if user is None or not auth.verify_password(str(data.get("password") or ""), user["password_hash"]):
            raise HttpError(401, "ユーザ名かパスワードが違います。")
        token, csrf = auth.create_session(user["id"])
        self._json({"user": models.serialize_user(user, user["id"], full=True), "csrf": csrf},
                   200, self._session_cookie(token))

    @route("POST", r"/api/logout")
    def logout(self):
        auth.destroy_session(self._cookie(SESSION_COOKIE))
        self._json({"ok": True}, 200,
                   {"Set-Cookie": f"{SESSION_COOKIE}=; Path=/; HttpOnly; SameSite=Lax; Max-Age=0"})

    @route("GET", r"/api/me")
    def me(self):
        if self.session is None:
            self._json({"user": None})
            return
        user = models.get_user(self.session["user_id"])
        self._json({
            "user": models.serialize_user(user, user["id"], full=True),
            "csrf": self.session["csrf"],
            "unread_dm": models.dm_unread_total(user["id"]),
        })

    @route("PATCH", r"/api/me")
    def update_me(self):
        user = self._require_user()
        data = self._json_body()
        updated = models.update_profile(user["id"], data.get("display_name"), data.get("bio"))
        self._json({"user": models.serialize_user(updated, updated["id"], full=True)})

    @route("POST", r"/api/verify/request")
    def verify_request(self):
        """東大メールの確認コードを発行する。

        実際の送信は外部のメール基盤に任せる前提。開発モードでは応答に含める。
        """
        user = self._require_user(allow_guest=False)
        self._limit("email_code", str(user["id"]))
        email = str(self._json_body().get("email") or "")
        domain = auth.email_domain(email)
        if domain is None:
            raise HttpError(400, "メールアドレスの形式が正しくありません。")
        if not auth.is_utokyo_domain(domain):
            raise HttpError(400, "東京大学のメールアドレス（u-tokyo.ac.jp）を入れてください。")
        import secrets as _secrets
        code = f"{_secrets.randbelow(10**6):06d}"
        db.execute(
            "INSERT INTO email_codes (user_id, email_hash, domain, code_hash, expires_at)"
            " VALUES (?,?,?,?,?)",
            (user["id"], auth.hash_email(email), domain, auth.hash_code(code),
             db.now_ms() + config.EMAIL_CODE_TTL_MS),
        )
        payload = {"ok": True, "sent_to_domain": domain}
        if config.DEV_MODE:
            payload["dev_code"] = code
        self._json(payload)

    @route("POST", r"/api/verify/confirm")
    def verify_confirm(self):
        user = self._require_user(allow_guest=False)
        code = str(self._json_body().get("code") or "").strip()
        row = db.query_one(
            "SELECT * FROM email_codes WHERE user_id = ? AND code_hash = ? AND used_at IS NULL"
            " AND expires_at > ? ORDER BY id DESC LIMIT 1",
            (user["id"], auth.hash_code(code), db.now_ms()),
        )
        if row is None:
            raise HttpError(400, "コードが違うか、期限が切れています。")
        now = db.now_ms()
        db.execute("UPDATE email_codes SET used_at = ? WHERE id = ?", (now, row["id"]))
        db.execute("UPDATE users SET verified_at = ?, verified_kind = ? WHERE id = ?",
                   (now, "u-tokyo", user["id"]))
        updated = models.get_user(user["id"])
        self._json({"user": models.serialize_user(updated, updated["id"], full=True)})

    # --- 板とタイムライン ---------------------------------------------------

    @route("GET", r"/api/boards")
    def list_boards(self):
        self._json({"boards": models.boards()})

    @route("GET", r"/api/timeline")
    def get_timeline(self):
        kind = (self.query.get("kind") or ["public"])[0]
        board = (self.query.get("board") or [None])[0]
        cursor = (self.query.get("cursor") or [None])[0]
        limit = int((self.query.get("limit") or ["25"])[0] or 25)
        user_id = None
        if kind == "user":
            handle = (self.query.get("handle") or [""])[0]
            target = models.get_user_by_handle(handle)
            if target is None:
                raise HttpError(404, "ユーザが見つかりません。")
            user_id = target["id"]
        self._json(models.timeline(kind, self.session, board=board, user_id=user_id,
                                   cursor=cursor, limit=limit))

    @route("GET", r"/api/search")
    def get_search(self):
        q = (self.query.get("q") or [""])[0]
        self._json({"items": models.search(q, self.session)})

    # --- 投稿 ---------------------------------------------------------------

    @route("POST", r"/api/posts")
    def create_post(self):
        user = self._require_user()
        self._limit("post_burst", str(user["id"]))
        self._limit("post", str(user["id"]))
        data = self._json_body()
        anonymous = bool(data.get("anonymous", True))
        if user["is_guest"] and not anonymous:
            anonymous = True  # ゲストは匿名のみ
        parent_id = data.get("parent_id")
        media_ids = [str(m) for m in (data.get("media_ids") or [])]
        post = models.create_post(
            user, str(data.get("body") or ""),
            board=(data.get("board") or None),
            anonymous=anonymous,
            parent_id=int(parent_id) if parent_id else None,
            media_ids=media_ids,
        )
        self._json({"post": post}, 201)

    @route("GET", r"/api/posts/(\d+)")
    def get_post(self, post_id):
        self._json(models.thread(int(post_id), self.session))

    @route("DELETE", r"/api/posts/(\d+)")
    def remove_post(self, post_id):
        user = self._require_user()
        models.delete_post(int(post_id), user)
        self._json({"ok": True})

    @route("POST", r"/api/posts/(\d+)/like")
    def like_post(self, post_id):
        user = self._require_user(allow_guest=False)
        on = bool(self._json_body().get("on", True))
        self._json(models.like(user["id"], int(post_id), on))

    @route("POST", r"/api/posts/(\d+)/repost")
    def repost_post(self, post_id):
        user = self._require_user(allow_guest=False)
        on = bool(self._json_body().get("on", True))
        self._json(models.repost(user["id"], int(post_id), on))

    # --- ユーザ -------------------------------------------------------------

    @route("GET", r"/api/users/([A-Za-z0-9_]+)")
    def get_profile(self, handle):
        user = models.get_user_by_handle(handle)
        if user is None:
            raise HttpError(404, "ユーザが見つかりません。")
        viewer_id = self.session["user_id"] if self.session else None
        self._json({"user": models.serialize_user(user, viewer_id, full=True)})

    @route("GET", r"/api/users/([A-Za-z0-9_]+)/follows")
    def get_follows(self, handle):
        user = models.get_user_by_handle(handle)
        if user is None:
            raise HttpError(404, "ユーザが見つかりません。")
        kind = (self.query.get("kind") or ["following"])[0]
        viewer_id = self.session["user_id"] if self.session else None
        self._json({"users": models.follow_list(user["id"], kind, viewer_id)})

    @route("POST", r"/api/users/([A-Za-z0-9_]+)/follow")
    def follow_user(self, handle):
        viewer = self._require_user(allow_guest=False)
        target = models.get_user_by_handle(handle)
        if target is None:
            raise HttpError(404, "ユーザが見つかりません。")
        on = bool(self._json_body().get("on", True))
        if on:
            models.follow(viewer["id"], target["id"])
        else:
            models.unfollow(viewer["id"], target["id"])
        self._json({"user": models.serialize_user(models.get_user(target["id"]), viewer["id"], full=True)})

    # --- 画像 ---------------------------------------------------------------

    @route("POST", r"/api/media")
    def upload_media(self):
        user = self._require_user()
        self._limit("media", str(user["id"]))
        raw = self._body_bytes(config.MEDIA_MAX_BYTES + 1024)
        sha = moderation.sha256(raw)
        blocked = models.hash_blocked(sha)
        if blocked is not None:
            raise HttpError(422, "この画像は過去にブロックされています。")

        verdict = moderation.inspect(raw)
        if verdict.status == moderation.BLOCKED:
            models.block_hash(sha, verdict.reason)
            self._json({"error": verdict.reason, "score": round(verdict.score, 3)}, 422)
            return

        media_id = models.insert_media(user["id"], verdict, sha)
        config.ensure_dirs()
        (config.MEDIA_DIR / media_id).write_bytes(verdict.data)
        self._json({"media": {
            "id": media_id, "status": verdict.status, "mime": verdict.mime,
            "width": verdict.width, "height": verdict.height,
            "reason": verdict.reason, "url": f"/media/{media_id}",
            "score": round(verdict.score, 3),
        }}, 201)

    @route("GET", r"/media/([a-f0-9]{8,64})")
    def serve_media(self, media_id):
        row = models.get_media(media_id)
        if row is None:
            raise HttpError(404, "画像が見つかりません。")
        viewer_id = self.session["user_id"] if self.session else None
        is_admin = bool(self.session and self.session["is_admin"])
        if row["status"] != "approved" and not is_admin and row["uploader_id"] != viewer_id:
            raise HttpError(403, "この画像はまだ公開されていません。")
        path = config.MEDIA_DIR / media_id
        if not path.is_file():
            raise HttpError(404, "画像が見つかりません。")
        body = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", row["mime"])
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Content-Disposition", "inline")
        self.send_header("Cache-Control",
                         "public, max-age=31536000, immutable" if row["status"] == "approved"
                         else "private, no-store")
        self._security_headers()
        self.end_headers()
        if not getattr(self, "_head_only", False):
            self.wfile.write(body)

    # --- DM -----------------------------------------------------------------

    @route("GET", r"/api/dm")
    def list_dm(self):
        user = self._require_user(allow_guest=False)
        self._json({"threads": models.dm_threads(user["id"])})

    @route("GET", r"/api/dm/(\d+)")
    def get_dm(self, thread_id):
        user = self._require_user(allow_guest=False)
        self._json(models.dm_messages(user["id"], int(thread_id)))

    @route("POST", r"/api/dm")
    def send_dm(self):
        user = self._require_user(allow_guest=False)
        self._limit("dm", str(user["id"]))
        data = self._json_body()
        self._json({"message": models.dm_send(user, str(data.get("handle") or ""),
                                              str(data.get("body") or ""))}, 201)

    # --- 通報・管理 ---------------------------------------------------------

    @route("GET", r"/api/report-reasons")
    def report_reasons(self):
        self._json({"reasons": [{"key": k, "label": v} for k, v in models.REPORT_REASONS.items()]})

    @route("POST", r"/api/reports")
    def create_report(self):
        user = self._require_user()
        self._limit("report", str(user["id"]))
        data = self._json_body()
        self._json(models.create_report(
            user["id"], str(data.get("target_type") or "post"), str(data.get("target_id") or ""),
            str(data.get("reason") or ""), str(data.get("note") or "")), 201)

    @route("GET", r"/api/admin/queue")
    def admin_queue(self):
        user = self._require_admin()
        self._json(models.moderation_queue(user))

    @route("POST", r"/api/admin/media/([a-f0-9]{8,64})")
    def admin_media(self, media_id):
        user = self._require_admin()
        status = str(self._json_body().get("status") or "")
        if status not in ("approved", "blocked"):
            raise HttpError(400, "status は approved か blocked。")
        models.set_media_status(media_id, status, user["id"],
                                "管理者が公開を止めました。" if status == "blocked" else "")
        if status == "blocked":
            path = config.MEDIA_DIR / media_id
            if path.is_file():
                path.unlink()
        self._json({"ok": True, "status": status})

    @route("POST", r"/api/admin/reports/(\d+)")
    def admin_report(self, report_id):
        user = self._require_admin()
        resolution = str(self._json_body().get("resolution") or "dismiss")
        models.resolve_report(int(report_id), resolution, user)
        self._json({"ok": True})


class Server(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True


def make_server(host: str = config.HOST, port: int = config.PORT) -> Server:
    config.ensure_dirs()
    db.init()
    auth.purge_expired_sessions()
    return Server((host, port), Handler)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="東大生向け情報交換掲示板のサーバ")
    parser.add_argument("--host", default=config.HOST)
    parser.add_argument("--port", type=int, default=config.PORT)
    parser.add_argument("--make-admin", metavar="HANDLE", help="指定ユーザを管理者にして終了")
    parser.add_argument("--demo", action="store_true", help="動作確認用のデモデータを入れて終了")
    args = parser.parse_args(argv)

    config.ensure_dirs()
    db.init()

    if args.make_admin:
        user = models.get_user_by_handle(args.make_admin)
        if user is None:
            print(f"ユーザ {args.make_admin} がいません。", file=sys.stderr)
            return 1
        db.execute("UPDATE users SET is_admin = 1 WHERE id = ?", (user["id"],))
        print(f"{args.make_admin} を管理者にしました。")
        return 0

    if args.demo:
        from . import seed
        seed.run()
        return 0

    server = Server((args.host, args.port), Handler)
    print(f"http://{args.host}:{args.port}/ で待ち受けます（Ctrl-C で終了）")
    print(f"画像の自動審査: {'Pillow あり' if moderation.PILLOW else 'なし（すべて確認待ちになります）'}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n終了します。")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
