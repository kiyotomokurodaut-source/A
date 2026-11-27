#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""r25: AI検索（ChatGPT・Claude・Gemini）が引用しやすい要点ブロックを主要4ページに置く。

対象: / ・/about/ ・/pricing/ ・/cases/
方針:
  * サイト本文にある事実だけを書く（新しい実績・数値は作らない）
  * 料金は build.py の正本と同じ5プラン
  * /cases/ は「指導経験」と「合格が確認できている事例」を区別したまま要約する
  * 既に同じブロックがある場合は二重に挿入しない（冪等）

    python3 tools/aio_facts_r25.py           # 適用
    python3 tools/aio_facts_r25.py --check   # 挿入位置が見つかるかだけ確認
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "public"
TODAY = "2026-11-27"

FACTS_SECTION = (
    '<section class="section wrap" id="facts"><div class="section-intro">'
    '<p class="eyebrow">AT A GLANCE</p><h2>黒田塾の基本情報</h2>'
    "<p>塾選びで確認される項目を、このサイトの内容から一か所にまとめました。"
    "料金・対応科目・指導形態の詳細は、それぞれのリンク先が一次情報です。</p></div>"
    '<div class="subject-overview">'
    "<p><b>塾名</b><span>黒田塾（Kuroda School）／個人運営</span></p>"
    "<p><b>代表・講師</b><span>黒田清友（東京大学文科二類に現役合格、教育学部卒）</span></p>"
    "<p><b>指導形態</b><span>オンライン個別指導のみ。教室・校舎はなく、"
    "全国47都道府県から受講できます</span></p>"
    "<p><b>担当</b><span>授業・学習計画・答案添削を代表が一人で担当"
    "（講師の交代はありません）</span></p>"
    "<p><b>対象</b><span>中学受験・大学受験（小学生・中学生・高校生・浪人生）</span></p>"
    "<p><b>科目</b><span>英語・数学（算数）・国語・社会・小論文・面接。"
    "大学二次試験レベルの理科は対象外です</span></p>"
    "<p><b>料金</b><span>月額24,000円（面談のみ）〜104,990円（面談＋授業・週3回）。"
    "税込・月4セットです</span></p>"
    "<p><b>実績</b><span>累計50人以上を指導。東京大学・慶應義塾大学・医学部・"
    "難関中学・外国語大学などへの合格指導があります</span></p>"
    "<p><b>向いている生徒</b><span>復習の優先順位と週次の計画を整理したい、"
    "答案を継続して添削してほしい、通塾の時間を確保しにくい</span></p>"
    "</div>"
    '<p class="ks-more"><a class="text-link" href="/juku/">'
    "向いている場合・向いていない場合を読む →</a></p></section>"
)

ABOUT_ADDITIONS = (
    "<li>担当：授業・学習計画・答案添削を代表の黒田清友が一人で担当"
    "（講師の交代はありません）</li>"
    "<li>向いている生徒：学校や塾の授業はあるが復習の優先順位と週次の計画が"
    "崩れている、答案を継続して添削してほしい、通塾の時間を確保しにくい</li>"
    "<li>向いていない場合：大人数の集団授業、校舎の自習室、大学二次試験レベルの"
    '理科を主科目として求める場合は、他塾との比較を勧めています（'
    '<a href="/juku/">向き不向きの詳細</a>）</li>'
)

PRICING_BOX = (
    '<div class="summary-box"><strong>このページの要点</strong><ul>'
    "<li>継続受講は5プラン。面談のみ24,000円、授業のみ（週1回）30,000円、"
    "面談＋授業は週1回54,990円・週2回79,990円・週3回104,990円</li>"
    "<li>いずれも月額・税込・月4セット分。地域や志望校によって料金は変わらない</li>"
    "<li>授業のみ（週1回）は定期面談なし。面談＋授業は週1回30分の面談と"
    "90分授業の組み合わせ</li>"
    "</ul><p>「週2回」「週3回」は授業の回数で、面談の回数ではありません。</p></div>"
)

CASES_BOX = (
    '<div class="summary-box"><strong>このページの要点</strong><ul>'
    "<li>掲載しているのは3件の指導事例（東大文科一類の日本史・数学、"
    "医学部受験の数学・英語、不登校からの外国語大学合格）</li>"
    "<li>東大文科一類と医学部の2件は指導経験の紹介で、合格実績として"
    "掲載しているものではありません</li>"
    "<li>個人が特定される情報は伏せて掲載しています。"
    "個別の結果であり、同じ結果を保証するものではありません</li>"
    "</ul></div>"
)


def apply(path: Path, old: str, new: str, label: str, problems: list[str]) -> bool:
    text = path.read_text(encoding="utf-8")
    if new.strip()[:80] in text:
        return False
    if old not in text:
        problems.append(f"{label}: 挿入位置が見つからない")
        return False
    path.write_text(text.replace(old, new, 1), encoding="utf-8")
    return True


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    problems: list[str] = []
    changed: list[str] = []

    def run(path: Path, old: str, new: str, label: str) -> None:
        if args.check:
            text = path.read_text(encoding="utf-8")
            if new.strip()[:60] not in text and old not in text:
                problems.append(f"{label}: 挿入位置が見つからない")
            return
        if apply(path, old, new, label, problems):
            changed.append(label)

    run(
        PUBLIC / "index.html",
        '<section class="section wrap" id="start-flow">',
        FACTS_SECTION + '<section class="section wrap" id="start-flow">',
        "/ 基本情報ブロック",
    )
    run(
        PUBLIC / "about" / "index.html",
        "</ul></section><section><h2>経歴と指導実績</h2>",
        ABOUT_ADDITIONS + "</ul></section><section><h2>経歴と指導実績</h2>",
        "/about/ 概要の追記",
    )
    run(
        PUBLIC / "pricing" / "index.html",
        '<div class="summary-box"><strong>「授業のみ」と「面談＋授業」は別プランです</strong>',
        PRICING_BOX + '<div class="summary-box"><strong>「授業のみ」と「面談＋授業」は別プランです</strong>',
        "/pricing/ 要点ボックス",
    )
    run(
        PUBLIC / "cases" / "index.html",
        '<div class="case-links">',
        CASES_BOX + '<div class="case-links">',
        "/cases/ 要点ボックス",
    )

    for label in changed:
        print("inserted:", label)

    # 変更した4ページの last-modified を今日に揃える（未来日は不可）
    for rel in ("index.html", "about/index.html", "pricing/index.html", "cases/index.html"):
        path = PUBLIC / rel
        text = path.read_text(encoding="utf-8")
        text2 = re.sub(
            r'(<meta content=")[^"]*(" name="last-modified"/>)',
            rf"\g<1>{TODAY}\g<2>",
            text,
        )
        text2 = re.sub(
            r'(<meta content=")[^"]*(" name="last-modified">)',
            rf"\g<1>{TODAY}\g<2>",
            text2,
        )
        text2 = re.sub(
            r'(<meta name="last-modified" content=")[^"]*(")',
            rf"\g<1>{TODAY}\g<2>",
            text2,
        )
        text2 = re.sub(
            r'("dateModified":\s*")[^"]*(")',
            rf"\g<1>{TODAY}\g<2>",
            text2,
        )
        if text2 != text and not args.check:
            path.write_text(text2, encoding="utf-8")

    for p in problems:
        print("PROBLEM:", p)
    print("done" if not problems else "done with problems")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
