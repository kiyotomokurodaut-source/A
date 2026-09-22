#!/usr/bin/env python3
"""検査済みの ``public/`` を、どこにでも置けるプレビュー一式に写す。

本番は ``/profile/`` のような絶対パスで動きます。サブディレクトリ配下や、
ディレクトリの index を返さないホストではそれが壊れるので、リンクを
``profile/index.html`` のような相対パスに書き換えた複製を作ります。

    python3 tools/make_preview.py <出力先>

中身は変えません。書き換えるのはリンクの綴りと、検索避けの meta robots だけです。
本番の ``public/`` には触りません。
"""

from __future__ import annotations

import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PUBLIC = ROOT / "public"

# プレビューに要らないもの。ホスト固有の設定と、SNS用のカード。
SKIP_DIRS = {"og"}
SKIP_FILES = {"sitemap.xml", "robots.txt", "_headers", "_redirects", "llms.txt"}


def to_relative(target: str, depth: int) -> str:
    """``/profile/#faq`` と深さ1 → ``../profile/index.html#faq``。"""
    path, hash_, frag = target.partition("#")
    if path in ("", "/"):
        rel = "index.html"
    elif path.endswith("/"):
        rel = path.strip("/") + "/index.html"
    else:
        rel = path.lstrip("/")
    return ("../" * depth) + rel + hash_ + frag


def rewrite(markup: str, depth: int) -> str:
    # href/src の絶対パスだけを相対に。 //example.com や https:// は触らない。
    def repl(m: re.Match[str]) -> str:
        attr, value = m.group(1), m.group(2)
        return f'{attr}="{to_relative(value, depth)}"'

    out = re.sub(r'\b(href|src)="(/(?!/)[^"]*)"', repl, markup)

    # srcset は "URL 420w, URL 640w" のリストなので、個別に直す。
    def repl_srcset(m: re.Match[str]) -> str:
        entries = []
        for entry in m.group(1).split(","):
            parts = entry.split()
            if parts and parts[0].startswith("/") and not parts[0].startswith("//"):
                parts[0] = to_relative(parts[0], depth)
            entries.append(" ".join(parts))
        return 'srcset="' + ", ".join(entries) + '"'

    out = re.sub(r'\bsrcset="([^"]*)"', repl_srcset, out)

    # プレビューが検索結果に出ないようにする。
    out = out.replace(
        '<meta name="robots" content="index, follow, max-image-preview:large">',
        '<meta name="robots" content="noindex, nofollow">',
    )
    # 実在しないホストを指す canonical は、プレビューでは外す。
    out = re.sub(r'\n\s*<link rel="canonical" href="[^"]*">', "", out)
    return out


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    out_root = Path(sys.argv[1]).resolve()
    if out_root.exists():
        shutil.rmtree(out_root)
    out_root.mkdir(parents=True)

    copied = 0
    for src in sorted(PUBLIC.rglob("*")):
        if not src.is_file():
            continue
        rel = src.relative_to(PUBLIC)
        if rel.parts[0] in SKIP_DIRS or rel.name in SKIP_FILES:
            continue

        dest = out_root / rel
        dest.parent.mkdir(parents=True, exist_ok=True)

        if src.suffix == ".html":
            depth = len(rel.parts) - 1
            dest.write_text(rewrite(src.read_text(encoding="utf-8"), depth), encoding="utf-8")
        elif src.suffix == ".webmanifest":
            # アイコンのパスも相対にする（マニフェストはルート直下）
            dest.write_text(
                src.read_text(encoding="utf-8").replace('"/assets/', '"assets/'),
                encoding="utf-8",
            )
        else:
            shutil.copy2(src, dest)
        copied += 1

    print(f"{copied} ファイルを {out_root} に書き出しました。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
