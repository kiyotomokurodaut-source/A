#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""r28（2026-11-27）GA4（Google Analytics 4）の計測タグを全ページに同期する。

    python3 tools/ga4_r28.py            # 全HTMLの<head>に挿入（既存ブロックは差し替え）
    python3 tools/ga4_r28.py --check    # 不足・重複の点検のみ（書き込みなし）

方針:
* 測定IDは GA4 プロパティ「黒田塾」（ストリーム 16429483808）の G-QBX05P7M5T。
* 挿入するのは、gtag.js の読み込み・config・LINEクリック計測JS（/assets/analytics-*.js）。
* Google シグナルと広告のパーソナライズは無効にする。このサイトは広告目的の
  リマーケティングを行わず、プライバシーポリシーの記載とも一致させる。
* Google アナリティクスはCookie（_ga）を使うため、プライバシーポリシーに
  外部送信（アクセス解析）の記載を置く。記載は /privacy/ が正本。
* 本スクリプトはHTMLだけを書き換える。build.py --check が全ページの
  タグ有無を検査するので、ページを増やしたらこのスクリプトを通してから
  コミットする。
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "public"

MEASUREMENT_ID = "G-QBX05P7M5T"
GTAG_SRC = f"https://www.googletagmanager.com/gtag/js?id={MEASUREMENT_ID}"
ANALYTICS_SRC = "/assets/analytics-r28.js"

START = "<!-- r28:ga4:start -->"
END = "<!-- r28:ga4:end -->"

BLOCK = (
    START
    + f'<script async src="{GTAG_SRC}"></script>'
    + "<script>window.dataLayer=window.dataLayer||[];function gtag(){dataLayer.push(arguments);}"
    + "gtag('js',new Date());"
    + f"gtag('config', '{MEASUREMENT_ID}', "
    + "{allow_google_signals:false,allow_ad_personalization_signals:false});</script>"
    + f'<script defer src="{ANALYTICS_SRC}"></script>'
    + END
)

BLOCK_RE = re.compile(re.escape(START) + r".*?" + re.escape(END), re.S)


def html_files() -> list[Path]:
    return sorted(PUBLIC.rglob("*.html"))


def route(path: Path) -> str:
    rel = path.relative_to(PUBLIC).as_posix()
    if rel == "index.html":
        return "/"
    return "/" + rel[: -len("index.html")] if rel.endswith("/index.html") else "/" + rel


def apply_page(raw: str) -> str:
    if START in raw:
        # 何度実行しても同じ結果になるよう、既存ブロックは丸ごと置き換える。
        return BLOCK_RE.sub(lambda _m: BLOCK, raw, count=1)
    return raw.replace("</head>", BLOCK + "</head>", 1)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    changed, missing, doubled = 0, [], []
    for path in html_files():
        url = route(path)
        raw = path.read_text(encoding="utf-8")
        new = apply_page(raw)
        n_start = new.count(START)
        if n_start != 1:
            doubled.append(f"{url}: GA4ブロックが{n_start}個")
            continue
        if GTAG_SRC not in new or f"gtag('config', '{MEASUREMENT_ID}'" not in new:
            missing.append(url)
            continue
        if not args.check and new != raw:
            path.write_text(new, encoding="utf-8")
            changed += 1

    pages = len(html_files())
    print(f"GA4({MEASUREMENT_ID}): {pages}ページ / 更新 {changed} / 不足 {len(missing)} / 重複 {len(doubled)}")
    problems = missing + doubled
    if problems:
        print("\n".join(problems[:40]), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
