#!/usr/bin/env python3
"""Harvest prospects from the Google Places API (New) — the high-precision source.

Why this exists alongside ``harvest_osm.py``
--------------------------------------------
OpenStreetMap is free and needs no key, but the harvest proved what it is
missing. Across all of Tokyo, OSM holds about 5,100 businesses with a phone and
no website, and exactly **two** of them have 工務店 in the name. Storefronts
(restaurants, clinics, salons) get mapped; the office- and workshop-based
trades that can actually afford a website do not.

Google has all of them, and — crucially — a ``websiteUri`` field, so "no
website" is a fact from the listing itself rather than an absence of
volunteer effort.

Cost
----
``websiteUri`` and ``nationalPhoneNumber`` are **Enterprise**-tier fields, and
Enterprise SKUs get 1,000 free calls per month. One Text Search call returns up
to 20 places, so the free tier is worth roughly **20,000 businesses a month**,
which is far more than anyone can phone. Keep the field mask exactly as it is
below: adding a reviews or photos field re-prices every call at a higher SKU.

Setup
-----
1. Google Cloud console → enable "Places API (New)" → create an API key
2. Restrict the key to the Places API (New)
3. ``export GOOGLE_PLACES_KEY=...``

Usage
-----
    python3 harvest_places.py --area 墨田区 --category 工務店
    python3 harvest_places.py --all              # 全区 × 全業種（コール数に注意）
    python3 harvest_places.py --all --dry-run    # 何コール消費するかだけ表示
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw_places"
OUT = ROOT / "data" / "out"

ENDPOINT = "https://places.googleapis.com/v1/places:searchText"

# Exactly the Enterprise fields needed and nothing more. Every extra field
# class on the mask can move the whole call to a costlier SKU.
FIELD_MASK = ",".join([
    "places.id",
    "places.displayName",
    "places.formattedAddress",
    "places.nationalPhoneNumber",
    "places.websiteUri",
    "places.businessStatus",
    "places.primaryTypeDisplayName",
    "places.regularOpeningHours.weekdayDescriptions",
    "places.location",
])

TOKYO_23 = [
    "千代田区", "中央区", "港区", "新宿区", "文京区", "台東区", "墨田区", "江東区",
    "品川区", "目黒区", "大田区", "世田谷区", "渋谷区", "中野区", "杉並区", "豊島区",
    "北区", "荒川区", "板橋区", "練馬区", "足立区", "葛飾区", "江戸川区",
]

# The search terms, and what each is worth. Ordered by score so that a partial
# run still spends its calls on the profitable trades first. The reasoning
# behind the scores is in ../PRICING.md §3-③: the same work, very different
# customer value.
QUERIES = [
    ("工務店", "建設・職人", 10),
    ("リフォーム会社", "建設・職人", 10),
    ("塗装工事", "建設・職人", 10),
    ("電気工事", "建設・職人", 10),
    ("水道工事 設備", "建設・職人", 10),
    ("内装工事", "建設・職人", 9),
    ("解体工事", "建設・職人", 9),
    ("税理士事務所", "士業・コンサル", 9),
    ("行政書士事務所", "士業・コンサル", 9),
    ("司法書士事務所", "士業・コンサル", 9),
    ("社会保険労務士", "士業・コンサル", 9),
    ("不動産会社", "不動産", 8),
    ("自動車整備工場", "自動車・バイク整備", 9),
    ("板金塗装", "自動車・バイク整備", 9),
    ("葬儀社", "葬祭", 9),
    ("町工場 製作所", "製造・町工場", 9),
    ("印刷会社", "印刷", 7),
    ("運送会社", "運送・物流", 7),
    ("接骨院", "整体・接骨・鍼灸", 8),
    ("整体院", "整体・接骨・鍼灸", 8),
    ("鍼灸院", "整体・接骨・鍼灸", 8),
    ("動物病院", "動物病院", 8),
    ("学習塾", "塾・教室・習い事", 9),
    ("そろばん教室", "塾・教室・習い事", 9),
    ("書道教室", "塾・教室・習い事", 8),
    ("ピアノ教室", "塾・教室・習い事", 8),
    ("クリーニング店", "クリーニング", 6),
    ("造園業", "花・造園", 6),
    ("美容室", "美容・理容・エステ", 6),
    ("理容室", "美容・理容・エステ", 6),
]

# A listing whose only "website" is a social profile or a free page builder is
# still a prospect — arguably a better one, because the owner has already shown
# they want to be found and has run into the limits of a borrowed page.
BORROWED_HOSTS = (
    "instagram.com", "facebook.com", "twitter.com", "x.com", "tiktok.com",
    "ameblo.jp", "ameba.jp", "note.com", "peraichi.com", "jimdofree.com",
    "wixsite.com", "goo.ne.jp", "hotpepper.jp", "beauty.hotpepper.jp",
    "tabelog.com", "ekiten.jp", "r.gnavi.co.jp", "gnavi.co.jp",
    "itp.ne.jp", "line.me", "lit.link", "linktr.ee", "google.com",
    "business.site",   # retired Google "website from your Business Profile"
)


def call(query: str, area: str, key: str, *, refresh: bool) -> dict:
    cache = RAW / f"{area}_{query.replace(' ', '_')}.json"
    if cache.exists() and not refresh:
        return json.loads(cache.read_text(encoding="utf-8"))

    body = json.dumps({
        "textQuery": f"東京都{area} {query}",
        "languageCode": "ja",
        "regionCode": "JP",
        "pageSize": 20,
    }).encode("utf-8")
    req = urllib.request.Request(
        ENDPOINT,
        data=body,
        headers={
            "Content-Type": "application/json",
            "X-Goog-Api-Key": key,
            "X-Goog-FieldMask": FIELD_MASK,
        },
        method="POST",
    )
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            cache.parent.mkdir(parents=True, exist_ok=True)
            cache.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
            return data
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")[:300]
            if exc.code in (400, 403):
                # A bad key or a disabled API will not fix itself by retrying.
                sys.exit(f"Places API が {exc.code} を返しました。設定を確認してください:\n{detail}")
            print(f"  ! {area}/{query}: HTTP {exc.code} — 再試行", file=sys.stderr)
            time.sleep(2 ** attempt)
        except (urllib.error.URLError, TimeoutError) as exc:
            print(f"  ! {area}/{query}: {exc} — 再試行", file=sys.stderr)
            time.sleep(2 ** attempt)
    print(f"  !! {area}/{query} は取得できませんでした", file=sys.stderr)
    return {}


def borrowed(url: str) -> bool:
    host = urllib.parse.urlparse(url).netloc.lower().removeprefix("www.")
    return any(host == h or host.endswith("." + h) for h in BORROWED_HOSTS)


def rows_from(data: dict, area: str, label: str, score: int) -> list[dict]:
    out = []
    for place in data.get("places", []):
        if place.get("businessStatus") not in (None, "OPERATIONAL"):
            continue
        phone = (place.get("nationalPhoneNumber") or "").replace(" ", "")
        if not phone:
            continue                      # cannot call them; not a prospect
        site = place.get("websiteUri") or ""
        if site and not borrowed(site):
            continue                      # already has a real site
        name = (place.get("displayName") or {}).get("text", "").strip()
        if not name:
            continue
        notes = []
        bonus = 0
        if site:
            notes.append(f"借り物のページのみ: {urllib.parse.urlparse(site).netloc}")
            bonus += 2                    # already wants to be found
        hours = (place.get("regularOpeningHours") or {}).get("weekdayDescriptions") or []
        if hours:
            bonus += 1
            notes.append("営業時間掲載あり")
        loc = place.get("location") or {}
        out.append({
            "スコア": score + bonus,
            "屋号": name,
            "業種": label,
            "市区町村": area,
            "住所": place.get("formattedAddress", "").replace("日本、", ""),
            "電話": phone,
            "メール": "",
            "営業時間": " / ".join(hours[:2]),
            "メモ": " / ".join(notes),
            "確認用検索": "https://www.google.com/search?q="
                          + urllib.parse.quote(f'"{name}" {area}'),
            "地図": f"https://www.google.com/maps/place/?q=place_id:{place.get('id','')}",
            "緯度": loc.get("latitude"),
            "経度": loc.get("longitude"),
            "接触状況": "",
            "次回アクション": "",
        })
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--area", nargs="*", default=None)
    ap.add_argument("--category", nargs="*", default=None,
                    help="検索語の部分一致で絞る（例: 工務店 税理士）")
    ap.add_argument("--all", action="store_true", help="全区 × 全業種")
    ap.add_argument("--dry-run", action="store_true", help="消費コール数だけ表示")
    ap.add_argument("--refresh", action="store_true")
    args = ap.parse_args()

    areas = args.area or (TOKYO_23 if args.all else ["墨田区"])
    queries = QUERIES
    if args.category:
        queries = [q for q in QUERIES
                   if any(c in q[0] or c in q[1] for c in args.category)]
    if not queries:
        sys.exit("該当する業種がありません")

    planned = len(areas) * len(queries)
    if args.dry_run:
        print(f"{len(areas)}地域 × {len(queries)}業種 = {planned} コール")
        print("Enterprise SKU の無料枠は月1,000コール（1コール最大20件）です。")
        if planned > 1000:
            print(f"!! 無料枠を {planned - 1000} コール超えます。"
                  f"--area か --category で絞ってください。", file=sys.stderr)
        return 0

    key = os.environ.get("GOOGLE_PLACES_KEY")
    if not key:
        sys.exit("環境変数 GOOGLE_PLACES_KEY が設定されていません")

    OUT.mkdir(parents=True, exist_ok=True)
    all_rows: list[dict] = []
    calls = 0
    for area in areas:
        for query, label, score in queries:
            cached = (RAW / f"{area}_{query.replace(' ', '_')}.json").exists() and not args.refresh
            data = call(query, area, key, refresh=args.refresh)
            if not cached:
                calls += 1
                time.sleep(0.2)
            rows = rows_from(data, area, label, score)
            all_rows.extend(rows)
            print(f"{area} / {query}: {len(rows)} 件"
                  + ("（キャッシュ）" if cached else ""), flush=True)

    # The same business can come back from two search terms.
    seen: dict[str, dict] = {}
    for r in all_rows:
        seen.setdefault(r["電話"], r)
    rows = sorted(seen.values(), key=lambda r: (-r["スコア"], r["市区町村"], r["業種"]))

    path = OUT / "prospects_places.csv"
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()) if rows else ["屋号"])
        w.writeheader()
        w.writerows(rows)

    print(f"\n{calls} コール消費、重複を除いて {len(rows)} 件 → {path}")
    by_cat: dict[str, int] = {}
    for r in rows:
        by_cat[r["業種"]] = by_cat.get(r["業種"], 0) + 1
    for cat, n in sorted(by_cat.items(), key=lambda kv: -kv[1]):
        print(f"  {n:5d}  {cat}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
