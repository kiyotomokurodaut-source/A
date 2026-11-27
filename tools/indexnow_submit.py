#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""IndexNow で Bing / ChatGPT検索 / Copilot などに URL の更新を通知する。

IndexNow は「サイト直下の <key>.txt に同じキーを書いておく」だけで、
検索エンジン側のアカウント登録なしに通知できる仕組み。Bing のインデックスは
ChatGPT Search と Copilot の検索結果の土台になっている。

    python3 tools/indexnow_submit.py                 # 送らずに件数とURLを確認（既定）
    python3 tools/indexnow_submit.py --limit 10      # 先頭10件だけ表示
    python3 tools/indexnow_submit.py --submit        # サイトマップの全URLを送信
    python3 tools/indexnow_submit.py --submit --urls https://kurodaschool.jp/new/  # 差分送信

* キーは public/ 直下の 32文字の .txt から読む（build.py が管理）。
* 送信先は api.indexnow.org と www.bing.com/indexnow。応答コードを表示する
  （200/202 が受け付け。403 はキーファイル不一致、422 はURL不備）。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path
from xml.etree import ElementTree

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "public"
SITE = "https://kurodaschool.jp"
ENDPOINTS = [
    "https://api.indexnow.org/indexnow",
    "https://www.bing.com/indexnow",
]


def find_key() -> str | None:
    for path in sorted(PUBLIC.glob("*.txt")):
        if re.fullmatch(r"[A-Za-z0-9]{32}", path.stem):
            body = path.read_text(encoding="utf-8").strip()
            if body == path.stem:
                return path.stem
    return None


def sitemap_urls() -> list[str]:
    tree = ElementTree.parse(PUBLIC / "sitemap.xml")
    return [
        el.text.strip()
        for el in tree.getroot().iter("{http://www.sitemaps.org/schemas/sitemap/0.9}loc")
        if el.text
    ]


def submit(endpoint: str, key: str, urls: list[str]) -> tuple[int, str]:
    payload = {
        "host": "kurodaschool.jp",
        "key": key,
        "keyLocation": f"{SITE}/{key}.txt",
        "urlList": urls,
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        endpoint,
        data=data,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, resp.read().decode("utf-8", "replace")[:300]
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", "replace")[:300]
    except Exception as exc:  # noqa: BLE001
        return 0, str(exc)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--submit", action="store_true", help="実際に送信する（既定はdry-run）")
    ap.add_argument("--urls", nargs="*", default=None, help="送るURLを指定（差分送信用）")
    ap.add_argument("--limit", type=int, default=0, help="表示するURL数の上限（0は全件）")
    args = ap.parse_args()

    key = find_key()
    if not key:
        print("IndexNow key file not found: public/<32文字>.txt", file=sys.stderr)
        return 1

    urls = args.urls or sitemap_urls()
    bad = [u for u in urls if not u.startswith(SITE + "/")]
    if bad:
        print(f"host mismatch: {bad[:3]}", file=sys.stderr)
        return 1

    print(f"key: {key}  keyLocation: {SITE}/{key}.txt")
    print(f"urls: {len(urls)}")
    shown = urls if args.limit <= 0 else urls[: args.limit]
    for u in shown:
        print("  " + u)
    if args.limit and len(urls) > args.limit:
        print(f"  ... and {len(urls) - args.limit} more")

    if not args.submit:
        print("\ndry-run: 送信していません。--submit で送信します。")
        return 0

    failed = 0
    for endpoint in ENDPOINTS:
        code, body = submit(endpoint, key, urls)
        ok = code in (200, 202)
        failed += 0 if ok else 1
        print(f"{endpoint} -> {code} {'OK' if ok else 'NG'} {body}".rstrip())
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
