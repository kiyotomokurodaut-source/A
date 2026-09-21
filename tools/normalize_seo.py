#!/usr/bin/env python3
"""Bring every page's head, structured data and site-wide nav to one standard.

Run it after adding or editing a page:

    python3 tools/normalize_seo.py

It edits the HTML in place with targeted string and JSON edits rather than
re-serialising the document, so the diff shows only what changed. Running it
twice changes nothing the second time.

What it enforces, and why each one is here:

* **Share cards.** Every page pointed at the 900x1200 portrait with
  ``twitter:card=summary``, so a shared link showed a cropped face and no
  words. Each page now points at its own 1200x630 card from
  ``tools/make_og_cards.py``, with the dimensions and type declared.
* **``last-modified``.** ``build.py`` reads it for ``sitemap.xml`` and
  ``feed.xml``. Keeping it in the page means the value is reviewable in the
  diff instead of coming from checkout mtimes.
* **Article dates and author.** Two guides had no ``dateModified``, and every
  guide credited the organisation. The guides are written by a named teacher
  with a stated degree, so the ``Person`` is the author and the school is the
  publisher.
* **FAQ markup.** ``/pricing/`` and ``/contact/`` already carried real Q&A in
  ``<details>`` with no machine-readable form. (Google restricted FAQ rich
  results to health and government sites in 2023, so this is for parsers and
  answer engines, not for stars in the SERP.)
* **Nav.** ``/faq/`` has to be reachable from every page, or it is an orphan.
* **``areaServed`` / ``availableLanguage``.** The organisation had no hint that
  it teaches in Japanese, online, to students in Japan.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PUBLIC = ROOT / "public"
SITE = "https://kiyotomokuroda.netlify.app"

# Date each page's content was last substantively touched. A page absent from
# this map keeps whatever `last-modified` it already declares.
LASTMOD = {
    "/": "2026-09-21",
    "/about/": "2026-09-16",
    "/cases/": "2026-09-21",
    "/contact/": "2026-09-21",
    "/faq/": "2026-09-21",
    "/junior-high-exam/": "2026-09-16",
    "/online-tutoring/": "2026-09-16",
    "/pricing/": "2026-09-21",
    "/site-map/": "2026-09-21",
    "/study-coaching/": "2026-09-16",
    "/study-guides/": "2026-09-21",
    "/study-guides/choosing-a-juku/": "2026-09-15",
    "/study-guides/common-test-english-time/": "2026-09-21",
    "/study-guides/english-reading-diagnosis/": "2026-09-16",
    "/study-guides/homework-priorities/": "2026-09-15",
    "/study-guides/kakomon-start-timing/": "2026-09-21",
    "/study-guides/math-self-solve/": "2026-09-15",
    "/study-guides/mock-exam-review/": "2026-09-15",
    "/study-guides/online-tutoring-vs-agency/": "2026-09-21",
    "/study-guides/todai-math-2026-3/": "2026-09-16",
    "/study-guides/weekly-study-plan/": "2026-09-16",
    "/university-exam/": "2026-09-16",
}

FEED_LINK = (
    '<link href="/feed.xml" rel="alternate" title="黒田塾｜学習ガイド" '
    'type="application/rss+xml"/>'
)
THEME = '<meta content="#fbfaf7" name="theme-color"/>'

# --- site-wide nav: /faq/ must be reachable from every page ---------------- #
NAV_EDITS = [
    # Mobile menu, between 講師紹介 and 料金.
    (
        '<a href="/about/">講師紹介</a><a href="/pricing/">料金</a>',
        '<a href="/about/">講師紹介</a><a href="/pricing/">料金</a>'
        '<a href="/faq/">よくある質問</a>',
    ),
    # Footer, after 料金.
    (
        '<a href="/pricing/">料金</a><a href="/contact/">無料相談</a>',
        '<a href="/pricing/">料金</a><a href="/faq/">よくある質問</a>'
        '<a href="/contact/">無料相談</a>',
    ),
]


def page_paths() -> list[tuple[Path, str]]:
    out = []
    for p in sorted(PUBLIC.rglob("*.html")):
        rel = p.relative_to(PUBLIC).as_posix()
        if rel == "index.html":
            url = "/"
        elif rel.endswith("/index.html"):
            url = "/" + rel[: -len("index.html")]
        else:
            url = "/" + rel
        out.append((p, url))
    return out


def card_for(url_path: str) -> str:
    """The share card for a page: the photo card for the home page and the
    404, a per-page card everywhere else."""
    if url_path in ("/", "/404.html"):
        return "/og-card.png"
    slug = url_path.strip("/").replace("/", "-")
    candidate = PUBLIC / "assets" / "og" / f"{slug}.png"
    return f"/assets/og/{slug}.png" if candidate.exists() else "/og-card.png"


def set_meta(html: str, key: str, value: str, *, prop: bool) -> str:
    """Replace a meta's content, or insert the tag before the JSON-LD block."""
    attr = "property" if prop else "name"
    pat = re.compile(
        rf'<meta content="[^"]*" {attr}="{re.escape(key)}"/>'
        rf'|<meta {attr}="{re.escape(key)}" content="[^"]*"/?>'
    )
    tag = f'<meta content="{value}" {attr}="{key}"/>'
    if pat.search(html):
        return pat.sub(tag, html, count=1)
    anchor = '<script type="application/ld+json">'
    if anchor in html:
        return html.replace(anchor, tag + anchor, 1)
    return html.replace("</head>", tag + "</head>", 1)


def get_meta(html: str, key: str) -> str | None:
    m = re.search(
        rf'<meta content="([^"]*)" (?:name|property)="{re.escape(key)}"/>', html
    )
    return m.group(1) if m else None


def edit_jsonld(html: str, fn) -> str:
    """Apply ``fn`` to each JSON-LD graph in the page and write it back."""

    def repl(m: re.Match) -> str:
        try:
            data = json.loads(m.group(1))
        except json.JSONDecodeError:
            return m.group(0)
        fn(data)
        body = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
        return f'<script type="application/ld+json">{body}</script>'

    return re.sub(
        r'<script type="application/ld\+json">(.*?)</script>',
        repl,
        html,
        flags=re.S,
    )


def faq_pairs(html: str, section_id: str) -> list[tuple[str, str]]:
    """Read the Q&A out of one <section>'s <details> blocks."""
    m = re.search(
        rf'<section id="{re.escape(section_id)}">(.*?)</section>', html, re.S
    )
    if not m:
        return []
    out = []
    for d in re.findall(r"<details[^>]*>(.*?)</details>", m.group(1), re.S):
        q = re.search(r"<summary>(.*?)</summary>", d, re.S)
        if not q:
            continue
        answer = d[q.end() :]
        text = re.sub(r"<[^>]+>", "", answer)
        text = re.sub(r"\s+", " ", text).strip()
        if text:
            out.append((re.sub(r"<[^>]+>", "", q.group(1)).strip(), text))
    return out


# The sections whose <details> are genuine FAQ. Everything else on the site
# that uses <details> holds worked answers to exercises, and marking those up
# as an FAQ would misdescribe the page.
FAQ_SECTIONS = {
    "/pricing/": "questions",
    "/contact/": "contact-faq",
}


def find_faq_section(html: str) -> str | None:
    """Locate the FAQ section id by its heading, so a renamed id still works."""
    for m in re.finditer(r'<section id="([^"]+)"><h2>([^<]*)</h2>', html):
        if "よく確認" in m.group(2) or "よくある確認" in m.group(2):
            return m.group(1)
    return None


def normalize(path: Path, url_path: str) -> bool:
    original = html = path.read_text(encoding="utf-8")
    url = SITE + url_path
    card = SITE + card_for(url_path)
    title = (re.search(r"<title>(.*?)</title>", html, re.S) or [None, ""])[1]

    # --- share card ------------------------------------------------------- #
    html = set_meta(html, "og:image", card, prop=True)
    html = set_meta(html, "og:image:type", "image/png", prop=True)
    html = set_meta(html, "og:image:width", "1200", prop=True)
    html = set_meta(html, "og:image:height", "630", prop=True)
    html = set_meta(html, "og:image:alt", title, prop=True)
    html = set_meta(html, "twitter:card", "summary_large_image", prop=False)
    html = set_meta(html, "twitter:image", card, prop=False)
    html = set_meta(html, "twitter:image:alt", title, prop=False)

    # --- freshness -------------------------------------------------------- #
    lastmod = LASTMOD.get(url_path) or get_meta(html, "last-modified")
    if lastmod:
        html = set_meta(html, "last-modified", lastmod, prop=False)

    # --- head extras ------------------------------------------------------ #
    if "theme-color" not in html:
        html = html.replace(
            '<link href="/favicon.png"', THEME + '<link href="/favicon.png"', 1
        )
    if 'rel="alternate"' not in html:
        html = html.replace(
            '<link href="/apple-touch-icon.png"',
            FEED_LINK + '<link href="/apple-touch-icon.png"',
            1,
        )

    # --- structured data -------------------------------------------------- #
    pairs: list[tuple[str, str]] = []
    if url_path in FAQ_SECTIONS:
        # Fall back to locating the section by its heading, so renaming the id
        # loses the markup loudly (a check failure) rather than silently.
        faq_id = FAQ_SECTIONS[url_path]
        pairs = faq_pairs(html, faq_id) or faq_pairs(
            html, find_faq_section(html) or ""
        )
        if not pairs:
            print(f"  WARNING {url_path}: no FAQ <details> found", file=sys.stderr)

    def fix(data) -> None:
        graph = data.get("@graph") if isinstance(data, dict) else None
        if graph is None:
            return

        # Every page should name the same publisher and teacher entities, so a
        # crawler reconciling them across URLs sees one organisation and one
        # person rather than a per-page guess. /cases/ was missing the
        # organisation.
        present = {n.get("@id") for n in graph}
        if f"{SITE}/#organization" not in present:
            graph.append(
                {
                    "@type": "EducationalOrganization",
                    "@id": f"{SITE}/#organization",
                    "name": "黒田塾",
                    "url": f"{SITE}/",
                    "founder": {"@id": f"{SITE}/#teacher"},
                    "logo": f"{SITE}/favicon.png",
                    "publishingPrinciples": f"{SITE}/about/#editorial-policy",
                }
            )

        for node in graph:
            t = node.get("@type")
            if t == "Article":
                node["author"] = {"@id": f"{SITE}/#teacher"}
                node["publisher"] = {"@id": f"{SITE}/#organization"}
                node.setdefault("datePublished", lastmod)
                if lastmod:
                    node["dateModified"] = lastmod
            elif t == "EducationalOrganization":
                node["areaServed"] = {"@type": "Country", "name": "日本"}
                node["availableLanguage"] = "ja"
                node["knowsLanguage"] = "ja"
            elif t == "Service":
                node.setdefault("areaServed", {"@type": "Country", "name": "日本"})
                node.setdefault("availableLanguage", "ja")
            elif t in ("WebPage", "ProfilePage", "CollectionPage", "ContactPage"):
                if lastmod:
                    node["dateModified"] = lastmod

        # Attach the FAQ, replacing any earlier run's copy.
        if pairs:
            fid = f"{url}#faq"
            graph[:] = [n for n in graph if n.get("@id") != fid]
            faq = {
                "@type": "FAQPage",
                "@id": fid,
                "mainEntity": [
                    {
                        "@type": "Question",
                        "name": q,
                        "acceptedAnswer": {"@type": "Answer", "text": a},
                    }
                    for q, a in pairs
                ],
            }
            # After the WebPage node, so the primary entity stays first.
            graph.insert(1, faq)
            for node in graph:
                if node.get("@id") == f"{url}#webpage":
                    node["significantLink"] = fid

    html = edit_jsonld(html, fix)

    # --- site-wide nav ---------------------------------------------------- #
    for old, new in NAV_EDITS:
        if new not in html:
            html = html.replace(old, new)

    if html != original:
        path.write_text(html, encoding="utf-8")
        return True
    return False


def main() -> int:
    changed = 0
    for path, url_path in page_paths():
        if normalize(path, url_path):
            changed += 1
            print(f"  updated {url_path}")
    print(f"{changed} page(s) changed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
