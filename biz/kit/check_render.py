#!/usr/bin/env python3
"""Render every page of a generated site in a real browser and fail on layout faults.

``build_site.py --check`` reads the HTML. This one looks at what a phone
actually shows, which is where the money is: most of these sites are found on
a mobile SERP and abandoned in three seconds if the first screen is broken.

It fails on:

* **Horizontal scroll.** One element refusing to shrink pushes the whole page
  sideways and every line of text gets clipped. Invisible on a laptop,
  fatal on a phone.
* **Tap targets under 44x44 CSS px**, the size below which a thumb misses.
* **Text smaller than 12px**, unreadable without pinch-zoom.
* **A console error**, which on a static site means something is genuinely wrong.

Usage:
    python3 check_render.py dist/sample-koumuten
    python3 check_render.py dist/sample-koumuten --shots /tmp/shots
"""

from __future__ import annotations

import argparse
import functools
import http.server
import socketserver
import sys
import threading
from pathlib import Path

try:
    from playwright.sync_api import sync_playwright
except ImportError:  # pragma: no cover - the check is optional tooling
    print("playwright が入っていません: pip install playwright", file=sys.stderr)
    raise SystemExit(2)

CHROMIUM = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"

# 320 is the narrowest phone still in use (iPhone SE 1st gen); if it survives
# that it survives everything.
VIEWPORTS = [("phone-320", 320, 780), ("phone-390", 390, 844),
             ("tablet-768", 768, 1024), ("desktop-1280", 1280, 900)]

# WCAG 2.2 AA (2.5.8 Target Size Minimum) asks for 24x24 CSS px, and exempts a
# link sitting inside a run of text. The primary calls to action are held to
# Apple's 44x44 instead, because those are the ones a customer taps on a phone
# while standing up, and a missed tap there is a lost job.
MIN_TAP = 24
MIN_TAP_PRIMARY = 44
PRIMARY_SELECTOR = ".cta, .tel-btn, .call-bar a, form.enquiry button, .site-nav a"
# Links that flow inside prose are exempt from 2.5.8; so is the skip link,
# which is off-screen until focused.
INLINE_EXEMPT = "p a, li a, dd a, address a, .a a, .skip"
MIN_FONT = 12.0

PROBE = """
() => {
  const doc = document.documentElement;
  const primary = new Set(document.querySelectorAll(%(primary)s));
  const exempt  = new Set(document.querySelectorAll(%(exempt)s));
  const small = [];
  for (const el of document.querySelectorAll('a, button, summary, input, textarea')) {
    if (exempt.has(el)) continue;
    const r = el.getBoundingClientRect();
    if (r.width === 0 && r.height === 0) continue;   // hidden at this width
    const need = primary.has(el) ? %(primaryMin)d : %(min)d;
    if (r.width < need || r.height < need) {
      small.push(el.tagName + '[' + (el.className || '-') + '] "'
                 + (el.textContent || '').trim().slice(0, 14) + '" '
                 + Math.round(r.width) + 'x' + Math.round(r.height)
                 + ' (要 ' + need + ')');
    }
  }
  const tiny = [];
  for (const el of document.querySelectorAll('p, li, a, dd, dt, small, span, summary')) {
    if (!el.textContent.trim()) continue;
    const size = parseFloat(getComputedStyle(el).fontSize);
    if (size < %(font)s) tiny.push(el.tagName + '.' + (el.className || '-') + ' ' + size + 'px');
  }
  return {
    scrollWidth: doc.scrollWidth,
    clientWidth: doc.clientWidth,
    smallTargets: [...new Set(small)],
    tinyText: [...new Set(tiny)],
  };
}
""" % {
    "primary": repr(PRIMARY_SELECTOR),
    "exempt": repr(INLINE_EXEMPT),
    "primaryMin": MIN_TAP_PRIMARY,
    "min": MIN_TAP,
    "font": MIN_FONT,
}


def serve(root: Path) -> tuple[socketserver.TCPServer, int]:
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(root))

    class Quiet(socketserver.TCPServer):
        allow_reuse_address = True

    httpd = Quiet(("127.0.0.1", 0), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd, httpd.server_address[1]


def page_paths(root: Path) -> list[str]:
    paths = []
    for f in sorted(root.rglob("index.html")):
        rel = f.relative_to(root).parent.as_posix()
        paths.append("/" if rel == "." else f"/{rel}/")
    return paths


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("dist", type=Path, help="生成済みサイトのディレクトリ")
    ap.add_argument("--shots", type=Path, help="スクリーンショットの保存先")
    args = ap.parse_args()

    root = args.dist.resolve()
    if not (root / "index.html").exists():
        print(f"{root} に index.html がありません", file=sys.stderr)
        return 2

    paths = page_paths(root)
    httpd, port = serve(root)
    base = f"http://127.0.0.1:{port}"
    problems: list[str] = []

    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(executable_path=CHROMIUM,
                                         args=["--no-sandbox"])
            for label, w, h in VIEWPORTS:
                ctx = browser.new_context(viewport={"width": w, "height": h},
                                          device_scale_factor=1, locale="ja-JP")
                page = ctx.new_page()
                errors: list[str] = []
                page.on("console", lambda m: errors.append(m.text)
                        if m.type == "error" else None)
                page.on("pageerror", lambda e: errors.append(str(e)))

                for path in paths:
                    errors.clear()
                    page.goto(base + path, wait_until="load")
                    r = page.evaluate(PROBE)
                    where = f"{label} {path}"
                    if r["scrollWidth"] > r["clientWidth"] + 1:
                        problems.append(
                            f"{where}: 横スクロールが発生 "
                            f"({r['scrollWidth']}px > {r['clientWidth']}px)")
                    for t in r["smallTargets"]:
                        problems.append(f"{where}: タップ領域が不足 — {t}")
                    for t in r["tinyText"]:
                        problems.append(f"{where}: 文字が{MIN_FONT}px未満 — {t}")
                    for e in errors:
                        problems.append(f"{where}: コンソールエラー — {e}")

                    if args.shots:
                        args.shots.mkdir(parents=True, exist_ok=True)
                        name = (path.strip("/").replace("/", "-") or "home")
                        page.screenshot(path=str(args.shots / f"{label}-{name}.png"),
                                        full_page=True)
                ctx.close()
            browser.close()
    finally:
        httpd.shutdown()

    checked = len(paths) * len(VIEWPORTS)
    if problems:
        print(f"{checked} 通りを検査し、{len(problems)} 件の問題:", file=sys.stderr)
        for p in problems:
            print(f"  - {p}", file=sys.stderr)
        return 1
    print(f"表示検査OK（{len(paths)}ページ × {len(VIEWPORTS)}画面幅 = {checked} 通り）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
