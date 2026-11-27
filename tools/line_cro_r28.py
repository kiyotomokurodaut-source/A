#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""r28（2026-11-27）LINE転換の追加実装。

    python3 tools/line_cro_r28.py            # 全ページに適用（既存ブロックは差し替え）
    python3 tools/line_cro_r28.py --check    # 適用状況の点検のみ（書き込みなし）

このスクリプトが足すもの（r27 の本文中CTA・追従バーはそのまま残す）:
1. 比較表の直下に「自分の条件でLINE相談する」1行導線（表のあるページ・法務/フォームを除く）
2. 学習ガイド本文に「よくある不安3つ→LINE相談」ブロック（r27 CTA の直前）
3. CTAボタンの文言をページごとに3種から出し分け（data-cta-variant で計測）
4. 診断ページ（/shindan/・/learning-check/）末尾のLINE導線
5. 保護者向けページの「お子さま」表記統一
6. タップ領域44px以上のCSS（/assets/r28-ux.css）の読み込み

事実だけを書く。料金・添削回数・対応科目は公開済みの記載に合わせ、
無い特典や実績は足さない。
"""
from __future__ import annotations

import argparse
import re
import sys
import zlib
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "public"
sys.path.insert(0, str(ROOT / "tools"))

import line_cro_r27 as base  # noqa: E402  (r27 の正本URL・相談文・分類を再利用)

LINE_ADD = base.LINE_ADD
OA_BASE = base.OA_BASE

CSS_LINK = '<link rel="stylesheet" href="/assets/r28-ux.css"/>'

TABLE_START = "<!-- r28:table-cta:start -->"
TABLE_END = "<!-- r28:table-cta:end -->"
ANX_START = "<!-- r28:anx:start -->"
ANX_END = "<!-- r28:anx:end -->"
DIAG_START = "<!-- r28:diag:start -->"
DIAG_END = "<!-- r28:diag:end -->"

# 比較表の直後に導線を置かないページ（入力フォーム・法務・診断）
NO_TABLE_CTA = {"/contact/", "/privacy/", "/legal/", "/materials/terms/", "/shindan/", "/learning-check/"}

# CTA文言の3種（ページごとに固定で1つを割り当てる）
VARIANTS = [
    ("a", "LINEで無料相談する（登録1分）"),
    ("b", "自分の条件でLINE相談する（無料）"),
    ("c", "まずは質問だけ、LINEで送る"),
]

FACT_LINE = (
    "無料・30分／オンライン（通話が苦手ならテキストのみでも可）／"
    "返信は原則24時間以内／無理な勧誘はしません"
)

ANX_ITEMS = [
    (
        "今の塾や教材を変えて、かえって遅れないか",
        "面談では、いま使っている教材・進度・宿題量を先に確認します。"
        "乗り換えを前提にした提案はしません。併用のまま進め方を整える相談もできます。",
    ),
    (
        "オンラインで集中して受けられるか",
        "授業は90分です。画面共有で手元の答案を見ながら進めます。"
        "相談そのものは、テキストのみでも構いません。",
    ),
    (
        "費用がどこまでかかるか読めるか",
        "継続受講は月額24,000円〜（税込・月4セット）。必要な量が少なければ、"
        "その分のプランを案内します。契約前の確認事項は先に共有します。"
        '入る前に確かめたい場合は、<a href="/materials/">無料で全文を読める英単語帳</a>や'
        '<a href="/downloads/learning-check-4.pdf">学習見本PDF</a>を登録なしで使えます。',
    ),
]


def variant_of(url: str) -> tuple[str, str]:
    return VARIANTS[zlib.crc32(url.encode("utf-8")) % len(VARIANTS)]


def oa_url(text: str) -> str:
    return OA_BASE + quote(text, safe="")


# 表の名前を、ページタイトルではなく表そのものの呼び名にする（社名だけの表記を避ける）
TABLE_LABEL = {
    "/": "料金表",
    "/pricing/": "料金表",
    "/materials/": "教材プランの価格表",
    "/about/": "指導形態の比較表",
    "/juku/": "塾の比較表",
}


def table_cta(url: str, raw: str) -> str:
    slug = url.strip("/").replace("/", "-") or "home"
    cat = base.category(url)
    if url in TABLE_LABEL:
        label = TABLE_LABEL[url]
    elif cat == "region":
        label = base.page_label(raw, url) + "の大学"
    elif cat == "local":
        label = base.page_label(raw, url) + "周辺の受験環境"
    elif cat == "guide":
        label = f"「{base.page_label(raw, url)}」の記事"
    else:
        label = base.page_label(raw, url)
    suffix = "" if label.endswith("表") else "の表"
    text = (
        f"{label}{suffix}を見ました。学年・志望校・今の悩みを送るので、"
        "自分の条件でどう進めるか相談したいです。"
    )
    return (
        f'{TABLE_START}<p class="r28-table-cta">'
        "この表の条件を、自分の学年・志望校で確かめる： "
        f'<a href="{oa_url(text)}" target="_blank" rel="noopener" '
        f'data-line-cta="table-{slug}">自分の条件でLINE相談する</a> '
        '<span class="r28-note">（無料・勧誘なし・返信は原則24時間以内）</span>'
        f"</p>{TABLE_END}"
    )


def anxiety_block(url: str, raw: str) -> str:
    slug = url.strip("/").replace("/", "-") or "home"
    label = base.page_label(raw, url)
    vid, vlabel = variant_of(url)
    items = "".join(
        f"<li><strong>{q}</strong>{a}</li>" for q, a in ANX_ITEMS
    )
    return (
        f'{ANX_START}<section class="r28-anx" aria-labelledby="r28-anx-title">'
        '<p class="r27-kicker">相談前に、よくある不安</p>'
        '<h2 id="r28-anx-title">この記事を読んで、残った不安を先に解消する</h2>'
        '<p class="r28-anx-lead">'
        f"「{label}」を読んで、当てはまる進め方か迷う場合の3点です。"
        "記事の内容は一般的な整理で、当てはめるかどうかは現在地で変わります。</p>"
        f"<ul>{items}</ul>"
        '<div class="r28-actions">'
        f'<a class="r28-line" href="{oa_url(base.prompt_text(base.category(url), label))}" '
        f'target="_blank" rel="noopener" data-line-cta="anx-{slug}" data-cta-variant="{vid}">{vlabel}</a>'
        f'<a class="r28-alt" href="/contact/?topic={slug}&amp;source=r28anx#consultation-flow">'
        "通話なしのフォームで相談する</a>"
        "</div>"
        f'<p class="r28-fact">{FACT_LINE}</p>'
        f"</section>{ANX_END}"
    )


def diag_block(url: str) -> str:
    slug = url.strip("/").replace("/", "-") or "home"
    vid, vlabel = variant_of(url)
    if url == "/shindan/":
        told = "簡易AI診断"
        prompt = (
            "簡易AI診断の結果を見ました。学年・志望校・結果を送るので、"
            "次に優先する学習を相談したいです。"
        )
    else:
        told = "無料の学習チェック"
        prompt = (
            "無料の学習チェックの結果を見ました。学年・志望校・結果を送るので、"
            "次に優先する学習を相談したいです。"
        )
    return (
        f'{DIAG_START}<section class="r28-diag" aria-labelledby="r28-diag-title">'
        '<h2 id="r28-diag-title">結果を、次の7日間の行動に変える</h2>'
        f"<p>{told}の結果は出発点です。学年・志望校・結果を送っていただければ、"
        "黒田が直接、次に優先する1つを返します。保護者の方からの相談も歓迎です。</p>"
        '<div class="r28-actions">'
        f'<a class="r28-line" href="{oa_url(prompt)}" target="_blank" rel="noopener" '
        f'data-line-cta="diag-{slug}" data-cta-variant="{vid}">結果をLINEで相談する（無料）</a>'
        f'<a class="r28-alt" href="/contact/?topic={slug}&amp;source=r28diag#consultation-flow">'
        "フォームで相談する（通話なし）</a>"
        "</div>"
        f'<p class="r28-fact">{FACT_LINE}</p>'
        f"</section>{DIAG_END}"
    )


def replace_block(raw: str, start: str, end: str, block: str) -> str:
    if start in raw and end in raw:
        head, _, rest = raw.partition(start)
        _, _, tail = rest.partition(end)
        return head + block + tail
    return raw


def insert_after_table(raw: str, block: str) -> str:
    """本文の最初の表の直後（表を囲むスクロール枠の外側）に置く。"""
    idx = raw.find("</table></div>")
    if idx >= 0:
        cut = idx + len("</table></div>")
        return raw[:cut] + "\n" + block + raw[cut:]
    idx = raw.find("</table>")
    if idx >= 0:
        cut = idx + len("</table>")
        return raw[:cut] + "\n" + block + raw[cut:]
    return raw


def apply_cta_variant(raw: str, url: str) -> str:
    """r27 本文中CTAのボタン文言を3種から1つにそろえる。"""
    vid, vlabel = variant_of(url)
    pattern = re.compile(
        r'(<a class="r27-line" href="[^"]*" target="_blank" rel="noopener" '
        r'data-line-cta="mid-[^"]*")([^>]*>)(.*?)(</a>)',
        re.S,
    )

    def repl(m: re.Match[str]) -> str:
        attrs = m.group(2)
        if "data-cta-variant" in attrs:
            attrs = re.sub(r'data-cta-variant="[^"]*"', f'data-cta-variant="{vid}"', attrs)
        else:
            attrs = attrs[:-1] + f' data-cta-variant="{vid}">'
        return m.group(1) + attrs + vlabel + m.group(4)

    return pattern.sub(repl, raw, count=1)


def apply_page(path: Path, raw: str, url: str) -> str:
    # 1) タップ領域のCSS
    if "/assets/r28-ux" not in raw:
        raw = raw.replace("</head>", CSS_LINK + "</head>", 1)

    # 2) CTA文言の出し分け（r27 の本文中CTAがあるページのみ）
    raw = apply_cta_variant(raw, url)

    # 3) 比較表の直下
    if url not in NO_TABLE_CTA and ("<table" in raw):
        block = table_cta(url, raw)
        raw = replace_block(raw, TABLE_START, TABLE_END, block)
        if TABLE_START not in raw:
            raw = insert_after_table(raw, block)

    # 4) 学習ガイドの不安3つブロック
    is_guide = url.startswith("/study-guides/") and url != "/study-guides/"
    if is_guide:
        block = anxiety_block(url, raw)
        raw = replace_block(raw, ANX_START, ANX_END, block)
        if ANX_START not in raw:
            anchor = "<!-- r27:cro-mid:start -->"
            if anchor in raw:
                raw = raw.replace(anchor, block + "\n" + anchor, 1)
            elif "</main>" in raw:
                raw = raw.replace("</main>", block + "</main>", 1)

    # 5) 診断ページ末尾
    if url in ("/shindan/", "/learning-check/"):
        block = diag_block(url)
        raw = replace_block(raw, DIAG_START, DIAG_END, block)
        if DIAG_START not in raw:
            for anchor in ('<nav aria-label="関連ページ"', '<nav class="r21-related"', "</main>"):
                if anchor in raw:
                    raw = raw.replace(anchor, block + "\n" + anchor, 1)
                    break

    # 6) 保護者向けの「お子さま」表記（本文とJSON-LDの両方）
    raw = raw.replace("お子さんが", "お子さまが").replace("お子さん", "お子さま")
    raw = raw.replace("子どもが乗り気", "お子さまが乗り気").replace(
        "かえって子どもの負担", "かえってお子さまの負担"
    )
    return raw


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    changed, problems = 0, []
    tables = anx = diag = variants = 0
    for path in sorted(PUBLIC.rglob("*.html")):
        url = base.route(path)
        raw = path.read_text(encoding="utf-8")
        new = apply_page(path, raw, url)
        if args.check:
            if url not in NO_TABLE_CTA and "<table" in raw and TABLE_START not in new:
                problems.append(f"{url}: 比較表の直後のCTAなし")
            if url.startswith("/study-guides/") and url != "/study-guides/" and ANX_START not in new:
                problems.append(f"{url}: 不安3つブロックなし")
            if url in ("/shindan/", "/learning-check/") and DIAG_START not in new:
                problems.append(f"{url}: 診断ページの末尾CTAなし")
            if "/assets/r28-ux" not in new:
                problems.append(f"{url}: r28 CSSなし")
        else:
            if new != raw:
                path.write_text(new, encoding="utf-8")
                changed += 1
        tables += 1 if TABLE_START in new else 0
        anx += 1 if ANX_START in new else 0
        diag += 1 if DIAG_START in new else 0
        variants += 1 if 'data-cta-variant="' in new else 0

    print(
        f"r28 CRO: 更新 {changed} / 比較表CTA {tables} / 不安3つ {anx} / 診断CTA {diag} / "
        f"文言出し分け {variants}"
    )
    if problems:
        print("\n".join(problems[:40]), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
