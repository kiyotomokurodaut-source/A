#!/usr/bin/env python3
"""Harvest Tokyo businesses that have a phone number but no website, from OpenStreetMap.

Why OSM: it is the only openly licensed (ODbL) source of business listings that
carries a ``website`` tag, so "the tag is absent" is a usable first-pass signal
for "this company has no homepage". It is a *first pass*, not proof: OSM is
volunteer-maintained and a shop can have a site nobody recorded. Every row is
emitted with a ready-made search URL so the absence gets confirmed by a human
before anyone picks up the phone. See ``verify.py``.

Chains are dropped on purpose. A 7-Eleven does not buy a 30,000 yen website;
an owner-operated 工務店 might.

Usage
-----
    python3 harvest_osm.py                 # all configured municipalities
    python3 harvest_osm.py --area 台東区 品川区
    python3 harvest_osm.py --refresh       # ignore the on-disk cache

Output: biz/data/out/prospects.csv (and the raw Overpass JSON under data/raw/).
Standard library only.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "out"

# Overpass is a free, donated service run on other people's hardware. It
# throttles per IP and refuses connections outright once a cooldown starts, so
# the harvester rotates mirrors, waits between municipalities, and caches every
# response to disk. A re-run costs the servers nothing.
ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
    "https://overpass.osm.jp/api/interpreter",
]
PAUSE_SECONDS = 25.0
TIMEOUT_SECONDS = 180

TOKYO_23 = [
    "千代田区", "中央区", "港区", "新宿区", "文京区", "台東区", "墨田区", "江東区",
    "品川区", "目黒区", "大田区", "世田谷区", "渋谷区", "中野区", "杉並区", "豊島区",
    "北区", "荒川区", "板橋区", "練馬区", "足立区", "葛飾区", "江戸川区",
]
TAMA = [
    "八王子市", "町田市", "府中市", "調布市", "武蔵野市", "三鷹市", "立川市",
    "西東京市", "小金井市", "日野市",
]
AREAS = TOKYO_23 + TAMA

# ---------------------------------------------------------------------------
# Which businesses are worth a call.
#
# `score` is the base priority (0-10). It encodes two things at once: how much
# a website is actually worth to that trade (does a customer search for it
# before buying?) and whether the owner is reachable and decides alone.
#
# A 工務店 scores high because a homeowner researching a 300万円 renovation
# will not call a company they cannot look up, so the site pays for itself in
# one job. A restaurant scores low not because there are few of them but
# because 食べログ and Instagram already do the job for the owner, which makes
# the sales call much harder.
# ---------------------------------------------------------------------------
CATEGORIES = [
    # (tag key, tag value regex, label, score)
    # `craft=*` is NOT a synonym for the building trades. In the Tokyo data it
    # holds photographers, confectioners, jewellers and dressmakers alongside
    # carpenters and electricians, so a catch-all here put a とんかつ屋 and a
    # 写真館 at the top of the builders' call sheet. Each value is mapped.
    ("craft", r"carpenter|electrician|plumber|painter|roofer|plasterer|scaffolder"
              r"|hvac|metal_construction|joiner|glaziery|stonemason|tiler"
              r"|carpet_layer|insulation|floorer|window_construction|builder"
              r"|blacksmith|welder|rigger",
     "建設・職人（工務店/内装/電気/塗装ほか）", 10),
    ("craft", r"gardener|horticulturist", "花・造園", 6),
    ("craft", r"confectionery|bakery|brewery|winery|distillery|caterer|butcher",
     "食品製造・仕出し", 6),
    ("craft", r"photographer", "写真館", 6),
    ("craft", r"tailor|dressmaker|shoemaker|upholsterer|leather|saddler",
     "衣料・修理", 5),
    ("craft", r"jeweller|watchmaker|pottery|musical_instrument", "専門小売", 5),
    ("craft", r"key_cutter|locksmith", "鍵・防犯", 6),
    ("craft", r"signmaker|bookbinder", "印刷", 7),
    # Anything else tagged as a craft is still a small owner-run workshop,
    # which is the right kind of prospect — just not a builder.
    ("craft", r".*", "職人・工房", 6),
    ("office", r"lawyer|accountant|tax_advisor|notary|consulting|employment_agency", "士業・コンサル", 9),
    ("office", r"estate_agent", "不動産", 8),
    ("shop", r"car_repair|car_parts|motorcycle_repair", "自動車・バイク整備", 9),
    ("shop", r"funeral_directors", "葬祭", 9),
    ("healthcare", r"physiotherapist|alternative|chiropractor", "整体・接骨・鍼灸", 8),
    ("amenity", r"dentist", "歯科", 8),
    ("amenity", r"doctors|clinic", "クリニック", 7),
    ("amenity", r"veterinary", "動物病院", 8),
    ("shop", r"hairdresser|beauty|massage|nail", "美容・理容・エステ", 6),
    ("shop", r"dry_cleaning|laundry", "クリーニング", 6),
    ("shop", r"florist|garden_centre", "花・造園", 6),
    ("office", r"company|it|insurance|financial|architect|engineer|logistics", "一般企業・専門事務所", 8),
    ("shop", r"printing|copyshop", "印刷", 7),
    ("shop", r"bakery|confectionery|butcher|greengrocer|seafood|deli", "食品小売", 5),
    ("leisure", r"fitness_centre|sports_centre", "スポーツ・ジム", 6),
    ("amenity", r"driving_school", "教習・スクール", 7),
    ("shop", r"clothes|shoes|jewelry|furniture|watches|antiques|musical_instrument", "専門小売", 5),
    ("amenity", r"restaurant|cafe|bar|pub", "飲食", 3),
]

# ---------------------------------------------------------------------------
# Name-based rules, applied BEFORE the tag rules.
#
# This exists because of what the data actually looks like. Across all of
# Tokyo, only 2 elements carry a name containing 工務店, and `craft=*` — the
# tag that should hold every builder, electrician and painter — is barely used
# in Japan. Meanwhile 整骨院 and 接骨院 are mapped roughly 80 times, but almost
# always as `shop=massage` or `amenity=doctors`, which the healthcare tag rule
# never matches.
#
# So in Japan the 屋号 is the reliable signal and the tag is not: a business
# called 〇〇接骨院 is an 接骨院 whatever a mapper typed in the tag field.
# ---------------------------------------------------------------------------
NAME_RULES = [
    (r"整骨|接骨|鍼灸|はり灸|針灸|整体|カイロプラクティック|指圧|マッサージ",
     "整体・接骨・鍼灸", 8),
    (r"工務店|建設|建築|塗装|電気工事|設備工業|土木|板金|解体|内装|左官|防水|外構|"
     r"サッシ|管工事|リフォーム|住器|工事",
     "建設・職人（工務店/内装/電気/塗装ほか）", 10),
    (r"税理士|会計士|行政書士|司法書士|社会保険労務士|社労士|弁護士|弁理士|法律事務所|"
     r"特許事務所|土地家屋調査士",
     "士業・コンサル", 9),
    (r"不動産|地所|土地建物|ハウジング|住宅販売", "不動産", 8),
    (r"製作所|鉄工|精機|製造|工場|金属|樹脂|加工", "製造・町工場", 9),
    (r"印刷|製本|出版", "印刷", 7),
    (r"教習所|自動車学校", "教習・スクール", 7),
    (r"自動車|モータース|オート|車検|カーサービス|ガレージ", "自動車・バイク整備", 9),
    (r"運送|運輸|物流|配送", "運送・物流", 7),
    (r"葬儀|葬祭|斎場|石材", "葬祭", 9),
    (r"造園|植木|緑化", "花・造園", 6),
    (r"クリーニング|ランドリー|洗濯", "クリーニング", 6),
    (r"保険|損保|生命", "保険", 7),
    (r"薬局|調剤|ドラッグ", "薬局・調剤", 5),
    (r"塾$|学院|ゼミナール|予備校|教室|スクール|そろばん|書道|珠算",
     "塾・教室・習い事", 9),
]

# A listing carrying any of these is run by a chain or already has a web
# presence somebody else maintains. Not our customer.
CHAIN_KEYS = ("brand", "brand:wikidata", "brand:wikipedia", "operator:wikidata")
WEB_KEYS = ("website", "contact:website", "url", "website:en", "contact:url")

PHONE_KEYS = ("phone", "contact:phone", "phone:JP")


def overpass_query(area: str) -> str:
    """One query per municipality: everything phoneable that has no website tag.

    The municipality is resolved *inside* 東京都 rather than by bare name,
    because names like 府中市 and 港区 exist in several prefectures and a bare
    name match silently returns the wrong city's shops.
    """
    return f"""
[out:json][timeout:{TIMEOUT_SECONDS}];
area["name"="東京都"]["admin_level"="4"]->.pref;
rel(area.pref)["name"="{area}"]["admin_level"="7"];
map_to_area->.a;
(
  nwr(area.a)["phone"]["name"][!"website"][!"contact:website"][!"url"];
  nwr(area.a)["contact:phone"]["name"][!"website"][!"contact:website"][!"url"];
);
out center tags;
""".strip()


def fetch(area: str, *, refresh: bool) -> dict:
    cache = RAW / f"{area}.json"
    if cache.exists() and not refresh:
        return json.loads(cache.read_text(encoding="utf-8"))

    query = overpass_query(area)
    attempts = 10
    for attempt in range(attempts):
        endpoint = ENDPOINTS[attempt % len(ENDPOINTS)]
        req = urllib.request.Request(
            endpoint + "?" + urllib.parse.urlencode({"data": query}),
            headers={
                "Accept": "application/json",
                # Overpass asks that automated clients identify themselves.
                "User-Agent": "tokyo-smb-prospecting/1.0 (OSM ODbL)",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS + 60) as resp:
                body = resp.read().decode("utf-8")
            data = json.loads(body)
            if "elements" not in data:
                raise json.JSONDecodeError("no elements", body[:200], 0)
            cache.parent.mkdir(parents=True, exist_ok=True)
            cache.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
            return data
        except (urllib.error.URLError, json.JSONDecodeError, TimeoutError, OSError) as exc:
            wait = min(120, 10 * 2 ** (attempt // len(ENDPOINTS)))
            host = urllib.parse.urlparse(endpoint).netloc
            print(f"  ! {area} @{host}: {exc} — {wait}秒待機", file=sys.stderr, flush=True)
            time.sleep(wait)
    print(f"  !! {area} は{attempts}回失敗。スキップします", file=sys.stderr, flush=True)
    return {"elements": []}


def classify(tags: dict) -> tuple[str, int] | None:
    """Name first, tag second. See the note above NAME_RULES for why."""
    name = tags.get("name", "")
    for pattern, label, score in NAME_RULES:
        if re.search(pattern, name):
            return label, score
    for key, pattern, label, score in CATEGORIES:
        value = tags.get(key)
        if value and re.fullmatch(pattern, value):
            return label, score
    return None


def address_of(tags: dict, area: str) -> str:
    """OSM stores Japanese addresses in pieces; reassemble in postal order."""
    parts = [
        tags.get("addr:province") or "東京都",
        tags.get("addr:city") or tags.get("addr:suburb") or area,
        tags.get("addr:quarter", ""),
        tags.get("addr:neighbourhood", ""),
    ]
    block = tags.get("addr:block_number", "")
    number = tags.get("addr:housenumber", "")
    tail = "-".join(p for p in (block, number) if p)
    body = "".join(p for p in parts if p)
    return f"{body}{tail}" if tail else body


def format_phone(digits: str) -> str:
    """Re-insert the hyphens a Japanese number is normally read with.

    Area-code length is not derivable from the number: 042 covers 立川・八王子・
    府中 while 0422 covers 武蔵野・三鷹, and both are ten digits starting 042.
    Splitting by position alone turns 042-362-2470 into 0423-62-2470, which is
    the pre-1999 spelling and reads as a typo on a call sheet. So only the
    codes that can be identified are hyphenated; everything else is left as
    plain digits, which still dials.
    """
    TOKYO_4 = ("0422", "0424", "0425", "0426", "0427", "0428")
    if len(digits) == 10 and digits.startswith("03"):
        return f"{digits[:2]}-{digits[2:6]}-{digits[6:]}"
    if len(digits) == 11 and digits[:3] in ("070", "080", "090"):
        return f"{digits[:3]}-{digits[3:7]}-{digits[7:]}"
    if len(digits) == 10 and digits[:4] in TOKYO_4:
        return f"{digits[:4]}-{digits[4:6]}-{digits[6:]}"
    if len(digits) == 10 and digits.startswith("042"):
        return f"{digits[:3]}-{digits[3:6]}-{digits[6:]}"
    if len(digits) == 10 and digits[:4] in ("0120", "0800"):
        return f"{digits[:4]}-{digits[4:7]}-{digits[7:]}"
    return digits


TOKYO_23_SET = set(TOKYO_23)


def normalise_phone(tags: dict, area: str) -> tuple[str, str]:
    """Return (number, note). An empty number means the row is unusable.

    OSM phone numbers are typed by hand and about 8% of the Tokyo rows are
    damaged in ways that are obvious once you look at them:

        0081336332863  国番号つき（0081 = +81）→ 03-3633-2863
        00333036308    先頭のゼロが重複 → 03-3303-6308
        33286754       23区の 03 が落ちている → 03-3328-6754

    Those three are recoverable without guessing. What is left — a seven-digit
    fragment, a number with one digit too many — could be repaired only by
    inventing a digit, and a wrong number on a call sheet costs a call and
    reaches a stranger. Those are kept but marked, and sorted to the bottom.
    """
    raw = next((tags[k] for k in PHONE_KEYS if tags.get(k)), "")
    raw = raw.split(";")[0].strip()
    digits = re.sub(r"[^\d+]", "", raw)
    if not digits:
        return "", ""

    note = ""
    if digits.startswith("+81"):
        digits = "0" + digits[3:]
    elif digits.startswith("0081"):
        digits = "0" + digits[4:]
    elif digits.startswith("+"):
        digits = digits.lstrip("+")
        note = "国際表記の崩れ／要確認"
    # A doubled leading zero is a typing slip, not an area code.
    while digits.startswith("00") and len(digits) > 10:
        digits = digits[1:]
    # Inside the 23 wards, an eight-digit number is the subscriber part of an
    # 03 number. Outside them the area code is not guessable, so leave it.
    if len(digits) == 8 and area in TOKYO_23_SET:
        digits = "03" + digits
        note = "03を補完（要確認）"

    if len(digits) in (10, 11) and digits.startswith("0"):
        return format_phone(digits), note
    return digits, (note or f"電話番号が{len(digits)}桁／要確認")


def bonus(tags: dict) -> tuple[int, list[str]]:
    """Signals that this owner already invests in being found, or is easy to pitch."""
    score, notes = 0, []
    if any(tags.get(k) for k in ("facebook", "contact:facebook", "contact:instagram", "contact:line")):
        score += 2
        notes.append("SNSあり=集客意欲あり")
    if tags.get("opening_hours"):
        score += 1
        notes.append("営業時間記載")
    if tags.get("addr:housenumber"):
        score += 1
        notes.append("住所完全=郵送可")
    if tags.get("contact:email") or tags.get("email"):
        score += 2
        notes.append("メールあり")
    return score, notes


def rows_from(data: dict, area: str) -> list[dict]:
    out = []
    for el in data.get("elements", []):
        tags = el.get("tags") or {}
        name = tags.get("name", "").strip()
        if not name:
            continue
        if any(tags.get(k) for k in CHAIN_KEYS):
            continue
        if any(tags.get(k) for k in WEB_KEYS):
            continue  # belt and braces; the query already excludes these
        phone, phone_note = normalise_phone(tags, area)
        if not phone:
            continue
        hit = classify(tags)
        if not hit:
            continue
        label, base = hit
        extra, notes = bonus(tags)
        if phone_note:
            # An unverified number is worth less than a verified one, and the
            # sort key is what puts it at the bottom of the call sheet.
            notes.insert(0, phone_note)
            extra -= 4
        lat = el.get("lat") or (el.get("center") or {}).get("lat")
        lon = el.get("lon") or (el.get("center") or {}).get("lon")
        out.append(
            {
                "スコア": base + extra,
                "屋号": name,
                "業種": label,
                "市区町村": area,
                "住所": address_of(tags, area),
                "電話": phone,
                "メール": tags.get("contact:email") or tags.get("email") or "",
                "営業時間": tags.get("opening_hours", ""),
                "メモ": " / ".join(notes),
                "確認用検索": "https://www.google.com/search?q="
                + urllib.parse.quote(f'"{name}" {area}'),
                "地図": f"https://www.openstreetmap.org/{el['type']}/{el['id']}",
                "緯度": lat,
                "経度": lon,
                "接触状況": "",   # 手で埋める列
                "次回アクション": "",
            }
        )
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--area", nargs="*", default=AREAS, help="対象の市区町村名")
    ap.add_argument("--refresh", action="store_true", help="キャッシュを無視して再取得")
    ap.add_argument("--min-score", type=int, default=0, help="この点未満を捨てる")
    args = ap.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)
    all_rows: list[dict] = []
    for i, area in enumerate(args.area):
        cached = (RAW / f"{area}.json").exists() and not args.refresh
        print(f"[{i+1}/{len(args.area)}] {area}", flush=True) if False else print(f"[{i+1}/{len(args.area)}] {area}" + ("（キャッシュ）" if cached else ""))
        data = fetch(area, refresh=args.refresh)
        rows = rows_from(data, area)
        print(f"    候補 {len(rows)} 件", flush=True)
        all_rows.extend(rows)
        if not cached and i < len(args.area) - 1:
            time.sleep(PAUSE_SECONDS)

    all_rows = [r for r in all_rows if r["スコア"] >= args.min_score]
    all_rows.sort(key=lambda r: (-r["スコア"], r["市区町村"], r["業種"]))

    path = OUT / "prospects.csv"
    # utf-8-sig so Excel on Windows does not mangle the Japanese.
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(all_rows[0].keys()) if all_rows else ["屋号"])
        writer.writeheader()
        writer.writerows(all_rows)

    print(f"\n合計 {len(all_rows)} 件 → {path}")
    by_cat: dict[str, int] = {}
    for r in all_rows:
        by_cat[r["業種"]] = by_cat.get(r["業種"], 0) + 1
    for cat, n in sorted(by_cat.items(), key=lambda kv: -kv[1]):
        print(f"  {n:5d}  {cat}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
