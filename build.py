#!/usr/bin/env python3
"""Generate the derived SEO files for kiyotomokuroda.pages.dev and check the
pages that feed them.

The site is hand-written static HTML under ``public/``. Nothing here compiles
or rewrites a page: the pages are the source of truth, and this script only

  * reads the SEO-relevant parts of every page,
  * regenerates the files that must agree with them
    (``sitemap.xml``, ``robots.txt``, ``llms.txt``, ``feed.xml``), and
  * refuses the build when a page and those files cannot agree.

``python3 build.py`` writes the files. ``python3 build.py --check`` writes them
and exits non-zero if any check failed, which is what the Cloudflare Pages build
runs so a regression never reaches the live site.

Standard library only, on purpose: the deploy must not depend on pip.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date, datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from xml.sax.saxutils import escape as xml_escape

SITE = "https://kiyotomokuroda.pages.dev"
ROOT = Path(__file__).resolve().parent
PUBLIC = ROOT / "public"

SITE_NAME = "黒田塾"
TEACHER = "黒田清友"
SITE_TAGLINE = (
    "東大卒・黒田清友による、中学受験・大学受験のオンライン家庭教師と学習管理（受験コーチング）。"
)

# Titles are Japanese, so the byte-ish limits used for English copy do not
# apply. Google truncates the SERP title at roughly 30-32 full-width
# characters; these bounds keep every title inside that and still descriptive.
TITLE_MIN, TITLE_MAX = 12, 40
DESC_MIN, DESC_MAX = 60, 130

# Crawlers that are allowed but must not be handed the print/tool query strings.
AI_CRAWLERS = [
    "GPTBot",
    "OAI-SearchBot",
    "ChatGPT-User",
    "ClaudeBot",
    "Claude-User",
    "Claude-SearchBot",
    "PerplexityBot",
    "Perplexity-User",
    "Google-Extended",
    "Applebot-Extended",
    "Bingbot",
]


# --------------------------------------------------------------------------- #
# Page parsing
# --------------------------------------------------------------------------- #
class PageParser(HTMLParser):
    """Pull out only what the generated files and the checks need."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title = ""
        self.meta: dict[str, str] = {}
        self.canonical: str | None = None
        self.jsonld_raw: list[str] = []
        self.h1s: list[str] = []
        self.ids: set[str] = set()
        self.links: list[str] = []
        self.imgs: list[dict[str, str]] = []
        self.lang: str | None = None
        self._grab: str | None = None
        self._buf: list[str] = []
        # The guide pages carry inline SVG diagrams, and an accessible <svg>
        # has its own <title>. Only the one in <head> is the page title.
        self._in_body = False

    # -- helpers ----------------------------------------------------------- #
    @staticmethod
    def _attrs(attrs: list[tuple[str, str | None]]) -> dict[str, str]:
        return {k.lower(): (v or "") for k, v in attrs}

    def handle_starttag(self, tag: str, attrs) -> None:  # noqa: ANN001
        a = self._attrs(attrs)
        if a.get("id"):
            self.ids.add(a["id"])

        if tag == "html":
            self.lang = a.get("lang")
        elif tag == "body":
            self._in_body = True
        elif tag == "title" and not self._in_body:
            self._grab, self._buf = "title", []
        elif tag == "h1":
            self._grab, self._buf = "h1", []
        elif tag == "meta":
            key = a.get("name") or a.get("property")
            if key:
                # First occurrence wins, which matches how crawlers read them.
                self.meta.setdefault(key.lower(), a.get("content", ""))
        elif tag == "link":
            rels = a.get("rel", "").lower().split()
            if "canonical" in rels:
                self.canonical = a.get("href")
        elif tag == "script":
            if a.get("type", "").lower() == "application/ld+json":
                self._grab, self._buf = "jsonld", []
        elif tag == "a":
            if a.get("href"):
                self.links.append(a["href"])
        elif tag == "img":
            self.imgs.append(a)

    def handle_endtag(self, tag: str) -> None:
        if self._grab is None:
            return
        text = "".join(self._buf)
        if tag == "title" and self._grab == "title":
            self.title = text.strip()
        elif tag == "h1" and self._grab == "h1":
            self.h1s.append(" ".join(text.split()))
        elif tag == "script" and self._grab == "jsonld":
            self.jsonld_raw.append(text)
        else:
            return
        self._grab, self._buf = None, []

    def handle_data(self, data: str) -> None:
        if self._grab is not None:
            self._buf.append(data)


class Page:
    def __init__(self, path: Path) -> None:
        self.path = path
        raw = path.read_text(encoding="utf-8")
        p = PageParser()
        p.feed(raw)

        rel = path.relative_to(PUBLIC).as_posix()
        if rel == "index.html":
            self.url_path = "/"
        elif rel.endswith("/index.html"):
            self.url_path = "/" + rel[: -len("index.html")]
        else:
            self.url_path = "/" + rel

        self.title = p.title
        self.description = p.meta.get("description", "")
        self.robots = p.meta.get("robots", "")
        self.canonical = p.canonical
        self.lang = p.lang
        self.h1s = p.h1s
        self.ids = p.ids
        self.links = p.links
        self.imgs = p.imgs
        self.meta = p.meta

        self.jsonld: list[dict] = []
        self.jsonld_errors: list[str] = []
        for block in p.jsonld_raw:
            try:
                data = json.loads(block)
            except json.JSONDecodeError as exc:
                self.jsonld_errors.append(str(exc))
                continue
            for item in data if isinstance(data, list) else [data]:
                if isinstance(item, dict):
                    self.jsonld.extend(item.get("@graph", [item]))

        self.lastmod = p.meta.get("last-modified", "")

    # -- derived ----------------------------------------------------------- #
    @property
    def noindex(self) -> bool:
        return "noindex" in self.robots.lower()

    @property
    def url(self) -> str:
        return SITE + self.url_path

    def ld_types(self) -> set[str]:
        out: set[str] = set()
        for node in self.jsonld:
            t = node.get("@type")
            if isinstance(t, str):
                out.add(t)
            elif isinstance(t, list):
                out.update(t)
        return out

    @property
    def is_article(self) -> bool:
        return "Article" in self.ld_types()

    def article_node(self) -> dict | None:
        for node in self.jsonld:
            if node.get("@type") == "Article":
                return node
        return None


def load_pages() -> list[Page]:
    return [Page(p) for p in sorted(PUBLIC.rglob("*.html"))]


# --------------------------------------------------------------------------- #
# Generated files
# --------------------------------------------------------------------------- #
def indexable(pages: list[Page]) -> list[Page]:
    return [p for p in pages if not p.noindex]


def write_sitemap(pages: list[Page]) -> str:
    """One <url> per indexable page, newest first.

    ``lastmod`` comes from each page's ``last-modified`` meta so the value is
    reviewable in the diff instead of being whatever the checkout's mtimes
    happen to be.
    """
    entries = sorted(
        indexable(pages), key=lambda p: (p.lastmod, p.url_path), reverse=True
    )
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"'
        ' xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">',
    ]
    for p in entries:
        lines.append("  <url>")
        lines.append(f"    <loc>{xml_escape(p.url)}</loc>")
        if p.lastmod:
            lines.append(f"    <lastmod>{p.lastmod}</lastmod>")
        # Only real content images belong in an image sitemap; the inline SVG
        # logo and the icons do not.
        for img in p.imgs:
            src = img.get("src", "")
            if src.startswith("/") and not src.endswith(".svg"):
                lines.append("    <image:image>")
                lines.append(f"      <image:loc>{xml_escape(SITE + src)}</image:loc>")
                if img.get("alt"):
                    lines.append(
                        f"      <image:title>{xml_escape(img['alt'])}</image:title>"
                    )
                lines.append("    </image:image>")
        lines.append("  </url>")
    lines.append("</urlset>")
    out = "\n".join(lines) + "\n"
    (PUBLIC / "sitemap.xml").write_text(out, encoding="utf-8")
    return out


def write_robots() -> str:
    lines = [
        "# https://kiyotomokuroda.pages.dev/robots.txt",
        "",
        "User-agent: *",
        "Allow: /",
        "",
        "# The guide pages carry in-browser worksheets whose state lives in the",
        "# query string. They render the same text as the clean URL, so keep",
        "# crawlers on the canonical version rather than spending crawl budget",
        "# on parameter permutations.",
        "Disallow: /*?*print=",
        "Disallow: /*?*plan=",
        "Disallow: /*?*sheet=",
        "",
    ]
    for agent in AI_CRAWLERS:
        lines += [f"User-agent: {agent}", "Allow: /", ""]
    lines += [f"Sitemap: {SITE}/sitemap.xml", ""]
    out = "\n".join(lines)
    (PUBLIC / "robots.txt").write_text(out, encoding="utf-8")
    return out


def write_llms(pages: list[Page]) -> str:
    """A plain-text map of the site for retrieval-based search engines.

    Answer engines quote a page far more reliably when they can see, in one
    request, which URL answers which question. Ordinary crawling still works;
    this only removes the guessing.
    """
    by_path = {p.url_path: p for p in indexable(pages)}

    def line(path: str) -> str | None:
        p = by_path.get(path)
        if not p:
            return None
        return f"- [{p.title.split('｜')[0]}]({p.url}): {p.description}"

    groups: list[tuple[str, list[str]]] = [
        (
            "指導内容と料金",
            [
                "/online-tutoring/",
                "/study-coaching/",
                "/junior-high-exam/",
                "/university-exam/",
                "/pricing/",
                "/cases/",
            ],
        ),
        ("講師・相談・よくある質問", ["/about/", "/contact/", "/faq/"]),
        (
            "無料の学習ガイドと記入シート",
            sorted(k for k in by_path if k.startswith("/study-guides/")),
        ),
        ("その他", ["/site-map/"]),
    ]

    out = [
        f"# {SITE_NAME}（{TEACHER}）",
        "",
        f"> {SITE_TAGLINE}",
        "",
        "指導は黒田清友が直接担当します。料金は月額・税込・月4セット分で、"
        "面談のみ24,000円／授業のみ（週1回）30,000円／面談＋授業は週1回54,990円・"
        "週2回79,990円・週3回104,990円の5プランです。",
        "",
    ]
    for heading, paths in groups:
        rows = [r for r in (line(path) for path in paths) if r]
        if not rows:
            continue
        out += [f"## {heading}", ""] + rows + [""]
    out += [
        "## 出典と注意",
        "",
        "- 料金・指導範囲は各ページの本文が一次情報です。振替・解約・支払い条件は"
        "契約前の個別確認事項で、サイト上では確定していません。",
        "- 指導事例は個人が特定されない範囲の紹介で、合格実績として示していない"
        "ものが含まれます。同じ結果を保証するものではありません。",
        "",
    ]
    text = "\n".join(out)
    (PUBLIC / "llms.txt").write_text(text, encoding="utf-8")
    return text


def write_feed(pages: list[Page]) -> str:
    """RSS 2.0 for the guide pages.

    A feed is how aggregators and readers discover a new guide without waiting
    for a crawl, and it is the cheapest discovery surface a static site has.
    """
    articles = [p for p in indexable(pages) if p.is_article]
    articles.sort(key=lambda p: (p.lastmod, p.url_path), reverse=True)

    def rfc822(value: str) -> str:
        try:
            d = datetime.strptime(value, "%Y-%m-%d")
        except ValueError:
            d = datetime.now(tz=timezone.utc)
        return d.replace(tzinfo=timezone.utc).strftime("%a, %d %b %Y %H:%M:%S +0000")

    items = []
    for p in articles:
        node = p.article_node() or {}
        published = node.get("datePublished") or p.lastmod
        items.append(
            "\n".join(
                [
                    "    <item>",
                    f"      <title>{xml_escape(p.title)}</title>",
                    f"      <link>{xml_escape(p.url)}</link>",
                    f"      <guid isPermaLink=\"true\">{xml_escape(p.url)}</guid>",
                    f"      <description>{xml_escape(p.description)}</description>",
                    f"      <pubDate>{rfc822(published)}</pubDate>",
                    "    </item>",
                ]
            )
        )

    newest = articles[0].lastmod if articles else date.today().isoformat()
    out = "\n".join(
        [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">',
            "  <channel>",
            f"    <title>{xml_escape(SITE_NAME)}｜学習ガイド</title>",
            f"    <link>{SITE}/study-guides/</link>",
            "    <description>"
            "中学受験・大学受験の学習ガイドと、無料で使える記入シートの更新情報。"
            "</description>",
            "    <language>ja</language>",
            f"    <lastBuildDate>{rfc822(newest)}</lastBuildDate>",
            f'    <atom:link href="{SITE}/feed.xml" rel="self"'
            ' type="application/rss+xml"/>',
            *items,
            "  </channel>",
            "</rss>",
            "",
        ]
    )
    (PUBLIC / "feed.xml").write_text(out, encoding="utf-8")
    return out


# --------------------------------------------------------------------------- #
# Checks
# --------------------------------------------------------------------------- #
def _target_exists(path: str) -> bool:
    if path in ("/",):
        return (PUBLIC / "index.html").exists()
    p = PUBLIC / path.lstrip("/")
    if p.is_file():
        return True
    return (p / "index.html").exists()


def check(pages: list[Page]) -> list[str]:
    errors: list[str] = []
    ids_by_path = {p.url_path: p.ids for p in pages}

    def err(page: Page, msg: str) -> None:
        errors.append(f"{page.url_path}: {msg}")

    seen_titles: dict[str, str] = {}
    seen_descs: dict[str, str] = {}

    for p in pages:
        # --- head essentials ---
        if p.lang != "ja":
            err(p, f'<html lang> is {p.lang!r}, expected "ja"')
        if not p.title:
            err(p, "no <title>")
        elif not TITLE_MIN <= len(p.title) <= TITLE_MAX:
            err(p, f"title is {len(p.title)} chars, want {TITLE_MIN}-{TITLE_MAX}: {p.title}")
        if not p.description:
            err(p, "no meta description")
        elif not DESC_MIN <= len(p.description) <= DESC_MAX:
            err(
                p,
                f"description is {len(p.description)} chars, "
                f"want {DESC_MIN}-{DESC_MAX}",
            )
        if not p.robots:
            err(p, "no meta robots")

        # --- duplicate head copy: the fastest way to lose a page from the
        #     index is to let two of them claim the same title ---
        if p.title:
            if p.title in seen_titles:
                err(p, f"title duplicates {seen_titles[p.title]}")
            seen_titles[p.title] = p.url_path
        if p.description:
            if p.description in seen_descs:
                err(p, f"description duplicates {seen_descs[p.description]}")
            seen_descs[p.description] = p.url_path

        # --- one h1 ---
        if len(p.h1s) != 1:
            err(p, f"{len(p.h1s)} <h1> elements, expected 1")

        # --- canonical ---
        if p.noindex:
            pass  # a noindex page needs no canonical
        elif p.canonical != p.url:
            err(p, f"canonical is {p.canonical!r}, expected {p.url!r}")

        # --- social cards ---
        for key in (
            "og:title",
            "og:description",
            "og:url",
            "og:image",
            "og:type",
            "twitter:card",
        ):
            if not p.meta.get(key):
                err(p, f"missing {key}")
        if p.meta.get("twitter:card") and p.meta["twitter:card"] != "summary_large_image":
            err(p, f"twitter:card is {p.meta['twitter:card']!r}")
        for key in ("og:image", "twitter:image"):
            ref = p.meta.get(key, "")
            if ref.startswith(SITE) and not _target_exists(ref[len(SITE) :]):
                err(p, f"{key} points at a missing file: {ref}")

        # --- lastmod, which sitemap.xml and feed.xml both read ---
        if not p.noindex:
            if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", p.lastmod or ""):
                err(p, f'meta last-modified is {p.lastmod!r}, expected "YYYY-MM-DD"')
            elif p.lastmod > date.today().isoformat():
                err(p, f"meta last-modified {p.lastmod} is in the future")

        # --- structured data ---
        for msg in p.jsonld_errors:
            err(p, f"JSON-LD does not parse: {msg}")
        if not p.noindex and not p.jsonld:
            err(p, "no JSON-LD")
        if not p.noindex:
            # The publisher and the teacher must be the same entities on every
            # page, or a crawler cannot reconcile them across URLs.
            ids = {n.get("@id") for n in p.jsonld}
            for required in ("#website", "#organization", "#teacher"):
                if f"{SITE}/{required}" not in ids:
                    err(p, f"JSON-LD has no {required} node")
        node = p.article_node()
        if node:
            for field in ("headline", "datePublished", "dateModified", "author"):
                if field not in node:
                    err(p, f"Article JSON-LD has no {field}")
            if node.get("dateModified") and node["dateModified"] != p.lastmod:
                err(
                    p,
                    f"Article dateModified {node['dateModified']} != "
                    f"meta last-modified {p.lastmod}",
                )

        # --- images ---
        for img in p.imgs:
            if not img.get("alt"):
                err(p, f"<img> without alt: {img.get('src')}")
            if not (img.get("width") and img.get("height")):
                err(p, f"<img> without width/height: {img.get('src')}")

        # --- internal links resolve, fragments included ---
        for href in p.links:
            if not href.startswith("/"):
                continue
            path, _, frag = href.partition("#")
            path = path.split("?")[0] or "/"
            if not _target_exists(path):
                err(p, f"dead internal link: {href}")
                continue
            if frag:
                known = ids_by_path.get(path if path.endswith("/") else path)
                if known is not None and frag not in known:
                    err(p, f"link to a missing anchor: {href}")

    # --- every indexable page is reachable from another page ---
    linked: set[str] = set()
    for p in pages:
        for href in p.links:
            if href.startswith("/"):
                target = href.split("#")[0].split("?")[0] or "/"
                linked.add(target)
    for p in indexable(pages):
        if p.url_path != "/" and p.url_path not in linked:
            errors.append(f"{p.url_path}: orphan, no page links to it")

    return errors


# --------------------------------------------------------------------------- #
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--check",
        action="store_true",
        help="exit non-zero when a check fails (used by the Netlify build)",
    )
    args = ap.parse_args()

    pages = load_pages()
    write_sitemap(pages)
    write_robots()
    write_llms(pages)
    write_feed(pages)

    n_index = len(indexable(pages))
    n_articles = sum(1 for p in pages if p.is_article and not p.noindex)
    print(
        f"generated sitemap.xml ({n_index} urls), robots.txt, llms.txt, "
        f"feed.xml ({n_articles} items) from {len(pages)} pages"
    )

    errors = check(pages)
    if errors:
        print(f"\n{len(errors)} SEO check failure(s):", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        if args.check:
            return 1
    else:
        print("SEO checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
