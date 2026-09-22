#!/usr/bin/env python3
"""Turn the raw prospect CSV into a day's call sheet.

Raw output is 3,000 rows, which is a spreadsheet, not a plan. Making calls off
a spreadsheet is slow for two reasons that both come from switching context:
the pitch changes per industry, and the local knowledge changes per ward. A
sheet that groups one ward and one industry together lets the same sentence be
reused twenty times, which is the only way the numbers in
``sales/phone-script.md`` are reachable.

It also enforces the rule that matters legally as well as practically: a row
already marked as contacted, or refused, never comes back.

Usage
-----
    python3 make_callsheet.py --day 1                      # top-scoring 20
    python3 make_callsheet.py --area 墨田区 --n 25
    python3 make_callsheet.py --category 建設 --n 30
    python3 make_callsheet.py --day 1 --format csv         # for a spreadsheet
"""

from __future__ import annotations

import argparse
import csv
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "out"
# Both harvesters write the same columns, so the sheet reads whichever exist.
# Places rows come first in the merge: when the same phone number appears in
# both, Google's record is the one with a verified "no website", where OSM's is
# only an absence of volunteer effort.
SOURCES = ["prospects_places.csv", "prospects.csv"]

# A row carrying any of these in 接触状況 is done with, for now. Re-calling a
# refusal is a re-solicitation, which the 特定商取引法 notes in sales/legal.md
# say not to do, and it is the fastest way to earn a bad name locally.
CLOSED = ("断り", "既存サイトあり", "成約", "着手", "番号違い", "廃業")

PITCH = {
    "建設": "「〈屋号〉 〈地名〉」で検索しても公式ページが出てこない。リフォームは相見積もりが普通なので、新規の分だけ取りこぼしている、という入り方。",
    "士業": "相談者は必ず先生の名前を検索する。出てこないと問い合わせが止まる。信用の担保という角度で。",
    "不動産": "物件は portal 経由でも、会社そのものは検索される。免許番号の表示義務があるので、その受け皿としても要る。",
    "自動車": "車検・板金は「地名＋車検」で探される。GBPだけだと料金が分からず電話されない。",
    "整体": "クーポンサイト経由だけだと手数料で利益が薄くなる。公式が要る、という角度。広告表現の規制が厳しいので注意（legal.md）。",
    "歯科": "医療広告ガイドラインの制約が大きい。慣れるまで後回し推奨。",
    "クリニック": "同上。医療広告ガイドライン。",
    "動物病院": "医療広告の規制は人医より緩い。診療時間と対応動物種が検索される。",
    "美容": "Instagram だけの店が多い。検索からは出てこないので、そこだけ補う話。",
    "クリーニング": "営業時間と料金表が検索される。単価は低いので3万円プラン。",
    "花": "冠婚葬祭の急ぎの需要は必ず検索される。",
    "一般企業": "採用ページの需要が大きい（BUSINESS-MODELS.md A-5）。制作より採用で入るほうが単価が高い。",
    "印刷": "同業なので話が早い。逆に相手が作れる場合もある。",
    "食品": "単価が低い。3万円プラン。",
    "スポーツ": "見学・体験の申し込み導線がない店が多い。",
    "教習": "料金と時間割が検索される。",
    "専門小売": "在庫を見せる必要はない。取扱ブランドと営業時間で十分。",
    "飲食": "食べログ・Instagram で足りていると言われやすい。優先度は低い。",
    "葬祭": "急ぎで検索される。料金の透明性が刺さる。",
}


def pitch_for(category: str) -> str:
    for key, text in PITCH.items():
        if key in category:
            return text
    return ""


def load() -> list[dict]:
    merged: dict[str, dict] = {}
    found = []
    for name in SOURCES:
        path = OUT / name
        if not path.exists():
            continue
        found.append(name)
        with path.open(encoding="utf-8-sig", newline="") as fh:
            for row in csv.DictReader(fh):
                row.setdefault("出典", "Google" if "places" in name else "OSM")
                # First writer wins, and SOURCES puts Places first on purpose.
                merged.setdefault(row["電話"], row)
    if not found:
        sys.exit(f"{OUT} に prospects*.csv がありません。"
                 f"先に harvest_osm.py か harvest_places.py を実行してください")
    print(f"読み込み: {', '.join(found)} → 重複を除いて {len(merged)} 件",
          file=sys.stderr)
    return list(merged.values())


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--day", type=int, help="通し番号。出力ファイル名に使う")
    ap.add_argument("--area", nargs="*", help="市区町村で絞る")
    ap.add_argument("--category", nargs="*", help="業種名の部分一致で絞る")
    ap.add_argument("--n", type=int, default=20, help="件数（既定20）")
    ap.add_argument("--min-score", type=int, default=0)
    ap.add_argument("--format", choices=["md", "csv"], default="md")
    args = ap.parse_args()

    rows = load()
    before = len(rows)
    rows = [r for r in rows
            if not any(tag in (r.get("接触状況") or "") for tag in CLOSED)]
    skipped = before - len(rows)

    if args.area:
        rows = [r for r in rows if r["市区町村"] in args.area]
    if args.category:
        rows = [r for r in rows
                if any(c in r["業種"] for c in args.category)]
    rows = [r for r in rows if int(r["スコア"]) >= args.min_score]

    # Sort so one sitting covers one ward and one trade at a time.
    rows.sort(key=lambda r: (-int(r["スコア"]), r["市区町村"], r["業種"], r["屋号"]))
    picked = rows[: args.n]

    if not picked:
        print("条件に合う行がありません", file=sys.stderr)
        return 1

    stem = f"callsheet-{args.day:02d}" if args.day else "callsheet"
    if args.format == "csv":
        path = OUT / f"{stem}.csv"
        cols = ["スコア", "屋号", "業種", "市区町村", "住所", "電話", "営業時間",
                "メモ", "出典", "確認用検索", "接触状況", "次回アクション"]
        with path.open("w", encoding="utf-8-sig", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
            w.writeheader()
            w.writerows(picked)
        print(f"{len(picked)} 件 → {path}")
        return 0

    groups: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for r in picked:
        groups[(r["市区町村"], r["業種"])].append(r)

    lines = [
        f"# 架電リスト{f' {args.day}日目' if args.day else ''}（{len(picked)}件）",
        "",
        "**かける前に必ず「確認用検索」を開いてください。**",
        "本当にサイトがない相手だけにかけます。出てきたら `接触状況` に "
        "`既存サイトあり` と書いて次へ。",
        "",
        f"※ 接触済み・お断り済みとして除外した行：{skipped}件",
        "",
        "台本は `../sales/phone-script.md`。守るべき線は `../sales/legal.md`。",
        "",
    ]
    for (area, cat), items in sorted(groups.items()):
        lines.append(f"## {area}／{cat}（{len(items)}件）")
        lines.append("")
        hint = pitch_for(cat)
        if hint:
            lines.append(f"> **入り方：** {hint}")
            lines.append("")
        lines.append("| ✓ | 屋号 | 電話 | 住所 | 営業時間 | メモ | 確認 |")
        lines.append("| --- | --- | --- | --- | --- | --- | --- |")
        for r in items:
            hours = r["営業時間"] or "—"
            lines.append(
                f"| ☐ | **{r['屋号']}** | `{r['電話']}` | {r['住所']} | {hours} "
                f"| {r.get('メモ') or '—'} | [検索]({r['確認用検索']}) |"
            )
        lines.append("")

    lines += [
        "---",
        "",
        "## 記録",
        "",
        "終わったら `data/out/prospects.csv` の `接触状況` に書き戻します。",
        "書き戻さないと同じ相手に二度かけます。",
        "",
        "| 記号 | 意味 |",
        "| --- | --- |",
        "| `既存サイトあり` | 検索で出てきた。以後対象外 |",
        "| `不在` | かけ直す。時間帯を `次回アクション` に |",
        "| `送付済/MM-DD` | URLを送る約束が取れた |",
        "| `断り/MM-DD/理由` | **半年はかけない** |",
        "| `成約/MM-DD` | |",
        "",
    ]
    path = OUT / f"{stem}.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    print(f"{len(picked)} 件 → {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
