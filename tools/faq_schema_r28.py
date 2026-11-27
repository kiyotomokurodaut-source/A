#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""r28（2026-11-27）/faq/ の FAQPage 構造化データを、画面に出ているQ&Aと一致させる。

    python3 tools/faq_schema_r28.py            # 生成して書き込む
    python3 tools/faq_schema_r28.py --check    # 不一致の件数だけ表示（書き込みなし）

* 対象は <details class="r6-faq"><summary>質問</summary>…</details> の並び。
* 回答はHTMLを落としてテキストにし、mainEntity の acceptedAnswer.text に入れる。
* Googleは「画面に見えているQ&A」と構造化データが一致していることを求めるため、
  Q&Aを足したらこのスクリプトを通す（build.py の検査は件数の一致も見る）。
"""
from __future__ import annotations

import argparse
import html
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "public/faq/index.html"

DETAIL_RE = re.compile(
    r'<details class="r6-faq"><summary>(.*?)</summary>(.*?)</details>', re.S
)
LD_RE = re.compile(r'<script type="application/ld\+json">(.*?)</script>', re.S)


def text_of(fragment: str) -> str:
    text = re.sub(r"<br\s*/?>", " ", fragment)
    text = re.sub(r"<[^>]+>", "", text)
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def visible_qa(raw: str) -> list[dict]:
    items = []
    for q, a in DETAIL_RE.findall(raw):
        items.append(
            {
                "@type": "Question",
                "name": text_of(q),
                "acceptedAnswer": {"@type": "Answer", "text": text_of(a)},
            }
        )
    return items


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    raw = PAGE.read_text(encoding="utf-8")
    qa = visible_qa(raw)
    if not qa:
        print("FAQのQ&Aが見つかりません", file=sys.stderr)
        return 1

    changed = 0
    for m in LD_RE.finditer(raw):
        try:
            data = json.loads(m.group(1))
        except json.JSONDecodeError:
            continue
        nodes = data.get("@graph", []) if isinstance(data, dict) else []
        target = next((n for n in nodes if isinstance(n, dict) and n.get("@type") == "FAQPage"), None)
        if target is None:
            continue
        if target.get("mainEntity") == qa:
            break
        target["mainEntity"] = qa
        new_block = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
        old = m.group(1)
        if args.check:
            print(f"FAQPage mainEntity が画面と不一致（{len(target.get('mainEntity', []))}件 → {len(qa)}件）", file=sys.stderr)
            return 1
        raw = raw.replace(old, new_block, 1)
        changed += 1
        break

    if changed and not args.check:
        PAGE.write_text(raw, encoding="utf-8")
    print(f"FAQ: 画面のQ&A {len(qa)}件 / JSON-LD更新 {changed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
