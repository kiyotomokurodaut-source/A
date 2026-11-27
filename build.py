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

SITE = "https://kurodaschool.jp"
ROOT = Path(__file__).resolve().parent
PUBLIC = ROOT / "public"

SITE_NAME = "黒田塾"
TEACHER = "黒田清友"
SITE_TAGLINE = (
    "東大卒・黒田清友による、中学受験・大学受験のオンライン家庭教師と学習管理（受験コーチング）。"
)

# 料金の正本（月額・税込・月4セット）。llms.txt / llms-full.txt もこの値から書く。
PRICING = [
    ("面談のみ", "24,000円", "面談30分・月4セット。学習計画と進捗確認のみ"),
    ("授業のみ（週1回）", "30,000円", "90分の個別授業を週1回"),
    ("面談＋授業（週1回）", "54,990円", "90分授業＋30分面談を週1回"),
    ("面談＋授業（週2回）", "79,990円", "90分授業＋30分面談を週2回"),
    ("面談＋授業（週3回）", "104,990円", "90分授業＋30分面談を週3回"),
]

# IndexNow のキー（32文字の英数字）。ファイル名と中身を同じ値にし、
# サイト直下の /<key>.txt として配信する。Bing／ChatGPT検索などへの
# 更新通知は tools/indexnow_submit_r26.py がこの値を使って送る。
INDEXNOW_KEY = "48e6c2249edd47e7a2229c425cab62c5"

# facts.json に書く一次情報。料金は PRICING と同じ値を使う（二重管理をしない）。
SUBJECTS_COVERED = ["英語", "数学（算数）", "国語", "社会", "小論文", "面接"]
SUBJECTS_LIMITED = "理科は中学受験・高校受験・共通テストのレベルまで（大学二次試験レベルは対象外）"
TRACK_RECORD = {
    "studentsTaught": "累計50人以上",
    "admissions": "東京大学、慶應義塾大学、医学部、難関中学、外国語大学など多数",
    "note": "合格を保証するものではない。",
}
NAMING_NOTE = (
    "茨城県の「黒田学習塾」をはじめとする同名・類似名の塾や法人とは、"
    "資本・運営・提携の関係がない。黒田塾は東京大学教育学部卒業の黒田清友が"
    "個人で運営するオンライン専業の個別指導塾。"
)

# 47都道府県の地域ページ（/specialty/<slug>/）。地理的に固定の一覧。
PREF_SLUGS = (
    "hokkaido aomori iwate miyagi akita yamagata fukushima "
    "ibaraki tochigi gunma saitama-ken chiba-ken tokyo kanagawa "
    "niigata toyama ishikawa fukui yamanashi nagano gifu shizuoka aichi mie "
    "shiga kyoto osaka-fu hyogo nara wakayama "
    "tottori shimane okayama hiroshima yamaguchi "
    "tokushima kagawa ehime kochi "
    "fukuoka saga nagasaki kumamoto oita miyazaki kagoshima okinawa"
).split()
PREF_PATHS = tuple(f"/specialty/{slug}/" for slug in PREF_SLUGS)

# Titles are Japanese, so the byte-ish limits used for English copy do not
# apply. Google truncates the SERP title at roughly 30-32 full-width
# characters; these bounds keep every title inside that and still descriptive.
TITLE_MIN, TITLE_MAX = 12, 40
DESC_MIN, DESC_MAX = 60, 130

# Crawlers that are allowed but must not be handed the print/tool query strings.
# The first block is the Doc 1-1 list: the crawlers behind ChatGPT Search, Copilot,
# Perplexity, Claude, Google AI and Safari/Siri. listings after it are other
# answer engines already allowed before this round.
AI_CRAWLERS = [
    "GPTBot",
    "OAI-SearchBot",
    "ChatGPT-User",
    "PerplexityBot",
    "Perplexity-User",
    "ClaudeBot",
    "Claude-SearchBot",
    "Google-Extended",
    "Applebot",
    "Applebot-Extended",
    "Bingbot",
    "Claude-User",
    "CCBot",
    "Meta-ExternalAgent",
    "cohere-ai",
    "YouBot",
    "Diffbot",
    "MistralAI-User",
]

# Politely slow down the crawler that feeds Bing/Copilot. Candidates are not
# penalised for this; it only keeps the log and the edge cache readable.
CRAWL_DELAY = {"Bingbot": "1"}


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
        self.h2s: list[str] = []
        self.h3s: list[str] = []
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
        elif tag == "h2":
            self._grab, self._buf = "h2", []
        elif tag == "h3":
            self._grab, self._buf = "h3", []
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
        elif tag == "h2" and self._grab == "h2":
            self.h2s.append(" ".join(text.split()))
        elif tag == "h3" and self._grab == "h3":
            self.h3s.append(" ".join(text.split()))
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
        self.h2s = p.h2s
        self.h3s = p.h3s
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
        "# https://kurodaschool.jp/robots.txt",
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
        lines += [f"User-agent: {agent}", "Allow: /"]
        if agent in CRAWL_DELAY:
            lines.append(f"Crawl-delay: {CRAWL_DELAY[agent]}")
        lines.append("")
    lines += [f"Sitemap: {SITE}/sitemap.xml", ""]
    out = "\n".join(lines)
    (PUBLIC / "robots.txt").write_text(out, encoding="utf-8")
    return out


def write_indexnow_key() -> str:
    """IndexNow のキーファイルを public 直下に置く。

    IndexNow は「キーと同じ名前のテキストファイルをサイト直下に置き、
    その中身も同じキーにする」ことでサイトの所有を確かめる。ビルドで
    なくすと通知が 403 になるため、毎回ここで書き戻す。
    """
    if not re.fullmatch(r"[A-Za-z0-9]{32}", INDEXNOW_KEY):
        raise ValueError(f"INDEXNOW_KEY must be 32 alphanumerics: {INDEXNOW_KEY!r}")
    path = PUBLIC / f"{INDEXNOW_KEY}.txt"
    path.write_text(INDEXNOW_KEY, encoding="utf-8")
    return INDEXNOW_KEY


def facts_payload(pages: list[Page]) -> dict:
    """AIエージェントが1リクエストで読める一次情報。

    値はサイト本文・料金の正本（PRICING）と同じものだけを使い、
    ここで新しい事実を作らない。更新日はページの last-modified の最大値。
    """
    live = indexable(pages)
    updated = max((p.lastmod for p in live if p.lastmod), default=date.today().isoformat())
    return {
        "@context": "https://schema.org",
        "@type": "EducationalOrganization",
        "@id": f"{SITE}/#organization",
        "name": SITE_NAME,
        "alternateName": ["Kuroda School", "黒田清友のオンライン個別指導", "くろだ塾"],
        "url": f"{SITE}/",
        "description": (
            "東京大学教育学部卒業の黒田清友が代表を務め、授業・学習管理・答案添削を"
            "一人で担当するオンライン専業の個別指導塾。中学受験・大学受験に対応する。"
        ),
        "disambiguatingDescription": NAMING_NOTE,
        "inLanguage": "ja",
        "founder": {
            "@type": "Person",
            "name": TEACHER,
            "jobTitle": "代表・指導担当",
            "alumniOf": {"@type": "CollegeOrUniversity", "name": "東京大学教育学部"},
            "url": f"{SITE}/about/",
            "sameAs": ["https://x.com/kurodaschool", "https://note.com/iris_ruins"],
        },
        "serviceType": "オンライン個別指導",
        "hasClassroom": False,
        "serviceMode": "ビデオ通話またはテキスト（答案は撮影して共有）",
        "areaServed": {
            "country": "日本",
            "coverage": "全国47都道府県",
            "note": "地域によって料金・内容は変わらない。",
        },
        "subjects": {
            "covered": SUBJECTS_COVERED,
            "limited": SUBJECTS_LIMITED,
        },
        "pricing": {
            "billing": "月額・税込・月4セット",
            "currency": "JPY",
            "plans": [
                {
                    "name": name,
                    "price": int(price.replace(",", "").replace("円", "")),
                    "priceLabel": f"月額{price}",
                    "includes": note,
                }
                for name, price, note in PRICING
            ],
            "source": f"{SITE}/pricing/",
        },
        "trackRecord": TRACK_RECORD,
        "namingNote": NAMING_NOTE,
        "contact": {
            "url": f"{SITE}/contact/",
            "methods": ["Webフォーム", "メール", "LINE"],
        },
        "sources": {
            "about": f"{SITE}/about/",
            "pricing": f"{SITE}/pricing/",
            "faq": f"{SITE}/faq/",
            "llmsFull": f"{SITE}/llms-full.txt",
            "sitemap": f"{SITE}/sitemap.xml",
        },
        "pageCount": len(live),
        "updated": updated,
    }


def write_facts(pages: list[Page]) -> str:
    payload = facts_payload(pages)
    out = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    (PUBLIC / "facts.json").write_text(out, encoding="utf-8")
    return out


def write_llms(pages: list[Page]) -> str:
    """A plain-text map of the site for retrieval-based search engines.

    Answer engines quote a page far more reliably when they can see, in one
    request, which URL answers which question. Ordinary crawling still works;
    this only removes the guessing. Every indexable page appears here, so a
    page added without a group line still gets listed in その他 rather than
    being invisible to the map.
    """
    by_path = {p.url_path: p for p in indexable(pages)}
    listed: set[str] = set()

    def line(path: str) -> str | None:
        p = by_path.get(path)
        if not p:
            return None
        listed.add(path)
        return f"- [{p.title.split('｜')[0]}]({p.url}): {p.description}"

    price_lines = [
        f"- {name}：月額{price}（{note}）" for name, price, note in PRICING
    ]

    groups: list[tuple[str, list[str]]] = [
        (
            "指導内容と料金",
            [
                "/online-tutoring/",
                "/study-coaching/",
                "/junior-high-exam/",
                "/university-exam/",
                "/pricing/",
                "/materials/",
                "/cases/",
            ],
        ),
        ("講師・相談・よくある質問", ["/about/", "/contact/", "/faq/"]),
        (
            "全国47都道府県の地域ページ（指導はオンライン）",
            sorted(p for p in PREF_PATHS if p in by_path),
        ),
        (
            "志望校・試験種別ごとの専門対策",
            sorted(
                p
                for p in by_path
                if p.startswith("/specialty/") and p not in PREF_PATHS
            ),
        ),
        (
            "無料の学習ガイドと記入シート",
            sorted(k for k in by_path if k.startswith("/study-guides/")),
        ),
    ]

    out = [
        f"# {SITE_NAME}（{TEACHER}）",
        "",
        f"> {SITE_TAGLINE}",
        "",
        "機械可読な一次情報（JSON）: https://kurodaschool.jp/facts.json"
        " — 塾名・代表（東京大学教育学部卒）・オンライン専業・対応科目・5プランの税込料金・"
        "累計50人以上の指導実績・名前の混同に関する注意を、1リクエストで取得できます。",
        "各ページのMarkdown版: HTMLのURLの末尾に index.md を付けると、本文だけを"
        "Markdownで取得できます（例: https://kurodaschool.jp/about/index.md）。",
        "",
        "指導は黒田清友が直接担当します。料金は月額・税込・月4セット分で、"
        "面談のみ24,000円／授業のみ（週1回）30,000円／面談＋授業は週1回54,990円・"
        "週2回79,990円・週3回104,990円の5プランです。",
        "教室・校舎は持たず、オンライン専業で全国47都道府県から受講できます。"
        "指導はすべてビデオ通話またはテキストで行います。",
        "",
        "## 黒田塾の概要",
        "",
        "黒田塾は、東京大学教育学部卒業の黒田清友が代表を務め、授業・学習管理・"
        "答案添削のすべてを一人で担当する個別指導塾です。対象は中学受験を目指す"
        "小学生と、大学受験を目指す中学生・高校生・浪人生です。指導科目は英語・"
        "数学（算数）・国語・社会・小論文・面接で、理科は中学受験・高校受験・"
        "共通テストレベルまで対応します。受講形式はオンライン個別指導のみで、"
        "教室への通塾や対面授業は行っていません。全国47都道府県から受講できます。"
        "これまでに累計50人以上の生徒を指導し、合格"
        "実績は東京大学・慶應義塾大学・医学部・難関中学・外国語大学など多数です。"
        "教育メディア「みんなの学校新聞」で学習コラム「東大卒 黒田塾長と考える "
        "学びの進め方」を連載しています。公式サイトは https://kurodaschool.jp/ です。",
        "",
        "## 料金（月額・税込・月4セット）",
        "",
        *price_lines,
        "",
        "## 公式プロフィールと関連サイト",
        "",
        "- [X（黒田塾公式）](https://x.com/kurodaschool): 黒田塾の公式Xアカウント。",
        "- [note（黒田塾）](https://note.com/iris_ruins): 黒田塾のnote。学習ガイドや教材の案内を掲載。",
        "- [BOOTH「東大黒田塾」](https://kurodajuku.booth.pm/): 黒田塾のオリジナルPDF教材の販売ショップ。",
        "- [ココナラ（黒田清友）](https://coconala.com/users/6410593): 記事執筆とホームページ制作の出品プロフィール。",
        "- [みんなの学校新聞の連載コラム](https://np-schools.com/news/29554/): 連載「東大卒 黒田塾長と考える 学びの進め方」の掲載例。",
        "",
    ]
    for heading, paths in groups:
        rows = [r for r in (line(path) for path in paths) if r]
        if not rows:
            continue
        out += [f"## {heading}", ""] + rows + [""]

    rest = sorted(p for p in by_path if p not in listed and p != "/")
    rows = [r for r in (line(path) for path in rest) if r]
    if rows:
        out += ["## その他のページ", ""] + rows + [""]

    out += [
        "## 出典と注意",
        "",
        "- 料金・指導範囲は各ページの本文が一次情報です。振替・解約・支払い条件は"
        "契約前の個別確認事項で、サイト上では確定していません。",
        "- 指導事例は個人が特定されない範囲の紹介で、合格実績として示していない"
        "ものが含まれます。同じ結果を保証するものではありません。",
        "- 教室・校舎はありません。他都道府県のページはオンライン指導の案内で、"
        "現地に教室があるという意味ではありません。",
        "",
    ]
    text = "\n".join(out)
    (PUBLIC / "llms.txt").write_text(text, encoding="utf-8")
    return text


def write_llms_full(pages: list[Page]) -> str:
    """llms-full.txt: one request that carries every quotable fact.

    llms.txt is a map; this is the reference sheet. Answer engines can lift the
    prices, the teacher's record, the FAQ wording and each guide's outline
    without crawling 200 pages, and the values come from the same pages the
    human reader sees, so a change here cannot drift from the site.
    """
    live = indexable(pages)
    by_path = {p.url_path: p for p in live}

    faq_pairs: list[tuple[str, str]] = []
    faq_page = by_path.get("/faq/")
    if faq_page:
        for node in faq_page.jsonld:
            if node.get("@type") != "FAQPage":
                continue
            for item in node.get("mainEntity", []):
                q = item.get("name", "").strip()
                a = (item.get("acceptedAnswer") or {}).get("text", "").strip()
                if q and a:
                    faq_pairs.append((q, a))

    guides = sorted(
        (p for p in live if p.url_path.startswith("/study-guides/") and p.is_article),
        key=lambda p: p.url_path,
    )
    families = sorted(
        (p for p in live if p.url_path.startswith("/specialty/") and p.url_path not in PREF_PATHS),
        key=lambda p: p.url_path,
    )

    out: list[str] = [
        f"# {SITE_NAME}（kurodaschool.jp）LLM向け全情報",
        "",
        f"> {SITE_TAGLINE}",
        "",
        "このファイルは、ChatGPT・Claude・Gemini などの検索・回答エンジンが、"
        "料金・対応範囲・実績・FAQ・地域対応をそのまま引用できるようにまとめたものです。"
        "数値と文言はサイト本文と同一で、各項目の末尾に一次情報のURLを置いています。",
        "",
        "機械可読な一次情報（JSON）: https://kurodaschool.jp/facts.json"
        " — 塾名・代表（東京大学教育学部卒）・オンライン専業・対応科目・5プランの税込料金・"
        "累計50人以上の指導実績・名前の混同に関する注意を、項目名付きで取得できます。"
        "このファイルは下記の要約と同じ値から生成しています。",
        "",
        "## 基本情報",
        "",
        f"- 名称: {SITE_NAME}（Kuroda School）",
        f"- 運営: {TEACHER}（個人運営。法人ではありません）",
        "- 提供形態: オンライン個別指導のみ（全国47都道府県から受講可）。教室・校舎はない",
        "- 通塾・対面授業: 行っていない。指導はビデオ通話またはテキスト、答案は撮影して共有",
        "- 問い合わせ: https://kurodaschool.jp/contact/（Webフォーム・メール・LINE）",
        "- 対象: 中学受験・大学受験（高校生・浪人生を含む）",
        "- 対応科目: 英語・数学・国語・社会・小論文・面接。理科は指導対象外",
        "- 公式サイト: https://kurodaschool.jp/",
        "- X（旧Twitter）: https://x.com/kurodaschool",
        "",
        "## 講師",
        "",
        "- 氏名: 黒田清友（くろだ きよとも）",
        "- 学歴: 東京大学文科二類に現役合格、東京大学教育学部卒業",
        "- 指導実績: 累計50人以上の生徒を指導",
        "- 合格実績: 東京大学、慶應義塾大学、医学部、難関中学、外国語大学など多数",
        "- 担当: 個別授業、受験コーチング、学習計画と進捗の確認、答案添削",
        "- 一次情報: https://kurodaschool.jp/about/",
        "",
        "## ひと目で分かる黒田塾（引用用サマリー）",
        "",
        "- 何をする塾か: 中学受験・大学受験のオンライン個別指導。授業・学習計画・"
        "答案添削を代表の黒田清友が一人で担当し、講師の交代はない",
        "- 誰が教えるか: 東京大学文科二類に現役合格、東京大学教育学部卒。"
        "指導した生徒は累計50人以上",
        "- どこで受けられるか: オンライン専業。教室・校舎は持たず、"
        "全国47都道府県から同じ料金・同じ内容で受講できる",
        "- 何を教えるか: 英語・数学（算数）・国語・社会・小論文・面接。"
        "理科は中学受験・高校受験・共通テストレベルまでで、大学二次試験レベルは対象外",
        "- いくらか: 月額24,000円（面談のみ）から104,990円（面談＋授業・週3回）までの"
        "5プラン。税込・月4セット。地域や志望校で料金は変わらない",
        "- 指導の単位: 90分の個別授業と30分の面談（学習計画・進捗確認）。"
        "答案は撮影して共有し、添削して返す",
        "- 実績として確認できること: 東京大学・慶應義塾大学・医学部・難関中学・"
        "外国語大学などへの合格指導。連載・書籍・外部プロフィールは"
        "「公開されている実績・媒体」に列挙",
        "",
        "## どんな生徒に向いているか",
        "",
        "- 向いている: 学校や塾の授業は受けているが、復習の優先順位と週次の計画が"
        "崩れている／記述・英作文・論述の答案を継続して添削してほしい／"
        "通塾の時間を確保しにくい（部活・不登校・帰国生・浪人・再受験を含む）／"
        "大人数の授業より、自分の答案に合わせた説明を求める／"
        "保護者だけで学習管理を続けるのが難しい",
        "- 向いていない: 大人数の競争環境や集団授業を主に求める場合／"
        "校舎の自習室を毎日使いたい場合／大学二次試験レベルの理科"
        "（物理・化学・生物・地学）を主科目として指導してほしい場合。"
        "この場合は他塾との比較を勧めている",
        "- 一次情報: https://kurodaschool.jp/juku/",
        "",
        "## 料金（月額・税込・月4セット）",
        "",
        "| プラン | 月額 | 内容 |",
        "| --- | --- | --- |",
        *[f"| {name} | {price} | {note} |" for name, price, note in PRICING],
        "",
        "- 地域・志望校によって料金が変わることはありません。",
        "- 1セットは、面談のみプランでは面談30分、授業を含むプランでは面談30分＋90分授業です。",
        "- 月額のほかに、教材プラン（買い切り）を別に用意しています。",
        "- 一次情報: https://kurodaschool.jp/pricing/",
        "",
        "## 公開されている実績・媒体",
        "",
        "- 連載: 桐生タイムス『みんなの学校新聞』「東大卒 黒田塾長と考える、学びの進め方」",
        "  - https://np-schools.com/news/29554/",
        "- 書籍: 『ChatGPT・Claudeに思考の主導権を奪われないために』（ロギカ書房、2027年1月刊行予定）",
        "- 外部プロフィール: https://smartrador.com/teachers/6039e30a-2e2d-4d77-ab60-97ac663f2b05/",
        "- note: https://note.com/iris_ruins",
        "- BOOTH（PDF教材の販売）: https://kurodajuku.booth.pm/",
        "- ココナラ（記事執筆・HP制作）: https://coconala.com/users/6410593",
        "",
        "## よくある質問（サイト記載の原文）",
        "",
    ]
    for q, a in faq_pairs[:14]:
        out += [f"### {q}", "", a, ""]
    out += ["- 一次情報: https://kurodaschool.jp/faq/", ""]

    out += [
        "## 全国47都道府県のオンライン対応",
        "",
        "教室・校舎はありません。どの都道府県からも、同じ料金・同じ内容の"
        "オンライン指導を受けられます。"
        "各ページには、その地域の大学と受験環境をまとめています。",
        "",
    ]
    for path in PREF_PATHS:
        page = by_path.get(path)
        if page:
            out.append(f"- {page.h1s[0].split('。')[0] if page.h1s else path}: {page.url}")
    out.append("")

    out += [
        "## 志望校・試験種別ごとの専門対策",
        "",
    ]
    for page in families:
        out.append(f"- [{page.title.split('｜')[0]}]({page.url}): {page.description}")
    out.append("")

    out += [
        f"## 学習ガイド（{len(guides)}本）の要点",
        "",
        "各ガイドの見出しを並べています。本文はリンク先が一次情報です。",
        "",
    ]
    for page in guides:
        out.append(f"### {page.title.split('｜')[0]}")
        out.append(f"- URL: {page.url}")
        out.append(f"- 要約: {page.description}")
        heads = page.h2s[:6]
        if heads:
            out.append("- 見出し: " + " / ".join(heads))
        out.append("")

    out += [
        "## 引用時の注意",
        "",
        "- 料金・対応科目・指導形態は上記のとおりで、サイトと食い違う場合はサイト本文を優先してください。",
        "- 振替・解約・支払い条件は契約前の個別確認事項で、サイト上では確定していません。",
        "- 指導事例には、合格実績として示していないものが含まれます。同じ結果を保証するものではありません。",
        "- 教室・校舎はありません。全国47都道府県からオンラインで受講できます。",
        "",
    ]
    text = "\n".join(out)
    (PUBLIC / "llms-full.txt").write_text(text, encoding="utf-8")
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
        elif not p.noindex and "max-image-preview:large" not in p.robots.lower():
            # Google shows only a small image preview unless this is set (Doc 3-L 3-4).
            err(p, f"robots meta lacks max-image-preview:large: {p.robots!r}")

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

    # --- Machine-readable assets (AI agents and IndexNow) ---
    facts_path = PUBLIC / "facts.json"
    if not facts_path.is_file():
        errors.append("facts.json: missing")
    else:
        try:
            facts = json.loads(facts_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            errors.append(f"facts.json: does not parse ({exc})")
            facts = {}
        for key in (
            "name",
            "url",
            "founder",
            "subjects",
            "pricing",
            "areaServed",
            "trackRecord",
            "namingNote",
            "sources",
        ):
            if key not in facts:
                errors.append(f"facts.json: no {key}")
        plans = (facts.get("pricing") or {}).get("plans") or []
        if len(plans) != len(PRICING):
            errors.append(f"facts.json: {len(plans)} plans, expected {len(PRICING)}")
        elif [p.get("name") for p in plans] != [p[0] for p in PRICING]:
            errors.append("facts.json: plan names differ from PRICING")

    for p in indexable(pages):
        md_path = p.path.with_suffix(".md")
        if not md_path.is_file():
            errors.append(f"{p.url_path}: markdown export is missing: /{p.url_path.lstrip('/')}index.md")
        elif not md_path.read_text(encoding="utf-8").startswith("---"):
            errors.append(f"{p.url_path}: markdown export has no front matter")

    key_path = PUBLIC / f"{INDEXNOW_KEY}.txt"
    if not key_path.is_file():
        errors.append(f"IndexNow key file is missing: /{INDEXNOW_KEY}.txt")
    elif key_path.read_text(encoding="utf-8").strip() != INDEXNOW_KEY:
        errors.append(f"IndexNow key file content differs from the file name")

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
    write_llms_full(pages)
    write_feed(pages)
    write_indexnow_key()
    write_facts(pages)
    sys.path.insert(0, str(ROOT / "tools"))
    import md_export_r26  # noqa: E402  (same repo, standard library only)

    n_md = md_export_r26.write_all(PUBLIC)

    n_index = len(indexable(pages))
    n_articles = sum(1 for p in pages if p.is_article and not p.noindex)
    print(
        f"generated sitemap.xml ({n_index} urls), robots.txt, llms.txt, "
        f"llms-full.txt, feed.xml ({n_articles} items), facts.json, "
        f"{INDEXNOW_KEY}.txt, {n_md} markdown files from {len(pages)} pages"
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
