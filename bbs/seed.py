"""動作確認用のデモデータ。`python3 -m bbs.server --demo` から呼ばれる。"""

from __future__ import annotations

from . import auth, db, models

DEMO_PASSWORD = "demopass123"

USERS = [
    ("komaba_1", "駒場のねこ", "1年 理一。数学と物理の課題に追われています。", True),
    ("hongo_lab", "本郷の院生", "工学系研究科。院試と研究室の話ができます。", True),
    ("shinfuri_memo", "進振りメモ", "底点と進振りの記録を淡々と。", True),
    ("circle_kanji", "サークル幹事", "新歓情報をまとめています。", False),
]

POSTS = [
    ("komaba_1", "zenpan", False,
     "駒場の1号館、今日も暖房が効きすぎている。上着を1枚減らすのが正解です。"),
    ("hongo_lab", "kenkyu", False,
     "院試の過去問、研究室訪問のときにもらえることが多いです。まず訪問の予約を取るのが先。"),
    ("shinfuri_memo", "shinfuri", True,
     "去年の底点、学科によっては2点近く動いています。直近3年の平均で見たほうがいい。"),
    ("circle_kanji", "circle", False,
     "新歓コンパの日程を調整中です。参加したい人は板に書き込んでください。"),
    ("komaba_1", "jugyo", True,
     "力学の期末、過去問と同じ形式でした。演習問題を全部解くより、過去問3年分を繰り返すほうが早い。"),
    ("hongo_lab", "seikatsu", False,
     "本郷周辺、安く食べるなら第二食堂。夕方は混むので17時前に行くのがコツ。"),
]


def run() -> None:
    db.init()
    created = {}
    for handle, name, bio, verified in USERS:
        user = models.get_user_by_handle(handle)
        if user is None:
            user = models.create_user(handle, name, DEMO_PASSWORD)
            models.update_profile(user["id"], name, bio)
            if verified:
                db.execute("UPDATE users SET verified_at = ?, verified_kind = 'u-tokyo' WHERE id = ?",
                           (db.now_ms(), user["id"]))
            user = models.get_user(user["id"])
        created[handle] = user

    admin = models.get_user_by_handle("moderator")
    if admin is None:
        admin = models.create_user("moderator", "運営", DEMO_PASSWORD)
        db.execute("UPDATE users SET is_admin = 1, verified_at = ? WHERE id = ?",
                   (db.now_ms(), admin["id"]))

    if db.query_one("SELECT COUNT(*) AS c FROM posts")["c"] == 0:
        first = None
        for handle, board, anonymous, body in POSTS:
            author = created[handle]
            post = models.create_post(author, body, board=board, anonymous=anonymous,
                                      parent_id=None, media_ids=[])
            first = first or post["id"]
        models.create_post(created["komaba_1"], "第二食堂、カレーが安いのでよく行きます。",
                           board=None, anonymous=True, parent_id=first, media_ids=[])

        models.follow(created["komaba_1"]["id"], created["hongo_lab"]["id"])
        models.follow(created["circle_kanji"]["id"], created["komaba_1"]["id"])
        models.like(created["komaba_1"]["id"], first, True)
        models.repost(created["hongo_lab"]["id"], first, True)
        models.dm_send(created["komaba_1"], "hongo_lab", "研究室訪問の件、来週うかがってもいいですか？")
        models.dm_send(created["hongo_lab"], "komaba_1", "水曜の午後なら空いています。")

    auth.reset_rate_limits()
    print("デモデータを入れました。")
    print(f"  ログイン: komaba_1 / {DEMO_PASSWORD}")
    print(f"  管理者  : moderator / {DEMO_PASSWORD}")
