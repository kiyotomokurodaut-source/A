#!/usr/bin/env python3
"""Build a single-file, offline copy of the demo.

``index.html`` loads three.js from jsDelivr. This script downloads those
scripts once and inlines them, so the result opens by double-click with no
internet (a seminar room with bad Wi-Fi, a USB stick, an email attachment).
Web fonts still come from Google Fonts when online and fall back to the
system's Japanese fonts when offline.

    python3 build_offline.py                # -> dist/ai-mind-offline.html
    python3 build_offline.py --out x.html
    python3 build_offline.py --cdn-dir DIR  # use already-downloaded files

Standard library only.
"""

from __future__ import annotations

import argparse
import re
import sys
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
PREFIX = "https://cdn.jsdelivr.net/npm/three@0.128.0/"
TAG = re.compile(r'<script src="(' + re.escape(PREFIX) + r'[^"]+)"></script>')


def fetch(url: str, cdn_dir: Path | None) -> str:
    if cdn_dir:
        return (cdn_dir / url[len(PREFIX):]).read_text(encoding="utf-8")
    with urllib.request.urlopen(url, timeout=60) as r:
        return r.read().decode("utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default=str(HERE / "index.html"))
    ap.add_argument("--out", default=str(HERE / "dist" / "ai-mind-offline.html"))
    ap.add_argument("--cdn-dir", help="three@0.128.0 のファイルを置いたディレクトリ")
    a = ap.parse_args()

    html = Path(a.src).read_text(encoding="utf-8")
    cdn_dir = Path(a.cdn_dir) if a.cdn_dir else None
    urls = TAG.findall(html)
    if not urls:
        print("CDN の script タグが見つかりません", file=sys.stderr)
        return 1

    def inline(m: re.Match) -> str:
        code = fetch(m.group(1), cdn_dir).replace("</script", "<\\/script")
        return f"<script>/* {m.group(1)} */\n{code}\n</script>"

    out = TAG.sub(inline, html)
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(out, encoding="utf-8")
    print(f"{a.out}: {len(urls)} scripts inlined, {len(out.encode()) // 1024} KB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
