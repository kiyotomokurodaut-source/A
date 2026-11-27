#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""r27（2026-11-27）LINE問い合わせ導線（CRO）の共通部品と一括適用。

    python3 tools/line_cro_r27.py            # 全ページに適用（既存ブロックは差し替え）
    python3 tools/line_cro_r27.py --check    # 適用状況の点検のみ（書き込みなし）

方針:
* LINEの短縮URLは 1つ（lin.ee/VKV65IQ）。相談内容を添えたい場合は
  line.me/R/oaMessage/%40670gzfpd/?<文言> を使う。過去に混在していた
  lin.ee/YXdwMqY・lin.ee/vb8qVu4 は同じ公式アカウント（@670gzfpd）へ
  転送されるため、表記を1つに揃える。
* 追従バーと本文中CTAは、JavaScriptに頼らずHTMLに直接置く（JS無効でも出る）。
  line-navigation-r15.js は .r27-sticky があるページでは追従バーを重複生成しない。
* 訴求は公開済みの事実のみ（無理な勧誘をしない・代表が直接返信・原則24時間以内・
  月額24,000円〜・オンライン専業・テキストのみでも可）。実績の誇張や口コミの捏造はしない。
"""
from __future__ import annotations

import argparse
import html
import re
import sys
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "public"
SITE = "https://kurodaschool.jp"

# --- LINEの正本 ------------------------------------------------------------
LINE_ADD = "https://lin.ee/VKV65IQ"                     # 友だち追加（現行本番）
LINE_OA_ID = "%40670gzfpd"                              # 公式アカウント @670gzfpd
OA_BASE = f"https://line.me/R/oaMessage/{LINE_OA_ID}/?"
LEGACY_LINE_URLS = {
    "https://lin.ee/YXdwMqY": LINE_ADD,
    "https://lin.ee/vb8qVu4": LINE_ADD,
    "https://line.me/R/ti/p/@670gzfpd": LINE_ADD,
}

CSS_HREF = "/assets/line-cro-r27.css?v=20261127"
CSS_LINK = f'<link rel="stylesheet" href="{CSS_HREF}"/>'

MID_START = "<!-- r27:cro-mid:start -->"
MID_END = "<!-- r27:cro-mid:end -->"

# 相談カードを置かないページ（入力フォーム・法務ページ・サイトマップ）
NO_MID = {
    "/contact/", "/shindan/", "/privacy/", "/legal/", "/materials/terms/",
}
# 追従バーを置かないページ（販売条件・個人情報の確認ページは導線を挟まない）
NO_STICKY = {"/privacy/", "/legal/", "/materials/terms/"}

PREF_NAMES = {
    "hokkaido": "北海道", "aomori": "青森県", "iwate": "岩手県", "miyagi": "宮城県",
    "akita": "秋田県", "yamagata": "山形県", "fukushima": "福島県", "ibaraki": "茨城県",
    "tochigi": "栃木県", "gunma": "群馬県", "saitama-ken": "埼玉県", "chiba-ken": "千葉県",
    "tokyo": "東京都", "kanagawa": "神奈川県", "niigata": "新潟県", "toyama": "富山県",
    "ishikawa": "石川県", "fukui": "福井県", "yamanashi": "山梨県", "nagano": "長野県",
    "gifu": "岐阜県", "shizuoka": "静岡県", "aichi": "愛知県", "mie": "三重県",
    "shiga": "滋賀県", "kyoto": "京都府", "osaka-fu": "大阪府", "hyogo": "兵庫県",
    "nara": "奈良県", "wakayama": "和歌山県", "tottori": "鳥取県", "shimane": "島根県",
    "okayama": "岡山県", "hiroshima": "広島県", "yamaguchi": "山口県",
    "tokushima": "徳島県", "kagawa": "香川県", "ehime": "愛媛県", "kochi": "高知県",
    "fukuoka": "福岡県", "saga": "佐賀県", "nagasaki": "長崎県", "kumamoto": "熊本県",
    "oita": "大分県", "miyazaki": "宮崎県", "kagoshima": "鹿児島県", "okinawa": "沖縄県",
}

CLEAN_H1 = re.compile(r"<[^>]+>")

# 駅・区のページ（大学別ではなく、地名からのオンライン受講案内）
LOCAL_SLUGS = {
    "bunkyo", "myogadani", "nezu", "yushima", "gokokuji", "kasuga", "korakuen",
    "hongo-sanchome", "edogawabashi", "iidabashi", "ochanomizu-eki", "todaimae",
    "shinjuku", "chiyoda",
}


def route(path: Path) -> str:
    r = path.relative_to(PUBLIC).as_posix()
    if r == "index.html":
        return "/"
    return "/" + r[: -len("index.html")] if r.endswith("/index.html") else "/" + r


def category(url: str) -> str:
    if url == "/":
        return "home"
    if url == "/pricing/":
        return "pricing"
    if url == "/cases/":
        return "cases"
    if url == "/contact/":
        return "contact"
    if url.startswith("/study-guides/"):
        return "guide"
    if url.startswith("/specialty/"):
        slug = url.strip("/").split("/")[-1]
        if slug in PREF_NAMES:
            return "region"
        return "local" if slug in LOCAL_SLUGS else "university"
    if url == "/study-guides/":
        return "hub"
    return "lp"


def page_label(raw: str, url: str) -> str:
    """ページの短い呼び名（相談文に使う）。"""
    cat = category(url)
    slug = url.strip("/").split("/")[-1]
    if cat == "region":
        return PREF_NAMES[slug]
    title = re.search(r"<title>(.*?)</title>", raw, re.S)
    name = title.group(1) if title else ""
    name = name.split("｜")[0].strip()
    if cat == "guide":
        return name[:32]
    name = re.sub(r"からの大学受験オンライン指導$", "", name)
    name = re.sub(r"(?:エリア|駅周辺)の大学受験オンライン指導$", "", name)
    name = re.sub(r"の(大学受験)?専門対策$", "", name)
    name = re.sub(r"専門対策$", "", name)
    return name


def prompt_text(cat: str, label: str) -> str:
    if cat == "guide":
        return (
            f"学習ガイド「{label}」を読みました。学年・志望校・今の模試の結果を送ります。"
            "学習の優先順位を相談したいです。"
        )
    if cat == "region":
        return (
            f"{label}からオンライン受講を考えています。"
            "学年・志望校・今の模擬試験の結果を送ります。"
        )
    if cat == "local":
        return (
            f"{label}周辺でオンライン受講を考えています。"
            "学年・志望校・今の模擬試験の結果を送ります。"
        )
    if cat == "university":
        if label.endswith("大学"):
            return (
                f"{label}の対策を相談したいです。"
                "学年・志望学部・今の模試の結果を送ります。"
            )
        return (
            f"「{label}」のページを読みました。"
            "学年・志望校・今の模試の結果を送るので、対策を相談したいです。"
        )
    if cat == "pricing":
        return (
            "料金プランを見ました。学年と志望校を送るので、"
            "プランの選び方を相談したいです。"
        )
    if cat == "cases":
        return (
            "指導事例を読みました。同じような状況から相談したいです。"
            "学年と志望校を送ります。"
        )
    return "無料相談を希望します。学年と志望校を送るので、学習方針を整理したいです。"


def head_lead(cat: str, label: str) -> tuple[str, str]:
    if cat == "guide":
        return (
            "この記事の内容を、自分の答案で確かめる",
            "読んで分かったつもりになっていないかを、答案と計画で確認します。"
            "記事をそのまま当てはめる必要はありません。",
        )
    if cat == "region":
        return (
            f"{label}から、オンラインで受験対策を始める",
            f"黒田塾に教室はありません。{label}のどの地域からでも、"
            "同じ料金・同じ内容で受講できます。",
        )
    if cat == "local":
        return (
            f"{label}周辺から、オンラインで受験対策を始める",
            "近くに教室がなくても、指導と答案確認はオンラインで完結します。"
            "移動時間はかかりません。",
        )
    if cat == "university":
        if label.endswith("大学"):
            return (
                f"{label}の対策を、現在地から組み直す",
                "志望学部の配点と今の答案を並べ、科目ごとの優先順位を決めます。",
            )
        return (
            f"「{label}」の対策を、現在地から組み直す",
            "一般論ではなく、今の答案と志望校の形式から、次に直す一点を決めます。",
        )
    if cat == "pricing":
        return (
            "プラン選びは、学年と志望校を送るだけで整理できます",
            "5プランのどれが合うかは、必要な指導量と今の課題で決まります。"
            "無理に上位のプランを勧めることはありません。",
        )
    if cat == "cases":
        return (
            "同じような状況から、どう組み直すか",
            "事例は一例です。同じ状況でなくても、現在地から次の一手を整理します。",
        )
    return (
        "無料相談（30分）で、次の7日を決める",
        "志望校と現在の答案から、次に優先することを決めます。"
        "相談だけでも歓迎します。",
    )


def mid_cta(url: str, raw: str) -> str:
    cat = category(url)
    label = page_label(raw, url)
    title, lead = head_lead(cat, label)
    slug = url.strip("/").replace("/", "-") or "home"
    href = OA_BASE + quote(prompt_text(cat, label), safe="")
    return (
        f'{MID_START}<section aria-labelledby="r27-cta-title" class="r27-cta">'
        '<p class="r27-kicker">LINEで無料相談・登録1分</p>'
        f'<h2 class="r27-heading" id="r27-cta-title">{html.escape(title)}</h2>'
        f'<p class="r27-lead">{html.escape(lead)}</p>'
        '<ul class="r27-points">'
        "<li>無理な勧誘はしません（相談だけでも歓迎）</li>"
        "<li>東大教育学部卒の黒田が直接返信（原則24時間以内）</li>"
        "<li>学年・志望校・模試の結果を送るだけで、学習の優先順位を整理</li>"
        "</ul>"
        '<div class="r27-actions">'
        f'<a class="r27-line" href="{href}" target="_blank" rel="noopener" '
        f'data-line-cta="mid-{slug}">この内容でLINE相談する（無料）</a>'
        f'<a class="r27-alt" href="/contact/?topic={slug}&amp;source=r27#consultation-flow">'
        "フォームで相談する（通話なし）</a>"
        "</div>"
        '<p class="r27-fact">無料・30分／オンライン（通話が苦手ならテキストのみでも可）／'
        "継続受講は月額24,000円〜（税込・月4セット）</p>"
        f"</section>{MID_END}"
    )


def sticky(url: str) -> str:
    cat = category(url)
    slug = url.strip("/").replace("/", "-") or "home"
    return (
        f'<a class="r27-sticky" href="{LINE_ADD}" target="_blank" rel="noopener" '
        f'data-line-cta="sticky-{slug}">'
        '<span class="r27-sticky-main">LINEで無料相談（登録1分）</span>'
        '<span class="r27-sticky-sub">東大卒が直接返信・勧誘なし</span>'
        "</a>"
    )


def insert_mid(raw: str, block: str) -> str:
    """FAQ見出しの直前（＝読み終わる前）に相談カードを置く。"""
    anchors = [
        '<section id="faq"',
        '<section id="questions"',
        '<aside class="learn-links"',
        '<div class="cta-box"',
        '<section class="r21-section"',
        "</main>",
    ]
    for anchor in anchors:
        idx = raw.find(anchor)
        if idx > 0:
            return raw[:idx] + "\n" + block + raw[idx:]
    raise SystemExit("insertion anchor not found")


def apply_page(path: Path, raw: str, url: str) -> str:
    cat = category(url)
    # 1) LINEのURLを正本へ統一（旧リンクの残存をなくす）
    for old, new in LEGACY_LINE_URLS.items():
        raw = raw.replace(old, new)
    # 2) CSS
    if "line-cro-r27.css" not in raw:
        raw = raw.replace("</head>", CSS_LINK + "</head>", 1)
    # 3) 本文中CTA（既存ブロックは中身を差し替え）
    if url not in NO_MID:
        block = mid_cta(url, raw)
        if MID_START in raw and MID_END in raw:
            head, _, rest = raw.partition(MID_START)
            _, _, tail = rest.partition(MID_END)
            raw = head + block + tail
        else:
            try:
                raw = insert_mid(raw, block)
            except SystemExit as exc:
                raise SystemExit(f"{path}: {exc}") from exc
    # 4) 追従バー（HTMLに静的設置）
    if url not in NO_STICKY and 'class="r27-sticky"' not in raw:
        raw = raw.replace("</body>", sticky(url) + "</body>", 1)
    return raw


def fix_index_sticky(raw: str) -> str:
    """トップの旧・固定ボタン（ks-line-fixed）をr27の追従バーへ寄せる。"""
    return re.sub(r'<a class="ks-line-fixed"[^>]*>.*?</a>', "", raw, flags=re.S)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    changed, problems, mids, sticks, oa = 0, [], 0, 0, 0
    for path in sorted(PUBLIC.rglob("index.html")):
        url = route(path)
        raw = path.read_text(encoding="utf-8")
        if url == "/" and 'class="ks-line-fixed"' in raw:
            raw = fix_index_sticky(raw)
            path.write_text(raw, encoding="utf-8")
        new = apply_page(path, raw, url)
        if args.check:
            if MID_START not in new and url not in NO_MID:
                problems.append(f"{url}: 本文中CTAなし")
            if 'class="r27-sticky"' not in new and url not in NO_STICKY:
                problems.append(f"{url}: 追従バーなし")
            if "line-cro-r27.css" not in new:
                problems.append(f"{url}: r27 CSSなし")
            if "oaMessage" not in new and url not in NO_MID:
                problems.append(f"{url}: 相談テンプレ（oaMessage）なし")
        else:
            if new != raw:
                path.write_text(new, encoding="utf-8")
                changed += 1
        mids += 1 if MID_START in new else 0
        sticks += 1 if 'class="r27-sticky"' in new else 0
        oa += 1 if "oaMessage" in new else 0

    print(f"r27 CRO: 更新 {changed} ページ / 本文中CTA {mids} / 追従バー {sticks} / oaMessage {oa}")
    if problems:
        print("\n".join(problems[:40]), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
