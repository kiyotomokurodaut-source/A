#!/usr/bin/env python3
"""Render a per-page 1200x630 social card into public/og/.

Every image the site already had was portrait (the 900x1200 portrait, the
893x1263 handout preview, the 1288x1192 diagram). A share card is 1.91:1, so
each of them was being centre-cropped to an unreadable strip. These cards are
built at the right ratio and carry the page's own headline, so a link posted to
LINE, X or Slack says which page it opens.

The card copy comes from ``CARDS`` below rather than from the page's <title>:
a SERP title and a share card want different phrasing, and the titles contain
the "｜黒田塾" suffix that the card renders as a logo instead.

Flat brand colours, no photograph, quantised to a small palette: the text stays
crisp and each card lands around 20-30 KB.

    python3 tools/make_og_cards.py
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
PUBLIC = ROOT / "public"
OUTDIR = PUBLIC / "og"

W, H = 1200, 630

PAPER = (251, 250, 247)
INK = (22, 23, 29)
ICHO = (177, 146, 47)
ICHO_SOFT = (239, 230, 200)
ASAGI = (95, 149, 168)
GREY = (99, 100, 107)
LINE = (228, 225, 216)

GOTHIC = "/usr/share/fonts/opentype/ipafont-gothic/ipag.ttf"
GOTHIC_BOLD = "/usr/share/fonts/opentype/ipafont-gothic/ipagp.ttf"

# slug -> (eyebrow, headline,支え書き)
# The headline is wrapped automatically; keep each one under ~26 full-width
# characters so it stays at the largest size.
CARDS: dict[str, tuple[str, str, str]] = {
    "about": (
        "講師紹介",
        "東大卒・黒田清友が直接指導します",
        "東京大学 文科二類 現役合格／教育学部卒",
    ),
    "cases": (
        "指導事例",
        "実際に担当した指導の事例",
        "東大文一の日本史・数学／医学部受験／不登校からの大学合格",
    ),
    "contact": (
        "無料相談",
        "今の学習状況から、必要な支援を整理します",
        "オンラインで30分程度／LINEで相談できます",
    ),
    "junior-high-exam": (
        "中学受験",
        "中学受験の家庭教師と学習管理",
        "塾の宿題と復習の優先順位から組み直す",
    ),
    "online-tutoring": (
        "オンライン家庭教師",
        "授業と自習を、一つの計画にまとめる",
        "授業のみ 月額30,000円／面談＋授業 月額54,990円〜",
    ),
    "pricing": (
        "料金とプラン",
        "面談のみ・授業のみ・面談＋授業の5プラン",
        "月額24,000円〜／税込・月4セット分",
    ),
    "study-coaching": (
        "学習管理のみ",
        "授業は取らず、学習管理だけを頼む",
        "面談のみ 月額24,000円／週1回30分の面談と週次の計画更新",
    ),
    "university-exam": (
        "大学受験",
        "志望校から逆算する受験コーチング",
        "東大卒の講師が学習計画と答案を直接見ます",
    ),
    "faq": (
        "よくある質問",
        "料金・科目・受講方法のよくある質問",
        "5プランの違い、対応科目、相談の進め方",
    ),
    "site-map": (
        "ページ一覧",
        "指導案内と無料の学習ガイド",
        "黒田塾のページをまとめて探す",
    ),
    "study-guides": (
        "学習ガイド",
        "無料の学習シートと例題",
        "英語・数学の例題／模試の復習／週間計画",
    ),
    "study-guides/choosing-a-juku": (
        "学習ガイド",
        "塾の選び方を4つの形態で比較する",
        "集団塾・個別指導・家庭教師・学習管理",
    ),
    "study-guides/english-reading-diagnosis": (
        "学習ガイド",
        "英単語は分かるのに長文が読めない",
        "例題6問と全文和訳・無料PDF",
    ),
    "study-guides/homework-priorities": (
        "学習ガイド",
        "中学受験の塾の宿題が終わらないとき",
        "記録と印刷シートで優先順位を決める",
    ),
    "study-guides/math-self-solve": (
        "学習ガイド",
        "数学の解説は分かるのに解けない",
        "二次関数の例題で、方針を選ぶ理由を確かめる",
    ),
    "study-guides/mock-exam-review": (
        "学習ガイド",
        "模試の復習のやり方",
        "失点原因を整理して、次の課題を決める",
    ),
    "study-guides/todai-math-2026-3": (
        "東大理系数学 2026",
        "第3問の解説：球面・重心・弦の通過範囲",
        "図解と記述答案で、必要条件と十分条件を確かめる",
    ),
    "study-guides/weekly-study-plan": (
        "学習ガイド",
        "大学受験の学習計画表をつくる",
        "曜日別プランナー／保存と印刷ができます",
    ),
    "study-guides/kakomon-start-timing": (
        "学習ガイド",
        "過去問はいつから解き始めるか",
        "中学受験・大学受験の判断基準と使い方",
    ),
    "study-guides/common-test-english-time": (
        "学習ガイド",
        "共通テスト英語で時間が足りない",
        "失点の原因を4つに分けて、対策を決める",
    ),
    "study-guides/online-tutoring-vs-agency": (
        "学習ガイド",
        "オンライン家庭教師の個人契約と会社経由",
        "料金の内訳・交代・トラブル時の違いを比較",
    ),
}


def font(path: str, size: int) -> ImageFont.FreeTypeFont:
    try:
        return ImageFont.truetype(path, size)
    except OSError:
        return ImageFont.truetype(GOTHIC, size)


def wrap(text: str, f: ImageFont.FreeTypeFont, max_w: int) -> list[str]:
    """Wrap Japanese text by character, keeping 、。／ off a line start."""
    lines: list[str] = []
    cur = ""
    for ch in text:
        trial = cur + ch
        if f.getlength(trial) <= max_w or not cur:
            cur = trial
        else:
            if ch in "、。）」":
                cur = trial
                lines.append(cur)
                cur = ""
            else:
                lines.append(cur)
                cur = ch
    if cur:
        lines.append(cur)
    return lines


def ginkgo(draw: ImageDraw.ImageDraw, cx: int, cy: int, scale: float) -> None:
    pts = [
        (50, 8), (42, 30), (20, 44), (8, 50),
        (20, 56), (42, 70), (50, 92),
        (58, 70), (80, 56), (92, 50),
        (80, 44), (58, 30),
    ]
    draw.polygon(
        [(cx + (x - 50) * scale, cy + (y - 50) * scale) for x, y in pts],
        fill=ICHO,
    )


def render(slug: str, eyebrow: str, headline: str, support: str) -> Path:
    img = Image.new("RGB", (W, H), PAPER)
    d = ImageDraw.Draw(img)

    # Right-hand panel: the site's ginkgo mark on the soft gold, so the card
    # is recognisable as this site at thumbnail size.
    d.rectangle([(W - 430, 0), (W, H)], fill=ICHO_SOFT)
    ginkgo(d, W - 215, H // 2, 3.1)
    d.rectangle([(0, 0), (W, 10)], fill=ICHO)
    d.rectangle([(0, H - 6), (W, H)], fill=ASAGI)

    x, right = 80, W - 470
    max_w = right - x

    ginkgo(d, x + 14, 78, 0.44)
    d.text((x + 46, 60), "黒田塾", font=font(GOTHIC_BOLD, 38), fill=INK)

    d.text((x, 148), eyebrow, font=font(GOTHIC_BOLD, 26), fill=ICHO)

    f_head = font(GOTHIC_BOLD, 58)
    lines = wrap(headline, f_head, max_w)
    if len(lines) > 3:
        f_head = font(GOTHIC_BOLD, 48)
        lines = wrap(headline, f_head, max_w)
    y = 200
    for ln in lines[:4]:
        d.text((x, y), ln, font=f_head, fill=INK)
        y += f_head.size + 14

    y = max(y + 18, 452)
    d.rectangle([(x, y), (x + 88, y + 5)], fill=ICHO)

    f_sup = font(GOTHIC, 27)
    for ln in wrap(support, f_sup, max_w + 260)[:2]:
        y += 44
        d.text((x, y), ln, font=f_sup, fill=GREY)

    d.text(
        (x, H - 66),
        "kiyotomokuroda.netlify.app",
        font=font(GOTHIC, 22),
        fill=ASAGI,
    )

    out = OUTDIR / f"{slug.replace('/', '-')}.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    # A flat card needs very few colours; quantising keeps the text crisp and
    # the file an order of magnitude smaller than a truecolour PNG.
    img.convert("P", palette=Image.ADAPTIVE, colors=64).save(
        out, "PNG", optimize=True
    )
    return out


def main() -> None:
    total = 0
    for slug, (eyebrow, headline, support) in sorted(CARDS.items()):
        out = render(slug, eyebrow, headline, support)
        size = out.stat().st_size
        total += size
        print(f"  {out.relative_to(PUBLIC)!s:52} {size:>7,} bytes")
    print(f"wrote {len(CARDS)} cards, {total:,} bytes total")


if __name__ == "__main__":
    main()
