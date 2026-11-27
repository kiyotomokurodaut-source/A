#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""r24: パンくずの欠損修正とプライバシーページのタイトル調整。

* /cases/ にパンくずHTMLを追加
* /legal/ /materials/ /materials/terms/ /privacy/ /site-map/ に BreadcrumbList JSON-LD を追加
  （画面のパンくずと項目を一致させる）
* /privacy/ のタイトルを15字以上に伸ばす（SERPでの切れを避けるためではなく、
  build.py の下限に合わせるためではなく、サイト内の他ページと揃えるため）
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "public"
SITE = "https://kurodaschool.jp"


def ld_block(items: list[tuple[str, str]]) -> str:
    node = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": i + 1, "name": name, "item": url}
            for i, (name, url) in enumerate(items)
        ],
    }
    return (
        '<script type="application/ld+json">\n'
        + json.dumps(node, ensure_ascii=False, indent=2)
        + "\n</script>\n"
    )


def insert_before_head_end(path: Path, block: str) -> bool:
    text = path.read_text(encoding="utf-8")
    if '"@type": "BreadcrumbList"' in text or '"@type":"BreadcrumbList"' in text:
        return False
    idx = text.find("</head>")
    if idx < 0:
        raise SystemExit(f"{path}: no </head>")
    path.write_text(text[:idx] + block + text[idx:], encoding="utf-8")
    return True


def replace_once(path: Path, old: str, new: str) -> int:
    text = path.read_text(encoding="utf-8")
    if old not in text:
        raise SystemExit(f"{path}: pattern not found: {old[:60]}")
    text = text.replace(old, new)
    path.write_text(text, encoding="utf-8")
    return 1


def main() -> int:
    # 1) /cases/ のパンくずHTML
    cases = PUBLIC / "cases" / "index.html"
    replace_once(
        cases,
        '<main class="detail" id="main-content"><div class="wrap cases-intro">',
        '<main class="detail" id="main-content">'
        '<nav aria-label="パンくずリスト"><ol class="breadcrumbs">'
        '<li><a href="/">黒田塾</a></li>'
        '<li aria-current="page">指導事例</li></ol></nav>'
        '<div class="wrap cases-intro">',
    )

    # 2) BreadcrumbList JSON-LD（表示しているパンくずと一致させる）
    plan = {
        "legal/index.html": [
            ("黒田塾", f"{SITE}/"),
            ("教材プラン", f"{SITE}/materials/"),
            ("特定商取引法に基づく表記", f"{SITE}/legal/"),
        ],
        "materials/index.html": [
            ("黒田塾", f"{SITE}/"),
            ("教材プラン", f"{SITE}/materials/"),
        ],
        "materials/terms/index.html": [
            ("黒田塾", f"{SITE}/"),
            ("教材プラン", f"{SITE}/materials/"),
            ("教材の購入条件", f"{SITE}/materials/terms/"),
        ],
        "privacy/index.html": [
            ("黒田塾", f"{SITE}/"),
            ("プライバシーポリシー", f"{SITE}/privacy/"),
        ],
        "site-map/index.html": [
            ("黒田塾", f"{SITE}/"),
            ("ページ一覧", f"{SITE}/site-map/"),
        ],
    }
    added = 0
    for rel, items in plan.items():
        if insert_before_head_end(PUBLIC / rel, ld_block(items)):
            added += 1

    # 画面のパンくずも現在ページまで含める（legal / materials/terms / privacy）
    replace_once(
        PUBLIC / "legal" / "index.html",
        '<a href="/materials/">教材プラン</a></nav>',
        '<a href="/materials/">教材プラン</a><span>/</span>'
        '<span aria-current="page">特定商取引法に基づく表記</span></nav>',
    )
    replace_once(
        PUBLIC / "materials" / "terms" / "index.html",
        '<a href="/materials/">教材プラン</a></nav>',
        '<a href="/materials/">教材プラン</a><span>/</span>'
        '<span aria-current="page">教材の購入条件</span></nav>',
    )
    replace_once(
        PUBLIC / "privacy" / "index.html",
        '<a href="/">黒田塾</a><span>/</span><a href="/materials/">教材プラン</a></nav>',
        '<a href="/">黒田塾</a><span>/</span>'
        '<span aria-current="page">プライバシーポリシー</span></nav>',
    )

    # 3) /privacy/ のタイトル（14字 → 21字）
    replace_once(
        PUBLIC / "privacy" / "index.html",
        "プライバシーポリシー｜黒田塾",
        "プライバシーポリシー｜個人情報の扱い｜黒田塾",
    )

    print(f"added {added} BreadcrumbList blocks, fixed cases/privacy")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
