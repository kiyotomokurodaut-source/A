"""API の結合テスト。実際にサーバを立てて HTTP で叩く。

  python3 -m unittest discover -s bbs/tests -t .
"""

from __future__ import annotations

import http.client
import io
import json
import os
import pathlib
import random
import shutil
import sys
import tempfile
import threading
import urllib.parse
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

_TMP = tempfile.mkdtemp(prefix="bbs-test-")
os.environ["BBS_DATA_DIR"] = _TMP
os.environ["BBS_SECRET_KEY"] = "test-secret-key"
os.environ["BBS_DEV"] = "1"

from bbs import auth, config, db, models, moderation, server  # noqa: E402

try:
    from PIL import Image, ImageDraw
    HAVE_PILLOW = True
except Exception:
    HAVE_PILLOW = False


class Client:
    """クッキーと CSRF トークンを覚える小さな HTTP クライアント。"""

    def __init__(self, port: int, reset_limits: bool = True):
        self.port = port
        self.cookie: str | None = None
        self.csrf: str | None = None
        self.reset_limits = reset_limits

    def request(self, method: str, path: str, body=None, *, raw: bytes | None = None,
                content_type: str = "application/json"):
        if self.reset_limits:
            auth.reset_rate_limits()
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=15)
        headers = {"Host": f"127.0.0.1:{self.port}"}
        payload = raw
        if raw is None and body is not None:
            payload = json.dumps(body).encode("utf-8")
        if payload is not None:
            headers["Content-Type"] = content_type
            headers["Content-Length"] = str(len(payload))
        if self.cookie:
            headers["Cookie"] = self.cookie
        if self.csrf:
            headers["X-CSRF-Token"] = self.csrf
        conn.request(method, path, body=payload, headers=headers)
        resp = conn.getresponse()
        data = resp.read()
        set_cookie = resp.getheader("Set-Cookie")
        if set_cookie:
            value = set_cookie.split(";")[0]
            self.cookie = None if value.endswith("=") else value
        status = resp.status
        conn.close()
        if resp.getheader("Content-Type", "").startswith("application/json"):
            parsed = json.loads(data.decode("utf-8")) if data else {}
            if isinstance(parsed, dict) and "csrf" in parsed:
                self.csrf = parsed["csrf"]
            return status, parsed, data
        return status, None, data

    def get(self, path): return self.request("GET", path)
    def post(self, path, body=None): return self.request("POST", path, body)
    def patch(self, path, body=None): return self.request("PATCH", path, body)
    def delete(self, path): return self.request("DELETE", path)

    def register(self, handle, password="testpass123"):
        status, data, _ = self.post("/api/register",
                                    {"handle": handle, "display_name": handle, "password": password})
        assert status == 201, data
        return data["user"]


def make_image(kind: str) -> bytes:
    """テスト用の画像。kind に応じて審査結果が変わるように作る。

    同じ画像を2回作らない（ハッシュのブロックリストがテスト間で干渉するため）。
    """
    random.seed(random.randint(0, 2**30))
    if kind == "landscape":
        img = Image.new("RGB", (320, 240))
        d = ImageDraw.Draw(img)
        for y in range(240):
            d.line([(0, y), (320, y)], fill=(50 + y // 6, 110 + y // 5, 190 - y // 3))
        d.rectangle([0, 180, 320, 240], fill=(40, 110, 50))
    elif kind == "skin":
        img = Image.new("RGB", (320, 320), (28, 28, 38))
        d = ImageDraw.Draw(img)
        d.ellipse([60, 15, 260, 305], fill=(224, 172, 140))
        d.ellipse([30, 120, 95, 265], fill=(219, 167, 135))
    else:
        raise ValueError(kind)
    px = img.load()
    for y in range(img.height):
        for x in range(img.width):
            r, g, b = px[x, y]
            n = random.randint(-14, 14)
            px[x, y] = (max(0, min(255, r + n)), max(0, min(255, g + n)), max(0, min(255, b + n)))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=92)
    return buf.getvalue()


class ApiTest(unittest.TestCase):
    httpd = None

    @classmethod
    def setUpClass(cls):
        cls.httpd = server.make_server("127.0.0.1", 0)
        cls.port = cls.httpd.server_address[1]
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()
        db.close()
        shutil.rmtree(_TMP, ignore_errors=True)

    def setUp(self):
        auth.reset_rate_limits()
        self.c = Client(self.port)

    def uniq(self, base: str) -> str:
        return f"{base}{random.randint(100000, 999999)}"

    # --- アカウント -------------------------------------------------------

    def test_register_login_logout(self):
        handle = self.uniq("taro")
        user = self.c.register(handle)
        self.assertEqual(user["handle"], handle)

        status, data, _ = self.c.get("/api/me")
        self.assertEqual(data["user"]["handle"], handle)

        self.c.post("/api/logout")
        status, data, _ = self.c.get("/api/me")
        self.assertIsNone(data["user"])

        status, data, _ = self.c.post("/api/login", {"handle": handle, "password": "testpass123"})
        self.assertEqual(status, 200)
        status, data, _ = self.c.post("/api/login", {"handle": handle, "password": "wrong-pass"})
        self.assertEqual(status, 401)

    def test_weak_password_and_duplicate_handle(self):
        handle = self.uniq("dup")
        status, data, _ = self.c.post("/api/register",
                                      {"handle": handle, "display_name": "x", "password": "short"})
        self.assertEqual(status, 400)
        self.c.register(handle)
        other = Client(self.port)
        status, data, _ = other.post("/api/register",
                                     {"handle": handle, "display_name": "x", "password": "testpass123"})
        self.assertEqual(status, 409)

    def test_csrf_required_for_writes(self):
        self.c.register(self.uniq("csrf"))
        saved, self.c.csrf = self.c.csrf, "bogus"
        status, data, _ = self.c.post("/api/posts", {"body": "だめなはず"})
        self.assertEqual(status, 403)
        self.c.csrf = saved

    def test_utokyo_verification(self):
        self.c.register(self.uniq("verify"))
        status, data, _ = self.c.post("/api/verify/request", {"email": "someone@example.com"})
        self.assertEqual(status, 400)
        status, data, _ = self.c.post("/api/verify/request", {"email": "someone@g.ecc.u-tokyo.ac.jp"})
        self.assertEqual(status, 200)
        code = data["dev_code"]
        status, data, _ = self.c.post("/api/verify/confirm", {"code": "000000" if code != "000000" else "111111"})
        self.assertEqual(status, 400)
        status, data, _ = self.c.post("/api/verify/confirm", {"code": code})
        self.assertEqual(status, 200)
        self.assertTrue(data["user"]["verified"])

    def test_verified_only_board(self):
        self.c.register(self.uniq("board"))
        status, data, _ = self.c.post("/api/posts", {"body": "進振りの話", "board": "shinfuri"})
        self.assertEqual(status, 403)
        status, data, _ = self.c.post("/api/verify/request", {"email": "x@u-tokyo.ac.jp"})
        self.c.post("/api/verify/confirm", {"code": data["dev_code"]})
        status, data, _ = self.c.post("/api/posts", {"body": "進振りの話", "board": "shinfuri"})
        self.assertEqual(status, 201)

    # --- 投稿 -------------------------------------------------------------

    def test_anonymous_post_hides_author(self):
        handle = self.uniq("anon")
        self.c.register(handle)
        status, data, _ = self.c.post("/api/posts", {"body": "匿名で書く", "anonymous": True})
        self.assertEqual(status, 201)
        post = data["post"]
        self.assertTrue(post["anonymous"])
        self.assertIsNone(post["author"]["handle"])
        self.assertEqual(post["author"]["display_name"], "匿名")
        self.assertRegex(post["author"]["anon_id"], r"^[0-9a-f]{8}$")

        # 他人から見ても作者が漏れないこと
        viewer = Client(self.port)
        status, thread, _ = viewer.get(f"/api/posts/{post['id']}")
        self.assertIsNone(thread["post"]["author"]["handle"])
        self.assertIsNone(thread["post"]["author"]["id"])
        self.assertNotIn(handle, json.dumps(thread, ensure_ascii=False))

    def test_anon_id_is_stable_per_thread_and_differs_across_threads(self):
        self.c.register(self.uniq("anonid"))
        _, a, _ = self.c.post("/api/posts", {"body": "スレ1", "anonymous": True})
        _, b, _ = self.c.post("/api/posts", {"body": "スレ2", "anonymous": True})
        _, reply, _ = self.c.post("/api/posts",
                                  {"body": "自分で返信", "anonymous": True, "parent_id": a["post"]["id"]})
        self.assertEqual(a["post"]["author"]["anon_id"], reply["post"]["author"]["anon_id"])
        self.assertNotEqual(a["post"]["author"]["anon_id"], b["post"]["author"]["anon_id"])

    def test_named_post_and_delete(self):
        handle = self.uniq("named")
        self.c.register(handle)
        _, data, _ = self.c.post("/api/posts", {"body": "実名で書く", "anonymous": False})
        post = data["post"]
        self.assertEqual(post["author"]["handle"], handle)

        stranger = Client(self.port)
        stranger.register(self.uniq("stranger"))
        status, _, _ = stranger.delete(f"/api/posts/{post['id']}")
        self.assertEqual(status, 403)

        status, _, _ = self.c.delete(f"/api/posts/{post['id']}")
        self.assertEqual(status, 200)
        _, thread, _ = self.c.get(f"/api/posts/{post['id']}")
        self.assertTrue(thread["post"]["deleted"])
        self.assertEqual(thread["post"]["body"], "")

    def test_post_requires_content_and_respects_length(self):
        self.c.register(self.uniq("len"))
        status, _, _ = self.c.post("/api/posts", {"body": "   "})
        self.assertEqual(status, 400)
        status, _, _ = self.c.post("/api/posts", {"body": "あ" * (config.POST_MAX_CHARS + 1)})
        self.assertEqual(status, 400)

    def test_guest_can_post_anonymously_only(self):
        status, data, _ = self.c.post("/api/guest")
        self.assertEqual(status, 201)
        self.assertTrue(data["user"]["is_guest"])
        status, data, _ = self.c.post("/api/posts", {"body": "ゲストの書き込み", "anonymous": False})
        self.assertEqual(status, 201)
        self.assertTrue(data["post"]["anonymous"])  # 実名にはできない
        status, _, _ = self.c.post("/api/dm", {"handle": "someone", "body": "こんにちは"})
        self.assertEqual(status, 403)

    def test_like_and_repost_counts(self):
        author = Client(self.port)
        author.register(self.uniq("author"))
        _, data, _ = author.post("/api/posts", {"body": "いいねされる投稿", "anonymous": False})
        post_id = data["post"]["id"]

        fan = Client(self.port)
        fan.register(self.uniq("fan"))
        _, like, _ = fan.post(f"/api/posts/{post_id}/like", {"on": True})
        self.assertEqual(like["likes"], 1)
        _, like, _ = fan.post(f"/api/posts/{post_id}/like", {"on": True})
        self.assertEqual(like["likes"], 1)  # 二重にならない
        _, rp, _ = fan.post(f"/api/posts/{post_id}/repost", {"on": True})
        self.assertEqual(rp["reposts"], 1)

        _, thread, _ = fan.get(f"/api/posts/{post_id}")
        self.assertTrue(thread["post"]["viewer"]["liked"])
        self.assertTrue(thread["post"]["viewer"]["reposted"])

        _, like, _ = fan.post(f"/api/posts/{post_id}/like", {"on": False})
        self.assertEqual(like["likes"], 0)

    def test_home_timeline_follows_and_reposts(self):
        alice = Client(self.port)
        alice_handle = self.uniq("alice")
        alice.register(alice_handle)
        bob = Client(self.port)
        bob_handle = self.uniq("bob")
        bob.register(bob_handle)

        _, data, _ = bob.post("/api/posts", {"body": "ボブの投稿", "anonymous": False})
        bob_post = data["post"]["id"]

        _, tl, _ = alice.get("/api/timeline?kind=home")
        self.assertEqual([p["id"] for p in tl["items"]], [])

        status, _, _ = alice.post(f"/api/users/{bob_handle}/follow", {"on": True})
        self.assertEqual(status, 200)
        _, tl, _ = alice.get("/api/timeline?kind=home")
        self.assertIn(bob_post, [p["id"] for p in tl["items"]])

        # 匿名投稿はフォロー経由では流れない
        _, data, _ = bob.post("/api/posts", {"body": "ボブの匿名投稿", "anonymous": True})
        anon_post = data["post"]["id"]
        _, tl, _ = alice.get("/api/timeline?kind=home")
        self.assertNotIn(anon_post, [p["id"] for p in tl["items"]])

        # リポストはフォロワーのホームに出る
        carol = Client(self.port)
        carol.register(self.uniq("carol"))
        _, data, _ = carol.post("/api/posts", {"body": "キャロルの投稿", "anonymous": False})
        carol_post = data["post"]["id"]
        bob.post(f"/api/posts/{carol_post}/repost", {"on": True})
        _, tl, _ = alice.get("/api/timeline?kind=home")
        reposted = [p for p in tl["items"] if p["id"] == carol_post]
        self.assertTrue(reposted)
        self.assertEqual(reposted[0]["reposted_by"]["handle"], bob_handle)

        alice.post(f"/api/users/{bob_handle}/follow", {"on": False})
        _, tl, _ = alice.get("/api/timeline?kind=home")
        self.assertNotIn(bob_post, [p["id"] for p in tl["items"]])

    def test_user_timeline_hides_others_anonymous_posts(self):
        handle = self.uniq("profile")
        self.c.register(handle)
        _, data, _ = self.c.post("/api/posts", {"body": "匿名の投稿", "anonymous": True})
        anon_id = data["post"]["id"]
        _, data, _ = self.c.post("/api/posts", {"body": "実名の投稿", "anonymous": False})
        named_id = data["post"]["id"]

        _, mine, _ = self.c.get(f"/api/timeline?kind=user&handle={handle}")
        self.assertIn(anon_id, [p["id"] for p in mine["items"]])

        other = Client(self.port)
        _, theirs, _ = other.get(f"/api/timeline?kind=user&handle={handle}")
        ids = [p["id"] for p in theirs["items"]]
        self.assertIn(named_id, ids)
        self.assertNotIn(anon_id, ids)

    def test_board_timeline_and_pagination(self):
        self.c.register(self.uniq("pager"))
        created = []
        for i in range(6):
            _, data, _ = self.c.post("/api/posts", {"body": f"ページング{i}", "board": "seikatsu"})
            created.append(data["post"]["id"])
        _, page1, _ = self.c.get("/api/timeline?kind=board&board=seikatsu&limit=3")
        self.assertEqual(len(page1["items"]), 3)
        self.assertIsNotNone(page1["next_cursor"])
        _, page2, _ = self.c.get(
            f"/api/timeline?kind=board&board=seikatsu&limit=3&cursor={page1['next_cursor']}")
        ids1 = [p["id"] for p in page1["items"]]
        ids2 = [p["id"] for p in page2["items"]]
        self.assertFalse(set(ids1) & set(ids2))
        self.assertEqual(ids1, sorted(ids1, reverse=True))

    def test_thread_replies(self):
        self.c.register(self.uniq("thread"))
        _, data, _ = self.c.post("/api/posts", {"body": "親の投稿", "board": "jugyo"})
        parent = data["post"]["id"]
        _, data, _ = self.c.post("/api/posts", {"body": "子の返信", "parent_id": parent})
        child = data["post"]["id"]
        self.assertEqual(data["post"]["board"], "jugyo")  # 板は親から継ぐ

        _, thread, _ = self.c.get(f"/api/posts/{parent}")
        self.assertEqual([r["id"] for r in thread["replies"]], [child])
        self.assertEqual(thread["post"]["counts"]["replies"], 1)

        _, thread, _ = self.c.get(f"/api/posts/{child}")
        self.assertEqual([a["id"] for a in thread["ancestors"]], [parent])

    def test_search(self):
        self.c.register(self.uniq("search"))
        needle = f"検索語{random.randint(10000, 99999)}"
        self.c.post("/api/posts", {"body": f"これは{needle}を含む投稿"})
        _, data, _ = self.c.get("/api/search?q=" + urllib.parse.quote(needle))
        self.assertEqual(len(data["items"]), 1)
        status, _, _ = self.c.get("/api/search?q=%")
        self.assertEqual(status, 400)

    # --- DM ---------------------------------------------------------------

    def test_dm_roundtrip_and_privacy(self):
        a = Client(self.port)
        a_handle = self.uniq("dma")
        a.register(a_handle)
        b = Client(self.port)
        b_handle = self.uniq("dmb")
        b.register(b_handle)

        status, data, _ = a.post("/api/dm", {"handle": b_handle, "body": "はじめまして"})
        self.assertEqual(status, 201)
        thread_id = data["message"]["thread_id"]

        _, threads, _ = b.get("/api/dm")
        self.assertEqual(threads["threads"][0]["unread"], 1)
        self.assertTrue(threads["threads"][0]["request"])  # 未フォローからは「リクエスト」

        _, msgs, _ = b.get(f"/api/dm/{thread_id}")
        self.assertEqual([m["body"] for m in msgs["messages"]], ["はじめまして"])
        _, threads, _ = b.get("/api/dm")
        self.assertEqual(threads["threads"][0]["unread"], 0)

        b.post("/api/dm", {"handle": a_handle, "body": "よろしく"})
        _, msgs, _ = a.get(f"/api/dm/{thread_id}")
        self.assertEqual(len(msgs["messages"]), 2)

        intruder = Client(self.port)
        intruder.register(self.uniq("nosy"))
        status, _, _ = intruder.get(f"/api/dm/{thread_id}")
        self.assertEqual(status, 404)

        status, _, _ = a.post("/api/dm", {"handle": a_handle, "body": "自分へ"})
        self.assertEqual(status, 400)

    def test_anonymous_requires_login_for_dm_and_likes(self):
        guest_view = Client(self.port)
        status, _, _ = guest_view.get("/api/dm")
        self.assertEqual(status, 401)
        status, _, _ = guest_view.post("/api/posts", {"body": "未ログイン"})
        self.assertEqual(status, 401)

    # --- 画像 -------------------------------------------------------------

    @unittest.skipUnless(HAVE_PILLOW, "Pillow が無い環境では自動審査を試せない")
    def test_upload_landscape_is_approved(self):
        self.c.register(self.uniq("img"))
        status, data, _ = self.c.request("POST", "/api/media", raw=make_image("landscape"),
                                         content_type="image/jpeg")
        self.assertEqual(status, 201, data)
        self.assertEqual(data["media"]["status"], "approved")

        media_id = data["media"]["id"]
        status, data, _ = self.c.post("/api/posts", {"body": "写真です", "media_ids": [media_id]})
        self.assertEqual(status, 201)
        self.assertEqual(data["post"]["media"][0]["url"], f"/media/{media_id}")

        status, _, body = Client(self.port).request("GET", f"/media/{media_id}")
        self.assertEqual(status, 200)
        self.assertTrue(body.startswith(b"\xff\xd8\xff"))

    @unittest.skipUnless(HAVE_PILLOW, "Pillow が無い環境では自動審査を試せない")
    def test_upload_r18_like_image_is_blocked(self):
        self.c.register(self.uniq("r18"))
        payload = make_image("skin")
        status, data, _ = self.c.request("POST", "/api/media", raw=payload, content_type="image/jpeg")
        self.assertEqual(status, 422, data)
        self.assertIn("R18", data["error"])

        # 同じ画像は二度目以降ハッシュで弾かれる
        status, data, _ = self.c.request("POST", "/api/media", raw=payload, content_type="image/jpeg")
        self.assertEqual(status, 422)
        self.assertIn("ブロック", data["error"])

    def test_upload_rejects_non_image(self):
        self.c.register(self.uniq("notimg"))
        status, data, _ = self.c.request("POST", "/api/media", raw=b"%PDF-1.7 not an image",
                                         content_type="image/jpeg")
        self.assertEqual(status, 422)

    @unittest.skipUnless(HAVE_PILLOW, "Pillow が無い環境では EXIF 除去を試せない")
    def test_exif_is_stripped_on_upload(self):
        self.c.register(self.uniq("exif"))
        img = Image.open(io.BytesIO(make_image("landscape")))
        buf = io.BytesIO()
        exif = img.getexif()
        exif[0x010F] = "Camera Maker"                  # Make
        exif[0x0110] = "Model X"                       # Model
        exif[0x9003] = "2026:09:22 12:34:56"           # DateTimeOriginal
        img.save(buf, format="JPEG", exif=exif.tobytes())
        with_exif = buf.getvalue()
        self.assertIn(b"Camera Maker", with_exif)

        status, data, _ = self.c.request("POST", "/api/media", raw=with_exif, content_type="image/jpeg")
        self.assertEqual(status, 201)
        _, _, stored = self.c.request("GET", f"/media/{data['media']['id']}")
        self.assertNotIn(b"Camera Maker", stored)
        self.assertNotIn(b"Model X", stored)
        self.assertNotIn(b"2026:09:22", stored)

    @unittest.skipUnless(HAVE_PILLOW, "Pillow が必要")
    def test_pending_media_is_not_public(self):
        owner = Client(self.port)
        owner.register(self.uniq("pend"))
        status, data, _ = owner.request("POST", "/api/media", raw=make_image("landscape"),
                                        content_type="image/jpeg")
        media_id = data["media"]["id"]
        db.execute("UPDATE media SET status = 'pending' WHERE id = ?", (media_id,))

        stranger = Client(self.port)
        status, _, _ = stranger.request("GET", f"/media/{media_id}")
        self.assertEqual(status, 403)
        status, _, _ = owner.request("GET", f"/media/{media_id}")  # 本人は見える
        self.assertEqual(status, 200)

        _, data, _ = owner.post("/api/posts", {"body": "審査中の画像", "media_ids": [media_id]})
        post_id = data["post"]["id"]
        _, thread, _ = stranger.get(f"/api/posts/{post_id}")
        self.assertEqual(thread["post"]["media"][0]["status"], "pending")
        self.assertIsNone(thread["post"]["media"][0]["url"])

    @unittest.skipUnless(HAVE_PILLOW, "Pillow が必要")
    def test_cannot_attach_someone_elses_media(self):
        owner = Client(self.port)
        owner.register(self.uniq("owner"))
        _, data, _ = owner.request("POST", "/api/media", raw=make_image("landscape"),
                                   content_type="image/jpeg")
        media_id = data["media"]["id"]
        thief = Client(self.port)
        thief.register(self.uniq("thief"))
        status, data, _ = thief.post("/api/posts", {"body": "盗用", "media_ids": [media_id]})
        self.assertEqual(status, 403)

    # --- 通報と管理 -------------------------------------------------------

    def test_report_and_admin_moderation(self):
        poster = Client(self.port)
        poster.register(self.uniq("bad"))
        _, data, _ = poster.post("/api/posts", {"body": "通報される投稿"})
        post_id = data["post"]["id"]

        reporter = Client(self.port)
        reporter.register(self.uniq("reporter"))
        status, _, _ = reporter.post("/api/reports",
                                     {"target_type": "post", "target_id": str(post_id),
                                      "reason": "r18", "note": "露出のある画像"})
        self.assertEqual(status, 201)
        status, _, _ = reporter.get("/api/admin/queue")
        self.assertEqual(status, 403)

        admin_handle = self.uniq("admin")
        admin = Client(self.port)
        admin.register(admin_handle)
        db.execute("UPDATE users SET is_admin = 1 WHERE handle = ?", (admin_handle,))

        status, queue, _ = admin.get("/api/admin/queue")
        self.assertEqual(status, 200)
        report = [r for r in queue["reports"] if r["target_id"] == str(post_id)][0]
        status, _, _ = admin.post(f"/api/admin/reports/{report['id']}", {"resolution": "delete_post"})
        self.assertEqual(status, 200)

        _, thread, _ = reporter.get(f"/api/posts/{post_id}")
        self.assertTrue(thread["post"]["deleted"])

    @unittest.skipUnless(HAVE_PILLOW, "Pillow が必要")
    def test_admin_can_block_pending_media(self):
        owner = Client(self.port)
        owner.register(self.uniq("mod"))
        _, data, _ = owner.request("POST", "/api/media", raw=make_image("landscape"),
                                   content_type="image/jpeg")
        media_id = data["media"]["id"]
        db.execute("UPDATE media SET status = 'pending' WHERE id = ?", (media_id,))

        admin_handle = self.uniq("admin2")
        admin = Client(self.port)
        admin.register(admin_handle)
        db.execute("UPDATE users SET is_admin = 1 WHERE handle = ?", (admin_handle,))
        status, _, _ = admin.post(f"/api/admin/media/{media_id}", {"status": "blocked"})
        self.assertEqual(status, 200)

        self.assertEqual(models.get_media(media_id)["status"], "blocked")
        self.assertIsNotNone(models.hash_blocked(models.get_media(media_id)["sha256"]))
        self.assertFalse((config.MEDIA_DIR / media_id).exists())
        status, _, _ = owner.post("/api/posts", {"body": "ブロック済み", "media_ids": [media_id]})
        self.assertEqual(status, 403)

    # --- レート制限 -------------------------------------------------------

    def test_post_burst_is_rate_limited(self):
        client = Client(self.port, reset_limits=False)
        auth.reset_rate_limits()
        client.register(self.uniq("burst"))
        limit = config.RATE_LIMITS["post_burst"][0]
        for i in range(limit):
            status, data, _ = client.post("/api/posts", {"body": f"連投{i}"})
            self.assertEqual(status, 201, data)
        status, data, _ = client.post("/api/posts", {"body": "制限を超える1件"})
        self.assertEqual(status, 429)
        self.assertIn("多すぎます", data["error"])


    def test_cannot_dm_a_guest(self):
        guest = Client(self.port)
        _, data, _ = guest.post("/api/guest")
        guest_handle = data["user"]["handle"]
        sender = Client(self.port)
        sender.register(self.uniq("dmguest"))
        status, data, _ = sender.post("/api/dm", {"handle": guest_handle, "body": "こんにちは"})
        self.assertEqual(status, 403)


class ModerationUnitTest(unittest.TestCase):
    def test_sniff_mime(self):
        self.assertEqual(moderation.sniff_mime(b"\xff\xd8\xff\xe0rest"), "image/jpeg")
        self.assertEqual(moderation.sniff_mime(b"\x89PNG\r\n\x1a\nrest"), "image/png")
        self.assertEqual(moderation.sniff_mime(b"RIFF1234WEBPVP8 "), "image/webp")
        self.assertIsNone(moderation.sniff_mime(b"<html>"))

    @unittest.skipUnless(HAVE_PILLOW, "Pillow が必要")
    def test_animated_image_goes_to_review(self):
        frames = [Image.new("RGB", (60, 60), (i * 70 % 255, 90, 140)) for i in range(3)]
        buf = io.BytesIO()
        frames[0].save(buf, format="GIF", save_all=True, append_images=frames[1:], duration=100)
        verdict = moderation.inspect(buf.getvalue())
        self.assertEqual(verdict.status, moderation.PENDING)
        self.assertTrue(verdict.details["animated"])

    @unittest.skipUnless(HAVE_PILLOW, "Pillow が必要")
    def test_large_image_is_downscaled(self):
        buf = io.BytesIO()
        Image.new("RGB", (3000, 1200), (20, 60, 120)).save(buf, format="JPEG")
        verdict = moderation.inspect(buf.getvalue())
        self.assertEqual(verdict.status, moderation.APPROVED)
        self.assertEqual(verdict.width, config.MEDIA_MAX_EDGE)

    def test_broken_image_rejected(self):
        self.assertEqual(moderation.inspect(b"\xff\xd8\xff" + b"garbage" * 20).status,
                         moderation.BLOCKED)

    def test_oversized_upload_rejected(self):
        verdict = moderation.inspect(b"\xff\xd8\xff" + b"0" * (config.MEDIA_MAX_BYTES + 1))
        self.assertEqual(verdict.status, moderation.BLOCKED)

    def test_anon_id_depends_on_secret(self):
        first = auth.anon_id(1, 2, "2026-09-22")
        self.assertEqual(first, auth.anon_id(1, 2, "2026-09-22"))
        self.assertNotEqual(first, auth.anon_id(1, 3, "2026-09-22"))
        self.assertNotEqual(first, auth.anon_id(1, 2, "2026-09-23"))

    def test_password_hashing(self):
        stored = auth.hash_password("correct horse")
        self.assertTrue(auth.verify_password("correct horse", stored))
        self.assertFalse(auth.verify_password("wrong horse", stored))
        self.assertFalse(auth.verify_password("x", None))


if __name__ == "__main__":
    unittest.main()
