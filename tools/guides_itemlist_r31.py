#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""r31（2026-11-28）: 学習ガイド一覧に ItemList の構造化データを置く。

    python3 tools/guides_itemlist_r31.py           # 生成・反映
    python3 tools/guides_itemlist_r31.py --check   # 差分の有無だけ確認

AI検索と検索エンジンが「どの記事がどのテーマを扱っているか」を一覧で
読み取れるように、/study-guides/ の head に ItemList（name・url・description）を
1ブロックだけ置く。記事を追加・改題したら、このスクリプトを実行して更新する
（実行しないと tools/seo_aio_meo_audit.py の #79 が件数不一致で FAIL する）。

* 各記事の題名（「｜」の前）・説明文・URL はページから読む（二重管理しない）。
* 何度実行しても同じ結果になる（マーカーの付いた script だけを差し替える）。
"""
from __future__ import annotations

import argparse
import html
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "public"
SITE = "https://kurodaschool.jp"
INDEX = PUBLIC / "study-guides" / "index.html"
MARK = 'data-r31="guides-itemlist"'


def route(path: Path) -> str:
    return ("/" + str(path.relative_to(PUBLIC))).replace("/index.html", "/")


def meta(raw: str, key: str) -> str:
    m = re.search(r'<meta content="([^"]*)" name="%s"' % key, raw)
    if m:
        return m.group(1)
    m = re.search(r'<meta name="%s" content="([^"]*)"' % key, raw)
    return m.group(1) if m else ""


def title_of(raw: str) -> str:
    m = re.search(r"<title>(.*?)</title>", raw, re.S)
    return html.unescape(m.group(1)).strip() if m else ""


def guides() -> list[dict]:
    out = []
    for p in sorted((PUBLIC / "study-guides").glob("*/index.html")):
        raw = p.read_text(encoding="utf-8")
        title = title_of(raw)
        if not title:
            continue
        out.append(
            {
                "name": title.split("｜")[0].strip(),
                "url": SITE + route(p),
                "description": meta(raw, "description"),
            }
        )
    return out


def payload(items: list[dict]) -> str:
    data = {
        "@context": "https://schema.org",
        "@type": "ItemList",
        "@id": f"{SITE}/study-guides/#guides",
        "name": "黒田塾の学習ガイド一覧",
        "description": "中学受験・大学受験の勉強法、科目別の対策、計画づくりを扱う無料の学習ガイド。",
        "numberOfItems": len(items),
        "itemListOrder": "https://schema.org/ItemListUnordered",
        "itemListElement": [
            {
                "@type": "ListItem",
                "position": i,
                "name": item["name"],
                "url": item["url"],
                "description": item["description"],
            }
            for i, item in enumerate(items, 1)
        ],
    }
    return (
        f'<script type="application/ld+json" {MARK}>'
        + json.dumps(data, ensure_ascii=False, separators=(",", ":"))
        + "</script>"
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    items = guides()
    if not items:
        print("no guides found")
        return 1
    raw = INDEX.read_text(encoding="utf-8")
    chunk = payload(items)
    pattern = re.compile(r'<script type="application/ld\+json" ' + re.escape(MARK) + r">.*?</script>", re.S)
    if pattern.search(raw):
        new = pattern.sub(lambda _m: chunk, raw, count=1)
    else:
        pos = raw.find("</head>")
        if pos == -1:
            print("</head> not found")
            return 1
        new = raw[:pos] + chunk + raw[pos:]
    if new == raw:
        print(f"guides ItemList: unchanged ({len(items)} items)")
        return 0
    if args.check:
        print(f"guides ItemList: would update ({len(items)} items)")
        return 0
    INDEX.write_text(new, encoding="utf-8")
    print(f"guides ItemList: updated ({len(items)} items)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
