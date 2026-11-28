#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""r31（2026-11-28）: 学習ガイド同士を文脈でつなぎ、被リンクの偏りをならす。

    python3 tools/related_links_r31.py           # 適用
    python3 tools/related_links_r31.py --check   # 点検のみ（書き込みなし）
    python3 tools/related_links_r31.py --dry     # 選ばれる組み合わせを表示

第10弾の内部リンク最適化。

* 学習ガイド86本それぞれに「あわせて読みたい学習ガイド」の節を置き、
  同じ科目・近いテーマの記事へ最大4本のリンクを張る。
* 分類は各記事の題名とh1だけで行う（本文や説明文の「塾」のような
  一般的な語で、関係の薄い記事が混ざらないようにする）。
* 科目は英語（長文・単語・リスニング・英作文…）／数学（確率・数列…）／
  国語（現代文・古文・漢文）／社会／小論文（面接・志望理由書）のまとまりで見る。
* テーマは共通テスト・東大・中学受験・保護者・計画・模試・過去問・復習・
  塾選び・メンタル・出願・習慣。
* 同点なら被リンクが少ない記事を先に選ぶ（評価を1ページに集めない）。
* 記事内ですでにリンクしている記事は後回しにし、重複リンクを作らない。
* 関係の薄い記事しか残らない一部の記事は OVERRIDES で手当てする。
* 何度実行しても同じ結果になる（マーカー間だけを差し替える）。
* 本文を変えたページは last-modified と dateModified を 2026-11-28 にそろえる。
"""
from __future__ import annotations

import argparse
import html
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "public"
TODAY = "2026-11-28"

START = "<!-- r31:related-guides:start -->"
END = "<!-- r31:related-guides:end -->"

# (ラベル, 題名・h1に現れる語, 科目のまとまり or None, 種類)
TAGS = [
    ("英語", r"英語|英単語|長文|リスニング|英作文|要約|英文和訳|英文解釈|外部検定|英検", "英語", "subject"),
    ("数学", r"数学|微分|積分|確率|数列|ベクトル|漸化式|場合の数", "数学", "subject"),
    ("現代文", r"現代文", "国語", "subject"),
    ("古文", r"古文", "国語", "subject"),
    ("漢文", r"漢文|句法|返り点", "国語", "subject"),
    ("記述", r"記述|答案の作り方", "国語", "subject"),
    ("日本史", r"日本史", "社会", "subject"),
    ("世界史", r"世界史", "社会", "subject"),
    ("情報", r"情報I|情報Ⅰ|情報１", "情報", "subject"),
    ("小論文", r"小論文|論述", "小論文", "subject"),
    ("面接", r"面接", "小論文", "subject"),
    ("志望理由書", r"志望理由書|志望理由", "小論文", "subject"),
    ("共通テスト", r"共通テスト|センタ", None, "theme"),
    ("東大", r"東大|東京大学", None, "theme"),
    ("中学受験", r"中学受験|小学生|塾の宿題", None, "theme"),
    ("保護者", r"保護者|親が|親の|お子さま|声かけ", None, "theme"),
    ("計画", r"計画|スケジュール|時間配分|週間|冬休み|夏休み|春休み|年末年始", None, "theme"),
    ("模試", r"模試|判定|偏差値", None, "theme"),
    ("過去問", r"過去問|赤本", None, "theme"),
    ("復習", r"復習|解き直し|定着", None, "theme"),
    ("塾選び", r"塾|予備校|家庭教師|個別指導|コーチング", None, "theme"),
    ("メンタル", r"やる気|メンタル|体調|睡眠|不安|ストレス", None, "theme"),
    ("出願", r"出願|願書|併願|合格発表|手続き|入学金", None, "theme"),
    ("習慣", r"習慣|ケアレス|成績が上がらない|集中|勉強の進め方", None, "theme"),
    ("内申", r"内申|定期テスト|評定", None, "theme"),
    ("講習", r"講習", None, "theme"),
]
LABEL_GROUP = {label: group for label, _p, group, _k in TAGS}
LABEL_KIND = {label: kind for label, _p, _g, kind in TAGS}

# 題名だけでは同じ科目・テーマの記事が見つからない場合の手当て（内容を確認して指定）。
OVERRIDES = {
    "/study-guides/careless-mistake/": [
        ("/study-guides/mock-exam-review/", "復習"),
        ("/study-guides/seiseki-agaranai/", "習慣"),
        ("/study-guides/math-self-solve/", "数学・復習"),
    ],
    "/study-guides/choosing-a-juku/": [
        ("/study-guides/kobetsu-vs-shudan/", "塾選び"),
        ("/study-guides/yobiko-vs-kojinjuku/", "塾選び"),
        ("/study-guides/coaching-vs-private-tutoring/", "塾選び"),
        ("/study-guides/juku-yametai/", "塾選び"),
    ],
    "/study-guides/gendaibun-yomikata/": [
        ("/study-guides/kijutsu-kakenai/", "記述"),
        ("/study-guides/kobun-tango-bunpo/", "古文"),
        ("/study-guides/kanbun-kuho/", "漢文"),
    ],
    "/study-guides/eizo-jugyo-tsukiaikata/": [
        ("/study-guides/dokugaku-susumekata/", "塾選び"),
        ("/study-guides/yobiko-vs-kojinjuku/", "塾選び"),
        ("/study-guides/online-tutoring-vs-agency/", "塾選び"),
        ("/study-guides/weekly-study-plan/", "計画"),
    ],
    "/study-guides/mock-exam-review/": [
        ("/study-guides/mock-e-hantei-recovery/", "模試"),
        ("/study-guides/parents-mock-exam-bad-result/", "模試"),
        ("/study-guides/shiboukou-sageru/", "模試"),
        ("/study-guides/kakomon-score-stuck/", "過去問"),
    ],
    "/study-guides/touki-koshu-fukushu/": [
        ("/study-guides/touki-koshu-erabikata/", "講習"),
        ("/study-guides/touki-koshu-yarubeki/", "講習"),
        ("/study-guides/winter-break-study-plan/", "計画"),
        ("/study-guides/eizo-jugyo-tsukiaikata/", "塾選び"),
    ],
    "/study-guides/ima-kara-maniau/": [
        ("/study-guides/gap-year-study-plan/", "計画"),
        ("/study-guides/weekly-study-plan/", "計画"),
        ("/study-guides/summer-break-study-plan/", "計画"),
        ("/study-guides/spring-break-shin-kou3/", "計画"),
    ],
    "/study-guides/teiki-test-juken-ryoritsu/": [
        ("/study-guides/weekly-study-plan/", "計画"),
        ("/study-guides/spring-break-shin-kou3/", "計画"),
        ("/study-guides/summer-break-study-plan/", "計画"),
    ],
    "/study-guides/nihonshi-nagare/": [
        ("/study-guides/sekaishi-yoko/", "社会"),
        ("/study-guides/kakomon-score-stuck/", "過去問"),
        ("/study-guides/mock-exam-review/", "復習"),
    ],
    "/study-guides/sekaishi-yoko/": [
        ("/study-guides/nihonshi-nagare/", "社会"),
        ("/study-guides/kakomon-score-stuck/", "過去問"),
        ("/study-guides/mock-exam-review/", "復習"),
    ],
    "/study-guides/yaruki-tatenaoshi/": [
        ("/study-guides/taicho-suimin-mental/", "メンタル"),
        ("/study-guides/seiseki-agaranai/", "習慣"),
        ("/study-guides/careless-mistake/", "習慣"),
        ("/study-guides/weekly-study-plan/", "計画"),
    ],
    "/study-guides/taicho-suimin-mental/": [
        ("/study-guides/yaruki-tatenaoshi/", "メンタル"),
        ("/study-guides/careless-mistake/", "習慣"),
        ("/study-guides/seiseki-agaranai/", "習慣"),
    ],
    "/study-guides/kanbun-kuho/": [
        ("/study-guides/kobun-tango-bunpo/", "国語"),
        ("/study-guides/gendaibun-yomikata/", "国語"),
        ("/study-guides/kijutsu-kakenai/", "記述"),
    ],
    "/study-guides/kobun-tango-bunpo/": [
        ("/study-guides/gendaibun-yomikata/", "国語"),
        ("/study-guides/kanbun-kuho/", "国語"),
        ("/study-guides/kijutsu-kakenai/", "記述"),
    ],
    "/study-guides/gendaibun-yomikata/": [
        ("/study-guides/kobun-tango-bunpo/", "国語"),
        ("/study-guides/kanbun-kuho/", "国語"),
        ("/study-guides/kijutsu-kakenai/", "記述"),
    ],
    "/study-guides/kijutsu-kakenai/": [
        ("/study-guides/gendaibun-yomikata/", "国語"),
        ("/study-guides/kobun-tango-bunpo/", "国語"),
        ("/study-guides/nijishiken-final-stage/", "記述"),
    ],
    "/study-guides/mensetsu-taisaku/": [
        ("/study-guides/shibou-riyusho/", "志望理由書"),
        ("/study-guides/kijutsu-kakenai/", "記述"),
        ("/study-guides/shutsugan-tetsuzuki/", "出願"),
    ],
    "/study-guides/shibou-riyusho/": [
        ("/study-guides/mensetsu-taisaku/", "志望理由書"),
        ("/study-guides/kijutsu-kakenai/", "記述"),
        ("/study-guides/shutsugan-tetsuzuki/", "出願"),
    ],
    "/study-guides/juku-yametai/": [
        ("/study-guides/choosing-a-juku/", "塾選び"),
        ("/study-guides/kobetsu-vs-shudan/", "塾選び"),
        ("/study-guides/tenjuku/", "塾選び"),
        ("/study-guides/yobiko-vs-kojinjuku/", "塾選び"),
    ],
    "/study-guides/materials-catalog/": [
        ("/study-guides/eitango-teichaku/", "英語"),
        ("/study-guides/math-self-solve/", "数学"),
        ("/study-guides/kijutsu-kakenai/", "記述"),
    ],
}


def route(path: Path) -> str:
    return ("/" + str(path.relative_to(PUBLIC))).replace("/index.html", "/")


def guide_pages() -> dict[str, Path]:
    return {
        route(p): p
        for p in sorted((PUBLIC / "study-guides").glob("*/index.html"))
    }


def meta(raw: str, key: str) -> str:
    m = re.search(r'<meta content="([^"]*)" name="%s"' % key, raw)
    if m:
        return m.group(1)
    m = re.search(r'<meta name="%s" content="([^"]*)"' % key, raw)
    return m.group(1) if m else ""


def title_of(raw: str) -> str:
    m = re.search(r"<title>(.*?)</title>", raw, re.S)
    return m.group(1).strip() if m else ""


def h1_of(raw: str) -> str:
    m = re.search(r"<h1[^>]*>(.*?)</h1>", raw, re.S)
    return html.unescape(re.sub(r"<[^>]+>", "", m.group(1))).strip() if m else ""


def label_of(raw: str) -> str:
    t = title_of(raw).split("｜")[0].strip()
    return t or h1_of(raw)


def classify(text: str) -> set[str]:
    # 「黒田塾」の塾で塾向け記事と誤判定しないよう、ブランド名を除いてから分類する。
    text = text.replace("黒田塾", "").replace("黒田式", "")
    return {label for label, pattern, _g, _k in TAGS if re.search(pattern, text)}


def strip_blocks(raw: str) -> str:
    for a, b in ((START, END), ("<!-- r31:hub-guides:start -->", "<!-- r31:hub-guides:end -->"),
                 ("<!-- r31:cluster:start -->", "<!-- r31:cluster:end -->")):
        raw = re.sub(re.escape(a) + r".*?" + re.escape(b), "", raw, flags=re.S)
    return raw


def body_guide_links(raw: str) -> set[str]:
    m = re.search(r"<main\b.*?</main>", raw, re.S)
    body = m.group(0) if m else raw
    body = re.sub(r"<script.*?</script>", "", body, flags=re.S)
    body = strip_blocks(body)
    out = set()
    for href in re.findall(r'href="([^"]+)"', body):
        h = href.split("#")[0].split("?")[0]
        if h.endswith("/index.html"):
            h = h[: -len("index.html")]
        if h.startswith("/study-guides/") and h != "/study-guides/" and h.endswith("/"):
            out.add(h)
    return out


def build_index() -> dict[str, dict]:
    idx = {}
    for url, path in guide_pages().items():
        raw = path.read_text(encoding="utf-8")
        idx[url] = {
            "label": label_of(raw),
            "tags": classify(title_of(raw) + " " + h1_of(raw)),
            "linked": body_guide_links(raw),
            "raw": raw,
            "path": path,
        }
    return idx


def inbound_counts() -> dict[str, int]:
    pages = {route(p): p for p in PUBLIC.rglob("*.html")}
    seen = defaultdict(set)
    for src, p in pages.items():
        raw = re.sub(r"<script.*?</script>", "", p.read_text(encoding="utf-8"), flags=re.S)
        for href in re.findall(r'href="([^"]+)"', raw):
            h = href.split("#")[0].split("?")[0]
            if h.endswith("/index.html"):
                h = h[: -len("index.html")]
            if h.startswith("/") and not re.search(r"\.[a-z0-9]+$", h) and not h.endswith("/"):
                h += "/"
            if h in pages and h != src:
                seen[h].add(src)
    return {h: len(srcs) for h, srcs in seen.items()}


def score(shared: set[str]) -> int:
    exact = sum(1 for t in shared if LABEL_KIND[t] == "subject")
    groups = {
        LABEL_GROUP[t] for t in shared
        if LABEL_KIND[t] == "subject" and LABEL_GROUP.get(t)
    }
    themes = sum(1 for t in shared if LABEL_KIND[t] == "theme")
    return exact * 4 + max(0, len(groups) - exact) * 2 + themes * 2


GROUP_LABEL = {"英語": "英語", "数学": "数学", "国語": "国語", "社会": "社会", "情報": "情報", "小論文": "小論文"}
GROUP_ORDER = ["英語", "数学", "国語", "社会", "小論文", "情報",
               "共通テスト", "東大", "中学受験", "保護者", "計画", "模試",
               "過去問", "復習", "塾選び", "メンタル", "出願", "習慣", "内申", "講習"]


def primary_group(tags: set[str]) -> str:
    for g in GROUP_ORDER:
        for t in tags:
            if (LABEL_KIND[t] == "subject" and LABEL_GROUP[t] == g) or t == g:
                return g
    return "その他"


def ring_neighbors(url: str, idx: dict[str, dict]) -> list[str]:
    """同じまとまりの中で、URL順の前後2本ずつ。全記事が必ず誰かから辿られるようにする。"""
    group = primary_group(idx[url]["tags"])
    members = sorted(u for u, i in idx.items() if primary_group(i["tags"]) == group)
    if url not in members or len(members) < 2:
        return []
    i = members.index(url)
    out = []
    for step in (1, -1, 2, -2):
        other = members[(i + step) % len(members)]
        if other != url and other not in out:
            out.append(other)
    return out


def pick(url: str, idx: dict[str, dict], inbound: dict[str, int]) -> list[tuple[str, str]]:
    if url in OVERRIDES:
        return [(o, r) for o, r in OVERRIDES[url] if o in idx and o != url]
    me = idx[url]
    my_groups = {LABEL_GROUP[t] for t in me["tags"] if LABEL_KIND[t] == "subject" and LABEL_GROUP[t]}
    ranked = []
    for other, info in idx.items():
        if other == url:
            continue
        shared = me["tags"] & info["tags"]
        groups = my_groups & {LABEL_GROUP[t] for t in info["tags"] if LABEL_KIND[t] == "subject" and LABEL_GROUP[t]}
        exact = sum(1 for t in shared if LABEL_KIND[t] == "subject")
        themes = sum(1 for t in shared if LABEL_KIND[t] == "theme")
        if not (exact or groups or themes):
            continue
        s = exact * 4 + themes * 2 + (2 if groups and not exact else 0)
        # 中学受験向けと大学受験向けを混ぜない（読者が違う記事を並べない）
        if ("中学受験" in me["tags"]) != ("中学受験" in info["tags"]):
            s -= 3
        fresh = other not in me["linked"]
        ranked.append((fresh, s, other))
    # 同点の並びはURLで固定する（被リンク数に依存させず、何度実行しても同じ結果にする）
    ranked.sort(key=lambda r: (r[0], r[1], r[2]), reverse=True)
    order: list[str] = []
    for _fresh, s, other in ranked:
        if s >= 2:
            order.append(other)
    for other in ring_neighbors(url, idx):
        if other not in order:
            order.append(other)
    # 3本に満たない記事は、点数の低い候補でも同じテーマのものを足す（空の節を作らない）
    if len(order) < 3:
        rest = sorted(
            (o for o in idx if o != url and o not in order
             and (me["tags"] & idx[o]["tags"])),
            key=lambda o: (-(score(me["tags"] & idx[o]["tags"])), o),
        )
        order.extend(rest)
    picked = []
    for other in order:
        if len(picked) == 4:
            break
        if other == url or other in [p[0] for p in picked]:
            continue
        shared = me["tags"] & idx[other]["tags"]
        labels = sorted(shared, key=lambda t: (LABEL_KIND[t] != "subject", TAGS_ORDER[t]))
        if labels:
            reason = "・".join(labels[:2])
        else:
            g = my_groups & {LABEL_GROUP[t] for t in idx[other]["tags"] if LABEL_GROUP[t]}
            reason = "・".join(GROUP_LABEL[x] for x in sorted(g, key=GROUP_ORDER.index))
        picked.append((other, reason))
    return picked


TAGS_ORDER = {label: i for i, (label, _p, _g, _k) in enumerate(TAGS)}



# 集客ハブ → 学習ガイドの導線（第10弾）。ページの文脈に合うガイドだけを選ぶ。
# すでに本文でリンクしているガイドは重ねない（重複リンクを作らない）。
HUBS = {
    "/university-exam/": [
        "kakomon-score-stuck", "mock-exam-review", "shiboukou-sageru",
        "weekly-study-plan", "gap-year-study-plan", "ima-kara-maniau",
        "teiki-test-juken-ryoritsu", "careless-mistake", "nihonshi-nagare",
        "kyotsu-listening", "joho-1-taisaku", "eigo-gaibu-kentei-nyushi",
        "gokaku-happyo-tetsuzuki",
    ],
    "/junior-high-exam/": [
        "homework-priorities", "kakomon-start-timing",
        "chugaku-juken-12gatsu-shutsugan", "parents-koekake",
        "junior-high-online-tutoring", "teiki-test-juken-ryoritsu",
        "winter-chugakusei", "summer-break-study-plan", "winter-break-study-plan",
    ],
    "/juku/": [
        "choosing-a-juku", "yobiko-vs-kojinjuku", "kobetsu-vs-shudan",
        "online-tutoring-vs-agency", "juku-yametai", "shinnendo-juku-erabi",
        "eizo-jugyo-tsukiaikata",
    ],
    "/for-parents/": [
        "parents-university-exam", "parents-koekake", "parents-ronin-handan",
        "parents-mock-exam-hantei", "parents-kyotsu-exam-day",
        "parents-kyotsu-6-weeks", "parents-mock-exam-bad-result",
        "yaruki-tatenaoshi", "teiki-test-juken-ryoritsu",
    ],
    "/online-tutoring/": [
        "online-tutoring-vs-agency", "eizo-jugyo-tsukiaikata",
        "kobetsu-vs-shudan", "coaching-vs-private-tutoring",
        "dokugaku-susumekata",
    ],
    "/study-coaching/": [
        "coaching-vs-private-tutoring", "weekly-study-plan",
        "yaruki-tatenaoshi", "seiseki-agaranai", "taicho-suimin-mental",
        "careless-mistake",
    ],
    "/todai-juku/": [
        "todai-juku-choosing", "todai-study-plan", "todai-english-strategy",
        "todai-english-writing", "todai-english-summary",
        "todai-english-time-allocation", "todai-listening",
        "todai-english-review", "todai-math-review",
        "todai-bunkei-math-strategy", "todai-kakomon-review", "todai-math-2026-3",
    ],
    "/specialty/": [
        "kakomon-score-stuck", "mock-exam-review", "shiboukou-sageru",
        "heiganko-kimekata", "gokaku-happyo-tetsuzuki",
    ],
    "/pricing/": [
        "private-tutoring-fees", "choosing-a-juku", "coaching-vs-private-tutoring",
        "materials-catalog",
    ],
    "/specialty/kyotsu-test/": [
        "kyotsu-6weeks-student", "kyotsu-test-final-stage", "kyotsu-test-last-week",
        "kyotsu-zenjitsu-tojitsu", "kyotsu-after-switch", "kyotsu-self-scoring",
        "kyotsu-riyo-nyushi", "kyotsu-english-time", "kyotsu-listening",
        "joho-1-taisaku",
    ],
    "/specialty/eigo/": [
        "eitango-teichaku", "english-reading-diagnosis", "eigo-gaibu-kentei-nyushi",
        "kyotsu-listening", "kyotsu-english-time", "todai-english-strategy",
    ],
    "/specialty/sugaku/": [
        "math-self-solve", "math-bisekibun", "math-kakuritsu", "math-suretsu",
        "math-vector", "todai-bunkei-math-strategy", "todai-math-review",
    ],
    "/specialty/kokugo/": [
        "gendaibun-yomikata", "kobun-tango-bunpo", "kanbun-kuho",
        "kijutsu-kakenai", "mensetsu-taisaku",
    ],
    "/specialty/shakai/": [
        "nihonshi-nagare", "sekaishi-yoko", "kijutsu-kakenai",
    ],
    "/specialty/shoronbun/": [
        "shibou-riyusho", "mensetsu-taisaku", "kijutsu-kakenai",
    ],
    "/specialty/sogogata/": [
        "shibou-riyusho", "mensetsu-taisaku", "kijutsu-kakenai",
    ],
    "/specialty/suisen/": [
        "shibou-riyusho", "mensetsu-taisaku", "kijutsu-kakenai",
        "eigo-gaibu-kentei-nyushi",
    ],
    "/specialty/ronin/": [
        "gap-year-study-plan", "dokugaku-susumekata", "yaruki-tatenaoshi",
        "kakomon-score-stuck", "gokaku-happyo-tetsuzuki",
    ],
    "/specialty/takuro/": [
        "gap-year-study-plan", "dokugaku-susumekata", "weekly-study-plan",
        "yaruki-tatenaoshi", "kakomon-score-stuck",
    ],
    "/specialty/kou1-kou2/": [
        "spring-break-shin-kou3", "teiki-test-juken-ryoritsu",
        "weekly-study-plan", "winter-kou1", "ima-kara-maniau",
    ],
    "/specialty/kou3-schedule/": [
        "university-study-plan", "summer-break-study-plan",
        "winter-break-study-plan", "kyotsu-test-final-stage", "ima-kara-maniau",
        "joho-1-taisaku",
    ],
    "/specialty/tenjuku/": [
        "juku-yametai", "choosing-a-juku", "shinnendo-juku-erabi",
        "yobiko-vs-kojinjuku",
    ],
    "/specialty/igakubu-buntan/": [
        "shibou-riyusho", "mensetsu-taisaku", "kijutsu-kakenai",
        "kyotsu-self-scoring", "math-self-solve", "eitango-teichaku",
    ],
    "/specialty/joshi/": [
        "shibou-riyusho", "gendaibun-yomikata", "kobun-tango-bunpo",
    ],
    "/specialty/kokkouritsu/": [
        "nihonshi-nagare", "sekaishi-yoko", "kijutsu-kakenai",
        "kyotsu-self-scoring",
    ],
    "/specialty/march/": [
        "eitango-teichaku", "english-reading-diagnosis", "kobun-tango-bunpo",
    ],
    "/specialty/waseda/": [
        "eitango-teichaku", "english-reading-diagnosis", "gendaibun-yomikata",
    ],
    "/specialty/keio/": [
        "eitango-teichaku", "english-reading-diagnosis", "kijutsu-kakenai",
    ],
    "/specialty/todai-bunkei/": [
        "todai-bunkei-math-strategy", "todai-math-review", "todai-kakomon-review",
        "kijutsu-kakenai", "shibou-riyusho",
    ],
}

HUB_START = "<!-- r31:hub-guides:start -->"
HUB_END = "<!-- r31:hub-guides:end -->"


def guide_url(slug: str) -> str:
    return f"/study-guides/{slug}/"


def hub_block(path: Path, idx: dict[str, dict]) -> str:
    raw = path.read_text(encoding="utf-8")
    already = body_guide_links(raw)
    items = []
    for slug in HUBS[route(path)]:
        url = guide_url(slug)
        if url not in idx or url in already:
            continue
        items.append(f'<li><a href="{url}">{html.escape(idx[url]["label"])}</a></li>')
    if not items:
        return ""
    return (
        f"{HUB_START}\n"
        '<section class="r31-hub-guides" id="hub-guides">\n'
        "<h2>あわせて読む学習ガイド（無料）</h2>\n"
        "<p>このページの内容と関係の深い記事です。登録なしで読めます。</p>\n"
        f'<ul class="r31-hub-list">\n' + "\n".join(items) + "\n</ul>\n"
        "</section>\n"
        f"{HUB_END}"
    )


def insert_hub(raw: str, chunk: str) -> str:
    if HUB_START in raw:
        return re.sub(re.escape(HUB_START) + r".*?" + re.escape(HUB_END), chunk, raw, flags=re.S)
    for anchor in ('<nav aria-label="関連ページ"', '<div class="cta-box">', '<footer'):
        pos = raw.find(anchor)
        if pos != -1:
            return raw[:pos] + chunk + "\n" + raw[pos:]
    raise SystemExit("hub insertion point not found")



# 系列内の回遊（第10弾）。同じ大学群・同じエリアのページ同士をつなぐ。
# 各ページには、まだリンクしていない同系列のページを最大4本だけ置く。
CLUSTERS = [
    ("同じ大学の学部別対策", [
        "/specialty/keio/", "/specialty/keio-bungaku/", "/specialty/keio-hogaku/",
        "/specialty/keio-keizai/", "/specialty/keio-shogaku/", "/specialty/keio-sfc/",
        "/specialty/keio-shoronbun/",
    ]),
    ("早稲田大学の学部別対策", [
        "/specialty/waseda/", "/specialty/waseda-bungaku/", "/specialty/waseda-bunka-koso/",
        "/specialty/waseda-hogaku/", "/specialty/waseda-kokusai-kyoyo/",
        "/specialty/waseda-kyoiku/", "/specialty/waseda-seikei/",
        "/specialty/waseda-shakai-kagaku/", "/specialty/waseda-shogaku/",
        "/specialty/waseda-eigo/",
    ]),
    ("文京区・本郷エリアの指導ページ", [
        "/specialty/bunkyo/", "/specialty/korakuen/", "/specialty/myogadani/",
        "/specialty/edogawabashi/", "/specialty/gokokuji/", "/specialty/nezu/",
        "/specialty/yushima/", "/specialty/todaimae/", "/specialty/hongo-sanchome/",
        "/specialty/ochanomizu-eki/", "/specialty/iidabashi/", "/specialty/kasuga/",
        "/specialty/shinjuku/", "/specialty/chiyoda/",
    ]),
    ("関西の大学対策", [
        "/specialty/kobe/", "/specialty/osaka/", "/specialty/kyoto/",
        "/specialty/osaka-fu/", "/specialty/kansai/", "/specialty/kankandoritsu/",
        "/specialty/doshisha/", "/specialty/ritsumeikan/", "/specialty/kwansei-gakuin/",
    ]),
    ("MARCHの大学別対策", [
        "/specialty/march/", "/specialty/meiji/", "/specialty/aoyama-gakuin/",
        "/specialty/rikkyo/", "/specialty/chuo/", "/specialty/hosei/",
        "/specialty/march-eigo/",
    ]),
    ("東海地方の大学対策", [
        "/specialty/nagoya/", "/specialty/aichi/", "/specialty/gifu/",
        "/specialty/mie/", "/specialty/shizuoka/",
    ]),
    ("東京の国公立・女子大対策", [
        "/specialty/tokyo-toritsu/", "/specialty/tokyo-gakugei/",
        "/specialty/tokyo-gaigo/", "/specialty/ochanomizu/", "/specialty/tokyo-rika/",
    ]),
    ("学校生活と受験の両立", [
        "/specialty/chukou-ikkan/", "/specialty/kou1-kou2/", "/specialty/kou3-schedule/",
        "/specialty/tsushin-kou/", "/specialty/futoukou-tsushin/", "/specialty/takuro/",
    ]),
    ("二次試験・記述の対策", [
        "/specialty/nijishiken/", "/specialty/kokkouritsu/", "/specialty/igakubu-buntan/",
        "/specialty/ronin/", "/specialty/saijuken/",
    ]),
    ("東大の科目別対策", [
        "/specialty/todai-bunkei/", "/specialty/todai-kokugo/", "/specialty/sugaku/",
        "/specialty/eigo/", "/specialty/kokugo/",
    ]),
]

CLUSTER_START = "<!-- r31:cluster:start -->"
CLUSTER_END = "<!-- r31:cluster:end -->"


def cluster_block(path: Path, heading: str, members: list[str], idx_all: dict[str, dict],
                  inbound: dict[str, int]) -> str:
    url = route(path)
    raw = strip_blocks(path.read_text(encoding="utf-8"))
    already = set()
    for href in re.findall(r'href="([^"]+)"', raw):
        h = href.split("#")[0].split("?")[0]
        if h.startswith("/") and not re.search(r"\.[a-z0-9]+$", h):
            already.add(h if h.endswith("/") else h + "/")
    members = [m for m in members if m in idx_all]
    if url not in members:
        return ""
    i = members.index(url)
    picked = []
    for step in range(1, len(members)):
        other = members[(i + step) % len(members)]
        if other == url or other in already or other in picked:
            continue
        picked.append(other)
        if len(picked) == 4:
            break
    if not picked:
        return ""
    items = "\n".join(
        f'<li><a href="{m}">{html.escape(idx_all[m]["label"])}</a></li>' for m in picked
    )
    return (
        f"{CLUSTER_START}\n"
        '<section class="r31-cluster" id="cluster-pages">\n'
        f"<h2>{heading}</h2>\n"
        "<p>同じ系列のページです。志望校・環境が近いものを選んでください。</p>\n"
        f'<ul class="r31-cluster-list">\n{items}\n</ul>\n'
        "</section>\n"
        f"{CLUSTER_END}"
    )


def insert_cluster(raw: str, chunk: str) -> str:
    if CLUSTER_START in raw:
        return re.sub(re.escape(CLUSTER_START) + r".*?" + re.escape(CLUSTER_END), chunk, raw, flags=re.S)
    for anchor in ('<nav aria-label="関連ページ"', '<div class="cta-box">', '<footer'):
        pos = raw.find(anchor)
        if pos != -1:
            return raw[:pos] + chunk + "\n" + raw[pos:]
    raise SystemExit("cluster insertion point not found")


def block(url: str, idx: dict[str, dict], inbound: dict[str, int]) -> str:
    picked = pick(url, idx, inbound)
    if not picked:
        return ""
    items = "\n".join(
        f'<li><a href="{other}">{html.escape(idx[other]["label"])}</a>'
        f'<span class="r31-theme">（{reason}）</span></li>'
        for other, reason in picked
    )
    return (
        f"{START}\n"
        '<section class="r31-related" id="related-guides" aria-labelledby="related-guides-title">\n'
        '<h2 id="related-guides-title">あわせて読みたい学習ガイド</h2>\n'
        "<p>この記事と近いテーマの記事です。読み終えたら、次に必要な1本だけ選んでください。</p>\n"
        f'<ul class="r31-related-list">\n{items}\n</ul>\n'
        "</section>\n"
        f"{END}"
    )


def insert(raw: str, chunk: str) -> str:
    if START in raw:
        return re.sub(re.escape(START) + r".*?" + re.escape(END), chunk, raw, flags=re.S)
    for anchor in ('<section id="related-specialty">', '<section id="author-profile">', '<div class="cta-box">'):
        pos = raw.find(anchor)
        if pos != -1:
            return raw[:pos] + chunk + "\n" + raw[pos:]
    pos = raw.rfind("<footer")
    if pos == -1:
        raise SystemExit("insertion point not found")
    return raw[:pos] + chunk + "\n" + raw[pos:]


def bump_date(raw: str) -> str:
    raw = re.sub(r'(<meta content=")[0-9]{4}-[0-9]{2}-[0-9]{2}(" name="last-modified")',
                 lambda m: m.group(1) + TODAY + m.group(2), raw)
    raw = re.sub(r'("dateModified"\s*:\s*")[0-9]{4}-[0-9]{2}-[0-9]{2}(")',
                 lambda m: m.group(1) + TODAY + m.group(2), raw)
    raw = re.sub(r'(更新日：<time datetime=")[0-9]{4}-[0-9]{2}-[0-9]{2}(">)[0-9]{4}年[0-9]{1,2}月[0-9]{1,2}日',
                 lambda m: m.group(1) + TODAY + m.group(2) + "2026年11月28日", raw)
    return raw


def apply_once(args) -> int:
    idx = build_index()
    inbound = inbound_counts()
    idx_all = {}
    for path in PUBLIC.rglob("*.html"):
        raw = path.read_text(encoding="utf-8")
        idx_all[route(path)] = {"label": label_of(raw)}
    cluster_changed = 0
    for heading, members in CLUSTERS:
        for member in members:
            path = PUBLIC / member.strip("/") / "index.html"
            if not path.is_file():
                continue
            chunk = cluster_block(path, heading, members, idx_all, inbound)
            if not chunk:
                continue
            raw = path.read_text(encoding="utf-8")
            new = bump_date(insert_cluster(raw, chunk))
            if new != raw:
                cluster_changed += 1
                if not args.dry and not args.check:
                    path.write_text(new, encoding="utf-8")
    hub_changed = 0
    for hub in HUBS:
        path = PUBLIC / hub.strip("/") / "index.html"
        if not path.is_file():
            print(f"!! hub missing: {hub}")
            continue
        chunk = hub_block(path, idx)
        if not chunk:
            continue
        raw = path.read_text(encoding="utf-8")
        new = bump_date(insert_hub(raw, chunk))
        if new != raw:
            hub_changed += 1
            if not args.dry and not args.check:
                path.write_text(new, encoding="utf-8")
    changed = 0
    short = []
    for url in sorted(idx):
        info = idx[url]
        picked = pick(url, idx, inbound)
        if len(picked) < 3:
            short.append((url, len(picked)))
        chunk = block(url, idx, inbound)
        if not chunk:
            print(f"!! no candidates: {url}")
            continue
        if args.dry:
            print(url, "->", picked)
            continue
        new = bump_date(insert(info["raw"], chunk))
        if new != info["raw"]:
            changed += 1
            if not args.check:
                info["path"].write_text(new, encoding="utf-8")
    verb = "would update" if args.check else "updated"
    print(f"r31 related guides: {verb} {changed}/{len(idx)} guide pages")
    print(f"r31 hub guides: {verb} {hub_changed}/{len(HUBS)} hub pages")
    print(f"r31 clusters: {verb} {cluster_changed} pages")
    print(f"fewer than 3 links: {len(short)}")
    for url, n in short:
        print(f"  {url} ({n})")
    return changed + hub_changed + cluster_changed


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--dry", action="store_true")
    args = ap.parse_args()
    if args.dry or args.check:
        apply_once(args)
        return 0
    # 選び方が被リンク数に依存するため、変化がなくなるまで適用して固定点にする。
    for _ in range(5):
        if apply_once(args) == 0:
            break
    return 0


if __name__ == "__main__":
    sys.exit(main())
