#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""56観点＋追加観点の SEO / AIO / MEO 診断ツール（黒田塾）。

    python3 tools/seo_aio_meo_audit.py                  # 診断してJSONとMarkdownを出力
    python3 tools/seo_aio_meo_audit.py --markdown out.md
    python3 tools/seo_aio_meo_audit.py --quiet          # サマリだけ表示

検査はすべて公開済みのHTMLと生成物（public/）に対する静的な検査で、
外部APIや順位の取得は行わない。出力:

* tools/audit_report.json … 機械可読な全項目
* tools/audit_report.md   … 改善優先度（P0/P1/P2）付きの人間向けレポート

観点は #1〜#56 が従来の56観点、#57〜#62 が r24 で追加した観点、
#63〜#67 が r26（Doc 1）で追加した観点、#68〜#74 が r27（LINE導線・CRO）の観点。

r25（2026-11-27）: 黒田塾は「オンライン専業・全国47都道府県対応」を方針としたため、
MEO系の観点（#50 #51 #54 #56）は「教室の住所・座標・地図・電話を載せないこと」を
正しい状態として判定する。GBP（Googleビジネスプロフィール）は実店舗向けで、
オンライン専業は対象外のため必須にしない。
"""
from __future__ import annotations

import argparse
import collections
import json
import re
import sys
import xml.etree.ElementTree as ET
from datetime import date
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urljoin, urlsplit

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "public"
SITE = "https://kurodaschool.jp"
OUT_JSON = Path(__file__).resolve().parent / "audit_report.json"
OUT_MD = Path(__file__).resolve().parent / "audit_report.md"

PREFECTURES = [
    "hokkaido", "aomori", "iwate", "miyagi", "akita", "yamagata", "fukushima",
    "ibaraki", "tochigi", "gunma", "saitama", "chiba", "tokyo", "kanagawa",
    "niigata", "toyama", "ishikawa", "fukui", "yamanashi", "nagano", "gifu",
    "shizuoka", "aichi", "mie", "shiga", "kyoto", "osaka", "hyogo", "nara",
    "wakayama", "tottori", "shimane", "okayama", "hiroshima", "yamaguchi",
    "tokushima", "kagawa", "ehime", "kochi", "fukuoka", "saga", "nagasaki",
    "kumamoto", "oita", "miyazaki", "kagoshima", "okinawa",
]

# 都道府県ページの実URL。saitama / chiba / osaka は大学別ページが使っているため別slug。
REGION_URL = {
    "saitama": "/specialty/saitama-ken/",
    "chiba": "/specialty/chiba-ken/",
    "osaka": "/specialty/osaka-fu/",
    "tokyo": "/specialty/tokyo/",
}
for _p in PREFECTURES:
    REGION_URL.setdefault(_p, f"/specialty/{_p}/")
REGION_URLS = set(REGION_URL.values())


class PageParser(HTMLParser):
    def __init__(self, raw: str):
        super().__init__(convert_charrefs=True)
        self.html_lang = ""
        self.title = ""
        self.meta = {}
        self.canonicals = []
        self.headings = []  # (level, text)
        self.links = []
        self.refs = []
        self.imgs = []
        self.ids = []
        self.tables = 0
        self.has_breadcrumb_html = False
        self.jsonld = []
        self.text_len = 0
        self._in_title = False
        self._in_h = None
        self._h_buf = []
        self._in_script_ld = False
        self._ld_buf = []
        self._ignore_text = 0
        self.feed(raw)

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if a.get("id"):
            self.ids.append(a["id"])
        if tag == "html":
            self.html_lang = a.get("lang", "")
        elif tag == "title":
            self._in_title = True
        elif tag == "meta":
            k = a.get("name") or a.get("property") or ""
            if k:
                self.meta[k.lower()] = a.get("content", "")
            if a.get("charset"):
                self.meta["charset"] = a["charset"]
        elif tag == "link":
            rel = a.get("rel", "").split()
            if "canonical" in rel:
                self.canonicals.append(a.get("href", ""))
            if "stylesheet" in rel and a.get("href"):
                self.refs.append(a["href"])
        elif tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            self._in_h = int(tag[1])
            self._h_buf = []
        elif tag == "a" and a.get("href"):
            self.links.append(a["href"])
        elif tag == "img":
            self.imgs.append(a)
            if a.get("src"):
                self.refs.append(a["src"])
        elif tag == "script":
            if a.get("type") == "application/ld+json":
                self._in_script_ld = True
                self._ld_buf = []
            else:
                self._ignore_text += 1
            if a.get("src"):
                self.refs.append(a["src"])
        elif tag == "style":
            self._ignore_text += 1
        elif tag == "table":
            self.tables += 1
        elif tag == "nav":
            aria = a.get("aria-label", "")
            cls = a.get("class", "")
            if "パンくず" in aria or "breadcrumb" in cls.lower():
                self.has_breadcrumb_html = True

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False
        elif tag in {"h1", "h2", "h3", "h4", "h5", "h6"} and self._in_h is not None:
            self.headings.append((self._in_h, "".join(self._h_buf).strip()))
            self._in_h = None
        elif tag == "script":
            if self._in_script_ld:
                try:
                    self.jsonld.append(json.loads("".join(self._ld_buf)))
                except Exception:
                    self.jsonld.append({"_parse_error": True})
                self._in_script_ld = False
            elif self._ignore_text > 0:
                self._ignore_text -= 1
        elif tag == "style" and self._ignore_text > 0:
            self._ignore_text -= 1

    def handle_data(self, data):
        if self._in_title:
            self.title += data
        if self._in_h is not None:
            self._h_buf.append(data)
        if self._in_script_ld:
            self._ld_buf.append(data)
        elif self._ignore_text == 0:
            self.text_len += len(re.sub(r"\s+", "", data))


def route(p: Path) -> str:
    r = p.relative_to(PUBLIC).as_posix()
    if r == "index.html":
        return "/"
    if r.endswith("/index.html"):
        return "/" + r[:-10]
    return "/" + r


def resolve_local(href: str, origin: str) -> Path | None:
    if not href or href.startswith(("mailto:", "tel:", "javascript:", "data:", "blob:")):
        return None
    u = urlsplit(urljoin(SITE + origin, href))
    if u.netloc != "kurodaschool.jp":
        return None
    path = unquote(u.path).lstrip("/")
    p = PUBLIC / path
    if p.is_dir():
        return p / "index.html"
    if not p.suffix and (PUBLIC / path / "index.html").is_file():
        return PUBLIC / path / "index.html"
    return p


def flatten_ld(jsonld_list):
    nodes = []
    for block in jsonld_list:
        if not isinstance(block, dict):
            continue
        if "@graph" in block and isinstance(block["@graph"], list):
            nodes.extend(n for n in block["@graph"] if isinstance(n, dict))
        else:
            nodes.append(block)
    return nodes


# 記事冒頭の要点ブロック（#48）。各ページは <head> だけで約10,000文字あり、
# 生HTMLの先頭6,000文字を見ると本文に届かない。記事の導入部（<h1> から
# 最初の <section> まで）を見て、要点ブロックの要素か見出し語があるかを判定する。
SUMMARY_RE = re.compile(r'summary-box|key-points|article-summary|この記事の(要点|要約|結論)|この記事のポイント')


def article_lead(raw: str, size: int = 4000) -> str:
    """Return the article lead: from <h1> to the first <section> (or size chars)."""
    i = raw.find("<h1")
    if i < 0:
        i = raw.find("<body")
    if i < 0:
        return raw[:size]
    j = raw.find("<section", i)
    end = j if 0 <= j <= i + size else min(len(raw), i + size)
    return raw[i:end]


# 改善優先度: FAILはP0、主要なWARNはP1、残りはP2
P1_CHECKS = {3, 5, 12, 16, 18, 19, 22, 25, 28, 31, 33, 34, 35, 41, 43, 44, 49}


def priority(check: dict) -> str:
    if check["status"] == "PASS":
        return "-"
    if check["status"] == "FAIL":
        return "P0"
    return "P1" if check["id"] in P1_CHECKS else "P2"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--markdown", default=str(OUT_MD))
    ap.add_argument("--json", dest="json_path", default=str(OUT_JSON))
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    pages = {}
    raws = {}
    for p in sorted(PUBLIC.rglob("*.html")):
        u = route(p)
        raw = p.read_text(encoding="utf-8")
        raws[u] = raw
        pages[u] = PageParser(raw)

    indexable = {
        u: pg for u, pg in pages.items()
        if "noindex" not in pg.meta.get("robots", "").lower() and u != "/404.html"
    }

    sitemap_urls = set()
    sitemap_ok = (PUBLIC / "sitemap.xml").is_file()
    if sitemap_ok:
        try:
            tree = ET.parse(PUBLIC / "sitemap.xml")
            for el in tree.getroot().iter("{http://www.sitemaps.org/schemas/sitemap/0.9}loc"):
                if el.text:
                    sitemap_urls.add(el.text.strip())
        except Exception:
            sitemap_ok = False

    robots_txt = (PUBLIC / "robots.txt").read_text(encoding="utf-8") if (PUBLIC / "robots.txt").is_file() else ""
    llms_txt = (PUBLIC / "llms.txt").read_text(encoding="utf-8") if (PUBLIC / "llms.txt").is_file() else ""
    llms_full_path = PUBLIC / "llms-full.txt"
    llms_full = llms_full_path.is_file()
    llms_full_text = llms_full_path.read_text(encoding="utf-8") if llms_full else ""
    feed_ok = (PUBLIC / "feed.xml").is_file()

    inbound = collections.Counter()
    outbound = collections.Counter()
    broken_links = []
    broken_assets = []
    for u, pg in indexable.items():
        seen_out = set()
        for href in pg.links:
            target = resolve_local(href, u)
            if target is not None:
                if not target.is_file():
                    broken_links.append(f"{u} -> {href}")
                else:
                    tu = route(target)
                    if tu != u and tu not in seen_out:
                        seen_out.add(tu)
                        inbound[tu] += 1
                        outbound[u] += 1
        for ref in pg.refs:
            target = resolve_local(ref, u)
            if target is not None and not target.is_file():
                broken_assets.append(f"{u} -> {ref}")

    checks = []

    def add(cat, cid, name, status, detail, samples=None):
        checks.append({
            "cat": cat, "id": cid, "name": name,
            "status": status, "detail": detail, "samples": samples or [],
        })

    # --- A. Technical & Crawlability (1-15) ---
    add("Technical", 1, "robots.txt 存在", "PASS" if robots_txt else "FAIL", "robots.txt あり" if robots_txt else "robots.txt なし")
    add("Technical", 2, "sitemap.xml 妥当性", "PASS" if sitemap_ok else "FAIL", f"{len(sitemap_urls)} URLs")
    missing_sm = sorted(SITE + u for u in indexable if (SITE + u) not in sitemap_urls)
    add("Technical", 3, "インデックス対象ページのサイトマップ網羅", "PASS" if not missing_sm else "FAIL", f"未登録 {len(missing_sm)}件", missing_sm[:5])
    extra_sm = sorted(s for s in sitemap_urls if s.replace(SITE, "") not in indexable)
    add("Technical", 4, "サイトマップ内のnoindex/不要URL混入", "PASS" if not extra_sm else "WARN", f"不一致 {len(extra_sm)}件", extra_sm[:5])
    no_canon = [u for u, pg in indexable.items() if not pg.canonicals]
    add("Technical", 5, "canonical 設定有無", "PASS" if not no_canon else "FAIL", f"未設定 {len(no_canon)}件", no_canon[:5])
    bad_canon = [u for u, pg in indexable.items() if pg.canonicals and pg.canonicals[0] != SITE + u]
    add("Technical", 6, "canonical 自己参照・HTTPS正規化", "PASS" if not bad_canon else "FAIL", f"不一致 {len(bad_canon)}件", bad_canon[:5])
    dup_canon = [u for u, pg in indexable.items() if len(pg.canonicals) > 1]
    add("Technical", 7, "canonical 重複なし", "PASS" if not dup_canon else "FAIL", f"重複 {len(dup_canon)}件", dup_canon[:5])
    no_robots = [u for u, pg in pages.items() if "robots" not in pg.meta]
    add("Technical", 8, "robots メタタグ設定", "PASS" if not no_robots else "WARN", f"未設定 {len(no_robots)}件", no_robots[:5])
    bad_lang = [u for u, pg in indexable.items() if not pg.html_lang.startswith("ja")]
    add("Technical", 9, "html lang='ja' 設定", "PASS" if not bad_lang else "WARN", f"未設定 {len(bad_lang)}件", bad_lang[:5])
    no_vp = [u for u, pg in indexable.items() if "viewport" not in pg.meta]
    add("Technical", 10, "viewport 設定（モバイル対応）", "PASS" if not no_vp else "FAIL", f"未設定 {len(no_vp)}件", no_vp[:5])
    no_cs = [u for u, pg in indexable.items() if "charset" not in pg.meta]
    add("Technical", 11, "UTF-8 charset 明示", "PASS" if not no_cs else "WARN", f"未設定 {len(no_cs)}件", no_cs[:5])
    add("Technical", 12, "内部リンク切れなし", "PASS" if not broken_links else "FAIL", f"リンク切れ {len(broken_links)}件", broken_links[:5])
    add("Technical", 13, "ローカルアセット（画像/CSS/JS）切れなし", "PASS" if not broken_assets else "FAIL", f"欠損 {len(broken_assets)}件", broken_assets[:5])
    dup_ids = [u for u, pg in indexable.items() if any(c > 1 for c in collections.Counter(pg.ids).values())]
    add("Technical", 14, "HTML id 重複なし", "PASS" if not dup_ids else "WARN", f"重複あり {len(dup_ids)}件", dup_ids[:5])
    heavy = [u for u, raw in raws.items() if len(raw.encode("utf-8")) > 250_000]
    add("Technical", 15, "HTMLサイズ肥大化なし（250KB未満）", "PASS" if not heavy else "WARN", f"超過 {len(heavy)}件", heavy[:5])

    # --- B. On-Page & Content SEO (16-32) ---
    no_title = [u for u, pg in indexable.items() if not pg.title.strip()]
    add("On-Page", 16, "title タグ設定", "PASS" if not no_title else "FAIL", f"未設定 {len(no_title)}件", no_title[:5])
    bad_tlen = [f"{u} ({len(pg.title.strip())}字)" for u, pg in indexable.items() if not (15 <= len(pg.title.strip()) <= 65)]
    add("On-Page", 17, "title 文字数適正（15〜65字）", "PASS" if not bad_tlen else "WARN", f"範囲外 {len(bad_tlen)}件", bad_tlen[:5])
    t_counts = collections.Counter(pg.title.strip() for pg in indexable.values())
    dup_t = [t for t, c in t_counts.items() if c > 1]
    add("On-Page", 18, "title 重複なし", "PASS" if not dup_t else "FAIL", f"重複 {len(dup_t)}種", dup_t[:5])
    no_desc = [u for u, pg in indexable.items() if not pg.meta.get("description", "").strip()]
    add("On-Page", 19, "meta description 設定", "PASS" if not no_desc else "FAIL", f"未設定 {len(no_desc)}件", no_desc[:5])
    bad_dlen = [f"{u} ({len(pg.meta.get('description','').strip())}字)" for u, pg in indexable.items() if not (50 <= len(pg.meta.get("description", "").strip()) <= 165)]
    add("On-Page", 20, "meta description 文字数適正（50〜165字）", "PASS" if not bad_dlen else "WARN", f"範囲外 {len(bad_dlen)}件", bad_dlen[:5])
    d_counts = collections.Counter(pg.meta.get("description", "").strip() for pg in indexable.values())
    dup_d = [d[:30] for d, c in d_counts.items() if c > 1 and d]
    add("On-Page", 21, "meta description 重複なし", "PASS" if not dup_d else "FAIL", f"重複 {len(dup_d)}種", dup_d[:5])
    bad_h1 = [u for u, pg in indexable.items() if sum(1 for lv, _ in pg.headings if lv == 1) != 1]
    add("On-Page", 22, "h1 が各ページ1つ", "PASS" if not bad_h1 else "FAIL", f"違反 {len(bad_h1)}件", bad_h1[:5])
    h1_counts = collections.Counter(next((txt for lv, txt in pg.headings if lv == 1), "") for pg in indexable.values())
    dup_h1 = [h for h, c in h1_counts.items() if c > 1 and h]
    add("On-Page", 23, "h1 重複なし", "PASS" if not dup_h1 else "WARN", f"重複 {len(dup_h1)}種", dup_h1[:5])
    skip_h = []
    for u, pg in indexable.items():
        prev = 0
        for lv, _ in pg.headings:
            if prev and lv > prev + 1:
                skip_h.append(f"{u} (h{prev}->h{lv})")
                break
            prev = lv
    add("On-Page", 24, "見出し階層（h1→h2→h3）飛びなし", "PASS" if not skip_h else "WARN", f"レベル飛び {len(skip_h)}件", skip_h[:5])
    thin = [f"{u} ({pg.text_len}字)" for u, pg in indexable.items() if pg.text_len < 600 and u not in {"/contact/", "/privacy/", "/legal/"}]
    add("On-Page", 25, "シンコンテンツ回避（600字以上）", "PASS" if not thin else "WARN", f"600字未満 {len(thin)}件", thin[:5])
    guides = {u: pg for u, pg in indexable.items() if u.startswith("/study-guides/") and u != "/study-guides/"}
    no_q_h = [u for u, pg in guides.items() if not any(("？" in txt or "?" in txt) for lv, txt in pg.headings if lv in {2, 3})]
    add("On-Page", 26, "記事見出しへの質問形式（？付きH2/H3）導入", "PASS" if not no_q_h else "WARN", f"質問見出しなし {len(no_q_h)}/{len(guides)}本", no_q_h[:5])
    no_tbl = [u for u, pg in guides.items() if pg.tables == 0]
    add("On-Page", 27, "学習ガイドへの比較表（table）設置", "PASS" if len(no_tbl) < len(guides) * 0.5 else "WARN", f"tableなし {len(no_tbl)}/{len(guides)}本", no_tbl[:5])
    no_alt = [u for u, pg in indexable.items() if any(not img.get("alt", "").strip() for img in pg.imgs)]
    add("On-Page", 28, "img alt 属性設定", "PASS" if not no_alt else "WARN", f"alt欠損 {len(no_alt)}件", no_alt[:5])
    no_dim = [u for u, pg in indexable.items() if any(not (img.get("width") and img.get("height")) for img in pg.imgs)]
    add("On-Page", 29, "img width/height 明示（CLS防止）", "PASS" if not no_dim else "WARN", f"未指定 {len(no_dim)}件", no_dim[:5])
    non_webp = [u for u, pg in indexable.items() if any(not (".webp" in img.get("src", "") or ".webp" in img.get("srcset", "") or ".svg" in img.get("src", "")) for img in pg.imgs)]
    add("On-Page", 30, "画像最適化（WebP/SVG利用）", "PASS" if not non_webp else "WARN", f"非WebPあり {len(non_webp)}件", non_webp[:5])
    no_og = [u for u, pg in indexable.items() if not all(k in pg.meta for k in ("og:title", "og:description", "og:url", "og:image"))]
    add("On-Page", 31, "OGPメタタグ完備", "PASS" if not no_og else "WARN", f"不足 {len(no_og)}件", no_og[:5])
    no_tw = [u for u, pg in indexable.items() if "twitter:card" not in pg.meta]
    add("On-Page", 32, "Twitter/X Card メタタグ完備", "PASS" if not no_tw else "WARN", f"不足 {len(no_tw)}件", no_tw[:5])

    # --- C. Internal Linking & Freshness (33-39) ---
    subpages = {u: pg for u, pg in indexable.items() if u != "/"}
    no_bc_html = [u for u, pg in subpages.items() if not pg.has_breadcrumb_html]
    add("Linking", 33, "下層ページのパンくずHTML設置", "PASS" if not no_bc_html else "WARN", f"未設置 {len(no_bc_html)}件", no_bc_html[:5])
    no_bc_ld = [u for u, pg in subpages.items() if not any(n.get("@type") == "BreadcrumbList" for n in flatten_ld(pg.jsonld))]
    add("Linking", 34, "下層ページの BreadcrumbList JSON-LD", "PASS" if not no_bc_ld else "WARN", f"未設置 {len(no_bc_ld)}件", no_bc_ld[:5])
    weak_in = [f"{u} ({inbound[u]})" for u in subpages if inbound[u] < 3]
    add("Linking", 35, "被リンク3本以上（孤立ページ防止）", "PASS" if not weak_in else "WARN", f"被リンク3未満 {len(weak_in)}件", weak_in[:5])
    weak_out = [f"{u} ({outbound[u]})" for u in indexable if outbound[u] < 3]
    add("Linking", 36, "発リンク3本以上（回遊導線確保）", "PASS" if not weak_out else "WARN", f"発リンク3未満 {len(weak_out)}件", weak_out[:5])
    no_cta = [u for u, pg in indexable.items() if not any("/contact" in l or "line.me" in l for l in pg.links)]
    add("Linking", 37, "相談CTAリンク（/contact/ または LINE）設置", "PASS" if not no_cta else "WARN", f"CTAなし {len(no_cta)}件", no_cta[:5])
    no_date = [u for u, pg in guides.items() if not any(n.get("dateModified") or n.get("datePublished") for n in flatten_ld(pg.jsonld))]
    add("Linking", 38, "学習ガイドの datePublished/dateModified 明示", "PASS" if not no_date else "WARN", f"日付なし {len(no_date)}/{len(guides)}本", no_date[:5])
    add("Linking", 39, "feed.xml（RSS/Atom）配信", "PASS" if feed_ok else "WARN", "feed.xml あり" if feed_ok else "なし")

    # --- D. AIO / LLM Search Optimization (40-49) ---
    ai_bots = ["GPTBot", "OAI-SearchBot", "ClaudeBot", "PerplexityBot", "Google-Extended"]
    missing_bots = [b for b in ai_bots if b not in robots_txt]
    add("AIO", 40, "robots.txt での主要AIクローラ許可", "PASS" if not missing_bots else "FAIL", f"未記載 {len(missing_bots)}種", missing_bots)
    add("AIO", 41, "llms.txt 設置", "PASS" if llms_txt else "FAIL", f"{len(llms_txt)} chars" if llms_txt else "なし")
    add("AIO", 42, "llms-full.txt（LLM向け全ページ要約集）設置", "PASS" if llms_full else "FAIL",
        f"{len(llms_full_text)} chars" if llms_full else "未設置（AIO引用率向上に有効）")
    llms_missing = [u for u in indexable if u not in llms_txt and u != "/"]
    add("AIO", 43, "llms.txt の全ページ網羅率", "PASS" if not llms_missing else "WARN", f"未掲載 {len(llms_missing)}/{len(indexable)}ページ", llms_missing[:5])
    faq_pages = [u for u, pg in indexable.items() if any(n.get("@type") == "FAQPage" for n in flatten_ld(pg.jsonld))]
    add("AIO", 44, "FAQPage JSON-LD 展開率", "PASS" if len(faq_pages) >= 50 else "WARN", f"実装 {len(faq_pages)}/{len(indexable)}ページ")

    home_nodes = flatten_ld(pages["/"].jsonld) if "/" in pages else []
    org_node = next((n for n in home_nodes if n.get("@type") in {"EducationalOrganization", "Organization", "LocalBusiness"}), {})
    person_node = next((n for n in home_nodes if n.get("@type") == "Person"), {})
    same_as = org_node.get("sameAs", [])
    add("AIO", 45, "組織 sameAs（外部媒体・SNS・書籍・連載リンク）", "PASS" if len(same_as) >= 3 else "FAIL", f"sameAs {len(same_as)}件", same_as)
    p_creds = all(k in person_node for k in ("alumniOf", "knowsAbout"))
    add("AIO", 46, "講師 Person スキーマ（学歴・専門領域・sameAs）", "PASS" if p_creds and person_node.get("sameAs") else "WARN", f"alumniOf/knowsAbout={'あり' if p_creds else '不足'}, sameAs={len(person_node.get('sameAs', []))}件")
    course_pages = [u for u, pg in indexable.items() if any(n.get("@type") == "Course" for n in flatten_ld(pg.jsonld))]
    add("AIO", 47, "Course/Offer スキーマ（料金・提供形態）", "PASS" if len(course_pages) >= 3 else "WARN", f"実装 {len(course_pages)}ページ")
    no_summary = [u for u, pg in guides.items() if not SUMMARY_RE.search(article_lead(raws[u]))]
    add("AIO", 48, "記事冒頭の結論・要点ブロック（AI引用向け）", "PASS" if len(no_summary) < len(guides) * 0.3 else "WARN", f"冒頭要点なし {len(no_summary)}/{len(guides)}本", no_summary[:5])
    has_media_proof = "みんなの学校新聞" in raws.get("/about/", "") and "50人" in raws.get("/about/", "")
    add("AIO", 49, "権威性・実績ファクトの構造的明示（累計50人・連載等）", "PASS" if has_media_proof else "WARN", "/about/ での確認結果")

    # --- E. MEO / Local & Regional Search (50-56) ---
    # オンライン専業の方針: 教室の詳細住所・電話・座標・地図は載せない。
    has_nap = bool(org_node.get("address") and org_node.get("telephone"))
    add("MEO", 50, "教室の詳細住所・電話を構造化データに載せない（オンライン専業）",
        "PASS" if not has_nap else "FAIL",
        "住所・電話は非掲載（方針どおり）" if not has_nap else "教室の住所・電話が残っている（集客ページから外す）")
    has_geo = "geo" in org_node
    add("MEO", 51, "GeoCoordinates（教室の座標）を載せない（オンライン専業）",
        "PASS" if not has_geo else "FAIL",
        "非掲載（方針どおり）" if not has_geo else "座標が残っている（教室所在地の公開になる）")
    has_hours = "openingHoursSpecification" in org_node
    add("MEO", 52, "openingHoursSpecification（営業時間）構造化", "PASS" if has_hours else "FAIL", "あり" if has_hours else "未設定")
    has_area = "areaServed" in org_node
    area_count = len(org_node.get("areaServed", [])) if isinstance(org_node.get("areaServed"), list) else 1
    add("MEO", 53, "areaServed（日本全国・オンライン対応）構造化", "PASS" if has_area else "FAIL",
        f"あり（{area_count}地域）" if has_area else "未設定（全国対応が検索/AIに伝わっていない）")
    has_map = "hasMap" in org_node
    add("MEO", 54, "hasMap（GoogleマップURL）を載せない（オンライン専業）",
        "PASS" if not has_map else "FAIL",
        "非掲載（方針どおり）" if not has_map else "地図URLが残っている（教室への来訪を促す表示）")
    covered_prefs = [p for p in PREFECTURES if REGION_URL[p] in indexable]
    add("MEO", 55, "全国47都道府県の地域別ページ網羅率", "PASS" if len(covered_prefs) >= 47 else "FAIL",
        f"現在 {len(covered_prefs)}/47都道府県 ({', '.join(covered_prefs[:10])}{'...' if len(covered_prefs) > 10 else ''})")
    has_gbp_link = any("google.com/maps" in raws[u] or "goo.gl/maps" in raws[u] or "g.page" in raws[u] for u in indexable)
    citation_count = len(org_node.get("sameAs", []))
    add("MEO", 56, "地図・GBPリンクに頼らず、外部サイテーションで信頼を補う",
        "PASS" if (not has_gbp_link and citation_count >= 3) else "WARN",
        f"地図リンクなし・sameAs {citation_count}件" if not has_gbp_link else "Googleマップ/GBPリンクあり（オンライン専業では不要）")

    # --- F. r24 追加観点 (57-62) ---
    need_full = ["## 料金", "24,000円", "54,990円", "104,990円", "## 全国47都道府県", "## よくある質問"]
    missing_full = [s for s in need_full if s not in llms_full_text]
    add("AIO", 57, "llms-full.txt の必須セクション（料金・47都道府県・FAQ）", "PASS" if llms_full and not missing_full else "FAIL",
        f"不足 {len(missing_full)}件" if missing_full else f"{len(llms_full_text)} chars に主要情報あり", missing_full)
    org_variants = set()
    for u, pg in indexable.items():
        for n in flatten_ld(pg.jsonld):
            if n.get("@id") == f"{SITE}/#organization":
                org_variants.add(json.dumps(n, ensure_ascii=False, sort_keys=True))
    add("AIO", 58, "全ページの EducationalOrganization 定義が同一", "PASS" if len(org_variants) == 1 else "FAIL",
        f"{len(org_variants)}種の定義")
    region_pages = {u: pg for u, pg in indexable.items() if u in REGION_URLS}
    thin_region = [
        u for u, pg in region_pages.items()
        if pg.text_len < 1500 or len(pg.headings) < 8
    ]
    add("MEO", 59, "47都道府県ページの固有コンテンツ量（1,500字・見出し8以上）", "PASS" if not thin_region else "WARN",
        f"不足 {len(thin_region)}/{len(region_pages)}ページ", thin_region[:5])
    weak_region = [f"{u} ({inbound[u]})" for u in region_pages if inbound[u] < 3]
    add("MEO", 60, "47都道府県ページの被リンク3本以上", "PASS" if not weak_region else "WARN",
        f"3本未満 {len(weak_region)}/{len(region_pages)}ページ", weak_region[:5])
    pref_words = [u for u, pg in region_pages.items() if pg.title.strip() and pg.title.strip() in raws[u]]
    add("MEO", 61, "都道府県ページのタイトル・見出しに地域名", "PASS" if len(pref_words) == len(region_pages) else "WARN",
        f"地域名あり {len(pref_words)}/{len(region_pages)}ページ")
    today = date.today().isoformat()
    fut = [u for u, pg in indexable.items() if pg.meta.get("last-modified", "") > today]
    add("Technical", 62, "last-modified が未来日でない", "PASS" if not fut else "FAIL", f"未来日 {len(fut)}件", fut[:5])

    # --- G. r26 追加観点（Doc 1: facts.json / Speakable / エンティティ整合 /
    #     IndexNowキー / Markdown版） (63-67) ---
    facts_problems = []
    facts_data = None
    if not (PUBLIC / "facts.json").is_file():
        facts_problems.append("facts.json なし")
    else:
        try:
            facts_data = json.loads((PUBLIC / "facts.json").read_text(encoding="utf-8"))
        except Exception:
            facts_problems.append("JSONとして読めない")
        if isinstance(facts_data, dict):
            for key in ("name", "url", "founder", "subjects", "pricing", "areaServed", "trackRecord", "namingNote", "sources"):
                if key not in facts_data:
                    facts_problems.append(f"{key} なし")
            plans = (facts_data.get("pricing") or {}).get("plans") or []
            if len(plans) != 5:
                facts_problems.append(f"料金プラン {len(plans)}件")
    add("AIO", 63, "facts.json（AI向け一次情報のJSON）", "PASS" if not facts_problems else "FAIL",
        f"項目 {len(facts_data) if isinstance(facts_data, dict) else 0}・料金5プラン" if not facts_problems else f"不備 {len(facts_problems)}件",
        facts_problems[:5])

    no_speakable = [u for u, raw in raws.items() if u in indexable and '"SpeakableSpecification"' not in raw]
    add("AIO", 64, "全ページの SpeakableSpecification（h1・要点ボックス）",
        "PASS" if not no_speakable else "WARN", f"未実装 {len(no_speakable)}/{len(indexable)}件", no_speakable[:5])

    person_variants = set()
    website_variants = set()
    for u, pg in indexable.items():
        for n in flatten_ld(pg.jsonld):
            if n.get("@id") == f"{SITE}/#teacher":
                person_variants.add(json.dumps(n, ensure_ascii=False, sort_keys=True))
            elif n.get("@id") == f"{SITE}/#website":
                website_variants.add(json.dumps(n, ensure_ascii=False, sort_keys=True))
    entity_ok = len(person_variants) == 1 and len(website_variants) == 1
    add("AIO", 65, "全ページの Person / WebSite 定義が同一", "PASS" if entity_ok else "FAIL",
        f"Person {len(person_variants)}種・WebSite {len(website_variants)}種")

    key_files = [
        f for f in PUBLIC.glob("*.txt")
        if re.fullmatch(r"[A-Za-z0-9]{32}", f.stem)
    ]
    key_ok = bool(key_files) and all(
        f.read_text(encoding="utf-8").strip() == f.stem for f in key_files
    )
    add("Technical", 66, "IndexNow キーファイル（32文字・中身一致）",
        "PASS" if key_ok else "FAIL",
        ", ".join(f"/{f.name}" for f in key_files) if key_files else "なし")

    paths = {route(p): p for p in PUBLIC.rglob("*.html")}
    md_missing = [
        u for u in indexable
        if not (paths[u].with_suffix(".md")).is_file()
        or 'rel="alternate" type="text/markdown"' not in raws[u]
    ]
    add("AIO", 67, "各ページのMarkdown版（.md）と head の alternate リンク",
        "PASS" if not md_missing else "WARN",
        f"未整備 {len(md_missing)}/{len(indexable)}件", md_missing[:5])

    # --- H. r27 追加観点（LINE導線／相談CRO） (68-74) ---
    legal = {"/privacy/", "/legal/", "/materials/terms/"}
    no_mid = legal | {"/contact/", "/shindan/"}
    line_cta = [
        u for u, pg in indexable.items()
        if not any(("lin.ee/" in l) or ("oaMessage" in l) or ("line.me/R/ti" in l) for l in pg.links)
    ]
    add("CRO", 68, "全ページにLINE相談リンク（1本以上・法務ページを除く）",
        "PASS" if not line_cta else "FAIL",
        f"LINEリンクなし {len(line_cta)}/{len(indexable)}件", line_cta[:5])

    few_line = []
    for u, pg in indexable.items():
        if u in legal:
            continue
        n = sum(1 for l in pg.links if ("lin.ee/" in l) or ("oaMessage" in l) or ("line.me/R/ti" in l))
        if n < 3:
            few_line.append(f"{u} ({n})")
    add("CRO", 69, "1ページ内のLINE接点3本以上（ヘッダー・本文中・固定バー）",
        "PASS" if not few_line else "WARN",
        f"3本未満 {len(few_line)}/{len(indexable)}件", few_line[:5])

    no_mid_pages = [u for u, raw in raws.items() if u in indexable and u not in no_mid
                    and '<!-- r27:cro-mid:start -->' not in raw]
    add("CRO", 70, "記事中盤〜FAQ前のLINE相談カード（読み終わる前の離脱対策）",
        "PASS" if not no_mid_pages else "FAIL",
        f"未設置 {len(no_mid_pages)}/{len(indexable) - len(no_mid & set(indexable))}件", no_mid_pages[:5])

    no_sticky = [u for u, raw in raws.items() if u in indexable and u not in legal
                 and 'class="r27-sticky"' not in raw]
    add("CRO", 71, "スマホ追従バーがHTMLに静的設置（JS無効でも表示・初回表示から押せる）",
        "PASS" if not no_sticky else "FAIL",
        f"未設置 {len(no_sticky)}/{len(indexable) - len(legal & set(indexable))}件", no_sticky[:5])

    no_oa = [u for u, raw in raws.items() if u in indexable and u not in no_mid
             and "line.me/R/oaMessage" not in raw]
    add("CRO", 72, "カテゴリ別の相談テンプレ（oaMessageで文言プリフィル）",
        "PASS" if not no_oa else "WARN",
        f"プリフィルなし {len(no_oa)}/{len(indexable)}件", no_oa[:5])

    legacy = [u for u, raw in raws.items()
              if "lin.ee/YXdwMqY" in raw or "lin.ee/vb8qVu4" in raw
              or "line.me/R/ti/p/@670gzfpd" in raw]
    add("CRO", 73, "LINEリンクの正規化（lin.ee/VKV65IQ・oaMessage の2種類に統一）",
        "PASS" if not legacy else "FAIL",
        f"旧リンク残存 {len(legacy)}件", legacy[:5])

    no_facts = []
    for u, raw in raws.items():
        if u in indexable and u not in legal:
            needed = ["勧誘", "直接返信", "24時間"]
            if not all(k in raw for k in needed):
                no_facts.append(u)
    add("CRO", 74, "心理的ハードルを下げる事実ベースのマイクロコピー（勧誘なし・直接返信・返信目安）",
        "PASS" if not no_facts else "WARN",
        f"明示なし {len(no_facts)}/{len(indexable)}件", no_facts[:5])

    counts = collections.Counter(c["status"] for c in checks)
    core = [c for c in checks if c["id"] <= 56]
    core_counts = collections.Counter(c["status"] for c in core)
    report = {
        "total_pages": len(pages),
        "indexable_pages": len(indexable),
        "total_checks": len(checks),
        "summary": dict(core_counts),
        "summary_all": dict(counts),
        "checks": checks,
        "generated_at": today,
    }
    Path(args.json_path).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    # Markdown レポート
    for c in checks:
        c["priority"] = priority(c)
    lines = [
        "# 黒田塾 SEO / AIO / MEO 診断レポート",
        "",
        f"- 実行日: {today}",
        f"- 対象: {len(indexable)}ページ（総HTML {len(pages)}） / 診断項目 {len(checks)}（うち従来56観点）",
        f"- 結果（56観点）: PASS {core_counts['PASS']} / WARN {core_counts['WARN']} / FAIL {core_counts['FAIL']}",
        f"- 結果（全体）: PASS {counts['PASS']} / WARN {counts['WARN']} / FAIL {counts['FAIL']}",
        "",
        "優先度は P0（FAIL: 検索・AI検索への流入に直結）／ P1（WARN: 主要な改善余地）／ "
        "P2（WARN: 望ましい改善）です。",
        "",
    ]
    for level in ("P0", "P1", "P2"):
        rows = [c for c in checks if c["priority"] == level]
        if not rows:
            continue
        title = {"P0": "P0 — すぐ直す", "P1": "P1 — 次に直す", "P2": "P2 — 余力で直す"}[level]
        lines += [f"## {title}（{len(rows)}件）", ""]
        for c in rows:
            smp = "／".join(str(s) for s in c["samples"][:3])
            lines.append(f"- **#{c['id']:02d} [{c['cat']}] {c['name']}** — {c['detail']}"
                         + (f"（例: {smp}）" if smp else ""))
        lines.append("")
    lines += ["## 全項目", "", "| # | 分類 | 観点 | 判定 | 優先度 | 詳細 |", "| --- | --- | --- | --- | --- | --- |"]
    for c in checks:
        detail = str(c["detail"]).replace("|", "／")
        lines.append(f"| {c['id']:02d} | {c['cat']} | {c['name']} | {c['status']} | {c['priority']} | {detail} |")
    lines += [
        "",
        "## 直し方の目安",
        "",
        "- P0 は build.py / tools/seo_guard_r17.py が検出しない種類の欠損が中心なので、"
        "構造化データと生成物（llms-full.txt・地域ページ）を先に埋める。",
        "- P1 の多くはコンテンツ側（質問見出し・比較表・冒頭要約）の積み上げで、"
        "一度に全記事を直すより、検索流入のある記事から順に直すほうが費用対効果が高い。",
        "- WARN は「無くても動くが、AI検索とMEOで差がつく」項目。四半期ごとの見直しで足りる。",
        "",
    ]
    Path(args.markdown).write_text("\n".join(lines) + "\n", encoding="utf-8")

    print("=== kurodaschool.jp SEO/AIO/MEO 診断 ===")
    print(f"対象ページ: {len(indexable)} (総HTML: {len(pages)}) | 診断項目: {len(checks)}")
    print(f"56観点: PASS {core_counts['PASS']} | WARN {core_counts['WARN']} | FAIL {core_counts['FAIL']}")
    print(f"全体  : PASS {counts['PASS']} | WARN {counts['WARN']} | FAIL {counts['FAIL']}")
    if not args.quiet:
        for c in checks:
            if c["status"] != "PASS":
                smp = f" 例: {', '.join(str(s) for s in c['samples'][:3])}" if c["samples"] else ""
                print(f"[{c['status']}][{c['priority']}] #{c['id']:02d} [{c['cat']}] {c['name']}: {c['detail']}{smp}")
    print(f"\nwrote {args.json_path} / {args.markdown}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
