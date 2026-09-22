#!/usr/bin/env python3
"""ほんごうねむり 公式サイトのビルド。

``site.json`` の内容を静的HTMLに起こして ``public/`` に書き出します。
テンプレートエンジンは使いません（デプロイを pip に依存させないため、
標準ライブラリだけで動きます）。

    python3 build.py           # 生成する
    python3 build.py --check   # 生成して、検査に落ちたら異常終了する

``--check`` はデプロイ側でも実行します。壊れたページが本番に出ないように、
canonical・OGP・内部リンク・見出しの数などをここで止めます。
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import shutil
import sys
from datetime import date, datetime
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PUBLIC = ROOT / "public"
ASSETS_SRC = ROOT / "assets"

DATA = json.loads((ROOT / "site.json").read_text(encoding="utf-8"))
SITE = DATA["site"]
TALENT = DATA["talent"]
HOST = SITE["host"].rstrip("/")

# 日本語のタイトルは全角で数えます。Googleがモバイルの検索結果でタイトルを
# 切るのが概ね全角30文字前後なので、その内側に収まる範囲にしています。
TITLE_MIN, TITLE_MAX = 10, 40
DESC_MIN, DESC_MAX = 60, 130

BUILT_ON = date.today().isoformat()

# シェアカードは写真的な絵なので JPEG。PNGだと1枚260KBになります。
OG_EXT = "jpg"

# --------------------------------------------------------------------------- #
# アセット（内容ハッシュつきのファイル名にして、1年キャッシュさせる）
# --------------------------------------------------------------------------- #
_ASSET_MAP: dict[str, str] = {}


def build_assets() -> None:
    """``assets/`` を ``public/assets/`` へ、名前にハッシュを足して写す。"""
    out = PUBLIC / "assets"
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)

    # CSS は中の {{asset:...}} を先に解決する必要があるので後回しにします。
    files = sorted(p for p in ASSETS_SRC.rglob("*") if p.is_file())
    deferred = [p for p in files if p.suffix in {".css", ".js"}]

    for path in files:
        if path in deferred:
            continue
        _emit_asset(path, path.read_bytes(), out)

    for path in deferred:
        body = substitute(path.read_text(encoding="utf-8"))
        _emit_asset(path, body.encode("utf-8"), out)


def _emit_asset(path: Path, body: bytes, out: Path) -> None:
    rel = path.relative_to(ASSETS_SRC).as_posix()
    digest = hashlib.sha256(body).hexdigest()[:12]
    stem, _, ext = rel.rpartition(".")
    hashed = f"{stem}-{digest}.{ext}"
    target = out / hashed
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(body)
    _ASSET_MAP[rel] = f"/assets/{hashed}"


def substitute(text: str) -> str:
    """``{{asset:site.css}}`` のような印を、実際のURLへ置き換える。"""

    def repl(match: re.Match[str]) -> str:
        key = match.group(1)
        if key not in _ASSET_MAP:
            raise SystemExit(f"アセットが見つかりません: {key}")
        return _ASSET_MAP[key]

    return re.sub(r"\{\{asset:([^}]+)\}\}", repl, text)


# --------------------------------------------------------------------------- #
# 小さな道具
# --------------------------------------------------------------------------- #
def e(value) -> str:
    """HTMLとして安全にする。None は空文字。"""
    return html.escape(str(value), quote=True) if value is not None else ""


def tbd(value, placeholder: str = "近日公開") -> str:
    """未記入の項目を、それと分かる形で出す。嘘の値では埋めません。"""
    if value in (None, "", []):
        return f'<span class="tbd">{e(placeholder)}</span>'
    return e(value)


def jp_datetime(iso: str | None) -> str | None:
    """``2026-10-04T21:00`` → ``2026年10月4日(土) 21:00``。"""
    if not iso:
        return None
    try:
        dt = datetime.fromisoformat(iso)
    except ValueError:
        return iso
    wd = "月火水木金土日"[dt.weekday()]
    stamp = f"{dt.year}年{dt.month}月{dt.day}日({wd})"
    if dt.hour or dt.minute:
        stamp += f" {dt.hour:02d}:{dt.minute:02d}"
    return stamp


def jp_date(iso: str | None) -> str | None:
    if not iso:
        return None
    try:
        d = date.fromisoformat(iso)
    except ValueError:
        return iso
    return f"{d.year}年{d.month}月{d.day}日"


# --------------------------------------------------------------------------- #
# アイコン（外部ファイルにせず埋め込む。数が少ないので往復のほうが高くつく）
# --------------------------------------------------------------------------- #
STROKE = 'fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"'

ICONS = {
    "desk": f'<path {STROKE} d="M4 5.5h6.5a2 2 0 0 1 2 2V19a1.6 1.6 0 0 0-1.6-1.6H4zm16.5 0H14a2 2 0 0 0-2 2V19a1.6 1.6 0 0 1 1.6-1.6h6.9z"/>',
    "moon": f'<path {STROKE} d="M20 13.4A8.2 8.2 0 1 1 10.6 4a6.6 6.6 0 0 0 9.4 9.4"/><path {STROKE} d="M17 3.2v3M15.5 4.7h3"/>',
    "pencil": f'<path {STROKE} d="m14.8 4.6 4.6 4.6M4 20l1.1-4.2L15.6 5.3a1.8 1.8 0 0 1 2.6 0l.5.5a1.8 1.8 0 0 1 0 2.6L8.2 18.9z"/>',
    "game": f'<path {STROKE} d="M7.5 7.5h9a4.5 4.5 0 0 1 4.4 3.6l.8 4a3.3 3.3 0 0 1-6 2.4l-.9-1.3H9.2l-.9 1.3a3.3 3.3 0 0 1-6-2.4l.8-4a4.5 4.5 0 0 1 4.4-3.6Z"/><path {STROKE} d="M7 11v2.4M5.8 12.2h2.4M15.5 11.4h.01M17.7 13.2h.01"/>',
    "clock": f'<circle {STROKE} cx="12" cy="12" r="8.4"/><path {STROKE} d="M12 7.4V12l3 1.8"/>',
    "star": f'<path {STROKE} d="m12 3.8 2.6 5.3 5.8.8-4.2 4.1 1 5.8-5.2-2.7-5.2 2.7 1-5.8L3.6 9.9l5.8-.8z"/>',
    "mail": f'<rect {STROKE} x="3" y="5.5" width="18" height="13" rx="2.2"/><path {STROKE} d="m3.6 7 7.3 5.2a2 2 0 0 0 2.2 0L20.4 7"/>',
    "x": '<path fill="currentColor" d="M17.3 3h3.3l-7.2 8.2L21.7 21h-6.3l-4.6-6-5.3 6H2.2l7.7-8.8L2.4 3h6.5l4.2 5.5Zm-1.2 16.1h1.8L7.7 4.8H5.8Z"/>',
    "youtube": '<path fill="currentColor" d="M21.6 7.2a2.5 2.5 0 0 0-1.8-1.8C18.2 5 12 5 12 5s-6.2 0-7.8.4A2.5 2.5 0 0 0 2.4 7.2 26 26 0 0 0 2 12a26 26 0 0 0 .4 4.8 2.5 2.5 0 0 0 1.8 1.8C5.8 19 12 19 12 19s6.2 0 7.8-.4a2.5 2.5 0 0 0 1.8-1.8A26 26 0 0 0 22 12a26 26 0 0 0-.4-4.8ZM10 15.2V8.8l5.2 3.2Z"/>',
    "chat": f'<path {STROKE} d="M20.5 12.6c0 3.9-3.8 7-8.5 7a10 10 0 0 1-2.6-.3l-4.9 1.4 1.5-3.8a6.5 6.5 0 0 1-2-4.3c0-3.9 3.8-7 8-7s8.5 3.1 8.5 7Z"/>',
    "bag": f'<path {STROKE} d="M5.6 8h12.8l1 11.2a1.8 1.8 0 0 1-1.8 2H6.4a1.8 1.8 0 0 1-1.8-2z"/><path {STROKE} d="M8.8 10V6.9a3.2 3.2 0 0 1 6.4 0V10"/>',
    "external": f'<path {STROKE} d="M13.5 4.5H19.5V10.5M19.5 4.5 11 13M18 14.4v4.1a1.6 1.6 0 0 1-1.6 1.6H5.6A1.6 1.6 0 0 1 4 18.5V7.7a1.6 1.6 0 0 1 1.6-1.6h4.1"/>',
}

LINK_ICONS = {"x": "x", "youtube": "youtube", "marshmallow": "chat", "booth": "bag"}


def icon(name: str, cls: str = "") -> str:
    body = ICONS[name]
    attr = f' class="{e(cls)}"' if cls else ""
    return f'<svg{attr} viewBox="0 0 24 24" aria-hidden="true" focusable="false">{body}</svg>'


# --------------------------------------------------------------------------- #
# ページ共通のつくり
# --------------------------------------------------------------------------- #
NAV = [
    ("/profile/", "プロフィール"),
    ("/schedule/", "スケジュール"),
    ("/guidelines/", "ガイドライン"),
    ("/contact/", "お問い合わせ"),
]

FOOTER_LINKS = [
    ("/", "トップ"),
    ("/profile/", "プロフィール"),
    ("/schedule/", "配信スケジュール"),
    ("/guidelines/", "二次創作ガイドライン"),
    ("/contact/", "お問い合わせ"),
]

GOOGLE_FONTS = (
    "https://fonts.googleapis.com/css2"
    "?family=M+PLUS+Rounded+1c:wght@700;800"
    "&family=Zen+Kaku+Gothic+New:wght@400;500;700"
    "&family=Outfit:wght@500;600;700"
    "&display=swap"
)


def role_without_vtuber() -> str:
    """ヒーローのバッジ用。丸いラベルが「VTUBER」なので、肩書き側の重複を落とす。"""
    return re.sub(r"\s*VTuber$", "", TALENT["role"])


def primary_link(link_id: str) -> dict | None:
    for link in DATA["links"]:
        if link["id"] == link_id:
            return link
    return None


X_URL = (primary_link("x") or {}).get("url") or HOST
YT_URL = (primary_link("youtube") or {}).get("url")


def person_schema() -> dict:
    same_as = [l["url"] for l in DATA["links"] if l.get("url")]
    node = {
        "@type": "Person",
        "@id": f"{HOST}/#nemuri",
        "name": TALENT["name"],
        "alternateName": TALENT["name_latin"],
        "url": f"{HOST}/",
        "image": f"{HOST}/og/index.{OG_EXT}",
        "description": TALENT["lead"],
        "jobTitle": "VTuber",
        "knowsLanguage": "ja",
    }
    if same_as:
        node["sameAs"] = same_as
    return node


def website_schema() -> dict:
    return {
        "@type": "WebSite",
        "@id": f"{HOST}/#website",
        "url": f"{HOST}/",
        "name": SITE["name"],
        "inLanguage": "ja",
        "publisher": {"@id": f"{HOST}/#nemuri"},
    }


def breadcrumb_schema(trail: list[tuple[str, str]]) -> dict:
    return {
        "@type": "BreadcrumbList",
        "itemListElement": [
            {
                "@type": "ListItem",
                "position": i,
                "name": name,
                "item": f"{HOST}{path}",
            }
            for i, (path, name) in enumerate(trail, start=1)
        ],
    }


def render_head(page) -> str:
    url = f"{HOST}{page.path}"
    graph = [website_schema(), person_schema()] + page.schema
    jsonld = json.dumps(
        {"@context": "https://schema.org", "@graph": graph},
        ensure_ascii=False,
        separators=(",", ":"),
    )
    robots = "noindex, follow" if page.noindex else "index, follow, max-image-preview:large"
    canonical = "" if page.noindex else f'\n  <link rel="canonical" href="{e(url)}">'

    return f"""  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{e(page.title)}</title>
  <meta name="description" content="{e(page.description)}">
  <meta name="robots" content="{robots}">{canonical}
  <meta name="theme-color" content="#05091c">
  <meta name="format-detection" content="telephone=no">

  <meta property="og:type" content="{e(page.og_type)}">
  <meta property="og:site_name" content="{e(SITE['short_name'])}">
  <meta property="og:locale" content="{e(SITE['locale'])}">
  <meta property="og:url" content="{e(url)}">
  <meta property="og:title" content="{e(page.title)}">
  <meta property="og:description" content="{e(page.description)}">
  <meta property="og:image" content="{e(HOST)}/og/{e(page.og_name)}.{OG_EXT}">
  <meta property="og:image:type" content="image/jpeg">
  <meta property="og:image:width" content="1200">
  <meta property="og:image:height" content="630">
  <meta property="og:image:alt" content="{e(page.og_alt)}">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:site" content="@hongounemuri">
  <meta name="twitter:creator" content="@hongounemuri">

  <link rel="icon" href="{{{{asset:img/favicon.png}}}}" sizes="32x32">
  <link rel="apple-touch-icon" href="{{{{asset:img/icon-180.png}}}}">
  <link rel="manifest" href="/site.webmanifest">

  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link rel="stylesheet" href="{e(GOOGLE_FONTS)}">
  <link rel="stylesheet" href="{{{{asset:site.css}}}}">

  <script type="application/ld+json">{jsonld}</script>"""


def render_header(current: str) -> str:
    items = []
    for path, label in NAV:
        aria = ' aria-current="page"' if path == current else ""
        items.append(f'<li><a class="nav__link" href="{path}"{aria}>{e(label)}</a></li>')
    home = ' aria-current="page"' if current == "/" else ""

    return f"""<header class="site-header">
  <div class="site-header__inner">
    <a class="brand" href="/"{home}>
      <img class="brand__mark" src="{{{{asset:img/avatar-240.webp}}}}" width="38" height="38" alt="" aria-hidden="true" loading="eager" decoding="async">
      <span>
        <span class="brand__name">{e(TALENT['name'])}</span>
        <span class="brand__sub">{e(TALENT['name_latin'])}</span>
      </span>
    </a>
    <button class="nav-toggle" type="button" aria-expanded="false" aria-controls="site-nav">
      <span class="nav-toggle__bar"></span>
      <span class="visually-hidden">メニューを開く</span>
    </button>
    <nav class="nav" id="site-nav" aria-label="サイト内のページ">
      <ul class="nav__list">
        {chr(10).join('        ' + i for i in items).strip()}
      </ul>
      <a class="nav__cta" href="{e(X_URL)}" rel="me noopener" target="_blank">Xをフォロー</a>
    </nav>
  </div>
</header>"""


def render_footer() -> str:
    links = "".join(
        f'<li><a href="{path}">{e(label)}</a></li>' for path, label in FOOTER_LINKS
    )
    socials = "".join(
        f'<li><a href="{e(l["url"])}" rel="noopener" target="_blank">{e(l["label"])}</a></li>'
        for l in DATA["links"]
        if l.get("url")
    )
    year = SITE["copyright_from"]
    now = date.today().year
    span = str(year) if now <= year else f"{year}-{now}"

    return f"""<footer class="site-footer">
  <div class="wrap">
    <div class="site-footer__top">
      <div>
        <p class="site-footer__title">{e(TALENT['name'])}</p>
        <p class="site-footer__about">{e(TALENT['catch'])}<br>{e(TALENT['role'])}。</p>
      </div>
      <div>
        <p class="site-footer__title">SITE</p>
        <ul class="site-footer__list">{links}</ul>
      </div>
      <div>
        <p class="site-footer__title">SOCIAL</p>
        <ul class="site-footer__list">{socials}</ul>
      </div>
    </div>
    <div class="site-footer__bottom">
      <p>&copy; {span} {e(TALENT['name'])}</p>
      <p>このサイトの文章・画像の無断転載を禁じます。</p>
    </div>
  </div>
</footer>"""


def render_crumbs(trail: list[tuple[str, str]]) -> str:
    items = []
    for i, (path, name) in enumerate(trail):
        last = i == len(trail) - 1
        inner = e(name) if last else f'<a href="{path}">{e(name)}</a>'
        items.append(f"<li>{inner}</li>")
    return f"""<nav class="crumbs wrap" aria-label="パンくずリスト">
  <ol>{''.join(items)}</ol>
</nav>"""


class Page:
    """1ページ分の材料。body は <main> の中身。"""

    def __init__(
        self,
        path: str,
        title: str,
        description: str,
        body: str,
        *,
        og_name: str,
        og_alt: str,
        og_type: str = "website",
        schema: list | None = None,
        trail: list[tuple[str, str]] | None = None,
        noindex: bool = False,
        priority: str = "0.6",
    ) -> None:
        self.path = path
        self.title = title
        self.description = description
        self.body = body
        self.og_name = og_name
        self.og_alt = og_alt
        self.og_type = og_type
        self.trail = trail or []
        self.noindex = noindex
        self.priority = priority
        self.schema = list(schema or [])
        if self.trail:
            self.schema.append(breadcrumb_schema(self.trail))

    def render(self) -> str:
        crumbs = render_crumbs(self.trail) if self.trail else ""
        return f"""<!doctype html>
<html lang="ja" class="no-js">
<head>
{render_head(self)}
</head>
<body>
  <a class="skip-link" href="#main">本文へスキップ</a>
  <div class="sky" aria-hidden="true"><div class="sky__stars"></div></div>
{render_header(self.path)}
{crumbs}
  <main id="main">
{self.body}
  </main>
{render_footer()}
  <script src="{{{{asset:site.js}}}}" defer></script>
</body>
</html>
"""

    @property
    def out_path(self) -> Path:
        if self.path.endswith(".html"):
            return PUBLIC / self.path.lstrip("/")
        return PUBLIC / self.path.strip("/") / "index.html"


# --------------------------------------------------------------------------- #
# 部品
# --------------------------------------------------------------------------- #
def section_head(kicker: str, title: str, lead: str = "", center: bool = False) -> str:
    cls = "head head--center" if center else "head"
    lead_html = f'<p class="head__lead">{e(lead)}</p>' if lead else ""
    return f"""<div class="{cls}" data-reveal>
        <p class="head__kicker">{e(kicker)}</p>
        <h2 class="head__title">{e(title)}</h2>
        {lead_html}
      </div>"""


def portrait_picture(cls: str, sizes: str, *, eager: bool = False) -> str:
    load = 'loading="eager" fetchpriority="high"' if eager else 'loading="lazy"'
    return (
        f'<img class="{e(cls)}" src="{{{{asset:img/portrait-640.webp}}}}" '
        f'srcset="{{{{asset:img/portrait-420.webp}}}} 420w, '
        f'{{{{asset:img/portrait-640.webp}}}} 640w, '
        f'{{{{asset:img/portrait-900.webp}}}} 900w" sizes="{e(sizes)}" '
        f'width="640" height="985" decoding="async" {load} '
        f'alt="{e(TALENT["name"])}の立ち絵。水色とピンクのグラデーションの髪に、'
        f'マゼンタのゴーグルを頭にのせている。">'
    )


def link_cards() -> str:
    cards = []
    for link in DATA["links"]:
        name = LINK_ICONS.get(link["id"], "external")
        note = link.get("note") or ""
        handle = link.get("handle")
        sub = f"{note}{'・' + handle if handle else ''}"
        if link.get("url"):
            cards.append(
                f'<li><a class="link-card" href="{e(link["url"])}" rel="noopener" target="_blank">'
                f'{icon(name, "link-card__icon")}'
                f'<span><span class="link-card__label">{e(link["label"])}</span>'
                f'<span class="link-card__note">{e(sub)}</span></span></a></li>'
            )
        else:
            cards.append(
                f'<li><span class="link-card link-card--soon" aria-disabled="true">'
                f'{icon(name, "link-card__icon")}'
                f'<span><span class="link-card__label">{e(link["label"])}</span>'
                f'<span class="link-card__note">{e(note)}</span></span></span></li>'
            )
    return f'<ul class="links" data-reveal>{"".join(cards)}</ul>'


# --------------------------------------------------------------------------- #
# トップページ
# --------------------------------------------------------------------------- #
def page_index() -> Page:
    h = DATA["highlight"]
    when = jp_datetime(h.get("datetime"))
    when_html = (
        f'<p class="highlight__meta">{icon("clock")}{e(when)}</p>'
        if when
        else f'<p class="highlight__meta">{icon("clock")}日時は近日お知らせします</p>'
    )
    if h.get("url"):
        watch = f'<a class="btn btn--primary" href="{e(h["url"])}" rel="noopener" target="_blank">配信ページへ{icon("external")}</a>'
    else:
        watch = '<span class="btn btn--primary" aria-disabled="true">配信ページ準備中</span>'

    news = "".join(
        f'<li class="news__item"><time class="news__date" datetime="{e(n["date"])}">'
        f'{e(jp_date(n["date"]))}</time>'
        f'<span class="news__tag">{e(n["tag"])}</span>'
        f'<span class="news__text">{e(n["text"])}</span></li>'
        for n in DATA["news"]
    )

    contents = "".join(
        f'<article class="card card--hover" data-reveal data-reveal-delay="{i * 90}">'
        f'{icon(c["icon"], "content-card__icon")}'
        f'<p class="content-card__sub">{e(c["subtitle"])}</p>'
        f'<h3 class="content-card__title">{e(c["title"])}</h3>'
        f'<p class="content-card__text">{e(c["text"])}</p></article>'
        for i, c in enumerate(DATA["contents"])
    )

    intro = "".join(f"<p>{e(p)}</p>" for p in TALENT["intro"][:2])

    return Page(
        "/",
        f"{TALENT['name']}｜{TALENT['role']} 公式サイト",
        f"{TALENT['catch']}｜{TALENT['role']}・{TALENT['name']}の公式サイトです。"
        "配信スケジュール、プロフィール、二次創作ガイドライン、お仕事のご依頼はこちらから。",
        f"""    <section class="hero">
      <img class="hero__glow" src="{{{{asset:img/hero-glow.webp}}}}" width="1280" height="720" alt="" aria-hidden="true" decoding="async">
      <div class="wrap hero__inner">
        <div>
          <p class="hero__badge"><span>VTUBER</span>{e(role_without_vtuber())}</p>
          <h1 class="hero__name neon">{e(TALENT['name'])}</h1>
          <p class="hero__latin">{e(TALENT['name_latin'])}</p>
          <p class="hero__catch">{e(TALENT['catch'])}</p>
          <p class="hero__lead">{e(TALENT['lead'])}</p>
          <div class="hero__actions">
            <a class="btn btn--primary" href="{e(X_URL)}" rel="me noopener" target="_blank">{icon('x')}Xをフォロー</a>
            <a class="btn btn--ghost" href="/profile/">プロフィールを見る</a>
          </div>
        </div>
        <div class="hero__figure">
          <p class="hero__zzz" aria-hidden="true">z z Z</p>
          {portrait_picture("hero__portrait", "(max-width: 880px) 74vw, 420px", eager=True)}
        </div>
      </div>
    </section>

    <section class="section" aria-labelledby="highlight-title">
      <div class="wrap">
        <div class="card highlight" data-reveal>
          <div class="highlight__grid">
            <div class="highlight__media">
              <img src="{{{{asset:img/keyvisual-1200.webp}}}}"
                   srcset="{{{{asset:img/keyvisual-800.webp}}}} 800w, {{{{asset:img/keyvisual-1200.webp}}}} 1200w, {{{{asset:img/keyvisual-1600.webp}}}} 1600w"
                   sizes="(max-width: 820px) 100vw, 55vw"
                   width="1200" height="675" loading="lazy" decoding="async"
                   alt="初配信の告知イラスト。頬づえをついた{e(TALENT['name'])}と、「バーチャル東京大学卒 初配信」の文字。">
            </div>
            <div class="highlight__body">
              <p class="highlight__badge">{e(h['badge'])}</p>
              <h2 class="highlight__title" id="highlight-title">{e(h['title'])}</h2>
              <p class="highlight__subtitle">{e(h['subtitle'])}</p>
              {when_html}
              <p class="highlight__text">{e(h['body'])}</p>
              <div class="hero__actions">{watch}</div>
            </div>
          </div>
        </div>
      </div>
    </section>

    <section class="section" aria-labelledby="news-title">
      <div class="wrap">
        <div class="head" data-reveal>
          <p class="head__kicker">News</p>
          <h2 class="head__title" id="news-title">お知らせ</h2>
        </div>
        <ul class="news" data-reveal>{news}</ul>
      </div>
    </section>

    <section class="section" aria-labelledby="about-title">
      <div class="wrap">
        <div class="head" data-reveal>
          <p class="head__kicker">About</p>
          <h2 class="head__title" id="about-title">どんな人か</h2>
        </div>
        <div class="card" data-reveal>
          <div class="prose">{intro}</div>
          <p style="margin-top:1.6em"><a class="btn btn--ghost" href="/profile/">くわしいプロフィールへ</a></p>
        </div>
      </div>
    </section>

    <section class="section" aria-labelledby="contents-title">
      <div class="wrap">
        <div class="head" data-reveal>
          <p class="head__kicker">Contents</p>
          <h2 class="head__title" id="contents-title">やっていること</h2>
          <p class="head__lead">配信の中身はだいたいこの4つです。時間の目安は配信スケジュールにまとめています。</p>
        </div>
        <div class="grid grid--4">{contents}</div>
      </div>
    </section>

    <section class="section" aria-labelledby="links-title">
      <div class="wrap">
        <div class="head" data-reveal>
          <p class="head__kicker">Links</p>
          <h2 class="head__title" id="links-title">リンク</h2>
        </div>
        {link_cards()}
      </div>
    </section>

    <section class="section">
      <div class="wrap">
        <div class="cta" data-reveal>
          <h2 class="cta__title neon">夜、ひまだったら</h2>
          <p class="cta__text">配信の予定はXでお知らせします。勉強のおともにも、眠れない夜にもどうぞ。</p>
          <div class="cta__actions">
            <a class="btn btn--primary" href="{e(X_URL)}" rel="me noopener" target="_blank">{icon('x')}Xをフォロー</a>
            <a class="btn btn--ghost" href="/schedule/">配信スケジュール</a>
          </div>
        </div>
      </div>
    </section>""",
        og_name="index",
        og_alt=f"{TALENT['name']}公式サイトのシェアカード",
        schema=[],
        priority="1.0",
    )


# --------------------------------------------------------------------------- #
# プロフィール
# --------------------------------------------------------------------------- #
def page_profile() -> Page:
    rows = [
        ("名前", e(TALENT["name"]), f'{TALENT["name_latin"]} と書きます'),
        ("肩書き", e(TALENT["role"]), "「バーチャル東京大学」は設定上の出身校です"),
        ("誕生日", tbd(TALENT["birthday"]), ""),
        ("身長", tbd(TALENT["height"]), ""),
        ("初配信", tbd(jp_date(TALENT["debut_date"]), "日程が決まりしだいお知らせします"), ""),
        ("ファンネーム", tbd(TALENT["fan_name"]), ""),
        ("推しマーク", tbd(TALENT["oshi_mark"]), ""),
        ("活動場所", tbd((primary_link("youtube") or {}).get("url") and "YouTube", "YouTube（チャンネル準備中）"), ""),
    ]
    spec = "".join(
        f"<tr><th scope=\"row\">{e(label)}</th><td>{value}"
        + (f'<span class="spec__note">{e(note)}</span>' if note else "")
        + "</td></tr>"
        for label, value, note in rows
    )

    likes = "".join(f'<li class="chip">{e(x)}</li>' for x in TALENT["likes"])
    dislikes = "".join(f'<li class="chip chip--pink">{e(x)}</li>' for x in TALENT["dislikes"])
    intro = "".join(f"<p>{e(p)}</p>" for p in TALENT["intro"])

    swatches = "".join(
        f'<li class="swatch"><div class="swatch__chip" style="background:{e(c["hex"])}"></div>'
        f'<div class="swatch__body"><p class="swatch__name">{e(c["name"])}</p>'
        f'<p class="swatch__hex">{e(c["hex"])}</p>'
        f'<p class="swatch__note">{e(c["note"])}</p></div></li>'
        for c in TALENT["colors"]
    )

    design = "".join(
        f'<tr><th scope="row">{e(d["label"])}</th><td>{e(d["text"])}</td></tr>'
        for d in TALENT["design_notes"]
    )

    credits = "".join(
        f'<tr><th scope="row">{e(c["role"])}</th><td>{tbd(c["name"], "公開準備中")}</td></tr>'
        for c in TALENT["credits"]
    )

    return Page(
        "/profile/",
        f"プロフィール｜{TALENT['name']}",
        f"{TALENT['name']}のプロフィールです。基本情報、好きなものと苦手なもの、"
        "キャラクターデザインの設定、イメージカラーの一覧をまとめています。",
        f"""    <section class="page-head">
      <div class="wrap">
        <p class="head__kicker">Profile</p>
        <h1 class="page-head__title neon">プロフィール</h1>
        <p class="page-head__lead">{e(TALENT['catch'])}</p>
      </div>
    </section>

    <section class="section" style="padding-top:0" aria-labelledby="basic-title">
      <div class="wrap">
        <div class="grid grid--2">
          <div data-reveal>
            {portrait_picture("hero__portrait", "(max-width: 760px) 86vw, 440px")}
          </div>
          <div class="card" data-reveal data-reveal-delay="120">
            <h2 class="head__title" id="basic-title" style="font-size:1.4rem;margin-bottom:12px">基本情報</h2>
            <table class="spec">
              <caption class="visually-hidden">{e(TALENT['name'])}の基本情報</caption>
              <tbody>{spec}</tbody>
            </table>
          </div>
        </div>
      </div>
    </section>

    <section class="section" aria-labelledby="story-title">
      <div class="wrap">
        {section_head("Story", "どういう子か")}
        <div class="card" data-reveal>
          <div class="prose" id="story-title">{intro}</div>
        </div>
      </div>
    </section>

    <section class="section" aria-labelledby="taste-title">
      <div class="wrap">
        {section_head("Taste", "すきときらい")}
        <div class="grid grid--2">
          <div class="card" data-reveal>
            <h3 class="content-card__title">すきなもの</h3>
            <ul class="chips">{likes}</ul>
          </div>
          <div class="card" data-reveal data-reveal-delay="110">
            <h3 class="content-card__title" id="taste-title">にがてなもの</h3>
            <ul class="chips">{dislikes}</ul>
          </div>
        </div>
      </div>
    </section>

    <section class="section" aria-labelledby="design-title">
      <div class="wrap">
        {section_head("Design", "デザインの覚え書き", "ファンアートを描いてくださるときの参考にどうぞ。細かいところは、描きやすいように変えてもらって大丈夫です。")}
        <div class="grid grid--2">
          <div class="card" data-reveal>
            <h3 class="content-card__title" id="design-title">衣装と小物</h3>
            <table class="spec"><tbody>{design}</tbody></table>
          </div>
          <div class="card" data-reveal data-reveal-delay="110">
            <h3 class="content-card__title">イメージカラー</h3>
            <ul class="swatches">{swatches}</ul>
          </div>
        </div>
      </div>
    </section>

    <section class="section" aria-labelledby="credit-title">
      <div class="wrap">
        {section_head("Credits", "クレジット")}
        <div class="card" data-reveal>
          <h3 class="visually-hidden" id="credit-title">制作クレジット</h3>
          <table class="spec"><tbody>{credits}</tbody></table>
        </div>
      </div>
    </section>""",
        og_name="profile",
        og_alt=f"{TALENT['name']}のプロフィールページのシェアカード",
        og_type="profile",
        trail=[("/", "トップ"), ("/profile/", "プロフィール")],
        priority="0.9",
    )


# --------------------------------------------------------------------------- #
# 配信スケジュール
# --------------------------------------------------------------------------- #
def page_schedule() -> Page:
    sc = DATA["schedule"]
    slots = []
    for s in sc["slots"]:
        kind = s.get("kind", "talk")
        time_html = (
            f'<p class="slot__time">{e(s["time"])}</p>'
            if s.get("time")
            else '<p class="slot__time">—</p>'
        )
        slots.append(
            f'<li class="slot slot--{e(kind)}" data-reveal>'
            f'<p class="slot__day">{e(s["day"])}</p>'
            f"{time_html}"
            f'<p class="slot__title">{e(s["title"])}</p></li>'
        )

    contents = "".join(
        f'<article class="card card--hover" data-reveal data-reveal-delay="{i * 90}">'
        f'{icon(c["icon"], "content-card__icon")}'
        f'<p class="content-card__sub">{e(c["subtitle"])}</p>'
        f'<h3 class="content-card__title">{e(c["title"])}</h3>'
        f'<p class="content-card__text">{e(c["text"])}</p></article>'
        for i, c in enumerate(DATA["contents"])
    )

    yt = (
        f'<a class="btn btn--primary" href="{e(YT_URL)}" rel="noopener" target="_blank">{icon("youtube")}YouTubeチャンネル</a>'
        if YT_URL
        else '<span class="btn btn--primary" aria-disabled="true">YouTubeチャンネル準備中</span>'
    )

    return Page(
        "/schedule/",
        f"配信スケジュール｜{TALENT['name']}",
        f"{TALENT['name']}の週の配信スケジュールです。もくもく自習、深夜の雑談、"
        "過去問配信、ゲームの目安の時間をまとめています。変更はXでお知らせします。",
        f"""    <section class="page-head">
      <div class="wrap">
        <p class="head__kicker">Schedule</p>
        <h1 class="page-head__title neon">配信スケジュール</h1>
        <p class="page-head__lead">{e(sc['note'])}表示している時刻は{e(sc['timezone'])}です。</p>
      </div>
    </section>

    <section class="section" style="padding-top:0" aria-labelledby="week-title">
      <div class="wrap">
        <h2 class="visually-hidden" id="week-title">週のスケジュール</h2>
        <ul class="schedule" style="list-style:none;padding:0;margin:0">{"".join(slots)}</ul>
        <p class="note" style="margin-top:28px">
          配信の開始は前後します。当日の告知と、休止・時間変更のお知らせはXに出します。
          はじめて来てくださる方は、まず「もくもく自習」の枠がいちばん入りやすいと思います。
        </p>
      </div>
    </section>

    <section class="section" aria-labelledby="kinds-title">
      <div class="wrap">
        {section_head("Contents", "枠の種類", "それぞれの枠で、だいたいこういうことをしています。")}
        <h2 class="visually-hidden" id="kinds-title">枠の種類</h2>
        <div class="grid grid--4">{contents}</div>
      </div>
    </section>

    <section class="section">
      <div class="wrap">
        <div class="cta" data-reveal>
          <h2 class="cta__title">配信の通知を受け取る</h2>
          <p class="cta__text">開始のお知らせはXに流れます。アーカイブはYouTubeに残します。</p>
          <div class="cta__actions">
            <a class="btn btn--ghost" href="{e(X_URL)}" rel="me noopener" target="_blank">{icon('x')}Xをフォロー</a>
            {yt}
          </div>
        </div>
      </div>
    </section>""",
        og_name="schedule",
        og_alt=f"{TALENT['name']}の配信スケジュールページのシェアカード",
        trail=[("/", "トップ"), ("/schedule/", "配信スケジュール")],
        priority="0.8",
    )


# --------------------------------------------------------------------------- #
# 二次創作ガイドライン（＋よくある質問）
# --------------------------------------------------------------------------- #
def page_guidelines() -> Page:
    g = DATA["guidelines"]
    blocks = []
    for sec in g["sections"]:
        parts = [f'<h2 id="{e(sec["id"])}">{e(sec["title"])}</h2>']
        for p in sec.get("body", []):
            parts.append(f"<p>{e(p)}</p>")
        if sec.get("ok"):
            parts.append("<h3>こうしてもらえると嬉しいこと</h3>")
            parts.append(
                '<ul class="rule-list rule-list--ok">'
                + "".join(f"<li>{e(x)}</li>" for x in sec["ok"])
                + "</ul>"
            )
        if sec.get("ng"):
            parts.append("<h3>お断りしていること</h3>")
            parts.append(
                '<ul class="rule-list rule-list--ng">'
                + "".join(f"<li>{e(x)}</li>" for x in sec["ng"])
                + "</ul>"
            )
        blocks.append("".join(parts))

    tags = g["tags"]
    tag_rows = "".join(
        f'<tr><th scope="row">{e(label)}</th><td><code>{e(tags[key])}</code></td></tr>'
        for key, label in (
            ("fanart", "ファンアート"),
            ("clip", "切り抜き"),
            ("stream", "配信の感想"),
        )
        if tags.get(key)
    )

    faq = "".join(
        f'<details class="faq__item"><summary class="faq__q">{e(item["q"])}</summary>'
        f'<div class="faq__a"><p>{e(item["a"])}</p></div></details>'
        for item in DATA["faq"]
    )

    faq_schema = {
        "@type": "FAQPage",
        "@id": f"{HOST}/guidelines/#faq",
        "mainEntity": [
            {
                "@type": "Question",
                "name": item["q"],
                "acceptedAnswer": {"@type": "Answer", "text": item["a"]},
            }
            for item in DATA["faq"]
        ],
    }

    return Page(
        "/guidelines/",
        f"二次創作ガイドライン｜{TALENT['name']}",
        f"{TALENT['name']}のファンアート・切り抜き動画についてのお願いです。"
        "使ってよい範囲、お断りしていること、商用利用の相談先、よくある質問をまとめています。",
        f"""    <section class="page-head">
      <div class="wrap">
        <p class="head__kicker">Guidelines</p>
        <h1 class="page-head__title neon">二次創作ガイドライン</h1>
        <p class="page-head__lead">応援してくださる方へのお願いです。最終更新：{e(jp_date(g['updated']))}</p>
      </div>
    </section>

    <section class="section" style="padding-top:0">
      <div class="wrap">
        <div class="card" data-reveal>
          <h2 class="content-card__title">投稿に使うタグ</h2>
          <table class="spec"><tbody>{tag_rows}</tbody></table>
          <p class="note" style="margin-top:20px">
            タグをつけていただいた投稿は、配信やSNSで紹介させていただくことがあります。
            紹介されたくないときは、その旨を書き添えてください。
          </p>
        </div>
      </div>
    </section>

    <section class="section" style="padding-top:0">
      <div class="wrap">
        <div class="card" data-reveal>
          <div class="prose">
            {"".join(blocks)}
            <h2 id="disclaimer">おことわり</h2>
            <p>
              ここに書いた範囲であっても、内容によってはお声がけして取り下げをお願いすることがあります。
              判断に迷うときは、お問い合わせページからご相談ください。答えられる範囲でお返事します。
            </p>
          </div>
        </div>
      </div>
    </section>

    <section class="section" aria-labelledby="faq-title">
      <div class="wrap">
        {section_head("FAQ", "よくある質問")}
        <h2 class="visually-hidden" id="faq-title">よくある質問</h2>
        <div class="faq" data-reveal>{faq}</div>
      </div>
    </section>""",
        og_name="guidelines",
        og_alt=f"{TALENT['name']}の二次創作ガイドラインページのシェアカード",
        og_type="article",
        schema=[faq_schema],
        trail=[("/", "トップ"), ("/guidelines/", "二次創作ガイドライン")],
        priority="0.7",
    )


# --------------------------------------------------------------------------- #
# お問い合わせ
# --------------------------------------------------------------------------- #
def page_contact() -> Page:
    c = DATA["contact"]
    topics = "".join(
        f'<article class="card card--hover" data-reveal data-reveal-delay="{i * 90}">'
        f'<h3 class="content-card__title">{e(t["title"])}</h3>'
        f'<p class="content-card__text">{e(t["text"])}</p></article>'
        for i, t in enumerate(c["topics"])
    )

    channels = []
    if c.get("email"):
        channels.append(
            f'<a class="btn btn--primary" href="mailto:{e(c["email"])}">{icon("mail")}{e(c["email"])}</a>'
        )
    if c.get("form_url"):
        channels.append(
            f'<a class="btn btn--primary" href="{e(c["form_url"])}" rel="noopener" target="_blank">お問い合わせフォーム{icon("external")}</a>'
        )
    channels.append(
        f'<a class="btn btn--ghost" href="{e(X_URL)}" rel="me noopener" target="_blank">{icon("x")}XのDM</a>'
    )

    no_mail = (
        ""
        if c.get("email") or c.get("form_url")
        else '<p class="note" style="margin-top:22px">'
        "メールアドレスとお問い合わせフォームは準備中です。それまでは、XのDMでご連絡ください。</p>"
    )

    return Page(
        "/contact/",
        f"お問い合わせ｜{TALENT['name']}",
        f"{TALENT['name']}へのお仕事のご依頼・取材・許諾のご相談の窓口です。"
        "企業案件、コラボレーション、権利侵害のご報告はこちらからご連絡ください。",
        f"""    <section class="page-head">
      <div class="wrap">
        <p class="head__kicker">Contact</p>
        <h1 class="page-head__title neon">お問い合わせ</h1>
        <p class="page-head__lead">{e(c['lead'])}</p>
      </div>
    </section>

    <section class="section" style="padding-top:0" aria-labelledby="channel-title">
      <div class="wrap">
        <div class="card" data-reveal>
          <h2 class="content-card__title" id="channel-title">連絡先</h2>
          <p class="content-card__text" style="margin-bottom:22px">{e(c['response_note'])}</p>
          <div class="hero__actions" style="margin-top:0">{"".join(channels)}</div>
          {no_mail}
        </div>
      </div>
    </section>

    <section class="section" aria-labelledby="topics-title">
      <div class="wrap">
        {section_head("Topics", "こういうご相談を受け付けています", "ご連絡のときに、件名へ用件の種類を書いていただけると助かります。")}
        <h2 class="visually-hidden" id="topics-title">受け付けている相談</h2>
        <div class="grid grid--2">{topics}</div>
      </div>
    </section>

    <section class="section">
      <div class="wrap">
        <div class="note" data-reveal>
          ファンアートや切り抜きなど、個人の趣味の範囲での利用については
          <a href="/guidelines/">二次創作ガイドライン</a>にまとめています。
          ご連絡の前に、そちらをご確認ください。
        </div>
      </div>
    </section>""",
        og_name="contact",
        og_alt=f"{TALENT['name']}のお問い合わせページのシェアカード",
        trail=[("/", "トップ"), ("/contact/", "お問い合わせ")],
        priority="0.6",
    )


# --------------------------------------------------------------------------- #
# 404
# --------------------------------------------------------------------------- #
def page_404() -> Page:
    links = "".join(f'<li><a href="{p}">{e(t)}</a></li>' for p, t in FOOTER_LINKS[1:])
    return Page(
        "/404.html",
        "ページが見つかりません｜ほんごうねむり",
        "お探しのページは見つかりませんでした。URLが変わったか、削除された可能性があります。"
        "サイト内の主なページへのリンクからお探しください。",
        f"""    <section class="section" style="min-height:52vh;display:flex;align-items:center">
      <div class="wrap" style="text-align:center">
        <p class="head__kicker" style="justify-content:center">404</p>
        <h1 class="page-head__title neon">ページが見つかりません</h1>
        <p class="page-head__lead" style="margin-inline:auto">
          URLが変わったか、削除されたようです。寝ぼけて消したのかもしれません。
        </p>
        <ul class="chips" style="justify-content:center;margin-top:30px">{links}</ul>
        <p style="margin-top:34px"><a class="btn btn--primary" href="/">トップへ戻る</a></p>
      </div>
    </section>""",
        og_name="index",
        og_alt=f"{TALENT['name']}公式サイトのシェアカード",
        noindex=True,
    )


PAGES = [page_index, page_profile, page_schedule, page_guidelines, page_contact, page_404]


# --------------------------------------------------------------------------- #
# 生成ファイル
# --------------------------------------------------------------------------- #
def write_sitemap(pages: list[Page]) -> None:
    rows = []
    for p in sorted(pages, key=lambda x: x.path):
        if p.noindex:
            continue
        rows.append(
            "  <url>\n"
            f"    <loc>{HOST}{p.path}</loc>\n"
            f"    <lastmod>{BUILT_ON}</lastmod>\n"
            f"    <priority>{p.priority}</priority>\n"
            "  </url>"
        )
    (PUBLIC / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "\n".join(rows)
        + "\n</urlset>\n",
        encoding="utf-8",
    )


def write_robots() -> None:
    (PUBLIC / "robots.txt").write_text(
        "User-agent: *\n"
        "Allow: /\n"
        "\n"
        "# 生成物の直リンクはクロールさせません（内容はページ側にあります）\n"
        "Disallow: /og/\n"
        "\n"
        f"Sitemap: {HOST}/sitemap.xml\n",
        encoding="utf-8",
    )


def write_llms(pages: list[Page]) -> None:
    lines = [
        f"# {TALENT['name']}（{TALENT['name_latin']}）",
        "",
        f"> {TALENT['role']}。{TALENT['catch']}",
        "",
        TALENT["lead"],
        "",
        "## 注意",
        "",
        "- 「バーチャル東京大学」はキャラクターの設定上の出身校です。",
        "  実在する大学の卒業資格・学歴を示すものではありません。",
        "- 誕生日・身長・初配信日など、このサイトに書かれていない事実を補わないでください。",
        "",
        "## ページ",
        "",
    ]
    for p in sorted(pages, key=lambda x: x.path):
        if p.noindex:
            continue
        lines.append(f"- [{p.title}]({HOST}{p.path}): {p.description}")
    lines += ["", "## 連絡先", "", f"- X: {X_URL}"]
    if DATA["contact"].get("email"):
        lines.append(f"- Email: {DATA['contact']['email']}")
    (PUBLIC / "llms.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_manifest() -> None:
    manifest = {
        "name": SITE["name"],
        "short_name": SITE["short_name"],
        "start_url": "/",
        "display": "standalone",
        "background_color": "#05091c",
        "theme_color": "#05091c",
        "lang": "ja",
        "icons": [
            {"src": _ASSET_MAP["img/icon-180.png"], "sizes": "180x180", "type": "image/png"},
            {"src": _ASSET_MAP["img/icon-512.png"], "sizes": "512x512", "type": "image/png"},
        ],
    }
    (PUBLIC / "site.webmanifest").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def write_headers() -> None:
    (PUBLIC / "_headers").write_text(
        """# Cloudflare Pages / Netlify が読みます。
# 変更したら python3 build.py --check を実行してください。

/*
  X-Content-Type-Options: nosniff
  X-Frame-Options: SAMEORIGIN
  Referrer-Policy: strict-origin-when-cross-origin
  Permissions-Policy: geolocation=(), microphone=(), camera=(), interest-cohort=()

# ファイル名に内容のハッシュが入っています。名前が同じなら中身も同じなので、
# 期限切れを気にせず長くキャッシュさせます。
/assets/*
  Cache-Control: public, max-age=31536000, immutable

# シェアカードはハッシュなしの固定名です。文面を直して作り直したときに
# 古い画像が返り続けないよう、immutable にはしません。
/og/*
  Cache-Control: public, max-age=86400, must-revalidate

/sitemap.xml
  Cache-Control: public, max-age=0, must-revalidate

/llms.txt
  Cache-Control: public, max-age=0, must-revalidate
""",
        encoding="utf-8",
    )


def write_redirects() -> None:
    (PUBLIC / "_redirects").write_text(
        """# 打ち間違い・よくある別表記からの転送。
/about/*      /profile/     301
/profile      /profile/     301
/schedule     /schedule/    301
/guidelines   /guidelines/  301
/guideline/*  /guidelines/  301
/contact      /contact/     301
/faq          /guidelines/#faq  301
/links        /#links-title 301
""",
        encoding="utf-8",
    )


# --------------------------------------------------------------------------- #
# 検査
# --------------------------------------------------------------------------- #
class PageScan(HTMLParser):
    """生成したHTMLから、検査に必要なところだけ拾う。"""

    def __init__(self, markup: str) -> None:
        super().__init__(convert_charrefs=True)
        self.h1 = 0
        self.links: list[str] = []
        self.imgs: list[dict[str, str]] = []
        self.ids: set[str] = set()
        self.feed(markup)

    def handle_starttag(self, tag, attrs) -> None:
        a = {k: (v or "") for k, v in attrs}
        if "id" in a:
            self.ids.add(a["id"])
        if tag == "h1":
            self.h1 += 1
        elif tag == "a" and "href" in a:
            self.links.append(a["href"])
        elif tag == "img":
            self.imgs.append(a)


def check(pages: list[Page], rendered: dict[str, str]) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    titles: dict[str, str] = {}
    descs: dict[str, str] = {}
    ids_by_path: dict[str, set[str]] = {}
    known = {p.path for p in pages}

    scans = {p.path: PageScan(rendered[p.path]) for p in pages}
    for p in pages:
        ids_by_path[p.path] = scans[p.path].ids

    for p in pages:
        s = scans[p.path]

        def err(msg: str) -> None:
            errors.append(f"{p.path}: {msg}")

        # --- head ---
        if not TITLE_MIN <= len(p.title) <= TITLE_MAX:
            err(f"タイトルが{len(p.title)}文字（{TITLE_MIN}〜{TITLE_MAX}に収めてください）: {p.title}")
        if not DESC_MIN <= len(p.description) <= DESC_MAX:
            err(f"meta description が{len(p.description)}文字（{DESC_MIN}〜{DESC_MAX}に）")
        if p.title in titles:
            err(f"タイトルが {titles[p.title]} と重複しています")
        titles[p.title] = p.path
        if p.description in descs:
            err(f"description が {descs[p.description]} と重複しています")
        descs[p.description] = p.path

        # --- 見出し ---
        if s.h1 != 1:
            err(f"<h1> が{s.h1}個あります（1個にしてください）")

        # --- 画像 ---
        for img in s.imgs:
            src = img.get("src", "?")
            if "alt" not in img:
                err(f"alt 属性のない <img>: {src}")
            elif img["alt"] == "" and img.get("aria-hidden") != "true":
                warnings.append(f"{p.path}: alt が空の <img>（装飾なら aria-hidden も）: {src}")
            if not img.get("width") or not img.get("height"):
                err(f"width/height のない <img>（表示のガタつきの原因になります）: {src}")

        # --- 内部リンク ---
        for href in s.links:
            if href.startswith(("http://", "https://", "mailto:", "tel:")):
                continue
            path, _, frag = href.partition("#")
            path = path or p.path
            if path not in known and not (PUBLIC / path.lstrip("/")).exists():
                err(f"リンク先がありません: {href}")
            elif frag and path in ids_by_path and frag not in ids_by_path[path]:
                err(f"リンク先に id={frag!r} がありません: {href}")

        # --- シェアカード ---
        if not (PUBLIC / "og" / f"{p.og_name}.{OG_EXT}").exists():
            err(f"シェアカードがありません: /og/{p.og_name}.{OG_EXT}（python3 tools/make_og_cards.py）")

        # --- 置換し忘れ ---
        if "{{asset:" in rendered[p.path]:
            err("{{asset:...}} が解決されていません")

    # --- site.json の未記入（止めはしないが、公開前に埋めたい項目） ---
    todo = [
        ("talent.birthday", TALENT["birthday"]),
        ("talent.height", TALENT["height"]),
        ("talent.debut_date", TALENT["debut_date"]),
        ("talent.fan_name", TALENT["fan_name"]),
        ("talent.oshi_mark", TALENT["oshi_mark"]),
        ("highlight.datetime", DATA["highlight"]["datetime"]),
        ("highlight.url", DATA["highlight"]["url"]),
        ("contact.email", DATA["contact"]["email"]),
    ]
    todo += [(f"links[{l['id']}].url", l.get("url")) for l in DATA["links"]]
    todo += [
        (f"talent.credits[{c['role']}]", c.get("name")) for c in TALENT["credits"]
    ]
    for name, value in todo:
        if value in (None, ""):
            warnings.append(f"site.json: {name} が未記入です")

    return errors, warnings


# --------------------------------------------------------------------------- #
def main() -> int:
    parser = argparse.ArgumentParser(description="ほんごうねむり 公式サイトのビルド")
    parser.add_argument("--check", action="store_true", help="検査に落ちたら異常終了する")
    args = parser.parse_args()

    # public/ のうち、生成物だけを消します（og/ は別のスクリプトが作るので残す）。
    for path in ("assets", "profile", "schedule", "guidelines", "contact"):
        shutil.rmtree(PUBLIC / path, ignore_errors=True)
    PUBLIC.mkdir(exist_ok=True)

    build_assets()

    pages = [factory() for factory in PAGES]
    rendered: dict[str, str] = {}
    for page in pages:
        markup = substitute(page.render())
        rendered[page.path] = markup
        page.out_path.parent.mkdir(parents=True, exist_ok=True)
        page.out_path.write_text(markup, encoding="utf-8")

    write_sitemap(pages)
    write_robots()
    write_llms(pages)
    write_manifest()
    write_headers()
    write_redirects()

    errors, warnings = check(pages, rendered)

    print(f"{len(pages)} ページ、{len(_ASSET_MAP)} アセットを書き出しました。")
    for w in warnings:
        print(f"  注意  {w}")
    for err in errors:
        print(f"  エラー {err}")

    if errors:
        print(f"\n検査に {len(errors)} 件の問題があります。")
        return 1 if args.check else 0
    print("検査を通りました。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
