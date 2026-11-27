#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""r30: 料金ページと特商法表記を、単発メニュー・年間一括・上位アンカーに合わせる。

    python3 tools/pricing_r30.py          # 適用（2回目以降は何もしない）
    python3 tools/pricing_r30.py --check  # 適用済みかを確認するだけ

方針:
* 金額の正本は build.py（PRICING / SINGLE_MENUS / ANNUAL_PAY）。ここでは表示だけを直す。
* 継続受講5プランの金額・内容は変えない。並び順を上位（週3回）からに変える。
* 単発添削3,000円・スポット相談60分12,000円・年間一括（12か月前払いで2か月分無料）を
  /pricing/ と /legal/ に足す。
* 無料の学習チェック・無料PDFは「入口」として残し、有料メニューの代わりに見せない。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "public"
MARK = "<!-- r30:pricing -->"

PER_SET = {
    "面談＋授業（週3回）": "8,750円",
    "面談＋授業（週2回）": "10,000円",
    "面談＋授業（週1回）": "13,750円",
    "授業のみ（週1回）": "7,500円",
    "面談のみ": "6,000円",
}

ROWS = [
    # (data-price-plan, id, プラン名, 月額, 1セットの内容, 月4セットの面談・授業)
    ("interview-lesson-3", "interview-lesson-3", "面談＋授業（週3回）", "104,990円", "面談30分＋授業90分×3回", "面談4回・授業12回"),
    ("interview-lesson-2", "interview-lesson-2", "面談＋授業（週2回）", "79,990円", "面談30分＋授業90分×2回", "面談4回・授業8回"),
    ("interview-lesson-1", "interview-lesson-1", "面談＋授業（週1回）", "54,990円", "面談30分＋授業90分×1回", "面談4回・授業4回"),
    ("lesson-only", "lesson-only", "授業のみ（週1回）", "30,000円", "授業90分×1回（面談なし）", "個別授業4回・定期面談なし"),
    ("interview-only", "interview-only", "面談のみ", "24,000円", "面談30分", "面談4回・個別授業なし"),
]


def table_html() -> str:
    body = "".join(
        f'<tr data-price-plan="{key}" id="{rid}"><th scope="row">{name}</th>'
        f'<td class="price-amount" data-price-amount="{int(price.replace(",", "").replace("円", ""))}">{price}</td>'
        f'<td>{PER_SET[name]}<small>（目安）</small></td>'
        f"<td>{content}</td><td>{monthly}</td></tr>"
        for key, rid, name, price, content, monthly in ROWS
    )
    return (
        '<div aria-label="料金比較表。狭い画面では横にスクロールできます" class="table-scroll"'
        ' role="region" tabindex="0"><table class="r6-table">'
        "<caption>5プランの比較（月額・税込／月4セット分・上位プランから）</caption>"
        '<thead><tr><th scope="col">プラン</th><th scope="col">月額</th>'
        '<th scope="col">1セットあたり</th><th scope="col">1セットの内容</th>'
        '<th scope="col">月4セットの面談・授業</th></tr></thead>'
        f"<tbody>{body}</tbody></table></div>"
    )


ONE_OFF = (
    MARK
    + '<section id="oneoff"><h2>単発で頼めるメニュー（継続契約なし）</h2>'
    "<p>継続受講の前に一度試したい場合と、必要なときだけ頼みたい場合のメニューです。"
    "いずれも税込で、継続契約は発生しません。"
    "志望校と現在の答案が決まっていれば、この2つだけで次の一手まで進められます。</p>"
    '<div class="table-scroll"><table class="r6-table">'
    "<caption>単発メニュー（税込）</caption><thead><tr>"
    '<th scope="col">メニュー</th><th scope="col">料金</th><th scope="col">内容</th>'
    "</tr></thead><tbody>"
    '<tr id="tanka-tensaku"><th scope="row">単発添削</th>'
    '<td class="price-amount" data-price-amount="3000">1答案 3,000円</td>'
    "<td>答案1通を添削して返却します。科目は英語・数学・国語・社会・小論文。"
    "返却は申込み時に合意した期日までです。</td></tr>"
    '<tr id="spot-soudan"><th scope="row">スポット相談</th>'
    '<td class="price-amount" data-price-amount="12000">60分 12,000円</td>'
    "<td>60分のオンライン相談。答案や模試の結果を持ち込んで、次の一手を決めます。"
    "ビデオ通話でも、テキストだけでも実施できます。</td></tr>"
    '<tr id="nenkan-ikkatsu"><th scope="row">年間一括（継続受講）</th>'
    "<td>12か月分を10か月分の額</td>"
    "<td>継続受講5プランのいずれかを12か月前払いすると、2か月分が無料になります。"
    "例：面談＋授業（週1回）は月額54,990円×10か月＝549,900円（税込）で12か月。</td></tr>"
    "</tbody></table></div>"
    '<p class="fine-print">単発添削は答案の受領後、スポット相談は予約した日時に実施します。'
    "年間一括の途中解約・休会の扱いは、契約前に確認してください。"
    '支払い方法と支払い時期は<a href="/legal/">特定商取引法に基づく表記</a>と契約前の確認文で示します。</p>'
    "</section>"
)

ANCHOR_NOTE = (
    MARK
    + "<p>上の表は、回数の多い上位プランから並べています。回数が増えるほど1セットあたりの"
    "金額は下がりますが、必要以上の回数を契約しても成績は上がりません。"
    "1セットあたりは月4セットで割った目安（税込）で、週3回は8,750円、週2回は10,000円、"
    "週1回は13,750円です。自分の課題に対して必要な回数はどれかで選んでください。</p>"
)


def patch_pricing() -> bool:
    path = PUBLIC / "pricing" / "index.html"
    raw = path.read_text()
    if MARK in raw:
        return False
    changed = raw

    # 1) last-modified
    changed = changed.replace('content="2026-11-27" name="last-modified"',
                              'content="2026-11-28" name="last-modified"', 1)

    # 2) 導入文：単発メニューと上位プラン先出し
    old_intro = (
        "継続受講は、面談のみ24,000円、授業のみ（週1回）30,000円、面談＋授業（週1回）54,990円、"
        "面談＋授業（週2回）79,990円、面談＋授業（週3回）104,990円の5プランです。"
        "すべて月額・税込・月4セット分。必要な支援に合わせて比較できます。"
    )
    new_intro = (
        "継続受講は5プランで、上位は面談＋授業（週3回）104,990円、週2回79,990円、"
        "週1回54,990円、以下は授業のみ（週1回）30,000円、面談のみ24,000円です。"
        "すべて月額・税込・月4セット分。継続の前に試せる単発添削1答案3,000円と、"
        "スポット相談60分12,000円、12か月前払いで2か月分無料になる年間一括も用意しています。"
    )
    assert old_intro in changed
    changed = changed.replace(old_intro, new_intro, 1)

    # 3) 要点リスト
    old_li = (
        '<div class="summary-box"><strong>このページの要点</strong><ul>'
        "<li>継続受講は5プラン。面談のみ24,000円、授業のみ（週1回）30,000円、"
        "面談＋授業は週1回54,990円・週2回79,990円・週3回104,990円</li>"
        "<li>いずれも月額・税込・月4セット分。地域や志望校によって料金は変わらない</li>"
        "<li>授業のみ（週1回）は定期面談なし。面談＋授業は週1回30分の面談と90分授業の組み合わせ</li></ul>"
    )
    new_li = (
        '<div class="summary-box"><strong>このページの要点</strong><ul>'
        "<li>単発添削は1答案3,000円、スポット相談は60分12,000円（税込）。継続契約なしで申し込める</li>"
        "<li>継続受講は5プラン。週3回104,990円から順に並べ、1セットあたり8,750円〜13,750円の目安を併記</li>"
        "<li>年間一括は12か月前払いで2か月分無料（例：月額54,990円のプランは549,900円）</li>"
        "<li>いずれも税込。地域や志望校によって料金は変わらない</li></ul>"
    )
    assert old_li in changed
    changed = changed.replace(old_li, new_li, 1)

    # 4) 目次に単発メニューを足す
    changed = changed.replace(
        '<ol><li><a href="#comparison">月額料金と、月4セットで受けられる内容</a></li>',
        '<ol><li><a href="#oneoff">単発で頼めるメニュー</a></li>'
        '<li><a href="#comparison">月額料金と、月4セットで受けられる内容</a></li>',
        1,
    )

    # 5) 比較表を上位プランから・1セットあたり列つきに差し替え、単発メニューを前に置く
    table_start = changed.find(
        '<div aria-label="料金比較表。狭い画面では横にスクロールできます"'
    )
    table_end = changed.find("</table></div>", table_start) + len("</table></div>")
    assert 0 < table_start < table_end
    changed = changed[:table_start] + table_html() + changed[table_end:]
    changed = changed.replace('<section id="comparison">', ONE_OFF + '<section id="comparison">', 1)

    # 6) 表の直後にアンカーの説明
    changed = changed.replace(
        "実施日程と調整後の金額は事前に確認します。</p></section>",
        "実施日程と調整後の金額は事前に確認します。</p>" + ANCHOR_NOTE + "</section>",
        1,
    )

    # 7) FAQ: 単発メニュー・年間一括・無料との違い
    old_faq = (
        '<details class="r6-faq"><summary>無料相談だけでも利用できますか？</summary>'
        "<p>はい。オンラインで30分程度、現在の学習状況や悩みを整理できます。"
        "相談を受けたことによって入会が決まるわけではありません。</p></details>"
    )
    new_faq = (
        '<details class="r6-faq"><summary>無料の相談と、有料のスポット相談はどう違いますか？</summary>'
        "<p>無料の相談は、状況を整理して次に確かめることを決める入口です。"
        "30分の無料相談か、テキストでの事前相談で足ります。"
        "スポット相談（60分12,000円）は、答案や模試の結果を持ち込んで、"
        "分野ごとの優先順位や直近1か月の計画まで具体的に決める枠です。"
        "どちらも入会を条件にしません。</p></details>"
        '<details class="r6-faq"><summary>単発添削だけでも頼めますか？</summary>'
        "<p>頼めます。1答案3,000円（税込）で、継続契約は発生しません。"
        "科目は英語・数学・国語・社会・小論文です。"
        "同じ答案を続けて添削してほしい場合は、継続受講の面談＋授業に含まれる添削を使います。</p></details>"
        '<details class="r6-faq"><summary>年間一括の支払いと、途中でやめた場合は？</summary>'
        "<p>12か月分を前払いすると、2か月分が無料になります（10か月分の額で12か月受講）。"
        "例：面談＋授業（週1回）は549,900円（税込）。"
        "途中解約・休会の扱いは契約前に個別に確認してください。</p></details>" + old_faq
    )
    assert old_faq in changed
    changed = changed.replace(old_faq, new_faq, 1)

    # 8) 無料枠の位置づけを「入口」に寄せる
    old_free = (
        '<h2>自分の場合、何を確かめるか迷ったら</h2>'
        "<p>会員登録なしの学習チェックで、英語・数学・算数・学習計画の困りごとから"
        "最初に試すことを確認できます。保護者向けの案内では、指導例・料金・無料相談をまとめて確認できます。</p>"
    )
    new_free = (
        '<h2>無料でできること（入口）と、有料で頼めること</h2>'
        "<p>無料の学習チェック・無料PDF・無料の相談は、塾の水準と相性を確かめる入口です。"
        "実際の答案を直す・計画を組み替えるところからは、単発添削（1答案3,000円）と"
        "スポット相談（60分12,000円）で進めます。"
        "毎週続ける場合は、継続受講の5プランから回数を選びます。</p>"
    )
    assert old_free in changed
    changed = changed.replace(old_free, new_free, 1)

    # 9) JSON-LD: OfferCatalog に単発メニュー、FAQ に新しい質問を足す
    changed = patch_jsonld(changed)

    path.write_text(changed)
    return True


def patch_jsonld(raw: str) -> str:
    blocks = list(re.finditer(r'<script type="application/ld\+json">(.*?)</script>', raw, re.S))
    if not blocks:
        return raw
    block = blocks[0]
    data = json.loads(block.group(1))
    graph = data.get("@graph", [])
    for node in graph:
        if node.get("@type") == "OfferCatalog":
            have = {o.get("name") for o in node.get("itemListElement", [])}
            for name, price, desc in (
                ("単発添削", 3000, "答案1通を添削して返却（税込）"),
                ("スポット相談", 12000, "60分のオンライン相談（税込）"),
            ):
                if name not in have:
                    node["itemListElement"].append(
                        {
                            "@type": "Offer",
                            "name": name,
                            "price": price,
                            "priceCurrency": "JPY",
                            "description": desc,
                            "url": "https://kurodaschool.jp/pricing/",
                        }
                    )
        if node.get("@type") == "WebPage":
            node["dateModified"] = "2026-11-28"
        if node.get("@type") == "FAQPage":
            have = {q.get("name") for q in node.get("mainEntity", [])}
            for q, a in (
                (
                    "無料の相談と、有料のスポット相談はどう違いますか？",
                    "無料の相談は状況を整理して次に確かめることを決める入口です。"
                    "スポット相談（60分12,000円）は、答案や模試の結果を持ち込んで、"
                    "分野ごとの優先順位や直近1か月の計画まで決める枠です。",
                ),
                (
                    "単発添削だけでも頼めますか？",
                    "頼めます。1答案3,000円（税込）で継続契約は発生しません。"
                    "科目は英語・数学・国語・社会・小論文です。",
                ),
                (
                    "年間一括の支払いと、途中でやめた場合は？",
                    "12か月分を前払いすると2か月分が無料になります（10か月分の額で12か月受講）。"
                    "例：面談＋授業（週1回）は549,900円（税込）。途中解約・休会の扱いは契約前に確認してください。",
                ),
            ):
                if q not in have:
                    node["mainEntity"].append(
                        {
                            "@type": "Question",
                            "name": q,
                            "acceptedAnswer": {"@type": "Answer", "text": a},
                        }
                    )
    new_json = json.dumps(
        {"@context": "https://schema.org", "@graph": graph},
        ensure_ascii=False,
        separators=(", ", ": "),
    )
    return raw[: block.start(1)] + new_json + raw[block.end(1) :]


LEGAL_SECTION = (
    MARK
    + '<section id="service-terms"><h2>指導・添削・相談（役務）の販売条件</h2>'
    "<p>この節は、継続受講・単発添削・スポット相談の条件です。"
    "教材（PDF）の条件は上の表のとおりで、別契約になります。</p>"
    '<div class="table-scroll"><table class="spec-table"><tbody>'
    "<tr><th>販売価格</th><td>単発添削 1答案3,000円／スポット相談 60分12,000円／"
    "継続受講 月額24,000円・30,000円・54,990円・79,990円・104,990円（いずれも税込・月4セット）／"
    "年間一括は12か月分を10か月分の額で前払い（例：月額54,990円のプランは549,900円）。"
    "すべて税込。</td></tr>"
    "<tr><th>商品代金以外の費用</th><td>銀行振込手数料、通信費。入会金はありません。</td></tr>"
    "<tr><th>支払方法・支払時期</th><td>銀行振込による前払い。申込確定の連絡から7日以内。"
    "年間一括は開始月の前払い。支払い方法と期日は申込み前の確認文でも示します。</td></tr>"
    "<tr><th>役務提供時期</th><td>継続受講は入金確認後の初回面談日から。"
    "単発添削は答案の受領後、申込み時に合意した期日までに返却。"
    "スポット相談は予約した日時に実施します。オンライン（ビデオ通話またはテキスト）。</td></tr>"
    "<tr><th>キャンセル・変更</th><td>単発添削は答案の受領前、スポット相談は実施日の前日まで、"
    "無料で取り消せます。継続受講の振替・解約は契約前の確認文によります。</td></tr>"
    "<tr><th>返金</th><td>当塾の責めに帰す事由で提供できなかった場合は、"
    "未提供分を返金します。返金は内容と振込先の確認後7営業日以内に銀行振込。</td></tr>"
    "</tbody></table></div></section>"
)


def patch_legal() -> bool:
    path = PUBLIC / "legal" / "index.html"
    raw = path.read_text()
    if MARK in raw:
        return False
    anchor = '<section id="scope">'
    if anchor in raw:
        raw = raw.replace(anchor, LEGAL_SECTION + anchor, 1)
    else:
        raw = raw.replace("</main>", LEGAL_SECTION + "</main>", 1)
    # 適用範囲の文言を、役務もこのページの対象であることが伝わる形に直す
    raw = raw.replace(
        "このページは「完全対策講座」の教材のみプランの表記です。継続受講の授業・面談は別契約であり、"
        "既存契約の条件は変更しません。",
        "このページは「完全対策講座」の教材と、継続受講・単発添削・スポット相談の表記です。"
        "教材と役務は別契約で、既存契約の条件は変更しません。",
        1,
    )
    raw = raw.replace('content="2026-11-27" name="last-modified"',
                      'content="2026-11-28" name="last-modified"', 1)
    path.write_text(raw)
    return True


def patch_home() -> bool:
    path = PUBLIC / "index.html"
    raw = path.read_text()
    if MARK in raw:
        return False
    # 上位プランから並べ替える（行の並びだけを変える）
    rows = re.findall(r'<tr[^>]*>.*?</tr>', raw, re.S)
    plan_rows = [r for r in rows if "ks-plan-name" in r]
    if len(plan_rows) != 5:
        print("home: plan rows", len(plan_rows), file=sys.stderr)
        return False
    start = raw.find(plan_rows[0])
    end = raw.find(plan_rows[-1]) + len(plan_rows[-1])
    order = ["週3回", "週2回", "週1回", "授業のみ", "面談のみ"]
    ordered = []
    for key in order:
        for r in plan_rows:
            if key in r:
                ordered.append(r)
                break
    if len(ordered) != 5:
        return False
    new_block = "\n".join(ordered)
    raw = raw[:start] + new_block + raw[end:]
    # 単発メニューの案内を表の下に足す
    anchor = '<p class="ks-more"><a class="text-link" href="/pricing/">含まれる支援内容の詳細・プランの違いを見る →</a>'
    assert anchor in raw
    raw = raw.replace(
        anchor,
        MARK
        + '<p class="ks-more">単発で試す：単発添削 1答案3,000円／スポット相談 60分12,000円'
        '（税込）。12か月前払いの年間一括は2か月分無料です。'
        '<a class="text-link" href="/pricing/#oneoff">単発メニューの詳細を見る →</a></p>'
        + anchor,
        1,
    )
    path.write_text(raw)
    return True


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    if args.check:
        for rel in ("pricing/index.html", "legal/index.html", "index.html"):
            raw = (PUBLIC / rel).read_text()
            print(("applied " if MARK in raw else "not applied ") + rel)
        return 0
    for fn in (patch_pricing, patch_legal, patch_home):
        print(("applied " if fn() else "skipped ") + fn.__name__)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
