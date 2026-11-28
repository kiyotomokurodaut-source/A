#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""第11弾: 50観点以上の「新しい」SEO / AIO / 技術 / コンテンツ診断（r32）。

既存の ``tools/seo_aio_meo_audit.py``（82観点）とは重複しない観点だけを、
より深い実測水準で判定する。検査は公開物（``public/``）に対する静的検査のみで、
外部API・順位・実測CWVの取得は行わない。

    python3 tools/seo_deep_audit_r32.py                 # 診断してJSONとMarkdownを出力
    python3 tools/seo_deep_audit_r32.py --markdown out.md --json out.json
    python3 tools/seo_deep_audit_r32.py --quiet         # サマリだけ

出力:
* tools/deep_audit_r32.json … 機械可読な全項目
* tools/deep_audit_r32.md   … 優先度（P0/P1/P2）付きの人間向けレポート

観点の分類（#101〜#160）:
  A 配信・表示速度（101-110） … preconnect/preload/srcset/CSS・JS量/キャッシュ/重量
  B クロール・インデックス（111-120） … クリック深度/フラグメント/canonical・og:url・
      sitemapの厳密一致/lastmodの三重一致/noopener/一次情報/404/本文内被リンク
  C オンページ・コンテンツ（121-130） … SERP表示幅/H1とタイトルの語の一致/H2重複/
      本文量/E-E-A-Tの可視表記/出典/数値の明示/見出し構造/長すぎる段落
  D 構造化データ（131-140） … パンくずのHTML一致/@id解決/FAQ可視性/Article・Service・
      Courseの必須・推奨プロパティ/料金の一致/JSON-LDの妥当性
  E AIO（141-148） … llms.txt・llms-full.txt・facts.json・.mdの網羅と鮮度、Content-Type
  F モバイルUX・CRO（149-154） … 拡大禁止/追従バーの重なり/タップ領域/入力文字/ナビ数/初回CTA
  G 品質・スパム耐性・a11y（155-160） … 隠しテキスト/コメント指示/alt/表見出し/広告rel/タグ整合

黒田塾は「オンライン専業・全国47都道府県対応」が方針なので、教室の住所・電話・
地図を載せないことを正しい状態として扱う（既存82観点と同じ前提）。
"""
from __future__ import annotations

import argparse
import collections
import difflib
import json
import re
import struct
import sys
import xml.etree.ElementTree as ET
from datetime import date
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urljoin, urlsplit

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "public"
SITE = "https://kurodaschool.jp"
OUT_JSON = Path(__file__).resolve().parent / "deep_audit_r32.json"
OUT_MD = Path(__file__).resolve().parent / "deep_audit_r32.md"

VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link",
        "meta", "param", "source", "track", "wbr"}
# 端末幅で切れる前に読ませたい主要ページ（CRO / AIO の重点）
MONEY = ["/", "/pricing/", "/university-exam/", "/junior-high-exam/",
         "/online-tutoring/", "/study-coaching/", "/todai-juku/", "/contact/",
         "/materials/", "/juku/", "/for-parents/", "/specialty/"]
LEGAL = {"/privacy/", "/legal/", "/materials/terms/"}
PRICES = {24000, 30000, 54990, 79990, 104990, 3000, 12000, 549900}


def display_width(text: str) -> int:
    """SERPでの表示幅（全角=2・半角=1）。"""
    return sum(2 if ord(c) > 0x2E7F else 1 for c in text)


class PageParser(HTMLParser):
    """1ページ分のSEO要素を集める。"""

    def __init__(self, raw: str):
        super().__init__(convert_charrefs=True)
        self.raw = raw
        self.html_lang = ""
        self.title = ""
        self.meta: dict[str, str] = {}
        self.canonicals: list[str] = []
        self.stylesheets: list[str] = []
        self.scripts: list[tuple[str, str]] = []   # (src, 属性)
        self.inline_style = 0
        self.inline_script = 0
        self.imgs: list[dict] = []
        self.links: list[tuple[str, str, str]] = []  # (href, text, 属性)
        self.headings: list[tuple[int, str]] = []
        self.ids: list[str] = []
        self.tables = 0
        self.checkboxes = 0
        self.inputs = 0
        self.breadcrumb_html: list[tuple[str, str]] = []  # (name, url|"")
        self.main_html = ""
        self.jsonld: list = []
        self._in_title = False
        self._in_head = True
        self._in_h: int | None = None
        self._h_buf: list[str] = []
        self._in_ld = False
        self._ld_buf: list[str] = []
        self._in_style = False
        self._style_buf: list[str] = []
        self._in_script = False
        self._script_attr = ""
        self._script_buf: list[str] = []
        self._a_href = ""
        self._a_attr = ""
        self._a_buf: list[str] = []
        self._nav_buf: list[str] = []
        self._in_bc_nav = False
        self._main_depth = 0
        self._main_buf: list[str] = []
        self.feed(raw)
        m = re.search(r"<main\b.*?</main>", raw, re.S)
        self.main_html = m.group(0) if m else ""
        self.breadcrumb_html = []
        bc = re.search(r'<nav[^>]*aria-label="パンくず[^"]*"[^>]*>(.*?)</nav>', raw, re.S)
        if bc:
            self._parse_breadcrumb(bc.group(1))

    # --- 開始タグ -------------------------------------------------
    def handle_starttag(self, tag, attrs):
        a = {k: (v or "") for k, v in attrs}
        if a.get("id"):
            self.ids.append(a["id"])
        if tag == "html":
            self.html_lang = a.get("lang", "")
        elif tag == "title":
            if self._in_head and not self.title:
                self._in_title = True
        elif tag == "meta":
            key = (a.get("name") or a.get("property") or "").lower()
            if key:
                self.meta[key] = a.get("content", "")
            if a.get("charset"):
                self.meta["charset"] = a["charset"]
        elif tag == "link":
            rel = a.get("rel", "").split()
            if "canonical" in rel:
                self.canonicals.append(a.get("href", ""))
            if "stylesheet" in rel and a.get("href"):
                self.stylesheets.append(a["href"])
            if a.get("href"):
                self.links.append((a["href"], "", f"LINK {a.get('rel','')}"))
        elif tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            self._in_h = int(tag[1])
            self._h_buf = []
        elif tag == "a" and a.get("href"):
            self._a_href = a["href"]
            self._a_attr = " ".join(f"{k}={v}" for k, v in a.items())
            self._a_buf = []
        elif tag == "img":
            self.imgs.append(a)
        elif tag == "script":
            self._in_script = True
            self._script_attr = " ".join(f"{k}={v}" for k, v in a.items())
            self._script_buf = []
            if a.get("src"):
                self.scripts.append((a["src"], self._script_attr))
            if a.get("type") == "application/ld+json":
                self._in_ld = True
                self._ld_buf = []
        elif tag == "style":
            self._in_style = True
            self._style_buf = []
        elif tag == "table":
            self.tables += 1
        elif tag == "input":
            self.inputs += 1
            if a.get("type", "text") == "checkbox":
                self.checkboxes += 1
        elif tag == "textarea" or tag == "select":
            self.inputs += 1
        elif tag == "nav":
            aria = a.get("aria-label", "")
            if "パンくず" in aria:
                self._in_bc_nav = True
                self._nav_buf = []
        if tag == "main":
            self._main_depth = 1
        elif self._main_depth and tag not in VOID:
            self._main_depth += 1
        if self._main_depth:
            self._main_buf.append(f"<{tag}>")

    # --- 終了タグ -------------------------------------------------
    def handle_endtag(self, tag):
        if tag == "head":
            self._in_head = False
        if tag == "title":
            self._in_title = False
        elif tag in {"h1", "h2", "h3", "h4", "h5", "h6"} and self._in_h is not None:
            self.headings.append((self._in_h, re.sub(r"\s+", " ", "".join(self._h_buf)).strip()))
            self._in_h = None
        elif tag == "a":
            text = re.sub(r"\s+", " ", "".join(self._a_buf)).strip()
            if self._a_href:
                self.links.append((self._a_href, text, self._a_attr))
            self._a_href = ""
            self._a_buf = []
        elif tag == "script":
            if self._in_ld:
                try:
                    self.jsonld.append(json.loads("".join(self._ld_buf)))
                except Exception:
                    self.jsonld.append({"_parse_error": True})
                self._in_ld = False
            elif not self._script_attr.startswith("src"):
                self.inline_script += len("".encode() if False else "".join(self._script_buf).encode())
            self._in_script = False
        elif tag == "style":
            self.inline_style += len("".join(self._style_buf).encode())
            self._in_style = False
        elif tag == "nav" and self._in_bc_nav:
            self._in_bc_nav = False
        if self._main_depth:
            self._main_buf.append(f"</{tag}>")
            self._main_depth -= 1
            if self._main_depth == 0:
                self.main_html = "".join(self._main_buf)

    def handle_data(self, data):
        if self._in_title:
            self.title += data
        if self._in_h is not None:
            self._h_buf.append(data)
        if self._in_ld:
            self._ld_buf.append(data)
        elif self._in_script:
            self._script_buf.append(data)
        elif self._in_style:
            self._style_buf.append(data)
        if self._a_href and not self._in_script and not self._in_style:
            self._a_buf.append(data)
        if self._in_bc_nav:
            self._nav_buf.append(data)

    # --- パンくず -------------------------------------------------
    def _parse_breadcrumb(self, html: str):
        for m in re.finditer(r"<li([^>]*)>(.*?)</li>", html, re.S):
            attr, inner = m.group(1), m.group(2)
            if "aria-hidden" in attr:      # 「/」などの区切り
                continue
            hm = re.search(r'<a[^>]*href="([^"]+)"', inner)
            name = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", inner)).strip()
            self.breadcrumb_html.append((name, hm.group(1) if hm else ""))


def route(p: Path) -> str:
    r = p.relative_to(PUBLIC).as_posix()
    if r == "index.html":
        return "/"
    if r.endswith("/index.html"):
        return "/" + r[:-10]
    return "/" + r


def flatten_ld(blocks) -> list[dict]:
    nodes: list[dict] = []
    for b in blocks:
        if not isinstance(b, dict):
            continue
        g = b.get("@graph")
        if isinstance(g, list):
            nodes.extend(n for n in g if isinstance(n, dict))
        else:
            nodes.append(b)
    return nodes


def visible_text(html: str) -> str:
    html = re.sub(r"<script.*?</script>", "", html, flags=re.S)
    html = re.sub(r"<style.*?</style>", "", html, flags=re.S)
    return re.sub(r"\s+", "", re.sub(r"<[^>]+>", "", html))


def num(text: str) -> set[int]:
    return {int(x.replace(",", "")) for x in re.findall(r"\d[\d,]{2,}", text)}


def png_size(path: Path) -> tuple[int, int] | None:
    try:
        head = path.read_bytes()[:26]
    except OSError:
        return None
    if head[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    return struct.unpack(">II", head[16:24])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--markdown", default=str(OUT_MD))
    ap.add_argument("--json", dest="json_path", default=str(OUT_JSON))
    ap.add_argument("--quiet", action="store_true")
    ap.add_argument("--label", default="", help="レポートに残す計測ラベル（Before/After）")
    args = ap.parse_args()

    pages: dict[str, PageParser] = {}
    raws: dict[str, str] = {}
    files: dict[str, Path] = {}
    for p in sorted(PUBLIC.rglob("*.html")):
        u = route(p)
        raw = p.read_text(encoding="utf-8")
        raws[u] = raw
        files[u] = p
        pages[u] = PageParser(raw)

    indexable = {u: pg for u, pg in pages.items()
                 if "noindex" not in pg.meta.get("robots", "").lower() and u != "/404.html"}
    guides = {u: pg for u, pg in indexable.items()
              if u.startswith("/study-guides/") and u != "/study-guides/"}
    today = date.today().isoformat()

    # sitemap
    sitemap_urls: dict[str, str] = {}
    sitemap_ok = (PUBLIC / "sitemap.xml").is_file()
    if sitemap_ok:
        try:
            tree = ET.parse(PUBLIC / "sitemap.xml")
            for url_el in tree.getroot().iter("{http://www.sitemaps.org/schemas/sitemap/0.9}url"):
                loc = url_el.find("{http://www.sitemaps.org/schemas/sitemap/0.9}loc")
                lm = url_el.find("{http://www.sitemaps.org/schemas/sitemap/0.9}lastmod")
                if loc is not None and loc.text:
                    sitemap_urls[loc.text.strip()] = (lm.text or "").strip() if lm is not None else ""
        except Exception:
            sitemap_ok = False

    # ローカル解決
    def resolve(href: str, origin: str) -> str | None:
        if not href or href.startswith(("mailto:", "tel:", "javascript:", "data:", "blob:", "#")):
            return None
        u = urlsplit(urljoin(SITE + origin, href))
        if u.netloc != "kurodaschool.jp":
            return None
        path = unquote(u.path)
        cand = path if path.endswith("/") else path + "/"
        if cand in pages:
            return cand
        if path in pages:
            return path
        return None

    checks: list[dict] = []

    def add(cat, cid, name, status, detail, samples=None, note=""):
        checks.append({"cat": cat, "id": cid, "name": name, "status": status,
                       "detail": detail, "samples": samples or [], "note": note})

    # 共通の素材
    heads = {}
    for u, pg in pages.items():
        h = pg.raw.split("</head>")[0]
        heads[u] = h

    # ============ A. 配信・表示速度 (101-110) ============
    third_party = collections.Counter()
    for u, pg in pages.items():
        for src, _ in pg.scripts:
            if src.startswith("http"):
                third_party[urlsplit(src).netloc] += 1
    no_pre = [u for u in indexable
              if not re.search(r'rel="(?:preconnect|dns-prefetch)"', heads[u])]
    add("Delivery", 101, "サードパーティ（GTM）への preconnect / dns-prefetch",
        "PASS" if not no_pre else "FAIL",
        f"未設定 {len(no_pre)}/{len(indexable)}ページ（外部ホスト: "
        + ", ".join(sorted(third_party)) + "）" if no_pre else "全ページで事前接続あり",
        no_pre[:5])

    home = pages.get("/")
    home_preload = bool(home and re.search(r'rel="preload"[^>]*as="image"', heads["/"]))
    hero = next((img for img in (home.imgs if home else []) if "fetchpriority" in img), None)
    add("Delivery", 102, "LCP画像の preload（トップのヒーロー画像）",
        "PASS" if home_preload else "FAIL",
        "preload あり" if home_preload else
        (f"preload なし（LCP候補: {hero.get('src', '不明')}）" if hero else "preload なし"),
        note="ヒーロー画像は fetchpriority=high でも、HTMLの解析後に発見されるため preload が効く")

    no_srcset = []
    for u, pg in pages.items():
        for img in pg.imgs:
            w = img.get("width", "")
            if w.isdigit() and int(w) >= 600 and not img.get("srcset"):
                no_srcset.append(f"{u} ({img.get('src','')} {w}px)")
    add("Delivery", 103, "大きい画像の srcset（モバイルへの過大配信を避ける）",
        "PASS" if not no_srcset else "WARN",
        f"srcset なし {len(no_srcset)}件", no_srcset[:5])

    css_bytes = {}
    for u, pg in pages.items():
        total = 0
        for href in pg.stylesheets:
            f = PUBLIC / unquote(href.split("?")[0]).lstrip("/")
            if f.is_file():
                total += f.stat().st_size
        css_bytes[u] = total
    heavy_css = [f"{u} ({b//1024}KB)" for u, b in css_bytes.items() if b > 70_000]
    add("Delivery", 104, "1ページの参照CSS合計 ≤ 70KB",
        "PASS" if not heavy_css else "WARN",
        f"超過 {len(heavy_css)}件（中央値 {sorted(css_bytes.values())[len(css_bytes)//2]//1024}KB）",
        heavy_css[:5])

    # スタイルシートのクラス定義が1つも使われていないページ＝丸ごと未使用のCSS
    def css_classes(path: Path) -> set[str]:
        css = path.read_text(encoding="utf-8")
        return set(re.findall(r"\.([A-Za-z][\w-]+)", css))

    sheet_cache: dict[str, tuple] = {}
    unused_sheets = collections.Counter()
    unused_pages = 0
    for u, pg in pages.items():
        used = {c for c in re.findall(r'class="([^"]*)"', pg.raw) for c in c.split()}
        dead = []
        for href in pg.stylesheets:
            f = PUBLIC / unquote(href.split("?")[0]).lstrip("/")
            if not f.is_file():
                continue
            key = f.as_posix()
            if key not in sheet_cache:
                css = f.read_text(encoding="utf-8")
                css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
                bare = [p.strip() for sel in re.findall(r"([^{}]+)\{", css) for p in sel.split(",")
                        if p.strip() and p.strip()[0] not in "@.:#["]
                class_only = all(b == "[hidden]" for b in bare)
                sheet_cache[key] = (set(re.findall(r"\.([A-Za-z][\w-]+)", css)), class_only)
            classes, class_only = sheet_cache[key]
            if class_only and classes and not (classes & used):
                dead.append(f.name)
        if dead:
            unused_pages += 1
            for d in dead:
                unused_sheets[d] += 1
    add("Delivery", 1051, "未使用スタイルシートを読み込まない（安全に外せるもの）",
        "PASS" if not unused_pages else "FAIL",
        f"未使用CSSのあるページ {unused_pages}/{len(pages)}（"
        + ", ".join(f"{n}×{c}ページ" for n, c in unused_sheets.most_common(3)) + "）",
        [f"{n}: {c}ページ" for n, c in unused_sheets.most_common(5)],
        note="クラス限定のCSSだけを対象にした。要素セレクタを含むCSSは、未使用クラスでも"
             "外すと崩れうるため対象外（conversion-r14・line-cro-r27 など）")

    heavy_style = [f"{u} ({pg.inline_style} bytes)" for u, pg in pages.items()
                   if pg.inline_style > 6_000]
    add("Delivery", 105, "インラインCSS ≤ 6KB/ページ",
        "PASS" if not heavy_style else "WARN",
        f"超過 {len(heavy_style)}件", heavy_style[:5])

    heavy_inline_js = [f"{u} ({pg.inline_script} bytes)" for u, pg in pages.items()
                       if pg.inline_script > 1_000]
    add("Delivery", 106, "インラインJS（JSON-LD以外）≤ 1KB/ページ",
        "PASS" if not heavy_inline_js else "WARN",
        f"超過 {len(heavy_inline_js)}件", heavy_inline_js[:5])

    headers_txt = (PUBLIC / "_headers").read_text(encoding="utf-8") if (PUBLIC / "_headers").is_file() else ""
    cache_rules = {}
    cur = None
    for line in headers_txt.splitlines():
        if line and not line.startswith((" ", "\t", "#")):
            cur = line.strip()
        elif cur and "Cache-Control" in line:
            cache_rules[cur] = line.split(":", 1)[1].strip()
    referenced: set[str] = set()
    for pg in pages.values():
        for ref in [h for h in pg.stylesheets] + [s for s, _ in pg.scripts] + [i.get("src", "") for i in pg.imgs]:
            if ref.startswith("/assets/") or ref.startswith("/images/"):
                referenced.add(ref.split("?")[0])
    import fnmatch
    def has_rule(ref: str) -> bool:
        if ref in cache_rules:
            return True
        return any(fnmatch.fnmatch(ref, pat) for pat in cache_rules)

    no_cache = sorted(r for r in referenced if not has_rule(r))
    add("Delivery", 107, "参照アセット全てに Cache-Control 規則",
        "PASS" if not no_cache else "FAIL",
        f"規則なし {len(no_cache)}件", no_cache[:5])

    hashed_revalidate = [r for r in sorted(referenced)
                         if re.search(r"-[0-9a-f]{12}\.(?:css|js)$", r)
                         and r in cache_rules and "immutable" not in cache_rules[r]]
    add("Delivery", 108, "ハッシュ付きCSS/JSは immutable キャッシュ",
        "PASS" if not hashed_revalidate else "WARN",
        f"immutable でない {len(hashed_revalidate)}件", hashed_revalidate[:5])

    blocking = []
    for u, pg in pages.items():
        for src, attr in pg.scripts:
            if src.startswith("http"):
                if "async" not in attr and "defer" not in attr:
                    blocking.append(f"{u} {src}")
    add("Delivery", 109, "レンダリングを止める外部JSがない（defer/async）",
        "PASS" if not blocking else "FAIL",
        f"ブロッキング {len(blocking)}件", blocking[:5])

    # モバイルで実際に落ちる量の見積り: 画像は srcset の最小版で数える。
    weight = []
    for u, pg in pages.items():
        total = len(pg.raw.encode())
        for ref in [h.split("?")[0] for h in pg.stylesheets] + [s.split("?")[0] for s, _ in pg.scripts]:
            f = PUBLIC / unquote(ref).lstrip("/")
            if ref.startswith("/") and f.is_file():
                total += f.stat().st_size
        for img in pg.imgs:
            best = None
            if img.get("srcset"):
                for cand in img["srcset"].split(","):
                    path, _, wdesc = cand.strip().partition(" ")
                    f = PUBLIC / unquote(path.split("?")[0]).lstrip("/")
                    if f.is_file():
                        size = f.stat().st_size
                        if best is None or size < best:
                            best = size
            if best is None:
                f = PUBLIC / unquote(img.get("src", "").split("?")[0]).lstrip("/")
                if f.is_file():
                    best = f.stat().st_size
            total += best or 0
        weight.append((total, u))
    over = [f"{u} ({b//1024}KB)" for b, u in weight if b > 220_000]
    add("Delivery", 110, "モバイルでの初期表示の総重量 ≤ 220KB（srcsetの最小版で見積り）",
        "PASS" if not over else "WARN",
        f"超過 {len(over)}件（最大 {max(weight)[0]//1024}KB / {max(weight)[1]}、"
        f"中央値 {sorted(w for w, _ in weight)[len(weight)//2]//1024}KB）", over[:5])

    # ============ B. クロール・インデックス (111-120) ============
    adj = collections.defaultdict(set)
    for u, pg in pages.items():
        for href, _t, _a in pg.links:
            tgt = resolve(href, u)
            if tgt and tgt != u and tgt in indexable:
                adj[u].add(tgt)
    depth = {"/": 0}
    frontier = ["/"]
    while frontier:
        nxt = []
        for u in frontier:
            for v in adj[u]:
                if v not in depth:
                    depth[v] = depth[u] + 1
                    nxt.append(v)
        frontier = nxt
    deep = sorted(f"{u} (depth {d})" for u, d in depth.items() if d > 3)
    unreached = sorted(set(indexable) - set(depth))
    add("Crawl", 111, "トップから3クリック以内に全ページ",
        "PASS" if not deep and not unreached else "WARN",
        f"4クリック以上 {len(deep)}件 / 到達不能 {len(unreached)}件 "
        f"（最大深度 {max(depth.values()) if depth else 0}）", (deep + unreached)[:5])

    bad_frag = []
    for u, pg in pages.items():
        ids = set(pg.ids)
        for href, _t, _a in pg.links:
            if "#" not in href or href.startswith(("mailto:", "tel:")):
                continue
            base, frag = href.split("#", 1)
            if not frag:
                continue
            tgt = resolve(base, u) if base else u
            if tgt != u:
                continue
            if frag not in ids:
                bad_frag.append(f"{u} -> #{frag}")
    add("Crawl", 112, "ページ内アンカー（#id）の到達性",
        "PASS" if not bad_frag else "WARN",
        f"行き先なし {len(bad_frag)}件", bad_frag[:5])

    og_url_bad = []
    for u, pg in indexable.items():
        c = pg.canonicals[0] if pg.canonicals else ""
        o = pg.meta.get("og:url", "")
        if c and o and c != o:
            og_url_bad.append(f"{u} ({o})")
    add("Crawl", 113, "canonical = og:url（厳密一致）",
        "PASS" if not og_url_bad else "FAIL",
        f"不一致 {len(og_url_bad)}件", og_url_bad[:5])

    canon_sitemap_bad = []
    for u, pg in indexable.items():
        c = pg.canonicals[0] if pg.canonicals else ""
        if c and sitemap_ok and c not in sitemap_urls:
            canon_sitemap_bad.append(f"{u} ({c})")
    add("Crawl", 114, "canonical が sitemap.xml の loc と一致",
        "PASS" if not canon_sitemap_bad else "FAIL",
        f"不一致 {len(canon_sitemap_bad)}件", canon_sitemap_bad[:5])

    lm_bad = []
    for u, pg in indexable.items():
        meta_lm = pg.meta.get("last-modified", "")
        sm_lm = sitemap_urls.get(SITE + u, "")
        lds = {n.get("dateModified") for n in flatten_ld(pg.jsonld) if n.get("dateModified")}
        if not meta_lm:
            lm_bad.append(f"{u} (last-modified なし)")
            continue
        if sm_lm and sm_lm != meta_lm:
            lm_bad.append(f"{u} (sitemap {sm_lm} / meta {meta_lm})")
        elif lds and meta_lm not in lds:
            lm_bad.append(f"{u} (JSON-LD {sorted(lds)} / meta {meta_lm})")
    add("Crawl", 115, "更新日の三重一致（last-modified・sitemap・dateModified）",
        "PASS" if not lm_bad else "FAIL",
        f"不一致 {len(lm_bad)}件", lm_bad[:5])

    bad_lm_format = [f"{u} ({v})" for u, v in sitemap_urls.items()
                     if v and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", v)] + \
                    [f"{u} (未来日 {v})" for u, v in sitemap_urls.items() if v > today]
    add("Crawl", 116, "sitemap の lastmod が ISO 形式・未来日なし",
        "PASS" if not bad_lm_format else "FAIL",
        f"不備 {len(bad_lm_format)}件", bad_lm_format[:5])

    noopener = []
    for u, pg in pages.items():
        for href, _t, attr in pg.links:
            if 'target="_blank"' in attr and "noopener" not in attr:
                noopener.append(f"{u} {href}")
    add("Crawl", 117, "target=_blank の外部リンクに rel=noopener",
        "PASS" if not noopener else "WARN",
        f"noopener なし {len(noopener)}件", noopener[:5])

    official = set()
    for pg in pages.values():
        for href, _t, _a in pg.links:
            host = urlsplit(href).netloc
            if host.endswith((".go.jp", ".ac.jp")):
                official.add(host)
    add("Crawl", 118, "公的・学術ドメイン（go.jp/ac.jp）への一次情報参照",
        "PASS" if len(official) >= 3 else "WARN",
        f"{len(official)}ドメイン: " + ", ".join(sorted(official)), sorted(official))

    p404 = pages.get("/404.html")
    noindex404 = bool(p404 and "noindex" in p404.meta.get("robots", "").lower())
    links404 = len([1 for href, _t, _a in (p404.links if p404 else []) if resolve(href, "/404.html")])
    add("Crawl", 119, "404ページの noindex と回遊リンク（20本以上）",
        "PASS" if noindex404 and links404 >= 20 else "WARN",
        f"noindex={'あり' if noindex404 else 'なし'} / 内部リンク {links404}本")

    in_main = collections.Counter()
    for u, pg in pages.items():
        if u not in indexable or not pg.main_html:
            continue
        body = re.sub(r'<nav[^>]*aria-label="パンくずリスト".*?</nav>', "", pg.main_html, flags=re.S)
        body = re.sub(r"<!-- r31:related-guides:start -->.*?<!-- r31:related-guides:end -->", "", body, flags=re.S)
        seen = set()
        for href in re.findall(r'<a[^>]*href="([^"]+)"', body):
            tgt = resolve(href, u)
            if tgt and tgt != u and tgt not in seen:
                seen.add(tgt)
                in_main[tgt] += 1
    weak_main = sorted(f"{u} ({in_main[u]})" for u in indexable if in_main[u] < 2)
    add("Crawl", 120, "本文（main）内からの被リンク2本以上（ナビ・フッター依存の解消）",
        "PASS" if not weak_main else "WARN",
        f"2本未満 {len(weak_main)}/{len(indexable)}", weak_main[:5])

    # ============ C. オンページ・コンテンツ (121-130) ============
    wide_title = [(display_width(pg.title), u, pg.title) for u, pg in indexable.items()
                  if display_width(pg.title) > 66]
    wide_title.sort(reverse=True)
    add("On-Page", 121, "title の表示幅 ≤ 66（SERPで切れない）",
        "PASS" if not wide_title else "WARN",
        f"66超 {len(wide_title)}件（最大 {wide_title[0][0] if wide_title else 0}）",
        [f"{u} ({w}) {t[:34]}" for w, u, t in wide_title[:5]])

    long_desc = [(len(pg.meta.get("description", "")), u) for u, pg in indexable.items()
                 if len(pg.meta.get("description", "")) > 120]
    long_desc.sort(reverse=True)
    add("On-Page", 122, "description ≤ 120字（読み切れる長さ）",
        "PASS" if not long_desc else "WARN",
        f"120字超 {len(long_desc)}件（最大 {long_desc[0][0] if long_desc else 0}字）",
        [f"{u} ({n}字)" for n, u in long_desc[:5]])

    h1_gap = []
    for u, pg in indexable.items():
        h1 = next((t for lv, t in pg.headings if lv == 1), "")
        head = pg.title.split("｜")[0]
        grams = {head[i:i + 3] for i in range(len(head) - 2)}
        if not h1:
            h1_gap.append(f"{u} (h1なし)")
        elif grams and not any(g in h1 for g in grams):
            h1_gap.append(f"{u} ({pg.title.split('｜')[0][:16]} / {h1[:16]})")
    add("On-Page", 123, "H1 が title の主題語（3文字n-gram）を含む",
        "PASS" if not h1_gap else "WARN",
        f"不一致 {len(h1_gap)}件", h1_gap[:5])

    dup_h2 = []
    for u, pg in indexable.items():
        c = collections.Counter(t for lv, t in pg.headings if lv == 2 and t)
        dup = [t for t, n in c.items() if n > 1]
        if dup:
            dup_h2.append(f"{u}: {dup[0][:24]}")
    add("On-Page", 124, "1ページ内で H2 が重複しない",
        "PASS" if not dup_h2 else "WARN",
        f"重複 {len(dup_h2)}件", dup_h2[:5])

    thin_guides = []
    for u, pg in guides.items():
        t = visible_text(pg.main_html or pg.raw)
        if len(t) < 3_000:
            thin_guides.append(f"{u} ({len(t)}字)")
    add("On-Page", 125, "学習ガイド本文 3,000字以上",
        "PASS" if not thin_guides else "WARN",
        f"不足 {len(thin_guides)}/{len(guides)}", thin_guides[:5])

    no_author_visible = []
    for u, pg in guides.items():
        text = visible_text(pg.raw)
        if "黒田清友" not in text or not re.search(r"更新日", text) or not re.search(r"公開日", text):
            no_author_visible.append(u)
    add("On-Page", 126, "ガイドに執筆者・公開日・更新日が画面上で読める（E-E-A-T）",
        "PASS" if not no_author_visible else "WARN",
        f"不足 {len(no_author_visible)}/{len(guides)}", no_author_visible[:5])

    SELF_DOMAINS = {"kurodaschool.jp", "lin.ee", "line.me", "kurodajuku.booth.pm"}
    no_source = []
    official_guides = []
    for u, pg in guides.items():
        ext = {urlsplit(h).netloc for h, _t, _a in pg.links
               if h.startswith("http") and urlsplit(h).netloc not in SELF_DOMAINS}
        if not ext:
            no_source.append(u)
        if any(d.endswith((".go.jp", ".ac.jp")) or d in ("www.dnc.ac.jp", "jnsas.jp")
               for d in ext):
            official_guides.append(u)
    add("On-Page", 127, "ガイドに外部の出典リンクがある",
        "PASS" if not no_source else "WARN",
        f"出典なし {len(no_source)}/{len(guides)}本", no_source[:5])
    add("On-Page", 1271, "公的・学術の一次情報を引くガイドが10本以上",
        "PASS" if len(official_guides) >= 10 else "WARN",
        f"公式参照あり {len(official_guides)}/{len(guides)}本", official_guides[:5])

    no_number = []
    for u in MONEY:
        pg = indexable.get(u)
        if not pg:
            continue
        if not re.search(r"\d", pg.meta.get("description", "")):
            no_number.append(u)
    add("On-Page", 128, "主要ページの説明文に具体数値（料金・分数・回数）",
        "PASS" if not no_number else "WARN",
        f"数値なし {len(no_number)}/{len(MONEY)}", no_number[:5])

    LISTING = {"/study-guides/", "/site-map/", "/area/", "/specialty/", "/materials/"}
    few_h2 = [f"{u} ({sum(1 for lv, _ in pg.headings if lv == 2)})" for u, pg in indexable.items()
              if sum(1 for lv, _ in pg.headings if lv == 2) < 5 and u not in LEGAL | LISTING]
    add("On-Page", 129, "本文の H2 が5つ以上（構造化された本文）",
        "PASS" if not few_h2 else "WARN",
        f"5未満 {len(few_h2)}件", few_h2[:5])

    long_p = []
    for u, pg in indexable.items():
        n = sum(1 for p in re.findall(r"<p[^>]*>(.*?)</p>", pg.main_html or "", re.S)
                if len(re.sub(r"<[^>]+>", "", p)) > 400)
        if n > 3:
            long_p.append(f"{u} ({n}段落)")
    add("On-Page", 130, "400字超の長段落が3つ以下（読みやすさ）",
        "PASS" if not long_p else "WARN",
        f"超過 {len(long_p)}件", long_p[:5])

    # ============ D. 構造化データ (131-140) ============
    bc_gap = []
    for u, pg in indexable.items():
        if not pg.breadcrumb_html:
            continue
        want = []
        for name, url in pg.breadcrumb_html:
            abs_url = urljoin(SITE + u, url) if url else (pg.canonicals[0] if pg.canonicals else SITE + u)
            want.append((name, abs_url))
        got = None
        for node in flatten_ld(pg.jsonld):
            if node.get("@type") == "BreadcrumbList":
                got = [(str(i.get("name", "")).strip(), i.get("item", ""))
                       for i in node.get("itemListElement", [])]
                break
        if got is None:
            bc_gap.append(f"{u} (JSON-LDなし)")
            continue
        if len(got) != len(want):
            bc_gap.append(f"{u} (画面{len(want)}件 / JSON-LD {len(got)}件)")
            continue
        for (n1, i1), (n2, i2) in zip(want, got):
            if re.sub(r"\s", "", n1) != re.sub(r"\s", "", n2):
                bc_gap.append(f"{u} ({n1} / {n2})")
                break
            if i1.rstrip("/") != (i2 or "").rstrip("/"):
                bc_gap.append(f"{u} ({i1} / {i2})")
                break
    add("Schema", 131, "パンくずの JSON-LD が画面の名称・URLと一致",
        "PASS" if not bc_gap else "FAIL",
        f"不一致 {len(bc_gap)}件", bc_gap[:5])

    dangling = []
    for u, pg in indexable.items():
        nodes = flatten_ld(pg.jsonld)
        ids = {n.get("@id") for n in nodes if n.get("@id")}
        text = json.dumps(nodes, ensure_ascii=False)
        for ref in set(re.findall(r'\{"@id":\s*"([^"]+)"\}', text)):
            if ref not in ids:
                dangling.append(f"{u} -> {ref}")
    add("Schema", 132, "JSON-LD の @id 参照が同一ページ内で解決する",
        "PASS" if not dangling else "FAIL",
        f"未解決 {len(dangling)}件", dangling[:5])

    dup_id = []
    for u, pg in indexable.items():
        ids = [n.get("@id") for n in flatten_ld(pg.jsonld) if n.get("@id")]
        d = [i for i, c in collections.Counter(ids).items() if c > 1]
        if d:
            dup_id.append(f"{u} ({d[0]})")
    add("Schema", 133, "JSON-LD の @id が重複しない",
        "PASS" if not dup_id else "WARN",
        f"重複 {len(dup_id)}件", dup_id[:5])

    hidden_faq = []
    for u, pg in indexable.items():
        text = visible_text(pg.raw)
        for node in flatten_ld(pg.jsonld):
            if node.get("@type") != "FAQPage":
                continue
            for item in node.get("mainEntity", []):
                q = re.sub(r"\s", "", item.get("name", ""))
                if q and q not in text:
                    hidden_faq.append(f"{u}: {item.get('name','')[:20]}")
    add("Schema", 134, "FAQPage の質問が画面上にも表示されている",
        "PASS" if not hidden_faq else "FAIL",
        f"非表示 {len(hidden_faq)}件", hidden_faq[:5])

    short_a = []
    for u, pg in indexable.items():
        for node in flatten_ld(pg.jsonld):
            if node.get("@type") != "FAQPage":
                continue
            for item in node.get("mainEntity", []):
                a = re.sub(r"\s", "", (item.get("acceptedAnswer") or {}).get("text", ""))
                if len(a) < 40:
                    short_a.append(f"{u} ({len(a)}字) {item.get('name','')[:16]}")
    short_a30 = [x for x in short_a if int(re.search(r"\((\d+)字\)", x).group(1)) < 30]
    add("Schema", 135, "FAQ回答が30字以上（AIが引用できる完結した文）",
        "PASS" if not short_a30 else "WARN",
        f"30字未満 {len(short_a30)}件（40字未満は {len(short_a)}件）", short_a30[:5])

    need_article = ("headline", "image", "author", "datePublished", "dateModified", "mainEntityOfPage")
    art_gap = []
    arts = 0
    for u, pg in indexable.items():
        for node in flatten_ld(pg.jsonld):
            if node.get("@type") not in ("Article", "BlogPosting", "NewsArticle"):
                continue
            arts += 1
            miss = [k for k in need_article if not node.get(k)]
            if miss:
                art_gap.append(f"{u} (欠: {','.join(miss)})")
    add("Schema", 136, "Article の必須6プロパティ",
        "PASS" if not art_gap else "FAIL",
        f"{arts}記事中 不足 {len(art_gap)}件", art_gap[:5])

    svc_gap = []
    services = 0
    for u, pg in indexable.items():
        for node in flatten_ld(pg.jsonld):
            if node.get("@type") != "Service":
                continue
            services += 1
            miss = [k for k in ("serviceType", "provider", "areaServed") if not node.get(k)]
            if miss:
                svc_gap.append(f"{u} (欠: {','.join(miss)})")
    add("Schema", 137, "Service に serviceType / provider / areaServed",
        "PASS" if not svc_gap else "WARN",
        f"{services}件中 不足 {len(svc_gap)}件", svc_gap[:5])

    course_gap = []
    courses = 0
    for u, pg in indexable.items():
        for node in flatten_ld(pg.jsonld):
            if node.get("@type") != "Course":
                continue
            courses += 1
            offers = (node.get("hasCourseInstance") or {}).get("offers") or node.get("offers") or {}
            if isinstance(offers, list):
                offers = offers[0] if offers else {}
            if not offers.get("price") or not offers.get("priceCurrency"):
                course_gap.append(f"{u} (offers欠)")
    add("Schema", 138, "Course の offers に price / priceCurrency",
        "PASS" if not course_gap else "WARN",
        f"{courses}件中 不足 {len(course_gap)}件", course_gap[:5])

    pricing_page = indexable.get("/pricing/")
    price_text = num(visible_text(pricing_page.raw)) if pricing_page else set()
    offer_prices = set()
    for u, pg in indexable.items():
        for node in flatten_ld(pg.jsonld):
            if node.get("@type") == "Offer" and node.get("price"):
                offer_prices.add(int(node["price"]))
            catalog = node.get("hasOfferCatalog") or {}
            for item in catalog.get("itemListElement", []) if isinstance(catalog, dict) else []:
                if isinstance(item, dict) and item.get("price"):
                    offer_prices.add(int(item["price"]))
    mismatch = sorted(p for p in offer_prices if p not in price_text and p not in PRICES)
    add("Schema", 139, "構造化データの料金が料金ページの本文と一致",
        "PASS" if not mismatch else "FAIL",
        f"Offer価格 {len(offer_prices)}種 / 本文にない額 {len(mismatch)}件", mismatch)

    no_ctx = []
    parse_err = []
    for u, pg in pages.items():
        for block in pg.jsonld:
            if isinstance(block, dict) and block.get("_parse_error"):
                parse_err.append(u)
                continue
            if isinstance(block, dict) and "@context" not in block:
                no_ctx.append(u)
    add("Schema", 140, "全JSON-LDがパースでき @context を持つ",
        "PASS" if not no_ctx and not parse_err else "FAIL",
        f"@context欠 {len(no_ctx)}件 / パース不能 {len(parse_err)}件",
        (parse_err + no_ctx)[:5])

    # ============ E. AIO (141-148) ============
    llms_txt = (PUBLIC / "llms.txt").read_text(encoding="utf-8") if (PUBLIC / "llms.txt").is_file() else ""
    link_lines = [x for x in llms_txt.splitlines() if re.search(r"\]\(https://kurodaschool\.jp", x)]
    no_desc = [x for x in link_lines if not re.search(r"\)\s*[:：]", x)]
    add("AIO", 141, "llms.txt の各リンク行に説明文",
        "PASS" if not no_desc else "WARN",
        f"{len(link_lines)}行中 説明なし {len(no_desc)}件", no_desc[:2])

    llms_full = (PUBLIC / "llms-full.txt").read_text(encoding="utf-8") if (PUBLIC / "llms-full.txt").is_file() else ""
    missing_full = sorted(u for u in indexable if (SITE + u) not in llms_full)
    add("AIO", 142, "llms-full.txt が全ページのURLを網羅",
        "PASS" if not missing_full else "WARN",
        f"未収録 {len(missing_full)}/{len(indexable)}", missing_full[:5])

    facts_path = PUBLIC / "facts.json"
    facts = json.loads(facts_path.read_text(encoding="utf-8")) if facts_path.is_file() else {}
    qa = facts.get("qa") or []
    bad_src = []
    for q in qa:
        src = (q.get("source") or "").replace(SITE, "")
        path = src.split("#")[0]
        cand = path if path.endswith("/") else path + "/"
        if not (cand in pages or path in pages or (PUBLIC / path.lstrip("/")).is_file()):
            bad_src.append(src)
    add("AIO", 143, "facts.json のQ&A 出典URLが実在ページ",
        "PASS" if qa and not bad_src else ("WARN" if not qa else "FAIL"),
        f"{len(qa)}問中 不達 {len(bad_src)}件", bad_src[:5])

    plan_prices = {int(p["price"]) for p in (facts.get("pricing") or {}).get("plans", []) if p.get("price")}
    plan_prices_all = plan_prices | {int(o["price"]) for o in (facts.get("pricing") or {}).get("options", []) if o.get("price")}
    facts_gap = sorted(p for p in plan_prices_all if p not in price_text)
    add("AIO", 144, "facts.json の料金が料金ページと一致",
        "PASS" if not facts_gap else "FAIL",
        f"facts {len(plan_prices_all)}件 / 料金ページにない額 {len(facts_gap)}件", facts_gap)

    md_gap = []
    for u, pg in indexable.items():
        md = files[u].with_suffix(".md")
        if not md.is_file():
            md_gap.append(f"{u} (.mdなし)")
            continue
        body = md.read_text(encoding="utf-8")
        h2_html = len([1 for lv, t in pg.headings if lv == 2 and "r27-cta" not in t])
        h2_html = len(re.findall(r"<h2(?![^>]*(?:r27-cta-title|r28-anx-title))[^>]*>", pg.raw))
        h2_md = len(re.findall(r"^## ", body, re.M))
        if abs(h2_html - h2_md) > 2:
            md_gap.append(f"{u} (h2 {h2_html} / md {h2_md})")
    add("AIO", 145, "全ページの .md があり見出し数が一致（±2）",
        "PASS" if not md_gap else "WARN",
        f"不備 {len(md_gap)}件", md_gap[:5])

    fm_gap = []
    for u, pg in indexable.items():
        md = files[u].with_suffix(".md")
        if not md.is_file():
            continue
        head = md.read_text(encoding="utf-8")[:400]
        if not all(k in head for k in ("title:", "description:", "updated:")):
            fm_gap.append(u)
    add("AIO", 146, ".md に title / description / updated のフロントマター",
        "PASS" if not fm_gap else "WARN",
        f"不足 {len(fm_gap)}件", fm_gap[:5])

    ct_gap = []
    for pattern, want in (("/*.md", "text/markdown"), ("/facts.json", "application/json"),
                          ("/llms-full.txt", "text/plain")):
        block = re.search(re.escape(pattern) + r"\n((?:\s+[^\n]+\n)+)", headers_txt)
        if not block or want not in block.group(1):
            ct_gap.append(pattern)
    add("AIO", 147, ".md・facts.json・llms-full.txt の Content-Type 明示",
        "PASS" if not ct_gap else "FAIL",
        f"未設定 {len(ct_gap)}件", ct_gap)

    md_count = sum(1 for u in indexable if files[u].with_suffix(".md").is_file())
    add("AIO", 148, "Markdown版のカバレッジ（全インデックス対象ページ）",
        "PASS" if md_count == len(indexable) else "WARN",
        f"{md_count}/{len(indexable)}ページ")

    # ============ F. モバイルUX・CRO (149-154) ============
    bad_vp = [u for u, pg in indexable.items()
              if "user-scalable=no" in pg.meta.get("viewport", "")
              or "maximum-scale=1.0" in pg.meta.get("viewport", "")]
    add("CRO", 149, "viewport でピンチズームを禁止していない",
        "PASS" if not bad_vp else "WARN",
        f"禁止 {len(bad_vp)}件", bad_vp[:5])

    css_all = "\n".join(p.read_text(encoding="utf-8") for p in sorted((PUBLIC / "assets").glob("*.css")))
    sticky_pad = "padding-bottom" in css_all and "r27-sticky" in css_all
    add("CRO", 150, "スマホ追従バーと本文の重なりを回避（bodyの下余白）",
        "PASS" if sticky_pad else "WARN",
        "body padding-bottom あり" if sticky_pad else "追従バー分の余白なし")

    tap_ok = len(re.findall(r"min-height:\s*(?:4[4-9]|[5-9]\d)px", css_all)) >= 5
    add("CRO", 151, "主要CTAのタップ領域44px以上（CSS）",
        "PASS" if tap_ok else "WARN",
        f"min-height 44px以上の宣言 {len(re.findall(r'min-height:\s*(?:4[4-9]|[5-9]\d)px', css_all))}件")

    pages_with_input = [u for u, pg in pages.items() if pg.inputs]
    loaded_css = set()
    for u in pages_with_input:
        for href in pages[u].stylesheets:
            f = PUBLIC / unquote(href.split("?")[0]).lstrip("/")
            if f.is_file():
                loaded_css.add(f)
    input_css = "\n".join(f.read_text(encoding="utf-8") for f in sorted(loaded_css))
    small_input = re.findall(r"(?:textarea|input|select)[^{}]*\{[^}]*font-size:\s*(\.\d+|\d)rem",
                             input_css)
    small_input = [s for s in small_input if float(s) < 1.0]
    add("CRO", 152, "入力欄のフォント16px以上（iOSの自動ズーム防止）",
        "PASS" if not small_input or not pages_with_input else "WARN",
        f"16px未満の指定 {len(small_input)}件（入力欄のあるページ {len(pages_with_input)}）",
        small_input[:3])

    many_nav = []
    for u, pg in indexable.items():
        m = re.search(r'<nav class="main-nav"[^>]*>(.*?)</nav>', pg.raw, re.S) or \
            re.search(r'<nav[^>]*aria-label="主要ページと指導案内"[^>]*>(.*?)</nav>', pg.raw, re.S)
        if m:
            n = len(re.findall(r"<a\s", m.group(1)))
            if n > 7:
                many_nav.append(f"{u} ({n})")
    add("CRO", 153, "ヘッダーの主要ナビが7項目以下",
        "PASS" if not many_nav else "WARN",
        f"7項目超 {len(many_nav)}件", many_nav[:5])

    late_cta = []
    for u in MONEY:
        pg = indexable.get(u)
        if not pg:
            continue
        body = pg.raw.split("</head>", 1)[-1]
        first = min([m.start() for m in re.finditer(r'href="(?:https://lin\.ee/|/contact/|https://line\.me/)', body)] or [10 ** 9])
        if first > 4_000:
            late_cta.append(f"{u} ({first}文字目)")
    add("CRO", 154, "主要ページのファーストビュー内にCTA",
        "PASS" if not late_cta else "WARN",
        f"4,000文字以降 {len(late_cta)}件", late_cta[:5])

    # ============ G. 品質・スパム耐性・a11y (155-160) ============
    hidden = []
    for u, pg in pages.items():
        if re.search(r"display:\s*none[^>]*>[^<]{40,}", pg.raw) or \
           "text-indent:-9999" in pg.raw or "color:#fff;background:#fff" in pg.raw:
            hidden.append(u)
    add("Quality", 155, "隠しテキスト・キーワード詰め込みがない",
        "PASS" if not hidden else "FAIL",
        f"疑い {len(hidden)}件", hidden[:5])

    spam_comment = []
    for u, pg in pages.items():
        for m in re.finditer(r"<!--(.*?)-->", pg.raw, re.S):
            c = m.group(1)
            if re.search(r"(検索エンジン|クローラ|LLM|AIに|ChatGPT|Gemini|必ず上位|ランキングを上げ)", c):
                spam_comment.append(f"{u}: {c[:32]}")
    add("Quality", 156, "HTMLコメントに検索/AI向けの指示がない",
        "PASS" if not spam_comment else "FAIL",
        f"疑い {len(spam_comment)}件", spam_comment[:3])

    bad_alt = []
    for u, pg in pages.items():
        for img in pg.imgs:
            alt = (img.get("alt") or "").strip()
            src = img.get("src", "")
            if alt and (len(alt) < 4 or alt in src or not re.search(r"[ぁ-んァ-ヶ一-龥A-Za-z]", alt)):
                bad_alt.append(f"{u}: {alt[:20]}")
    add("Quality", 157, "画像 alt が内容を説明している",
        "PASS" if not bad_alt else "WARN",
        f"不備 {len(bad_alt)}件", bad_alt[:5])

    no_th = [u for u, pg in pages.items() if pg.tables and "<th" not in pg.raw]
    add("Quality", 158, "表に th 見出しがある（読み上げ・構造理解）",
        "PASS" if not no_th else "WARN",
        f"th なし {len(no_th)}件", no_th[:5])

    ad_links = []
    for u, pg in pages.items():
        for href, _t, attr in pg.links:
            if any(d in href for d in ("amazon.co.jp", "rakuten.co.jp", "a8.net", "valuecommerce")):
                if "sponsored" not in attr and "nofollow" not in attr:
                    ad_links.append(f"{u} {href[:40]}")
    add("Quality", 159, "広告・アフィリエイトリンクに rel=sponsored",
        "PASS" if not ad_links else "WARN",
        f"rel なし {len(ad_links)}件", ad_links[:5])

    unbalanced = []
    for u, pg in pages.items():
        stack: list[str] = []
        svg = 0
        scan = re.sub(r"<script\b.*?</script>", "", pg.raw, flags=re.S)
        scan = re.sub(r"<style\b.*?</style>", "", scan, flags=re.S)
        for m in re.finditer(r"<(/?)([a-zA-Z0-9]+)([^>]*)>", scan):
            closing, tag, rest = m.group(1), m.group(2).lower(), m.group(3)
            if tag in ("svg",):
                svg += -1 if closing else 1
                continue
            if svg > 0 or tag in VOID or rest.rstrip().endswith("/"):
                continue
            if not closing:
                stack.append(tag)
            else:
                if tag in stack:
                    while stack and stack[-1] != tag:
                        stack.pop()
                    if stack:
                        stack.pop()
                else:
                    unbalanced.append(f"{u} (</{tag}> が余る)")
                    break
        if stack:
            unbalanced.append(f"{u} (未閉じ: {','.join(stack[:3])})")
    add("Quality", 160, "主要タグの開閉が揃っている",
        "PASS" if not unbalanced else "WARN",
        f"不備 {len(unbalanced)}件", unbalanced[:5])

    # ---- 集計 ----------------------------------------------------
    counts = collections.Counter(c["status"] for c in checks)
    cats = collections.defaultdict(collections.Counter)
    for c in checks:
        cats[c["cat"]][c["status"]] += 1
    report = {
        "label": args.label,
        "generated_at": today,
        "total_pages": len(pages),
        "indexable_pages": len(indexable),
        "total_checks": len(checks),
        "summary": dict(counts),
        "by_category": {k: dict(v) for k, v in cats.items()},
        "checks": checks,
    }
    Path(args.json_path).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    def priority(c):
        if c["status"] == "PASS":
            return "-"
        return "P0" if c["status"] == "FAIL" else "P1"

    lines = [
        "# 黒田塾 深掘りSEO/AIO診断（第11弾・新観点）",
        "",
        f"- 実行日: {today}" + (f" / 計測: {args.label}" if args.label else ""),
        f"- 対象: インデックス対象 {len(indexable)}ページ（総HTML {len(pages)}）",
        f"- 観点: {len(checks)}（既存82観点とは重複しない新観点。PASS "
        f"{counts['PASS']} / WARN {counts['WARN']} / FAIL {counts['FAIL']}）",
        "",
        "## カテゴリ別",
        "",
        "| カテゴリ | PASS | WARN | FAIL |",
        "| --- | --- | --- | --- |",
    ]
    for k in ["Delivery", "Crawl", "On-Page", "Schema", "AIO", "CRO", "Quality"]:
        c = cats[k]
        lines.append(f"| {k} | {c['PASS']} | {c['WARN']} | {c['FAIL']} |")
    lines.append("")
    for level, title in (("P0", "P0 — FAIL（検索・AI検索への流入に直結）"),
                         ("P1", "P1 — WARN（改善余地）")):
        rows = [c for c in checks if priority(c) == level]
        lines += [f"## {title}（{len(rows)}件）", ""]
        for c in rows:
            smp = "／".join(str(s) for s in c["samples"][:3])
            lines.append(f"- **#{c['id']} [{c['cat']}] {c['name']}** — {c['detail']}"
                         + (f"（例: {smp}）" if smp else ""))
        lines.append("")
    lines += ["## 全項目", "", "| # | 分類 | 観点 | 判定 | 詳細 |", "| --- | --- | --- | --- | --- |"]
    for c in checks:
        lines.append(f"| {c['id']} | {c['cat']} | {c['name']} | {c['status']} | "
                     f"{str(c['detail']).replace('|', '／')} |")
    lines.append("")
    Path(args.markdown).write_text("\n".join(lines) + "\n", encoding="utf-8")

    print("=== 深掘りSEO/AIO診断（第11弾・新観点） ===")
    print(f"対象: {len(indexable)}ページ / 観点: {len(checks)}"
          + (f" / 計測: {args.label}" if args.label else ""))
    print(f"PASS {counts['PASS']} / WARN {counts['WARN']} / FAIL {counts['FAIL']}")
    if not args.quiet:
        for c in checks:
            if c["status"] != "PASS":
                smp = f" 例: {', '.join(str(s) for s in c['samples'][:3])}" if c["samples"] else ""
                print(f"[{c['status']}] #{c['id']:03d} [{c['cat']}] {c['name']}: {c['detail']}{smp}")
    print(f"\nwrote {args.json_path} / {args.markdown}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
