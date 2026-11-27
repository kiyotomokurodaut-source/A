#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""r24: 全国47都道府県の地域ページを生成する。

    python3 tools/generate_region_pages_r24.py          # 生成
    python3 tools/generate_region_pages_r24.py --check  # 生成せず検証のみ

* 未作成の都道府県について public/specialty/<slug>/index.html を書き出す。
* r25（2026-11-27）以降の方針はオンライン専業・全国47都道府県対応。教室としての
  住所・電話・通塾案内は本文にも構造化データにも置かない。
* 既存の /specialty/tokyo/ など4ページと /specialty/ には、
  地域リンクのブロックをマーカー間だけ差し替えて挿入する（本文は触らない）。
* 地名の置換だけにならないよう、本文・FAQ・大学一覧は prefecture_data_r24.py の
  都道府県別データから組み立てる。
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import prefecture_data_r24 as D  # noqa: E402
import site_entity_r24 as E  # noqa: E402
import line_cro_r27 as C  # noqa: E402
import internal_links_r27 as IL  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "public"
SITE = E.SITE
TODAY = "2026-11-27"
OG_IMAGE = f"{SITE}/og/university-exam.png"
PLANS = (
    "面談のみ24,000円、授業のみ（週1回）30,000円、面談＋授業は週1回54,990円・"
    "週2回79,990円・週3回104,990円（いずれも月額・税込・月4セット）"
)

# 既に都道府県ページがあるのは東京都のみ。
# /specialty/saitama/ などは大学別ページなので、県ページは saitama-ken などのslugを持つ。
EXISTING_INFO = {"tokyo": ("東京都", "文京区")}

# 大学別ページが同じslugを使っている県は、その大学ページへ内部リンクする
UNI_LINK = {
    "saitama-ken": ("saitama", "埼玉大学"),
    "chiba-ken": ("chiba", "千葉大学"),
    "osaka-fu": ("osaka", "大阪大学"),
}


def pref_name(slug: str) -> str:
    if slug in D.PREFECTURES:
        return D.PREFECTURES[slug]["name"]
    return EXISTING_INFO[slug][0]


def block_of(slug: str) -> str:
    for name, slugs in D.BLOCKS:
        if slug in slugs:
            return name
    raise KeyError(slug)


HEADER = """<a class="skip-link" href="#main-content">本文へ移動</a><header>
<div class="wrap nav">
<a aria-label="黒田塾 トップページ" class="logo" href="/">
<svg aria-hidden="true" fill="none" viewbox="0 0 24 24"><path d="M12 3C10 8 5 11 3 12c2 1 7 4 9 9 2-5 7-8 9-9-2-1-7-4-9-9Z" fill="#b1922f"></path><path d="M12 6v13" stroke="#fbfaf7" stroke-width="1.1"></path></svg>
      黒田塾
    </a>
<nav aria-label="主要ページと指導案内" class="nav-links">
<a href="/#method">黒田式とは</a>
<a href="/pricing/">継続受講（月額）</a>
<a href="/materials/">教材プラン（買い切り）</a>
<a href="/about/">講師紹介</a>
<a href="/study-guides/">学び方ガイド</a>
</nav>
<a class="nav-cta" href="https://lin.ee/VKV65IQ" rel="noopener" target="_blank" data-line-cta="{line_id}">無料相談を申し込む</a>
</div>
<details class="mobile-menu wrap"><summary>指導案内・学習ガイドを開く</summary><nav aria-label="モバイルメニュー"><a href="/">トップページ</a><a href="/online-tutoring/">オンライン家庭教師</a><a href="/junior-high-exam/">中学受験</a><a href="/university-exam/">大学受験</a><a href="/study-guides/">学習ガイド</a><a href="/cases/">指導事例</a><a href="/about/">講師紹介</a><a href="/pricing/">料金</a><a href="/faq/">よくある質問</a><a href="/contact/">無料受験診断</a><a href="/study-coaching/">学習管理のみ</a><a href="/juku/">塾を探している方へ</a><a href="/todai-juku/">東大受験</a></nav></details></header>"""

FOOTER = """<footer><div class="wrap"><p class="footer-group"><strong>サービス</strong></p><nav aria-label="サービス" class="footer-links"><a href="/pricing/">継続受講の料金</a><a href="/materials/">教材プラン</a><a href="/online-tutoring/">オンライン受講</a><a href="/study-coaching/">学習管理・コーチング</a></nav><p class="footer-group"><strong>黒田塾について</strong></p><nav aria-label="黒田塾について" class="footer-links"><a href="/#method">黒田式メソッド</a><a href="/about/">講師紹介</a><a href="/contact/">お問い合わせ</a></nav><p class="footer-group"><strong>学び方ガイド</strong></p><nav aria-label="学び方ガイド" class="footer-links"><a href="/study-guides/">学習ガイド一覧</a></nav><p>黒田塾｜講師：黒田清友（東京大学教育学部卒）</p><p>© 2026 Kuroda Juku — Private Tutor</p><small class="release-marker">公開版 {today}</small></div><nav class="footer-nav legal-nav" aria-label="販売条件と個人情報"><a href="/materials/terms/">教材の購入条件</a><a href="/legal/">特定商取引法に基づく表記</a><a href="/privacy/">プライバシーポリシー</a></nav></footer><script defer="" src="/assets/acquisition-context-r22-bafa9a64e65c.js"></script></body></html>"""

STYLE_LINKS = (
    '<link href="/assets/site-r13-94a529657bd3.css" rel="stylesheet"/>'
    '<link href="/assets/conversion-r14-8afd3127941f.css" rel="stylesheet"/>'
    '<script defer="True" src="/assets/line-navigation-r15-bcf937681291.js"></script>'
    '<link href="/assets/search-guide-r15-07e09aa80f72.css" rel="stylesheet"/>'
    '<link rel="stylesheet" href="/assets/r17-components-3ce7c136239f.css"/>'
    '<script defer src="/assets/r17-components-7643958526ba.js"></script>'
    '<link rel="stylesheet" href="/assets/growth-r20-669164207105.css"/>'
    + C.CSS_LINK
)


def region_links(slug: str, heading: bool = True) -> str:
    block = block_of(slug)
    slugs = dict(D.BLOCKS)[block]
    others = [s for s in slugs if s != slug]
    links = "".join(
        f'<a href="/specialty/{s}/">{pref_name(s)}</a>' for s in others
    )
    body = (
        f'<nav aria-label="{block}の都道府県ページ" class="jump-links">{links}</nav>'
    )
    if not heading:
        return body
    return (
        f'<section id="regions"><h2>{block}の都道府県ページ</h2>'
        f"<p>同じ地方の都道府県からも探せるよう、一覧を並べています。"
        f"どのページからでも、指導内容と料金は共通です。</p>"
        f"{body}"
        f'<p><a href="/specialty/">大学受験の専門対策トップ</a>から全国47都道府県の'
        f"ページを一覧できます。</p></section>"
    )


def all_prefectures_section() -> str:
    parts = [
        '<section id="prefectures"><h2>全国47都道府県の大学受験対策ページ</h2>',
        "<p>黒田塾はオンライン専業の個別指導で、教室は設けていません。日本全国47"
        "都道府県から、同じ料金・同じ内容で受講できます。住んでいる地域の受験環境に"
        "合わせた読み物として、47都道府県すべてにページを用意しています。</p>",
    ]
    for block, slugs in D.BLOCKS:
        links = "".join(f'<a href="/specialty/{s}/">{pref_name(s)}</a>' for s in slugs)
        parts.append(f"<h3>{block}</h3>")
        parts.append(
            f'<nav aria-label="{block}の都道府県ページ" class="jump-links">{links}</nav>'
        )
    parts.append(
        "<p>どの都道府県のページも、案内しているのはオンラインでの受講です。"
        "現地に教室・校舎はありません。指導はすべてビデオ通話またはテキストで行い、"
        "答案は撮影して共有します。</p></section>"
    )
    return "".join(parts)


def jsonld(slug: str, d: dict) -> str:
    url = f"{SITE}/specialty/{slug}/"
    faqs = faq_items(slug, d)
    graph = [
        {
            "@type": "WebPage",
            "@id": f"{url}#webpage",
            "url": url,
            "name": d["title"],
            "description": d["desc"],
            "inLanguage": "ja",
            "speakable": E.SPEAKABLE,
            "isPartOf": {"@id": f"{SITE}/#website"},
            "about": {"@id": f"{url}#service"},
            "author": {"@id": f"{SITE}/#teacher"},
            "breadcrumb": {"@id": f"{url}#breadcrumb"},
            "datePublished": TODAY,
            "dateModified": TODAY,
            "significantLink": f"{url}#faq",
        },
        {
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
        },
        {
            "@type": "BreadcrumbList",
            "@id": f"{url}#breadcrumb",
            "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": "黒田塾", "item": f"{SITE}/"},
                {
                    "@type": "ListItem",
                    "position": 2,
                    "name": "大学受験の専門対策",
                    "item": f"{SITE}/specialty/",
                },
                {
                    "@type": "ListItem",
                    "position": 3,
                    "name": f"{d['name']}の大学受験対策",
                    "item": url,
                },
            ],
        },
        {
            "@type": "Service",
            "@id": f"{url}#service",
            "name": d["title"],
            "url": url,
            "provider": {"@id": f"{SITE}/#organization"},
            "areaServed": {"@type": "AdministrativeArea", "name": d["name"]},
            "priceRange": "24,000円〜104,990円（月額・税込・月4セット）",
            "availableChannel": {
                "@type": "ServiceChannel",
                "serviceUrl": url,
                "serviceLocation": {"@type": "VirtualLocation", "url": url},
            },
            "description": d["desc"],
            "dateModified": TODAY,
            "availableLanguage": "ja",
        },
        E.WEBSITE_NODE,
        E.ORG_NODE,
        E.PERSON_NODE,
    ]
    return (
        '<script type="application/ld+json">'
        + json.dumps(
            {"@context": "https://schema.org", "@graph": graph},
            ensure_ascii=False,
            separators=(", ", ": "),
        )
        + "</script>"
    )


def faq_items(slug: str, d: dict) -> list[tuple[str, str]]:
    return list(d["faq"]) + [
        (
            f"黒田塾に{d['name']}内の教室はありますか？",
            "ありません。黒田塾は教室を持たないオンライン専業の個別指導です。"
            f"{d['name']}を含む全国47都道府県から、同じ料金・同じ内容で受講できます。"
            "指導はビデオ通話またはテキストで行います。",
        ),
        (
            "料金は地域によって変わりますか？",
            "変わりません。月額・税込・月4セットで、" + PLANS + "の5プラン共通です。",
        ),
    ]


def build_page(slug: str, d: dict) -> str:
    url = f"{SITE}/specialty/{slug}/"
    faqs = faq_items(slug, d)
    uni_rows = "".join(
        f"<tr><td>{name}</td><td>{city}</td><td>{kind}</td><td>{note}</td></tr>"
        for name, city, kind, note in d["unis"]
    )
    uni_names = "・".join(name for name, *_ in d["unis"][:3])
    issues = "".join(
        f"<h3>{i + 1}. {h}</h3><p>{t}</p>" for i, (h, t) in enumerate(d["issues"])
    )
    faq_html = "".join(
        f'<details class="answer-box"><summary>{q}</summary><p>{a}</p></details>'
        for q, a in faqs
    )
    head = (
        '<!DOCTYPE html>\n<html lang="ja"><head>'
        '<meta charset="utf-8"/>'
        '<meta content="width=device-width, initial-scale=1.0" name="viewport"/>'
        f"<title>{d['title']}</title>"
        f'<meta content="{d["desc"]}" name="description"/>'
        '<meta content="index, follow, max-image-preview:large, max-snippet:-1" name="robots"/>'
        f'<link href="{url}" rel="canonical"/>'
        '<meta content="website" property="og:type"/>'
        '<meta content="ja_JP" property="og:locale"/>'
        '<meta content="黒田塾" property="og:site_name"/>'
        f'<meta content="{d["title"]}" property="og:title"/>'
        f'<meta content="{d["desc"]}" property="og:description"/>'
        f'<meta content="{url}" property="og:url"/>'
        '<meta content="summary_large_image" name="twitter:card"/>'
        f'<meta content="{OG_IMAGE}" property="og:image"/>'
        '<meta content="image/png" property="og:image:type"/>'
        '<meta content="1200" property="og:image:width"/>'
        '<meta content="630" property="og:image:height"/>'
        f'<meta content="{d["title"]}" property="og:image:alt"/>'
        f'<meta content="{OG_IMAGE}" name="twitter:image"/>'
        f'<meta content="{d["title"]}" name="twitter:image:alt"/>'
        f'<meta content="{TODAY}" name="last-modified"/>'
        f"{jsonld(slug, d)}"
        f'<meta content="{d["title"]}" name="twitter:title"/>'
        f'<meta content="{d["desc"]}" name="twitter:description"/>'
        '<meta content="#fbfaf7" name="theme-color"/>'
        '<link href="/favicon.png" rel="icon" sizes="96x96" type="image/png"/>'
        '<link href="/feed.xml" rel="alternate" title="黒田塾｜学習ガイド" type="application/rss+xml"/>'
        '<link href="/apple-touch-icon.png" rel="apple-touch-icon" sizes="180x180"/>'
        f'<meta content="{TODAY}" name="site-release"/>'
        f"{STYLE_LINKS}"
        "</head>"
    )
    body_parts = [
        f"<body>{HEADER.format(line_id=f'region-{slug}-line-1')}",
        '<main class="detail" id="main-content">',
        '<nav aria-label="パンくずリスト"><ol class="breadcrumbs">'
        '<li><a href="/">黒田塾</a></li>'
        '<li><a href="/specialty/">専門対策</a></li>'
        f'<li aria-current="page">{d["name"]}の大学受験対策</li></ol></nav>',
        f"<h1>{d['name']}の大学受験対策。<br/>{d['catch']}</h1>",
        f'<p class="intro">{d["name"]}で大学受験を目指すなら、最初にやることは参考書を'
        f"増やすことではなく、志望校の入試形式と自分の答案の差を分けることです。"
        f"{d['env'][0]}</p>"
        f"<p>黒田塾は教室を持たないオンライン専業の個別指導で、{d['name']}にも教室は"
        f"ありません。指導はすべてオンラインで行うため、"
        f"{d['capital']}はもちろん県内のどの地域からでも受講できます。東京大学教育学部を"
        f"卒業した黒田清友が、科目の指導から週単位の計画の確認までを直接担当します。</p>",
        '<p class="byline">指導・執筆：<a href="/about/">黒田清友</a>｜東京大学教育学部卒</p>',
        '<div class="seo-cta"><strong>30分の無料「受験戦略診断」</strong>'
        f"<p>{d['name']}の志望校と現在の答案、科目ごとの課題を整理し、"
        "次に優先することを決めます。面談実施後、希望者に90日学習ロードマップ設計キットを進呈します。</p>"
        f'<a class="btn btn-dark" href="/contact/?topic=specialty-{slug}-strategy&amp;source=site#consultation-flow">'
        "受験戦略診断を申し込む</a></div>",
        '<nav aria-label="目次" class="r7-toc">'
        f"<strong>{d['name']}での受験対策で確認すること</strong><ul>"
        '<li><a href="#issues">課題</a></li>'
        '<li><a href="#environment">受験環境</a></li>'
        '<li><a href="#universities">主な大学</a></li>'
        '<li><a href="#access">オンライン受講の進め方</a></li>'
        '<li><a href="#method">黒田塾の対策</a></li>'
        '<li><a href="#pricing-note">料金</a></li>'
        '<li><a href="#faq">よくある質問</a></li>'
        "</ul></nav>",
        f'<section id="issues"><h2>{d["name"]}で大学受験を進める受験生の課題</h2>{issues}</section>',
        f'<section id="environment"><h2>{d["name"]}の受験環境</h2>'
        f"<p>{d['env'][1]}</p>"
        f"<p>志望校として名前が挙がりやすいのは、{uni_names}などです。"
        f"同じ{d['name']}内でも、通える範囲と志望校の組み合わせによって、必要な科目配分は変わります。"
        "まずは志望校を一つに決め、その形式から逆算して計画を立てることが、"
        "地域に関係なく共通する出発点になります。</p></section>",
        f'<section id="universities"><h2>{d["name"]}で志望校になりやすい大学</h2>'
        '<p>公開情報で確認できる範囲で、大学名・所在地・設置区分を並べました。'
        "入試科目や配点は学部ごとに変わるため、必ず志望学部の募集要項と過去問で確認してください。</p>"
        '<div class="table-scroll"><table class="guide-table"><thead><tr>'
        "<th>大学</th><th>所在地</th><th>設置区分</th><th>確認したいこと</th>"
        f"</tr></thead><tbody>{uni_rows}</tbody></table></div>"
        "<p>国公立は共通テストと個別試験の両方が必要で、私立は科目を絞れる代わりに"
        "学部ごとの形式差が大きくなります。どちらを軸にするかで、平日の学習配分は変わります。</p>"
        + (
            f'<p>{UNI_LINK[slug][1]}の入試形式は「'
            f'<a href="/specialty/{UNI_LINK[slug][0]}/">{UNI_LINK[slug][1]}の専門対策</a>」'
            "で詳しく扱っています。</p>"
            if slug in UNI_LINK
            else ""
        )
        + "</section>",
        f'<section id="access"><h2>オンライン受講の進め方</h2><p>{d["access"]}</p>'
        f"<p>黒田塾はオンライン専業で、{d['name']}に教室はありません。"
        "指導はすべてオンラインで、答案は撮影して共有し、面談はビデオ通話で行います。"
        "通塾の移動がないぶん、その時間を演習と復習に回せます。</p>"
        "<p>通話や会議が難しい場合は、メールとテキストでも進められます。"
        "答案の添削と計画の確認は、文章だけでも完結します。</p></section>",
        '<section id="method"><h2>黒田塾の対策は、志望校起点の逆算から組み立てる</h2>'
        '<div class="r9-card-grid">'
        "<article class=\"r9-card\"><h3>志望校との差の診断</h3><p>志望校の形式と現在の答案を並べ、"
        "科目ごとの課題と目標点を分けます。併願校との共通部分も含めて設計します。</p></article>"
        "<article class=\"r9-card\"><h3>週単位の計画と面談</h3><p>学校・部活・通学の予定を前提に"
        "週単位の計画を作り、面談で進み具合を確認します。模試の結果は計画の微調整に使います。</p></article>"
        "<article class=\"r9-card\"><h3>答案の個別確認</h3><p>科目ごとに答案を確認し、次に直す一点を"
        "決めます。英語・数学・国語・社会・小論文が担当科目です。理科は指導対象外です。</p></article>"
        "</div>"
        "<p>指導を担当するのは、東京大学文科二類に現役合格し、同大学教育学部を卒業した黒田清友です。"
        "中学受験から大学受験まで、志望校の形式に合わせた計画と答案確認を行います。</p></section>",
        '<section id="flow"><h2>対策の進め方</h2><div class="table-scroll">'
        '<table class="guide-table"><thead><tr><th>段階</th><th>主な目的</th><th>終了条件の例</th></tr></thead>'
        "<tbody><tr><td>診断</td><td>志望校の形式と現在の答案の差を特定</td>"
        "<td>科目ごとの課題と目標点を説明できる</td></tr>"
        "<tr><td>計画の実行</td><td>週単位の計画と答案確認の反復</td>"
        "<td>忙しい週でも最低限の学習を維持できる</td></tr>"
        "<tr><td>形式への仕上げ</td><td>志望校の過去問での時間配分の調整</td>"
        "<td>失点原因を分類し、次の演習を自分で決められる</td></tr></tbody></table></div>"
        '<p>模試の見直し方は「<a href="/study-guides/mock-exam-review/">模試の見直し方</a>」、'
        '大学受験全体の計画は「<a href="/study-guides/university-study-plan/">大学受験の勉強計画</a>」にまとめました。</p></section>',
        '<section id="pricing-note"><h2>料金について</h2>'
        "<p>専門対策の料金は、通常の継続受講と共通の5プラン（月額・税込・月4セット）です。"
        f"{PLANS}で、地域によって料金が変わることはありません。"
        "授業を増やす前に、面談のみの学習管理で計画と添削だけを頼る使い方もできます。</p>"
        '<p><a href="/pricing/">料金とプランの詳細を見る</a></p></section>',
        IL.link_block(),
        C.mid_cta(url, f'<title>{d["name"]}の大学受験対策</title>'),
        f'<section id="faq"><h2>{d["name"]}の大学受験対策についてよくある質問</h2>{faq_html}</section>',
        f'<div class="cta-box"><h2>{d["name"]}での受験対策で、いま最優先の一手を決める。</h2>'
        "<p>30分で現在地・科目配分・次の7日を整理します。</p>"
        f'<a class="btn btn-line" href="/contact/?topic=specialty-{slug}-strategy&amp;source=site#consultation-flow">'
        "無料の受験戦略診断へ</a></div>",
        '<nav aria-label="関連ページ" class="jump-links">'
        '<a href="/specialty/">大学受験の専門対策トップ</a>'
        + (
            f'<a href="{EXTRA_LINKS[slug][0]}">{EXTRA_LINKS[slug][1]}</a>'
            if slug in EXTRA_LINKS
            else ""
        )
        + '<a href="/online-tutoring/">オンライン個別指導</a>'
        '<a href="/university-exam/">大学受験の個別指導</a>'
        '<a href="/study-coaching/">学習管理・受験コーチング</a>'
        '<a href="/pricing/">料金</a></nav>',
        '<p class="editor-note"><a href="/about/#editorial-policy">教材の編集方針・誤りの連絡窓口</a></p>',
        region_links(slug),
        "</main>",
        FOOTER.format(today=TODAY).replace("</body>", C.sticky(url) + "</body>", 1),
    ]
    return head + "".join(body_parts)


# 生成後に手で足した内部リンクのうち、再生成でも残すもの（slug -> (path, label)）
EXTRA_LINKS = {
    "aichi": ("/specialty/nagoya/", "名古屋大学専門対策"),
}

MARK_START = "<!-- r24:region-nav:start -->"
MARK_END = "<!-- r24:region-nav:end -->"
HUB_START = "<!-- r24:pref-index:start -->"
HUB_END = "<!-- r24:pref-index:end -->"


def strip_block(path: Path) -> bool:
    """このスクリプトが過去に挿入した地域ナビを除去する（差し替え用）。"""
    text = path.read_text(encoding="utf-8")
    new = text
    while MARK_START in new and MARK_END in new:
        head, _, rest = new.partition(MARK_START)
        _, _, tail = rest.partition(MARK_END)
        new = head + tail
    if new != text:
        path.write_text(new, encoding="utf-8")
        return True
    return False


def upsert_block(path: Path, start: str, end: str, html: str) -> bool:
    text = path.read_text(encoding="utf-8")
    block = f"{start}{html}{end}"
    if start in text and end in text:
        head, _, rest = text.partition(start)
        _, _, tail = rest.partition(end)
        new = head + block + tail
    else:
        marker = "</main>"
        idx = text.rfind(marker)
        if idx < 0:
            raise SystemExit(f"{path}: </main> not found")
        new = text[:idx] + block + text[idx:]
    if new != text:
        path.write_text(new, encoding="utf-8")
        return True
    return False


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    problems = []
    titles, descs = set(), set()
    for slug, d in D.PREFECTURES.items():
        if not 12 <= len(d["title"]) <= 40:
            problems.append(f"{slug}: title {len(d['title'])} chars")
        if not 60 <= len(d["desc"]) <= 130:
            problems.append(f"{slug}: desc {len(d['desc'])} chars")
        if d["title"] in titles:
            problems.append(f"{slug}: duplicate title")
        if d["desc"] in descs:
            problems.append(f"{slug}: duplicate description")
        titles.add(d["title"])
        descs.add(d["desc"])
        if len(d["unis"]) < 2:
            problems.append(f"{slug}: too few universities")
        if len(d["issues"]) != 3 or len(d["faq"]) < 2:
            problems.append(f"{slug}: data incomplete")
    if problems:
        print("\n".join(problems), file=sys.stderr)
        return 1
    if args.check:
        print(f"region data OK: {len(D.PREFECTURES)} prefectures")
        return 0

    written = 0
    for slug, d in D.PREFECTURES.items():
        target = PUBLIC / "specialty" / slug / "index.html"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(build_page(slug, d), encoding="utf-8")
        written += 1

    # 大学別ページなどに入ってしまった古いナビを取り除く
    hub_path = PUBLIC / "specialty" / "index.html"
    for path in sorted(PUBLIC.rglob("*.html")):
        if path == hub_path:
            continue
        if path.parent.name in EXISTING_INFO and path.name == "index.html":
            continue
        if MARK_START in path.read_text(encoding="utf-8"):
            strip_block(path)

    updated = 0
    for slug, (name, capital) in EXISTING_INFO.items():
        path = PUBLIC / "specialty" / slug / "index.html"
        if not path.exists():
            continue
        stub = {"name": name}
        if upsert_block(path, MARK_START, MARK_END, region_links(slug)):
            updated += 1

    hub = hub_path
    if upsert_block(hub, HUB_START, HUB_END, all_prefectures_section()):
        updated += 1

    print(f"wrote {written} region pages, updated {updated} existing pages")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
