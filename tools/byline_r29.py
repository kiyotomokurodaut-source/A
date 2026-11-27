#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""r29: 学習ガイドの著者表記と日付（公開日・更新日）を全記事で揃える。

    python3 tools/byline_r29.py            # 書き込み
    python3 tools/byline_r29.py --check    # 点検のみ（不足・揺れの件数を表示）

これまでの記事は、byline の書式が「制作：黒田塾」「執筆・監修」「内容更新」などに
分かれ、更新日がない記事が大半だった。著者ボックス（#author-profile）は全記事に
あるため、byline だけを次の1形に統一する。

    執筆・監修：黒田清友（東京大学教育学部卒・黒田塾代表）｜公開日：…｜更新日：…

日付はページが持つ値だけを使う（公開日は Article の datePublished、更新日は
meta last-modified）。新しい日付を作らない。
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "public"
GUIDES = PUBLIC / "study-guides"

BYLINE_RE = re.compile(r'<p class="byline">.*?</p>', re.S)
PUB_RE = re.compile(r'"datePublished"\s*:\s*"(\d{4}-\d{2}-\d{2})"')
LASTMOD_RE = re.compile(r'<meta content="(\d{4}-\d{2}-\d{2})" name="last-modified"/>')


def jp(iso: str) -> str:
    y, m, d = iso.split("-")
    return f"{int(y)}年{int(m)}月{int(d)}日"


def byline(published: str, modified: str) -> str:
    return (
        '<p class="byline">執筆・監修：<a href="/about/">黒田清友</a>'
        "（東京大学教育学部卒・黒田塾代表）"
        f'｜公開日：<time datetime="{published}">{jp(published)}</time>'
        f' ｜ 更新日：<time datetime="{modified}">{jp(modified)}</time></p>'
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    changed = 0
    missing: list[str] = []
    for path in sorted(GUIDES.glob("*/index.html")):
        raw = path.read_text(encoding="utf-8")
        pub_m = PUB_RE.search(raw)
        mod_m = LASTMOD_RE.search(raw)
        if not pub_m or not mod_m:
            missing.append(f"{path.parent.name}: {'公開日' if not pub_m else ''}{'更新日' if not mod_m else ''}が読めない")
            continue
        want = byline(pub_m.group(1), mod_m.group(1))
        current = BYLINE_RE.search(raw)
        if current:
            if current.group(0) == want:
                continue
            if args.check:
                changed += 1
                continue
            raw = raw.replace(current.group(0), want, 1)
        else:
            h1 = raw.find("</h1>")
            if h1 < 0:
                missing.append(f"{path.parent.name}: h1 がない")
                continue
            if args.check:
                changed += 1
                continue
            raw = raw[: h1 + 5] + "\n" + want + raw[h1 + 5 :]
        path.write_text(raw, encoding="utf-8")
        changed += 1

    verb = "未統一" if args.check else "更新"
    print(f"{verb} {changed}本 / 読めない値 {len(missing)}件")
    for m in missing:
        print("  -", m, file=sys.stderr)
    return 1 if (args.check and (changed or missing)) or missing else 0


if __name__ == "__main__":
    raise SystemExit(main())
