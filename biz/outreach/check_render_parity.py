#!/usr/bin/env python3
"""Check that the Apps Script renders the same text Python does.

The message body exists in two places at once. Python builds it for
``drafts.csv`` and the preview; the Apps Script builds it again inside Gmail
from the compact per-company data in Drive. The template is emitted from one
constant so they should agree — but "should" is not a guarantee anyone wants
to discover from a customer's inbox.

This runs the real shipped ``renderBody`` out of ``gmail-drafts-loader.gs``
under node, against the real ``drafts-data.json``, and compares every message
with the Python output in ``drafts.csv``.

    python3 make_drafts.py --preview
    python3 check_render_parity.py

Needs node on PATH. Exits non-zero on any difference.
"""

from __future__ import annotations

import csv
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "out"
SIG_RULE = "\n──────────────────────────────\n"

EXTRACT = r"""
const fs = require('fs');
const src = fs.readFileSync(process.argv[2], 'utf8');
// Take the constants and the renderer out of the shipped script and run them
// here, so the comparison exercises the real code rather than a copy of it.
const tpl = src.match(/const BODY_TEMPLATE = [\s\S]*?\n};\n/);
const fn  = src.match(/function renderBody\(d\)[\s\S]*?\n}\n/);
if (!tpl || !fn) { console.error('loader からテンプレートを取り出せません'); process.exit(2); }
eval(tpl[0] + fn[0]);
const data = JSON.parse(fs.readFileSync(process.argv[3], 'utf8'));
process.stdout.write(JSON.stringify(data.map(renderBody)));
"""


def main() -> int:
    loader = OUT / "gmail-drafts-loader.gs"
    data = OUT / "drafts-data.json"
    csv_path = OUT / "drafts.csv"
    for p in (loader, data, csv_path):
        if not p.exists():
            sys.exit(f"{p} がありません。先に make_drafts.py を実行してください")

    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False,
                                     encoding="utf-8") as fh:
        fh.write(EXTRACT)
        script = fh.name
    try:
        proc = subprocess.run(["node", script, str(loader), str(data)],
                              capture_output=True, text=True)
    except FileNotFoundError:
        sys.exit("node が見つかりません。この照合には node が必要です")
    finally:
        Path(script).unlink(missing_ok=True)

    if proc.returncode != 0:
        sys.exit(f"node が失敗しました:\n{proc.stderr}")
    js_bodies = json.loads(proc.stdout)

    with csv_path.open(encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh))
    if len(js_bodies) != len(rows):
        sys.exit(f"件数が違います: JS {len(js_bodies)} / Python {len(rows)}")

    bad = 0
    for i, (j, r) in enumerate(zip(js_bodies, rows)):
        # drafts.csv carries body + signature; the script adds the signature
        # separately, so compare what comes before it.
        py = r["body"].split(SIG_RULE)[0]
        if j.rstrip("\n") != py.rstrip("\n"):
            bad += 1
            if bad <= 2:
                print(f"--- 不一致 {i+1} 件目（{r['屋号']}） ---", file=sys.stderr)
                print(f"  JS : {j[-140:]!r}", file=sys.stderr)
                print(f"  PY : {py[-140:]!r}", file=sys.stderr)

    if bad:
        print(f"\n{len(rows)} 件中 {bad} 件が不一致", file=sys.stderr)
        return 1
    print(f"照合OK（{len(rows)} 件すべて一致）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
