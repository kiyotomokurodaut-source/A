#!/usr/bin/env python3
"""Turn the email target list into Gmail drafts, ready to send.

There is no Gmail API in this toolchain, so nothing here touches the mailbox.
Instead it writes a Google Apps Script that **you** run inside your own
account. Apps Script runs as you, with your own authorisation, and
``GmailApp.createDraft`` puts real drafts in your Drafts folder. No password
or token is shared with anyone.

    1. python3 make_drafts.py
    2. https://script.google.com/home → 新しいプロジェクト
    3. data/out/gmail-drafts.gs の中身を貼り付けて保存
    4. createDrafts を実行 → 初回だけ権限の確認が出る
    5. Gmail の「下書き」に入っている。読んで、直して、送る

A ``compose-links.md`` is also written: each link opens a Gmail compose window
already filled in. Useful for sending two or three without the script.

What the drafts say, and what they deliberately do not
------------------------------------------------------
Each message leads with **what is actually wrong with that company's own
site** — no viewport, no HTTPS, a 2014 copyright line — because
``find_email_targets.py`` checked. The owner can verify every claim on their
own phone in ten seconds, which is the only reason a cold email from a
stranger gets read.

Nothing is asserted about results. No "1位になります", no "問い合わせが増え
ます", no "通常20万円のところ今だけ". Those are 景品表示法 problems
(優良誤認・二重価格) and they are also the sentences that make a small
business owner stop reading. See ../sales/legal.md §4.

The track record line comes from ``sender.json``. It is left for you to fill
because a claim about past work is the one thing in the message the recipient
can check and you cannot take back. Put a real URL there — a site you built
that is live — and the message is strong. Invent one and the whole email is
worth nothing the moment they click.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HERE = Path(__file__).resolve().parent
OUT = ROOT / "data" / "out"
SRC = OUT / "email_targets.csv"
SENDER = HERE / "sender.json"

# What 特定電子メール法 actually requires in the body of an advertising mail:
# the sender's name, the sender's address, a contact for complaints, and where
# to send an opt-out. The contact and the opt-out can both be one email
# address. A 屋号, a postcode and a phone number are good for trust but are not
# legally required, so they are optional here and simply dropped from the
# signature when empty — that way the only thing standing between the drafts
# and a lawful send is the address.
REQUIRED = ["from_name", "address", "email"]
OPTIONAL = ["business_name", "postal", "phone"]

# The plainest description of each finding, in the owner's words rather than
# ours. "viewport がない" means nothing to them; "スマホで見ると文字が小さい"
# is something they have already noticed and been annoyed by.
PLAIN = {
    "スマホ対応なし": "スマートフォンで開くと、文字が小さいまま横に広がってしまう状態です",
    "常時SSL化されていない": "アドレスバーに「保護されていない通信」と出ます",
    "フレーム構造": "いまのブラウザだと表示が崩れることがある古い作りになっています",
    "テーブルレイアウト": "画面幅に合わせて折り返らない、古い組み方になっています",
    "Flashが残っている": "Flashを使った部分があり、いまはどのブラウザでも再生されません",
    "著作権表記": "ページ下部の年号が更新されていません",
    "構造化データなし": "検索結果に会社情報（住所・電話・営業時間）が出る設定が入っていません",
    "canonicalなし": "同じページが複数のURLで扱われ、検索での評価が分散しています",
    "OGP なし": "SNSやLINEで共有したときに、タイトルも画像も出ません",
}


def plain(reasons: str) -> list[str]:
    out = []
    for r in reasons.split(" / "):
        for key, text in PLAIN.items():
            if r.startswith(key):
                out.append(text)
                break
    # Keep the message short: the two worst findings carry it.
    return out[:2]


def subject(row: dict) -> str:
    reasons = row["根拠"]
    if "スマホ対応なし" in reasons:
        return f"{row['屋号']}様のサイトが、スマートフォンで崩れて表示されています"
    if "常時SSL" in reasons:
        return f"{row['屋号']}様のサイトに「保護されていない通信」と表示されています"
    if "Flash" in reasons:
        return f"{row['屋号']}様のサイトに、いま再生されない部分があります"
    if "著作権表記" in reasons:
        return f"{row['屋号']}様のサイトの表示について1点お知らせです"
    return f"{row['屋号']}様のサイトの検索表示について1点お知らせです"


# The message, with the five things that differ per company left as slots.
#
# It is a template rather than an f-string so that the Apps Script can render
# exactly the same text: the loader uploads only the per-company fields to
# Drive (about 12 KB for fifty companies instead of 85 KB of repeated
# boilerplate) and fills this same template in JavaScript. One template, two
# renderers — if it were written twice the two would drift apart.
BODY_TEMPLATE = """{name}
ご担当者様

突然のご連絡で失礼いたします。
{who}と申します。
ウェブサイトの制作と改修をしております。

{where}御社のページで気づいた点がありましたのでお知らせします。

{bullets}

（{origin} を拝見しました）

いまは検索する方の8割前後がスマートフォンなので、
この状態だと、せっかく見に来た方が読まずに離れてしまいます。

作り直す場合、{price}でお請けしています。{monthly}
{portfolio}
ご不要でしたら、このメールは破棄してください。
本メールは1回限りで、返信がない場合に再送することはありません。
今後の配信が不要な場合は、このメールに「不要」とだけご返信ください。
以後お送りいたしません。

なお、検索順位や問い合わせ件数をお約束することはできません。
「探している人に、正しく表示される状態にする」ところまでが
お引き受けする範囲です。
"""


def per_company(row: dict) -> dict:
    """The parts of the message that change from one recipient to the next."""
    # Quote the address the business itself published, not where the redirects
    # ended up. Following them lands on a deep path on some sites and on a
    # shared-hosting root on others (http://www.ksky.ne.jp/), and neither is
    # the page the owner thinks of as theirs.
    origin = (row.get("掲載URL") or "").strip()
    if not origin:
        parsed = urllib.parse.urlparse(row["最終URL"])
        origin = (f"{parsed.scheme}://{parsed.netloc}/" if parsed.netloc
                  else row["最終URL"])
    points = plain(row["根拠"])
    bullets = "\n".join(f"・{p}" for p in points) or "・検索結果での表示に改善の余地があります"

    # Name the place only when it is actually known. About 6% of rows have no
    # address tags and only a mobile number, and "不明の事業者様のサイトを
    # 拝見していて" is worse than saying nothing at all.
    place = row.get("市区町村", "").strip()
    if place in ("", "不明"):
        place = row.get("都道府県", "").strip()
    where = (f"{place}の事業者様のサイトを拝見していて、\n"
             if place and place != "不明"
             else "同業の方のサイトを順に拝見していて、\n")

    return {"name": row["屋号"], "where": where, "bullets": bullets,
            "origin": origin}


def shared(s: dict) -> dict:
    """The parts that are the same in every message."""
    portfolio = ""
    if s.get("portfolio_url"):
        note = s.get("portfolio_note") or "制作したサイトの一例です"
        portfolio = f"\n{note}\n{s['portfolio_url']}\n"
    return {
        "who": (f"{s['business_name']}の{s['from_name']}"
                if s.get("business_name") else s["from_name"]),
        "price": s["price_initial"],
        "monthly": ("月々の費用はいただきません。"
                    if s["price_monthly"] in ("なし", "", None)
                    else f"月額は{s['price_monthly']}です。"),
        "portfolio": portfolio,
    }


def body(row: dict, s: dict) -> str:
    return BODY_TEMPLATE.format(**per_company(row), **shared(s))


def signature(s: dict) -> str:
    """The block 特定電子メール法 requires, identical on every message.

    Kept separate from the body so the Apps Script can hold it as a few
    constants: the address is the one thing missing when the drafts are
    generated, and editing one line in the script beats editing fifty drafts.
    """
    name = (f"{s['business_name']} {s['from_name']}"
            if s.get("business_name") else s["from_name"])
    postal = f"〒{s['postal']} " if s.get("postal") else ""
    tel = f"TEL {s['phone']}\n" if s.get("phone") else ""
    return f"""
──────────────────────────────
{name}
{postal}{s['address']}
{tel}Mail {s['email']}
配信停止：本メールへの返信で「不要」とお知らせください
──────────────────────────────
"""


def compose_url(to: str, subj: str, text: str) -> str:
    q = urllib.parse.urlencode({"view": "cm", "fs": "1", "to": to,
                                "su": subj, "body": text})
    return "https://mail.google.com/mail/?" + q


def apps_script(drafts: list[dict], s: dict) -> str:
    payload = json.dumps(
        [{"to": d["to"], "subject": d["subject"], "body": d["body"]}
         for d in drafts],
        ensure_ascii=False, indent=2)
    return f"""/**
 * {s['business_name']} — 営業メールの下書きを Gmail に作ります。
 *
 * 使い方
 *   1. https://script.google.com/home で「新しいプロジェクト」
 *   2. このファイルの中身をすべて貼り付けて保存
 *   3. 上部の関数一覧で createDrafts を選び、実行
 *      （初回だけ「このアプリは確認されていません」と出ます。
 *        自分で書いたスクリプトなので「詳細」→「安全ではないページに移動」で進みます）
 *   4. Gmail の「下書き」に {len(drafts)} 通入ります
 *
 * 送信はしません。下書きを作るだけです。
 * 1通ずつ読んで、直して、自分で送ってください。
 *
 * 1日の下書き作成数には Gmail 側の上限があります（無料アカウントで概ね100通/日）。
 * LIMIT を変えれば分割して実行できます。
 */

const LIMIT = 100;   // 1回の実行で作る通数

const DRAFTS = {payload};

function createDrafts() {{
  const made = [];
  for (let i = 0; i < Math.min(DRAFTS.length, LIMIT); i++) {{
    const d = DRAFTS[i];
    // 同じ宛先にすでに下書きがあれば飛ばす（二重送信の予防）
    const dup = GmailApp.search('in:drafts to:' + d.to, 0, 1);
    if (dup.length > 0) {{
      Logger.log('スキップ（下書きが既にあります）: ' + d.to);
      continue;
    }}
    GmailApp.createDraft(d.to, d.subject, d.body);
    made.push(d.to);
    Utilities.sleep(300);
  }}
  Logger.log(made.length + ' 通の下書きを作りました');
  made.forEach(function (t) {{ Logger.log('  ' + t); }});
}}

/** 作った下書きをまとめて消したいとき。送信済みには触りません。 */
function deleteMyDrafts() {{
  const subjects = DRAFTS.map(function (d) {{ return d.subject; }});
  GmailApp.getDraftMessages().forEach(function (m) {{
    if (subjects.indexOf(m.getSubject()) >= 0) {{
      m.getThread().moveToTrash();
    }}
  }});
}}
"""


def loader_script(s: dict) -> str:
    """A short Apps Script that reads the bodies from the user's own Drive.

    The all-in-one ``gmail-drafts.gs`` embeds every message and runs past
    100 KB, which is a miserable thing to paste into the editor. This version
    is about forty lines: the text sits in Drive, and the only thing to edit is
    the address on line 4.
    """
    def js(value) -> str:
        return json.dumps(value if value is not None else "", ensure_ascii=False)

    template = js(BODY_TEMPLATE)
    shared_js = json.dumps(shared(s), ensure_ascii=False, indent=2)

    return f"""/**
 * 営業メールの下書きを Gmail に作ります。
 *
 *   1. Drive に drafts-data.json があることを確認
 *   2. https://script.google.com/home →「新しいプロジェクト」
 *   3. このファイルを貼り付けて保存
 *   4. ★ 下の ADDRESS に住所を入れる（ここだけ）
 *   5. createDrafts を実行
 *
 * 送信はしません。下書きを作るだけです。
 */

// ───────── ここだけ埋めてください ─────────
const ADDRESS  = "";                 // ★必須。例: 東京都〇〇区〇〇1-2-3
const NAME     = {js(s.get('from_name'))};
const EMAIL    = {js(s.get('email'))};
const BUSINESS = {js(s.get('business_name'))};   // 任意。屋号
const POSTAL   = {js(s.get('postal'))};          // 任意。郵便番号（〒なし）
const PHONE    = {js(s.get('phone'))};           // 任意。電話番号

const PER_RUN  = 20;   // 1回の実行で作る通数。1日20〜30通までにしてください
// ──────────────────────────────────────

const DATA_FILE = "drafts-data.json";

function createDrafts() {{
  if (!ADDRESS) {{
    throw new Error(
      "ADDRESS が空です。特定電子メール法は広告メールに送信者の住所の表示を" +
      "義務づけているので、入れるまで下書きは作りません。");
  }}
  const files = DriveApp.getFilesByName(DATA_FILE);
  if (!files.hasNext()) {{
    throw new Error(DATA_FILE + " が Drive に見つかりません。");
  }}
  const drafts = JSON.parse(files.next().getBlob().getDataAsString("UTF-8"));
  const sig = buildSignature();

  let made = 0, skipped = 0;
  for (const d of drafts) {{
    if (made >= PER_RUN) break;
    // すでに下書きがある、または過去にやりとりがある相手は飛ばす。
    // 本文で「1回限り」と約束しているので、二度目を送らないための歯止め。
    if (GmailApp.search("to:" + d.to, 0, 1).length > 0) {{ skipped++; continue; }}
    GmailApp.createDraft(d.to, d.subject, renderBody(d) + sig);
    made++;
    Utilities.sleep(300);
  }}
  Logger.log(made + " 通の下書きを作りました（既存のやりとりありで飛ばした宛先: "
             + skipped + "）");
}}

/**
 * 本文を組み立てます。Drive のデータには会社ごとに違う部分だけが入っていて、
 * 共通の文面はこのテンプレートにあります（85KBを12KBに減らすため）。
 */
const BODY_TEMPLATE = {template};

const SHARED = {shared_js};

function renderBody(d) {{
  const slots = Object.assign({{}}, SHARED, {{
    name: d.name, where: d.where, bullets: d.bullets, origin: d.origin,
  }});
  return BODY_TEMPLATE.replace(/\\{{(\\w+)\\}}/g, function (m, key) {{
    return key in slots ? slots[key] : m;
  }});
}}

function buildSignature() {{
  const name   = BUSINESS ? BUSINESS + " " + NAME : NAME;
  const postal = POSTAL ? "〒" + POSTAL + " " : "";
  const tel    = PHONE ? "TEL " + PHONE + "\\n" : "";
  return "\\n──────────────────────────────\\n"
       + name + "\\n"
       + postal + ADDRESS + "\\n"
       + tel + "Mail " + EMAIL + "\\n"
       + "配信停止：本メールへの返信で「不要」とお知らせください\\n"
       + "──────────────────────────────\\n";
}}

/** 署名だけ先に確認したいとき。 */
function previewSignature() {{
  Logger.log(buildSignature());
}}

/** このスクリプトで作った下書きをまとめて消すとき。送信済みには触りません。 */
function deleteMyDrafts() {{
  const files = DriveApp.getFilesByName(DATA_FILE);
  if (!files.hasNext()) return;
  const subjects = JSON.parse(files.next().getBlob().getDataAsString("UTF-8"))
                     .map(function (d) {{ return d.subject; }});
  GmailApp.getDraftMessages().forEach(function (m) {{
    if (subjects.indexOf(m.getSubject()) >= 0) m.getThread().moveToTrash();
  }});
}}
"""


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--src", type=Path, default=SRC)
    ap.add_argument("--sender", type=Path, default=SENDER,
                    help="送信者情報のJSON（既定: outreach/sender.json）")
    ap.add_argument("--limit", type=int, default=50, help="作る通数（既定50）")
    ap.add_argument("--min-need", type=int, default=2)
    ap.add_argument("--preview", action="store_true",
                    help="未記入の項目に【要記入】を入れて、とりあえず生成する")
    args = ap.parse_args()

    if not args.sender.exists():
        sys.exit(f"{args.sender} がありません")
    s = json.loads(args.sender.read_text(encoding="utf-8"))
    missing = [k for k in REQUIRED if not str(s.get(k, "")).strip()]
    if missing and not args.preview:
        print(f"{args.sender} の次の項目が空です: {', '.join(missing)}", file=sys.stderr)
        print("\n特定電子メール法は、広告メールに送信者の氏名・住所・問い合わせ先の",
              file=sys.stderr)
        print("表示を義務づけています。空欄のままでは送れません（../sales/legal.md §3）。",
              file=sys.stderr)
        print("\n中身だけ先に見たい場合は --preview を付けてください。",
              file=sys.stderr)
        return 1
    if missing:
        # The marker is deliberately loud and full-width: a draft carrying it
        # cannot be sent by accident, and it shows in the Gmail preview line.
        labels = {"from_name": "氏名", "address": "住所",
                  "email": "メールアドレス"}
        for k in missing:
            s[k] = f"【要記入：{labels.get(k, k)}】"
        print(f"⚠ 未記入のまま生成します: {', '.join(missing)}", file=sys.stderr)
        print("  このまま送ると特定電子メール法違反になります。",
              file=sys.stderr)
        print(f"  {args.sender} を埋めて、--preview なしで作り直してください。\n",
              file=sys.stderr)

    if not args.src.exists():
        sys.exit(f"{args.src} がありません。先に find_email_targets.py を実行してください")
    with args.src.open(encoding="utf-8-sig", newline="") as fh:
        rows = [r for r in csv.DictReader(fh)
                if r["メール"] and int(r["必要度"]) >= args.min_need
                and not r.get("接触状況", "").strip()]

    # One message per address, highest need first.
    seen, picked = set(), []
    for r in sorted(rows, key=lambda r: -int(r["必要度"])):
        addr = r["メール"].lower()
        if addr in seen:
            continue
        seen.add(addr)
        picked.append(r)
        if len(picked) >= args.limit:
            break

    if not picked:
        print("送付先がありません", file=sys.stderr)
        return 1

    sig = signature(s)
    drafts = [{"to": r["メール"], "subject": subject(r),
               "body": body(r, s) + sig,
               "body_only": body(r, s),
               "屋号": r["屋号"], "必要度": r["必要度"], "根拠": r["根拠"]}
              for r in picked]

    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / "drafts.csv").open("w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["屋号", "to", "subject", "body",
                                           "必要度", "根拠"],
                           extrasaction="ignore")
        w.writeheader()
        w.writerows(drafts)

    (OUT / "gmail-drafts.gs").write_text(apps_script(drafts, s), encoding="utf-8")

    # The Drive route: the bodies live in a JSON file on the user's own Drive
    # and the script that reads them is short enough to paste in one go. The
    # signature is rebuilt in the script from four constants, so filling in the
    # address is one edit rather than fifty.
    compact = [dict(to=r["メール"], subject=subject(r), **per_company(r))
               for r in picked]
    (OUT / "drafts-data.json").write_text(
        json.dumps(compact, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8")
    (OUT / "gmail-drafts-loader.gs").write_text(loader_script(s), encoding="utf-8")

    # The two renderers must agree. Check it here rather than discovering a
    # divergence in somebody's inbox.
    for d, c in zip(drafts, compact):
        want = BODY_TEMPLATE.format(**{k: c[k] for k in
                                       ("name", "where", "bullets", "origin")},
                                    **shared(s))
        if want != d["body_only"]:
            sys.exit("内部エラー: テンプレートの展開結果が一致しません")

    lines = [f"# Gmail 下書きリンク（{len(drafts)}件）", "",
             "クリックすると Gmail の作成画面が中身入りで開きます。",
             "Apps Script を使わず、数通だけ送りたいときに。", ""]
    for d in drafts:
        lines.append(f"- **{d['屋号']}** 〈必要度{d['必要度']}〉 "
                     f"[{d['to']} に書く]({compose_url(d['to'], d['subject'], d['body'])})")
        lines.append(f"  - 根拠: {d['根拠']}")
    (OUT / "compose-links.md").write_text("\n".join(lines), encoding="utf-8")

    print(f"{len(drafts)} 通分を作りました:")
    print(f"  {OUT/'drafts-data.json'}        ← Drive に置く本文データ")
    print(f"  {OUT/'gmail-drafts-loader.gs'}  ← 貼るのはこちら（約40行。住所1行だけ埋める）")
    print(f"  {OUT/'gmail-drafts.gs'}         ← Driveを使わない全部入り版（100KB超）")
    print(f"  {OUT/'compose-links.md'}        ← 数通だけならこちら")
    print(f"  {OUT/'drafts.csv'}              ← 中身の確認用")
    print("\n--- 1通目のプレビュー ---")
    print(f"To: {drafts[0]['to']}")
    print(f"Subject: {drafts[0]['subject']}\n")
    print(drafts[0]["body"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
