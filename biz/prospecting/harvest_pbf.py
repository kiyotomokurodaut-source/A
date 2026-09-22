#!/usr/bin/env python3
"""Harvest the whole of Japan from a local OSM extract, in one pass.

Why not Overpass
----------------
``harvest_osm.py`` works well for a handful of municipalities but does not
scale to the country. Asking the public Overpass servers for 111 cities took
hours and mostly returned 504s: the service is donated capacity, and a
nationwide sweep is not what it is for.

Geofabrik publishes the same data as a file. One download, then everything
runs locally with no rate limit, no timeouts, and complete coverage —
including the towns a hand-written city list would have missed.

    curl -O https://download.geofabrik.de/asia/japan-latest.osm.pbf
    python3 harvest_pbf.py data/pbf/japan-latest.osm.pbf

Where the address comes from
----------------------------
A PBF carries no administrative lookup, so the municipality is taken from the
``addr:*`` tags, which Japanese OSM fills in unusually well. When they are
missing, the area code of the phone number gives the prefecture — 03 is
Tokyo, 06 is Osaka, 011 is Sapporo. A row with neither is still usable (it has
a name and a number) and is marked 不明 rather than dropped.

Output mirrors ``harvest_osm.py`` so the same call sheet and email tooling
reads both: rows with no website go to ``prospects_jp.csv``, rows with one to
``with_site_jp.csv``.
"""

from __future__ import annotations

import argparse
import csv
import sys
import urllib.parse
from collections import Counter
from pathlib import Path

try:
    import osmium
    import osmium.filter
except ImportError:
    sys.exit("osmium が必要です: pip install osmium")

sys.path.insert(0, str(Path(__file__).resolve().parent))
from harvest_osm import (  # noqa: E402  (path set above)
    CHAIN_KEYS, PHONE_KEYS, WEB_KEYS, bonus, classify, format_phone,
)

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "out"

# Area code → prefecture, used only when the addr:* tags are missing. Just the
# major codes: the point is to make a row sortable by region, not to be a
# complete numbering-plan table.
AREA_CODE_PREF = {
    "011": "北海道", "0123": "北海道", "0134": "北海道", "0138": "北海道",
    "0166": "北海道", "017": "青森県", "019": "岩手県", "022": "宮城県",
    "018": "秋田県", "023": "山形県", "024": "福島県",
    "029": "茨城県", "028": "栃木県", "027": "群馬県", "048": "埼玉県",
    "043": "千葉県", "047": "千葉県", "04": "千葉県",
    "03": "東京都", "042": "東京都", "0422": "東京都", "0428": "東京都",
    "045": "神奈川県", "044": "神奈川県", "046": "神奈川県",
    "025": "新潟県", "0258": "新潟県", "076": "富山県・石川県",
    "0776": "福井県", "055": "山梨県・静岡県", "026": "長野県",
    "0263": "長野県", "058": "岐阜県", "054": "静岡県", "053": "静岡県",
    "052": "愛知県", "0565": "愛知県", "059": "三重県",
    "077": "滋賀県", "075": "京都府", "06": "大阪府", "072": "大阪府",
    "078": "兵庫県", "079": "兵庫県", "0742": "奈良県", "073": "和歌山県",
    "0857": "鳥取県", "0852": "島根県", "086": "岡山県", "082": "広島県",
    "084": "広島県", "083": "山口県", "088": "徳島県・高知県",
    "087": "香川県", "089": "愛媛県",
    "093": "福岡県", "092": "福岡県", "0942": "福岡県", "0952": "佐賀県",
    "095": "長崎県", "0956": "長崎県", "096": "熊本県", "097": "大分県",
    "0985": "宮崎県", "099": "鹿児島県", "098": "沖縄県",
}


def prefecture_from_phone(phone: str) -> str:
    digits = phone.replace("-", "")
    for length in (4, 3, 2):
        code = digits[:length]
        if code in AREA_CODE_PREF:
            return AREA_CODE_PREF[code]
    return "不明"


def normalise(raw: str) -> str:
    """Same repairs as harvest_osm, minus the ward-specific 03 completion.

    The nationwide pass has no reliable ward, so guessing an area code would
    invent a number. Short fragments are kept as digits and marked instead.
    """
    import re
    raw = raw.split(";")[0].strip()
    digits = re.sub(r"[^\d+]", "", raw)
    if not digits:
        return ""
    if digits.startswith("+81"):
        digits = "0" + digits[3:]
    elif digits.startswith("0081"):
        digits = "0" + digits[4:]
    elif digits.startswith("+"):
        digits = digits.lstrip("+")
    while digits.startswith("00") and len(digits) > 10:
        digits = digits[1:]
    if len(digits) in (10, 11) and digits.startswith("0"):
        return format_phone(digits)
    return digits


class Collector:
    """Pull the interesting objects out of the file.

    The work is driven by ``osmium.FileProcessor`` with the tag filters applied
    on the C++ side. That matters more than it sounds: Japan has well over a
    hundred million nodes, and a Python callback per node — which is what
    ``SimpleHandler`` does — never finishes. Filtering first means Python only
    ever sees the few hundred thousand objects that carry a phone number.
    """

    def __init__(self) -> None:
        self.rows: list[dict] = []
        self.seen_phone: set[str] = set()
        self.stats = Counter()

    def run(self, path: Path) -> None:
        fp = (osmium.FileProcessor(str(path))
              .with_filter(osmium.filter.EmptyTagFilter())
              .with_filter(osmium.filter.KeyFilter(*PHONE_KEYS)))
        kinds = {"n": "node", "w": "way", "r": "relation"}
        for obj in fp:
            self.stats["with_phone"] += 1
            self._take(obj, kinds.get(obj.type_str(), "node"))
            if self.stats["with_phone"] % 50_000 == 0:
                print(f"  電話番号つき {self.stats['with_phone']:,} 件を通過"
                      f"（採用 {len(self.rows):,}）", flush=True)

    def _take(self, obj, kind: str) -> None:
        tags = {t.k: t.v for t in obj.tags}

        name = (tags.get("name") or "").strip()
        if not name:
            self.stats["no_name"] += 1
            return
        raw_phone = next((tags[k] for k in PHONE_KEYS if tags.get(k)), "")
        if not raw_phone:
            return
        self.stats["named_with_phone"] += 1

        if any(tags.get(k) for k in CHAIN_KEYS):
            self.stats["chain"] += 1
            return
        hit = classify(tags)
        if not hit:
            self.stats["unclassified"] += 1
            return
        phone = normalise(raw_phone)
        if not phone:
            return
        # The same shop is often mapped as both a node and a building way.
        key = phone.replace("-", "")
        if key in self.seen_phone:
            self.stats["duplicate"] += 1
            return
        self.seen_phone.add(key)

        label, base = hit
        extra, notes = bonus(tags)
        if len(key) not in (10, 11):
            notes.insert(0, f"電話番号が{len(key)}桁／要確認")
            extra -= 4

        pref = tags.get("addr:province") or ""
        city = (tags.get("addr:city") or tags.get("addr:suburb") or "")
        if not pref:
            pref = prefecture_from_phone(phone)
        if pref == "不明":
            # Almost always a mobile-only listing with no address tags. Still a
            # real business, but you cannot open a call with "〈地名〉の事業者様"
            # if you do not know the 地名, so it sinks below the rest.
            extra -= 5
            notes.append("所在地不明（携帯番号のみ）")
        rest = "".join(filter(None, [
            tags.get("addr:quarter", ""), tags.get("addr:neighbourhood", ""),
        ]))
        block = "-".join(filter(None, [tags.get("addr:block_number", ""),
                                       tags.get("addr:housenumber", "")]))
        site = next((tags[k] for k in WEB_KEYS if tags.get(k)), "")

        self.rows.append({
            "スコア": base + extra,
            "屋号": name,
            "業種": label,
            "都道府県": pref,
            "市区町村": city or "不明",
            "住所": f"{pref}{city}{rest}{block}",
            "電話": phone,
            "メール": tags.get("contact:email") or tags.get("email") or "",
            "サイト": site,
            "営業時間": tags.get("opening_hours", ""),
            "メモ": " / ".join(notes),
            "確認用検索": "https://www.google.com/search?q="
                          + urllib.parse.quote(f'"{name}" {city or pref}'),
            "地図": f"https://www.openstreetmap.org/{kind}/{obj.id}",
            "接触状況": "",
            "次回アクション": "",
        })


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pbf", type=Path, help="japan-latest.osm.pbf")
    ap.add_argument("--min-score", type=int, default=0)
    args = ap.parse_args()

    if not args.pbf.exists():
        sys.exit(f"{args.pbf} がありません")

    print(f"{args.pbf}（{args.pbf.stat().st_size/1e9:.2f} GB）を読みます…", flush=True)
    h = Collector()
    h.run(args.pbf)

    rows = [r for r in h.rows if r["スコア"] >= args.min_score]
    rows.sort(key=lambda r: (-r["スコア"], r["都道府県"], r["市区町村"], r["業種"]))

    OUT.mkdir(parents=True, exist_ok=True)
    split = {
        "prospects_jp.csv": [r for r in rows if not r["サイト"]],
        "with_site_jp.csv": [r for r in rows if r["サイト"]],
    }
    for name, data in split.items():
        path = OUT / name
        with path.open("w", encoding="utf-8-sig", newline="") as fh:
            w = csv.DictWriter(
                fh, fieldnames=list(data[0].keys()) if data else ["屋号"])
            w.writeheader()
            w.writerows(data)
        print(f"{name}: {len(data):,} 件 → {path}")

    s = h.stats
    print(f"\n電話番号つき {s['with_phone']:,} ／ 名前もあり {s['named_with_phone']:,}"
          f" ／ チェーン除外 {s['chain']:,} ／ 業種不明 {s['unclassified']:,}"
          f" ／ 重複 {s['duplicate']:,}")

    print("\n--- サイトなし：都道府県上位20 ---")
    for pref, n in Counter(r["都道府県"] for r in split["prospects_jp.csv"]).most_common(20):
        print(f"  {n:6,}  {pref}")
    print("\n--- サイトなし：業種上位20 ---")
    for cat, n in Counter(r["業種"] for r in split["prospects_jp.csv"]).most_common(20):
        print(f"  {n:6,}  {cat}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
