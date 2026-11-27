#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""r26: 全ページの robots メタに max-image-preview:large を足す（Doc 3-L 3-4）。

Google の画像プレビューを大きく出すための指定で、Google は既定では
「小さいプレビュー」に制限している。noindex のページ（404）は対象外。

* `index,follow` のような既存の指定は残し、足りない指定だけを追加する。
* `max-snippet:-1` が既にあるページはそのまま（順序も変えない）。
* 何度実行しても増えない。

    python3 tools/robots_meta_r26.py            # 適用
    python3 tools/robots_meta_r26.py --check    # 検証のみ
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

PUBLIC = Path(__file__).resolve().parents[1] / "public"

# name が先でも content が先でも拾えるようにする。
ROBOTS_RE = re.compile(r'<meta\b[^>]*?name="robots"[^>]*?>')


def get_content(tag: str) -> str:
    m = re.search(r'content="([^"]*)"', tag)
    return m.group(1) if m else ""


def set_content(tag: str, content: str) -> str:
    return re.sub(r'content="[^"]*"', f'content="{content}"', tag, count=1)


def upgraded(content: str) -> str:
    tokens = [t.strip() for t in content.split(",") if t.strip()]
    lower = [t.lower() for t in tokens]
    if "max-image-preview:large" in lower:
        return content
    tokens.append("max-image-preview:large")
    return ", ".join(tokens)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    changed = 0
    problems: list[str] = []
    for path in sorted(PUBLIC.rglob("*.html")):
        text = path.read_text(encoding="utf-8")
        m = ROBOTS_RE.search(text)
        if not m:
            problems.append(f"{path}: no robots meta")
            continue
        tag = m.group(0)
        content = get_content(tag)
        if "noindex" in content.lower():
            continue
        new_content = upgraded(content)
        if new_content != content:
            changed += 1
            if not args.check:
                text = text.replace(tag, set_content(tag, new_content), 1)
                path.write_text(text, encoding="utf-8")

    # 検証
    for path in sorted(PUBLIC.rglob("*.html")):
        text = path.read_text(encoding="utf-8")
        m = ROBOTS_RE.search(text)
        if not m:
            continue
        content = get_content(m.group(0)).lower()
        if "noindex" not in content and "max-image-preview:large" not in content:
            problems.append(f"{path}: max-image-preview:large missing")

    print(f"{'would update' if args.check else 'updated'} {changed} pages")
    if problems:
        print("\n".join(problems[:20]), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
