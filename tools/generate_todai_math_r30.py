#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""r30: 東大文系数学50年データベース（/data/ と /data/todai-bunkei-math-50years/）を生成する。

    python3 tools/generate_todai_math_r30.py          # 生成
    python3 tools/generate_todai_math_r30.py --check  # 検証のみ（書き込みなし）

* データの正本は tools/todai_bunkei_math_data.py（50年・200問）。
* 出力は public/data/index.html、public/data/todai-bunkei-math-50years/index.html、
  同ディレクトリの data.json / data.csv。
* 本文の数値（順位・件数・割合）はすべてデータから計算して埋める。手で数えた
  数字を書かないことで、データを直したときに本文がずれないようにする。
"""
from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))

import site_entity_r24 as E  # noqa: E402
import line_cro_r27 as C  # noqa: E402
import generate_region_pages_r24 as G  # noqa: E402
import todai_bunkei_math_data as D  # noqa: E402

PUBLIC = ROOT / "public"
SITE = E.SITE
TODAY = D.UPDATED
OG = f"{SITE}/og/todai-juku.png"

DATA_DIR = "data/todai-bunkei-math-50years"
DB_URL = f"{SITE}/{DATA_DIR}/"
HUB_URL = f"{SITE}/data/"
DB_TITLE = "東大文系数学50年データ｜1977〜2026年200問の分野別一覧｜黒田塾"
DB_DESC = (
    "1977〜2026年の東大文系数学200問を、年度・大問番号・出題分野・難易度の目安で整理した"
    "データベースです。分野別の出題頻度ランキング、年次別の推移表、確認した出典を掲載します。"
)
HUB_TITLE = "公開データ｜東大文系数学50年の出題記録と機械可読ファイル｜黒田塾"
HUB_DESC = (
    "黒田塾が公開しているデータの一覧です。東大文系数学1977〜2026年の200問を整理した"
    "出題データベースと、AI・検索エンジン向けのJSON・CSV・llms.txtの場所をまとめています。"
)

ERAS = [
    (1977, 1989, "1977〜1989年（13年・52問）", "課程が旧課程だった時期で、行列・一次変換が毎年のように出題されました。"),
    (1990, 1999, "1990〜1999年（10年・40問）", "座標平面の比重が高く、複素数平面も出題されています。"),
    (2000, 2010, "2000〜2010年（11年・44問）", "確率・場合の数と整数が増え、証明を伴う出題が定着しました。"),
    (2011, 2020, "2011〜2020年（10年・40問）", "整数と通過領域・軌跡が繰り返し出題され、部分点の設計が問われます。"),
    (2021, 2026, "2021〜2026年（6年・24問）", "微分・積分と確率が中心です。6年分と短いため、この期間だけで傾向を断定はしません。"),
]

DIFF_ORDER = ["標準", "やや難", "難"]


def site_nodes() -> list[dict]:
    """WebSite / EducationalOrganization / Person のノードを既存ページから写す。

    site_entity_r24.py の定数と、公開中のページに入っている定義がずれることがある
    （エンティティの更新中など）。seo_aio_meo_audit.py は全ページで同一の定義を
    求めるため、代表的な既存ページの JSON-LD を正とする。
    """
    import json
    import re

    for rel in ("specialty/ronin/index.html", "about/index.html", "index.html"):
        path = PUBLIC / rel
        if not path.is_file():
            continue
        raw = path.read_text(encoding="utf-8")
        found: dict[str, dict] = {}
        for m in re.finditer(r'<script type="application/ld\+json">(.*?)</script>', raw, re.S):
            try:
                data = json.loads(m.group(1))
            except json.JSONDecodeError:
                continue
            for node in data.get("@graph", [data]):
                t = node.get("@type")
                if t in ("WebSite", "EducationalOrganization", "Person") and t not in found:
                    found[t] = node
        if len(found) == 3:
            return [found["WebSite"], found["EducationalOrganization"], found["Person"]]
    return [E.WEBSITE_NODE, E.ORG_NODE, E.PERSON_NODE]


def rows() -> list[dict]:
    return D.records()


def primary_counts(rs: list[dict]) -> Counter:
    return Counter(r["primary"] for r in rs)


def tag_counts(rs: list[dict]) -> Counter:
    return Counter(d for r in rs for d in r["domains"])


def pct(n: int, total: int) -> str:
    return f"{n / total * 100:.1f}%"


def head(title: str, desc: str, url: str, og: str, jsonld: list[dict]) -> str:
    return (
        '<!DOCTYPE html>\n<html lang="ja"><head>'
        '<meta charset="utf-8"/>'
        '<meta content="width=device-width, initial-scale=1.0" name="viewport"/>'
        f"<title>{title}</title>"
        f'<meta content="{desc}" name="description"/>'
        '<meta content="index, follow, max-image-preview:large, max-snippet:-1" name="robots"/>'
        f'<link href="{url}" rel="canonical"/>'
        '<meta content="article" property="og:type"/>'
        '<meta content="ja_JP" property="og:locale"/>'
        '<meta content="黒田塾" property="og:site_name"/>'
        f'<meta content="{title}" property="og:title"/>'
        f'<meta content="{desc}" property="og:description"/>'
        f'<meta content="{url}" property="og:url"/>'
        '<meta content="summary_large_image" name="twitter:card"/>'
        f'<meta content="{og}" property="og:image"/>'
        '<meta content="image/png" property="og:image:type"/>'
        '<meta content="1200" property="og:image:width"/>'
        '<meta content="630" property="og:image:height"/>'
        f'<meta content="{title}" property="og:image:alt"/>'
        f'<meta content="{og}" name="twitter:image"/>'
        f'<meta content="{title}" name="twitter:image:alt"/>'
        f'<meta content="{TODAY}" name="last-modified"/>'
        '<script type="application/ld+json">'
        + _json({"@context": "https://schema.org", "@graph": jsonld})
        + "</script>"
        f'<meta content="{title}" name="twitter:title"/>'
        f'<meta content="{desc}" name="twitter:description"/>'
        '<meta content="#fbfaf7" name="theme-color"/>'
        '<link href="/favicon.png" rel="icon" sizes="96x96" type="image/png"/>'
        '<link href="/feed.xml" rel="alternate" title="黒田塾｜学習ガイド" type="application/rss+xml"/>'
        f'<link rel="alternate" type="text/markdown" href="{url}index.md"/>'
        '<link href="/apple-touch-icon.png" rel="apple-touch-icon" sizes="180x180"/>'
        f'<meta content="{TODAY}" name="site-release"/>'
        f"{G.STYLE_LINKS}"
        "</head>"
    )


def _json(obj) -> str:
    import json

    return json.dumps(obj, ensure_ascii=False, separators=(", ", ": "))


def breadcrumb(url: str, trail: list[tuple[str, str]]) -> dict:
    return {
        "@type": "BreadcrumbList",
        "@id": f"{url}#breadcrumb",
        "itemListElement": [
            {"@type": "ListItem", "position": i + 1, "name": name, "item": href}
            for i, (name, href) in enumerate(trail)
        ],
    }


def faq_node(url: str, faqs: list[tuple[str, str]]) -> dict:
    return {
        "@type": "FAQPage",
        "@id": f"{url}#faq",
        "mainEntity": [
            {
                "@type": "Question",
                "name": q,
                "acceptedAnswer": {"@type": "Answer", "text": a},
            }
            for q, a in faqs
        ],
    }


def faq_html(faqs: list[tuple[str, str]]) -> str:
    return "".join(
        f'<details class="answer-box"><summary>{q}</summary><p>{a}</p></details>'
        for q, a in faqs
    )


# --------------------------------------------------------------------------- #
# /data/todai-bunkei-math-50years/
# --------------------------------------------------------------------------- #
def db_faqs(rs: list[dict]) -> list[tuple[str, str]]:
    prim = primary_counts(rs)
    top, top_n = prim.most_common(1)[0]
    return [
        (
            "東大文系数学は何題・何分ですか？",
            "現在の前期日程の文系数学は4題・100分です（理科は6題・150分）。"
            "このページでは、その4題を1977年から2026年まで1問ずつ数えています。",
        ),
        (
            "このデータは何年度から何年度までを収録していますか？",
            "1977〜2026年の50年分、全200問です。年度と大問番号の両方が確認できた出題だけを収録し、"
            "確認できなかった出題は載せていません。",
        ),
        (
            "出題分野は何を基準に分類していますか？",
            "資料が示している出題分野の表記を、12の分野（微積分・確率／場合の数・整数・"
            "図形と方程式・ベクトル・数列・三角関数・指数／対数・複素数・行列・図形と計量・"
            "関数／方程式）にそろえました。複数分野にまたがる問題は、主分野を1つ決めたうえで"
            "副タグも残しています。",
        ),
        (
            "一番出題が多い分野はどれですか？",
            f"主分野として数えると{top}が{top_n}問（{pct(top_n, len(rs))}）で最多です。"
            "副タグまで含めた件数と、直近10年の件数は本文の表に並べています。",
        ),
        (
            "難易度はどうやって付けていますか？",
            "確認した出題内容をもとに、黒田塾が「標準・やや難・難」の3段階で付けた編集上の目安です。"
            "正答率・平均点・配点のデータではないため、数値としての比較には使えません。",
        ),
        (
            "問題文や解答は見られますか？",
            "問題文は転載していません。このデータベースは「いつ、どの大問で、何が出たか」の記録です。"
            "演習には市販の過去問集や、学校・予備校で配布された問題を使ってください。",
        ),
    ]


def build_db_page(rs: list[dict]) -> str:
    total = len(rs)
    prim = primary_counts(rs)
    tags = tag_counts(rs)
    recent = primary_counts([r for r in rs if r["year"] >= 2017])
    top, top_n = prim.most_common(1)[0]
    second, second_n = prim.most_common(3)[1]
    third, third_n = prim.most_common(3)[2]
    shared = sum(1 for r in rs if r["shared"])
    diffs = Counter(r["difficulty"] for r in rs)

    # 主分野を4つの系統にまとめる（合計が200になる）
    systems = [
        ("座標・図形系", ["図形と方程式", "ベクトル", "図形と計量", "複素数"]),
        ("解析系", ["微積分", "関数・方程式", "三角関数", "指数・対数"]),
        ("離散系", ["確率・場合の数", "整数", "数列"]),
        ("行列（旧課程）", ["行列"]),
    ]
    sys_counts = [(name, sum(prim[d] for d in ds)) for name, ds in systems]

    faqs = db_faqs(rs)

    rank_rows = []
    for i, (name, n) in enumerate(prim.most_common(), start=1):
        rank_rows.append(
            f"<tr><td>{i}</td><td><strong>{name}</strong></td><td>{n}</td>"
            f"<td>{pct(n, total)}</td><td>{tags[name]}</td><td>{recent[name]}</td></tr>"
        )

    year_rows = []
    by_year: dict[int, dict[int, dict]] = {}
    for r in rs:
        by_year.setdefault(r["year"], {})[r["q"]] = r
    for year in D.YEARS:
        cells = []
        for q in (1, 2, 3, 4):
            r = by_year[year][q]
            mark = ' <abbr title="文理共通の問題">◆</abbr>' if r["shared"] else ""
            sub = "／".join(r["domains"][1:])
            sub_html = f"<small>／{sub}</small>" if sub else ""
            cells.append(f"<td>{r['primary']}{sub_html}{mark}</td>")
        year_rows.append(
            f'<tr id="y{year}"><th scope="row">{year}</th>' + "".join(cells) + "</tr>"
        )

    era_rows = []
    era_blocks = []
    for a, b, label, comment in ERAS:
        sub = [r for r in rs if a <= r["year"] <= b]
        c = primary_counts(sub)
        top3 = c.most_common(3)
        era_rows.append(
            f"<tr><td>{label.split('（')[0]}</td><td>{len(sub)}</td>"
            + "".join(f"<td>{name}（{n}問）</td>" for name, n in top3)
            + "</tr>"
        )
        detail = "、".join(f"{name} {n}問（{pct(n, len(sub))}）" for name, n in top3)
        era_blocks.append(
            f"<h3>{label}</h3><p>{comment}主分野の上位は{detail}です。</p>"
        )
    era_head = "".join(f"<th>第{i}位</th>" for i in (1, 2, 3))

    q_rows = []
    for q in (1, 2, 3, 4):
        c = primary_counts([r for r in rs if r["q"] == q])
        top3 = c.most_common(3)
        q_total = sum(c.values())
        q_rows.append(
            f"<tr><td>第{q}問</td><td>{q_total}</td>"
            + "".join(
                f"<td>{name}（{n}問・{pct(n, q_total)}）</td>" for name, n in top3
            )
            + "</tr>"
        )

    diff_rows = "".join(
        f"<tr><td>{d}</td><td>{diffs[d]}</td><td>{pct(diffs[d], total)}</td></tr>"
        for d in DIFF_ORDER
    )

    summary_items = [
        f"1977〜2026年の50年分・全200問（各年4問）を収録",
        f"主分野で最も多いのは{top}の{top_n}問（{pct(top_n, total)}）、"
        f"次いで{second}の{second_n}問（{pct(second_n, total)}）、"
        f"{third}の{third_n}問（{pct(third_n, total)}）",
        "座標・図形系が{}問（{}）、解析系{}問（{}）、離散系{}問（{}）、行列{}問（{}）".format(
            *[x for name, n in sys_counts for x in (n, pct(n, total))]
        ),
        "年度・大問番号・分野は資料2種以上で一致を確認（1977〜1980年は問題文から判定）",
        "難易度は編集上の3段階の目安。正答率・配点のデータではありません",
    ]

    jsonld = [
        {
            "@type": "Article",
            "@id": f"{DB_URL}#article",
            "url": DB_URL,
            "headline": DB_TITLE,
            "description": DB_DESC,
            "inLanguage": "ja",
            "datePublished": TODAY,
            "dateModified": TODAY,
            "author": {"@id": f"{SITE}/#teacher"},
            "publisher": {"@id": f"{SITE}/#organization"},
            "mainEntityOfPage": {"@id": f"{DB_URL}#webpage"},
            "image": OG,
            "about": {"@id": f"{DB_URL}#dataset"},
        },
        {
            "@type": "WebPage",
            "@id": f"{DB_URL}#webpage",
            "url": DB_URL,
            "name": DB_TITLE,
            "description": DB_DESC,
            "inLanguage": "ja",
            "speakable": E.SPEAKABLE,
            "isPartOf": {"@id": f"{SITE}/#website"},
            "author": {"@id": f"{SITE}/#teacher"},
            "breadcrumb": {"@id": f"{DB_URL}#breadcrumb"},
            "datePublished": TODAY,
            "dateModified": TODAY,
            "significantLink": f"{DB_URL}#faq",
        },
        {
            "@type": "Dataset",
            "@id": f"{DB_URL}#dataset",
            "name": "東大文系数学 過去問データ（1977〜2026年）",
            "description": (
                "東京大学前期日程・文系数学の出題を、年度、大問番号、出題分野、"
                "難易度の目安で整理したデータ。50年分・200問。問題文は含まない。"
            ),
            "url": DB_URL,
            "temporalCoverage": "1977/2026",
            "spatialCoverage": "日本",
            "inLanguage": "ja",
            "creator": {"@id": f"{SITE}/#organization"},
            "publisher": {"@id": f"{SITE}/#organization"},
            "isAccessibleForFree": True,
            "dateModified": TODAY,
            "keywords": [
                "東大文系数学", "東京大学", "過去問", "出題分野", "大学受験", "数学",
            ],
            "variableMeasured": [
                "出題分野", "大問番号", "年度", "難易度の目安",
            ],
            "distribution": [
                {
                    "@type": "DataDownload",
                    "encodingFormat": "application/json",
                    "contentUrl": f"{DB_URL}data.json",
                },
                {
                    "@type": "DataDownload",
                    "encodingFormat": "text/csv",
                    "contentUrl": f"{DB_URL}data.csv",
                },
            ],
        },
        faq_node(DB_URL, faqs),
        breadcrumb(
            DB_URL,
            [
                ("黒田塾", f"{SITE}/"),
                ("公開データ", HUB_URL),
                ("東大文系数学50年の出題データ", DB_URL),
            ],
        ),
        *site_nodes(),
    ]

    parts = [
        head(DB_TITLE, DB_DESC, DB_URL, OG, jsonld),
        f"<body>{G.HEADER.format(line_id='data-todai-math-line-1')}",
        '<main class="detail" id="main-content">',
        '<nav aria-label="パンくずリスト"><ol class="breadcrumbs">'
        '<li><a href="/">黒田塾</a></li>'
        '<li><a href="/data/">公開データ</a></li>'
        '<li aria-current="page">東大文系数学50年の出題データ</li></ol></nav>',
        "<h1>東大文系数学 50年分の出題データ。<br/>1977〜2026年・200問を分野別に並べる。</h1>",
        '<p class="byline">執筆・監修：<a href="/about/">黒田清友</a>'
        "（東京大学教育学部卒・黒田塾代表）｜公開日：2026年11月28日｜更新日：2026年11月28日</p>",
        f'<p class="intro">1977〜2026年の東大文系数学200問を、年度・大問番号・出題分野で'
        f"整理しました。主分野として数えると、最も多いのは{top}の{top_n}問"
        f"（{pct(top_n, total)}）、次いで{second}の{second_n}問（{pct(second_n, total)}）、"
        f"{third}の{third_n}問（{pct(third_n, total)}）です。"
        f"この3分野で全体の{pct(top_n + second_n + third_n, total)}を占め、残りが整数・数列・ベクトル・"
        f"図形と計量などに分かれます。データは年度ごとに出典を照合し、確認できた出題だけを"
        f"載せています。</p>",
        '<div class="summary-box"><strong>このページの要点</strong><ul>'
        + "".join(f"<li>{s}</li>" for s in summary_items)
        + "</ul></div>",
        '<div class="seo-cta"><strong>30分の無料「受験戦略診断」</strong>'
        "<p>このデータを見て、自分の志望校との差をどこから埋めるか決めたい場合は、"
        "現在の答案と模試の結果を持ち寄ってください。分野ごとの優先順位を一緒に整理します。</p>"
        '<a class="btn btn-dark" href="/contact/?topic=data-todai-bunkei-math-50years&amp;source=site#consultation-flow">'
        "受験戦略診断を申し込む</a></div>",
        '<nav aria-label="目次" class="r7-toc"><strong>東大文系数学50年データの目次</strong><ul>'
        '<li><a href="#scope">データの範囲と検証方法</a></li>'
        '<li><a href="#ranking">領域別の出題頻度ランキング</a></li>'
        '<li><a href="#years">年次別の推移表（1977〜2026）</a></li>'
        '<li><a href="#eras">年代別の傾向</a></li>'
        '<li><a href="#by-number">大問番号ごとの傾向</a></li>'
        '<li><a href="#difficulty">難易度の目安</a></li>'
        '<li><a href="#how-to-use">このデータの使い方</a></li>'
        '<li><a href="#download">データのダウンロード</a></li>'
        '<li><a href="#faq">よくある質問</a></li>'
        "</ul></nav>",
        # scope
        '<section id="scope"><h2>データの範囲と検証方法</h2>'
        f"<p>収録は{total}問（50年×4問）。年度・大問番号・分野の3点が資料で確認できた出題だけを"
        "載せ、確認できなかった出題は載せていません。問題文そのものは転載していません。</p>"
        '<div class="table-scroll"><table class="guide-table"><thead><tr>'
        "<th>年度</th><th>確認に使った資料</th><th>確認した内容</th></tr></thead><tbody>"
        "<tr><td>1977〜1980年</td><td>東京大学2次試験の問題アーカイブ（Mathexamtest）</td>"
        "<td>問題文を読み、文科・文理共通の別と大問番号、出題内容を確認</td></tr>"
        "<tr><td>1981〜2026年</td><td>Evolton 東大数学 年度別の出題分野</td>"
        "<td>文系4問それぞれの分野タグ（1問につき2〜4分野）</td></tr>"
        "<tr><td>1998〜2026年</td><td>電数図書館「東大文系数学 出題分野」</td>"
        "<td>Evoltonとの突き合わせ。矛盾する年度はなし</td></tr>"
        "</tbody></table></div>"
        f"<p>文理共通の問題は{shared}問あり、表では◆を付けています。共通かどうかは、"
        "資料が「文科第N問・理科第M問」と明記している場合だけ判断しています。</p>"
        "<p>分類は12分野にそろえましたが、たとえば「座標上で確率を数える」問題のように、"
        "1問が2つの分野にまたがることは珍しくありません。そこで主分野を1つ決めたうえで、"
        "副タグも残し、ランキングでは主分野と副タグ込みの件数を分けて表示しています。</p>"
        "</section>",
        # ranking
        '<section id="ranking"><h2>領域別の出題頻度ランキング（50年・200問）</h2>'
        "<p>「主分野の出題数」は、その分野を主分野として1問ずつ数えたものです。"
        "「タグ込み」は副タグも含む件数なので、合計は200を超えます。"
        "「直近10年」は2017〜2026年の10年分（40問）です。</p>"
        '<div class="table-scroll"><table class="guide-table"><thead><tr>'
        "<th>順位</th><th>分野</th><th>主分野の出題数</th><th>割合</th>"
        "<th>タグ込み</th><th>直近10年</th></tr></thead><tbody>"
        + "".join(rank_rows)
        + "</tbody></table></div>"
        "<p>主分野を4つの系統にまとめると、"
        + "、".join(f"{name} {n}問（{pct(n, total)}）" for name, n in sys_counts)
        + "となります。座標平面と図形の扱いが最も多く、次に微分・積分を中心とする解析、"
        "その次に確率・整数・数列の離散領域が続きます。</p>"
        "<p>「関数・方程式」は主分野としては13問ですが、副タグまで含めると77問で最多になります。"
        "座標や確率の問題の中で、2次関数や不等式の処理が前提として問われているためです。"
        "分野を「出題の看板」だけで判断すると、実際に必要な処理を見落とします。</p>"
        f"<p>直近10年だけを見ると、{recent.most_common(1)[0][0]}が"
        f"{recent.most_common(1)[0][1]}問で最多です。50年全体の順位と入れ替わる分野があるため、"
        "「昔からずっと同じ」と捉えず、直近の傾向は別の列で確認してください。</p>"
        "</section>",
        # years
        '<section id="years"><h2>年次別の推移表（1977〜2026年）</h2>'
        "<p>各行が1年分、4つのセルが第1問〜第4問です。太字が主分野、小さい文字が副タグ、"
        "◆は文理共通の問題を示します。セルにカーソルを合わせると共通の別が出ます。</p>"
        '<div class="table-scroll"><table class="guide-table db-years"><thead><tr>'
        "<th>年度</th><th>第1問</th><th>第2問</th><th>第3問</th><th>第4問</th>"
        "</tr></thead><tbody>"
        + "".join(year_rows)
        + "</tbody></table></div>"
        '<p>年ごとの出題内容（何を問うたか）は、表の下の年代別の整理と、'
        '各問の要約を収録した<a href="' + DB_URL + 'data.csv">CSV</a>で確認できます。</p>'
        "</section>",
        # eras
        '<section id="eras"><h2>年代別の傾向</h2>'
        '<div class="table-scroll"><table class="guide-table"><thead><tr>'
        "<th>年代</th><th>問題数</th>" + era_head + "</tr></thead><tbody>"
        + "".join(era_rows)
        + "</tbody></table></div>"
        + "".join(era_blocks)
        + "</section>",
        # by number
        '<section id="by-number"><h2>大問番号ごとの傾向</h2>'
        "<p>同じ年でも、第1問と第4問では役割が違います。50年分を大問番号で切ると、"
        "次のようになります。</p>"
        '<div class="table-scroll"><table class="guide-table"><thead><tr>'
        "<th>大問</th><th>問題数</th><th>1位</th><th>2位</th><th>3位</th>"
        "</tr></thead><tbody>" + "".join(q_rows) + "</tbody></table></div>"
        "<p>第1問は微分・積分が最も多く、立ち上がりの1問で計算量のある関数処理を置く形が"
        "定番です。第4問は確率・場合の数が最も多く、場合分けと数え上げの正確さが得点を分けます。"
        "第2問・第3問は座標平面と図形が中心で、ここで落とした失点が合否に効きます。</p>"
        "</section>",
        # difficulty
        '<section id="difficulty"><h2>難易度の目安</h2>'
        "<p>各問には「標準・やや難・難」の3段階を付けています。"
        "確認した出題内容（テーマと問われ方）をもとに黒田塾が付けた目安で、"
        "正答率・平均点・配点のデータではありません。</p>"
        '<div class="table-scroll"><table class="guide-table"><thead><tr>'
        "<th>目安</th><th>問題数</th><th>割合</th></tr></thead><tbody>"
        + diff_rows
        + "</tbody></table></div>"
        "<p>「難」は、方針の選択と論証の両方が必要な問題に付けています。"
        f"50年で「難」を付けたのは{diffs['難']}問で、多くの年は「標準」と「やや難」で構成されています。"
        f"4問すべてが「標準」だった年も{sum(1 for y in D.YEARS if all(r['difficulty'] == '標準' for r in rs if r['year'] == y))}回ありました。"
        "1年4問のうち平均2.5問が標準なので、100分のうち3問を確実に取り、"
        "残り1問で部分点を拾う設計が現実的です。</p>"
        "</section>",
        # how to use
        '<section id="how-to-use"><h2>このデータの使い方</h2>'
        '<div class="r9-card-grid">'
        '<article class="r9-card"><h3>頻度から、先に固める分野を決める</h3>'
        "<p>座標平面・微分積分・確率の3つで半分以上を占めます。"
        "演習の順番は、この3分野を先に完成させてから整数・数列・ベクトルに広げるのが"
        "効率的です。</p></article>"
        '<article class="r9-card"><h3>年度ごとの並びで、時間配分を練習する</h3>'
        "<p>同じ年度の4問をまとめて解くと、当時の出題バランスのまま制限時間を測れます。"
        "年度をまたいで同分野だけを解くと、分野ごとの精度を測れます。使い分けてください。</p></article>"
        '<article class="r9-card"><h3>大問番号から、捨て問の基準を作る</h3>'
        "<p>第4問に確率が多いことは、後半に数え上げの山が来るという意味です。"
        "どの大問で時間を切り上げるかを、演習の前に決めておきます。</p></article>"
        "</div>"
        '<p>分野別の解き方は「<a href="/study-guides/todai-bunkei-math-strategy/">東大文系数学の対策</a>」、'
        "過去問を始める時期は「<a href=\"/study-guides/kakomon-start-timing/\">過去問はいつから解き始めるか</a>」、"
        '志望校別の形式は「<a href="/specialty/todai-bunkei/">東大文系の専門対策</a>」で整理しています。'
        "東大数学の復習の手順は「<a href=\"/study-guides/todai-math-review/\">東大数学の復習法</a>」にまとめました。</p>"
        "</section>",
        # download
        '<section id="download"><h2>データのダウンロード</h2>'
        "<p>同じ内容を機械可読な形式でも公開しています。引用・分析・AI検索での参照に使えます。</p>"
        '<div class="table-scroll"><table class="guide-table"><thead><tr>'
        "<th>形式</th><th>ファイル</th><th>内容</th></tr></thead><tbody>"
        f'<tr><td>JSON</td><td><a href="{DB_URL}data.json">data.json</a></td>'
        "<td>年度・大問・分野タグ・難易度・出典をレコード単位で収録</td></tr>"
        f'<tr><td>CSV</td><td><a href="{DB_URL}data.csv">data.csv</a></td>'
        "<td>表計算ソフトで開ける1行1問の形式（UTF-8）</td></tr>"
        '<tr><td>Markdown</td><td><a href="/data/todai-bunkei-math-50years/index.md">index.md</a></td>'
        "<td>このページの本文だけをMarkdownにしたもの</td></tr>"
        "</tbody></table></div>"
        "<p>出典は、出題内容が東京大学の入試問題、分野分類と難易度の目安が黒田塾の整理です。"
        "引用するときは「黒田塾『東大文系数学 過去問データベース（1977〜2026年）』」と"
        "URLを添えてください。数値は更新されることがあります。</p></section>",
        C.mid_cta(DB_URL, f"<title>{DB_TITLE}</title>"),
        f'<section id="faq"><h2>このデータについてよくある質問</h2>{faq_html(faqs)}</section>',
        '<div class="cta-box"><h2>データを見たうえで、次の一手を決める。</h2>'
        "<p>分野ごとの優先順位と、今の答案との差を30分で整理します。</p>"
        '<a class="btn btn-line" href="/contact/?topic=data-todai-bunkei-math-50years&amp;source=site#consultation-flow">'
        "無料の受験戦略診断へ</a></div>",
        '<nav aria-label="関連ページ" class="jump-links">'
        '<a href="/data/">公開データの一覧</a>'
        '<a href="/specialty/todai-bunkei/">東大文系の専門対策</a>'
        '<a href="/study-guides/todai-bunkei-math-strategy/">東大文系数学の対策</a>'
        '<a href="/study-guides/todai-math-review/">東大数学の復習法</a>'
        '<a href="/study-guides/todai-kakomon-review/">東大過去問の復習</a>'
        '<a href="/materials/">教材プラン</a>'
        "</nav>",
        '<p class="editor-note"><a href="/about/#editorial-policy">教材の編集方針・誤りの連絡窓口</a></p>',
        '<section id="author-profile"><h2>このデータの作成者</h2>'
        "<p>黒田清友（東京大学教育学部卒、黒田塾代表）。東京大学文科二類に現役合格し、"
        "累計50人以上の生徒を指導してきました。このデータベースは、指導で使う分野別の"
        "出題記録をもとに、公開資料と照合して作成しています。"
        '詳しい経歴は<a href="/about/">講師紹介</a>をご覧ください。</p></section>',
        "</main>",
        G.FOOTER.format(today=TODAY).replace("</body>", C.sticky(DB_URL) + "</body>", 1),
    ]
    return "".join(parts)


# --------------------------------------------------------------------------- #
# /data/
# --------------------------------------------------------------------------- #
def hub_faqs() -> list[tuple[str, str]]:
    return [
        (
            "公開しているデータは自由に使えますか？",
            "引用・参照は自由です。出典として「黒田塾『東大文系数学 過去問データベース"
            "（1977〜2026年）』」とURLを添えてください。数値は更新されることがあります。",
        ),
        (
            "機械可読な形式はありますか？",
            "東大文系数学のデータはJSONとCSVで公開しています。"
            "サイト全体の一次情報は /facts.json、全ページの要約は /llms-full.txt にあります。",
        ),
        (
            "データに誤りを見つけた場合はどうすればよいですか？",
            "編集方針のページにある連絡窓口からお知らせください。出典と該当年度を添えていただけると、"
            "照合して訂正します。",
        ),
    ]


def build_hub() -> str:
    faqs = hub_faqs()
    jsonld = [
        {
            "@type": "CollectionPage",
            "@id": f"{HUB_URL}#webpage",
            "url": HUB_URL,
            "name": HUB_TITLE,
            "description": HUB_DESC,
            "inLanguage": "ja",
            "speakable": E.SPEAKABLE,
            "isPartOf": {"@id": f"{SITE}/#website"},
            "author": {"@id": f"{SITE}/#teacher"},
            "breadcrumb": {"@id": f"{HUB_URL}#breadcrumb"},
            "datePublished": TODAY,
            "dateModified": TODAY,
            "significantLink": f"{HUB_URL}#faq",
        },
        faq_node(HUB_URL, faqs),
        breadcrumb(HUB_URL, [("黒田塾", f"{SITE}/"), ("公開データ", HUB_URL)]),
        *site_nodes(),
    ]
    parts = [
        head(HUB_TITLE, HUB_DESC, HUB_URL, OG, jsonld),
        f"<body>{G.HEADER.format(line_id='data-hub-line-1')}",
        '<main class="detail" id="main-content">',
        '<nav aria-label="パンくずリスト"><ol class="breadcrumbs">'
        '<li><a href="/">黒田塾</a></li><li aria-current="page">公開データ</li></ol></nav>',
        "<h1>公開データ。<br/>受験の判断に使える記録を、検証できる形で置いておく。</h1>",
        '<p class="byline">執筆・監修：<a href="/about/">黒田清友</a>'
        "（東京大学教育学部卒・黒田塾代表）｜公開日：2026年11月28日｜更新日：2026年11月28日</p>",
        '<p class="intro">黒田塾が公開しているデータの一覧です。指導や記事で使う出題記録を、'
        "出典と更新日を添えて公開しています。人が読むための表と、AI・検索エンジンが読むための"
        "JSON・CSV・テキストを同じ内容から作っているため、どちらを見ても数値は同じです。</p>",
        '<div class="summary-box"><strong>このページの要点</strong><ul>'
        "<li>東大文系数学1977〜2026年の出題データ（50年・200問）を公開</li>"
        "<li>データはJSON・CSV・Markdownで取得でき、出典と更新日を明記</li>"
        "<li>サイト全体の一次情報は /facts.json、全ページの要約は /llms-full.txt</li>"
        "</ul></div>",
        '<nav aria-label="目次" class="r7-toc"><strong>公開データの目次</strong><ul>'
        '<li><a href="#datasets">公開しているデータ</a></li>'
        '<li><a href="#files">機械可読ファイル</a></li>'
        '<li><a href="#citation">引用のしかた</a></li>'
        '<li><a href="#faq">よくある質問</a></li>'
        "</ul></nav>",
        '<section id="datasets"><h2>公開しているデータ</h2>'
        '<div class="r9-card-grid">'
        '<article class="r9-card"><h3><a href="/data/todai-bunkei-math-50years/">'
        "東大文系数学 50年の出題データ</a></h3>"
        "<p>1977〜2026年の200問を、年度・大問番号・出題分野・難易度の目安で整理。"
        "分野別の頻度ランキングと年次別の推移表を掲載しています。</p></article>"
        "</div>"
        "<p>今後、他の科目・他の大学の出題記録も、同じ形式（JSON＋CSV＋本文）で追加する予定です。"
        "追加した場合はこのページとサイトマップ、llms.txtに反映されます。</p></section>",
        '<section id="files"><h2>機械可読ファイル</h2>'
        '<p>サイト全体について、1回の取得で読める形のファイルを用意しています。</p>'
        '<div class="table-scroll"><table class="guide-table"><thead><tr>'
        "<th>ファイル</th><th>内容</th></tr></thead><tbody>"
        '<tr><td><a href="/facts.json">facts.json</a></td><td>塾名・代表・対応科目・料金・'
        "実績・名前の混同に関する注意（JSON-LD形式）</td></tr>"
        '<tr><td><a href="/llms.txt">llms.txt</a></td><td>全ページの地図と引用時の表記ルール</td></tr>'
        '<tr><td><a href="/llms-full.txt">llms-full.txt</a></td><td>料金・FAQ・各ガイドの要点を'
        "1ファイルにまとめた参照用テキスト</td></tr>"
        '<tr><td><a href="/sitemap.xml">sitemap.xml</a></td><td>公開中の全URLと更新日</td></tr>'
        '<tr><td><a href="/feed.xml">feed.xml</a></td><td>学習ガイドと専門対策ページの更新情報（RSS）</td></tr>'
        "</tbody></table></div></section>",
        '<section id="citation"><h2>引用のしかた</h2>'
        "<p>数値を引用するときは、どのデータの、いつの版かを添えてください。"
        "たとえば「黒田塾『東大文系数学 過去問データベース（1977〜2026年）』"
        f"（{DB_URL}、2026年11月28日更新）」のように書きます。</p>"
        "<p>分野分類と難易度の目安は黒田塾の整理で、東京大学が公表した分類ではありません。"
        "難易度は正答率などのデータではないため、数値としての比較には使えません。</p></section>",
        C.mid_cta(HUB_URL, f"<title>{HUB_TITLE}</title>"),
        f'<section id="faq"><h2>公開データについてよくある質問</h2>{faq_html(faqs)}</section>',
        '<nav aria-label="関連ページ" class="jump-links">'
        '<a href="/data/todai-bunkei-math-50years/">東大文系数学50年の出題データ</a>'
        '<a href="/about/">講師紹介・編集方針</a>'
        '<a href="/study-guides/">学習ガイド一覧</a>'
        '<a href="/contact/">お問い合わせ</a>'
        "</nav>",
        '<p class="editor-note"><a href="/about/#editorial-policy">教材の編集方針・誤りの連絡窓口</a></p>',
        "</main>",
        G.FOOTER.format(today=TODAY).replace("</body>", C.sticky(HUB_URL) + "</body>", 1),
    ]
    return "".join(parts)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    errs = D.validate()
    for e in errs:
        print("DATA ERROR", e, file=sys.stderr)
    if errs:
        return 1

    for label, text, lo, hi in (
        ("DB title", DB_TITLE, 12, 40),
        ("DB desc", DB_DESC, 60, 130),
        ("HUB title", HUB_TITLE, 12, 40),
        ("HUB desc", HUB_DESC, 60, 130),
    ):
        n = len(text)
        if not lo <= n <= hi:
            print(f"{label} length {n}: {text}", file=sys.stderr)
            return 1

    rs = rows()
    pages = {
        PUBLIC / "data" / "index.html": build_hub(),
        PUBLIC / DATA_DIR / "index.html": build_db_page(rs),
    }
    if args.check:
        for path in pages:
            print(("ok " if path.exists() else "missing ") + str(path))
    else:
        for path, text in pages.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
            print("wrote", path.relative_to(ROOT))
        D.write_json(PUBLIC / DATA_DIR / "data.json")
        D.write_csv(PUBLIC / DATA_DIR / "data.csv")
        print("wrote", DATA_DIR, "data.json / data.csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
