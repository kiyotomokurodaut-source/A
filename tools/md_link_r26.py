#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""r26: 各HTMLの <head> に Markdown 版へのリンクを1本足す。

    <link rel="alternate" type="text/markdown" href="/about/index.md">

実体は tools/md_export_r26.py が生成する。HTMLを書き換えるのはこの
ツールだけで、build.py は生成物（.md）だけを作る。
何度実行しても増えない（text/markdown のリンクが既にあれば触らない）。

    python3 tools/md_link_r26.py            # 適用
    python3 tools/md_link_r26.py --check    # 検証のみ
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

PUBLIC = Path(__file__).resolve().parents[1] / "public"


def url_path(path: Path) -> str:
    rel = path.relative_to(PUBLIC).as_posix()
    if rel == "index.html":
        return "/"
    if rel.endswith("/index.html"):
        return "/" + rel[: -len("index.html")]
    return "/" + rel


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    changed = 0
    missing: list[str] = []
    for path in sorted(PUBLIC.rglob("*.html")):
        if path.name == "404.html":
            continue
        text = path.read_text(encoding="utf-8")
        if "text/markdown" in text:
            continue
        href = url_path(path) + "index.md"
        tag = f'<link rel="alternate" type="text/markdown" href="{href}"/>'
        if "</head>" not in text:
            missing.append(f"{path}: no </head>")
            continue
        text = text.replace("</head>", tag + "</head>", 1)
        changed += 1
        if not args.check:
            path.write_text(text, encoding="utf-8")

    # 検証: 全indexableページに1本ずつあること
    for path in sorted(PUBLIC.rglob("*.html")):
        if path.name == "404.html":
            continue
        text = path.read_text(encoding="utf-8")
        if 'rel="alternate" type="text/markdown"' not in text:
            missing.append(f"{url_path(path)}: no markdown alternate link")
        elif not (path.with_suffix(".md")).is_file():
            missing.append(f"{url_path(path)}: markdown file is missing")

    print(f"{'would update' if args.check else 'updated'} {changed} pages")
    if missing:
        print("\n".join(missing[:20]), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
