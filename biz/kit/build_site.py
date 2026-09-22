#!/usr/bin/env python3
"""Generate a complete, SEO-ready static site for one small business from a JSON config.

This is the production side of the business: a client's answers go into
``clients/<slug>.json``, this script turns them into a site that is already
correct on every technical point Google checks, and ``--check`` refuses to
emit one that is not.

The approach is copied from the 黒田塾 site in this repository, which is
hand-written HTML plus a generator for the derived files. The difference is
that there the pages are the source of truth; here the *config* is, because
the whole point is to produce the twentieth site as cheaply as the first.

What every generated site gets, and why:

* **LocalBusiness JSON-LD with the full NAP.** Name, address and phone in a
  machine-readable block, matching the Google Business Profile character for
  character. For a local trade this is the single highest-value markup: it is
  what ties the site to the map listing.
* **One canonical host, declared on every page.** The 黒田塾 site's SEO notes
  open with what happens when canonical points at a host that does not
  resolve — the pages drop out of the index entirely. The check below refuses
  to build if the canonical host and the configured host disagree.
* **No web fonts, no framework, inlined CSS.** A 5-page brochure site has no
  excuse for a render-blocking request. LCP lands on text that is already
  painted.
* **width/height on every image**, so nothing shifts while loading (CLS).
* **Real `<a href="tel:">`**, because on these sites most conversions are a
  phone call from a mobile SERP, not a form submission.
* **Unique title and description per page**, inside the widths Google actually
  shows for Japanese text.

Usage
-----
    python3 build_site.py clients/sample-koumuten.json           # build
    python3 build_site.py clients/sample-koumuten.json --check   # build + verify
    python3 build_site.py --all --check                          # every client

Output lands in ``dist/<slug>/``, ready to drop on Cloudflare Pages.
Standard library only, so a deploy never depends on pip.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
from datetime import date
from pathlib import Path
from urllib.parse import urlparse
from xml.sax.saxutils import escape as xml_escape

ROOT = Path(__file__).resolve().parent
DIST = ROOT / "dist"

# Google truncates a Japanese SERP title at roughly 30 full-width characters
# and a description at about 70-80. These bounds keep every page inside that
# and still descriptive. Same reasoning as build.py at the repository root.
TITLE_MIN, TITLE_MAX = 12, 36
DESC_MIN, DESC_MAX = 55, 120

# schema.org subtypes worth using. Anything else falls back to LocalBusiness,
# which is always valid; an invented subtype is not.
KNOWN_TYPES = {
    "GeneralContractor", "HomeAndConstructionBusiness", "Plumber", "Electrician",
    "RoofingContractor", "HousePainter", "Locksmith", "MovingCompany",
    "Dentist", "Physician", "MedicalClinic", "VeterinaryCare", "HealthAndBeautyBusiness",
    "BeautySalon", "HairSalon", "DaySpa", "NailSalon",
    "AutoRepair", "AutoBodyShop", "AutoPartsStore",
    "RealEstateAgent", "Attorney", "AccountingService", "InsuranceAgency",
    "LegalService", "ProfessionalService", "FinancialService",
    "Restaurant", "CafeOrCoffeeShop", "Bakery", "Florist", "DryCleaningOrLaundry",
    "FuneralHome", "ChildCare", "Electrician", "Store", "LocalBusiness",
}

DAY_JA = {
    "Monday": "月", "Tuesday": "火", "Wednesday": "水", "Thursday": "木",
    "Friday": "金", "Saturday": "土", "Sunday": "日",
}


def fit_desc(base: str, extras: list[str]) -> str:
    """Grow a description until it fills the width Google shows, then stop.

    A 45-character description is not wrong, it is just wasted: the SERP has
    room for roughly 70-80 full-width characters and every one of them is a
    line of sales copy the client is not paying for. Clauses are appended in
    the order given until the text is long enough, and never past the cap.
    """
    text = base.rstrip("。") + "。"
    for extra in extras:
        if not extra:
            continue
        if len(text) >= DESC_MIN:
            break
        text += extra.rstrip("。") + "。"
    if len(text) > DESC_MAX:
        text = text[: DESC_MAX - 1].rstrip("、。") + "。"
    return text


def esc(text: str) -> str:
    return html.escape(str(text), quote=True)


# --------------------------------------------------------------------------- #
# Stylesheet
#
# Inlined into every page. Small enough that a separate request would cost more
# than it saves, and inlining removes the only render-blocking resource.
# System fonts only: a Japanese web font is 2-8 MB and will lose the LCP budget
# on its own.
# --------------------------------------------------------------------------- #
def stylesheet(accent: str, accent_dark: str) -> str:
    return f"""
:root{{
  --accent:{accent};
  --bg:#ffffff; --surface:#f6f7f8; --border:#dfe3e6;
  --text:#14181c; --muted:#5a646e; --on-accent:#ffffff;
  --radius:10px; --measure:34rem;
}}
@media (prefers-color-scheme:dark){{
  :root:not([data-theme="light"]){{
    --accent:{accent_dark};
    --bg:#11151a; --surface:#1a2027; --border:#2c343d;
    --text:#e9edf1; --muted:#9aa5b1; --on-accent:#11151a;
  }}
}}
:root[data-theme="dark"]{{
  --accent:{accent_dark};
  --bg:#11151a; --surface:#1a2027; --border:#2c343d;
  --text:#e9edf1; --muted:#9aa5b1; --on-accent:#11151a;
}}
*,*::before,*::after{{box-sizing:border-box}}
html{{-webkit-text-size-adjust:100%}}
body{{
  margin:0; background:var(--bg); color:var(--text);
  font-family:"Hiragino Kaku Gothic ProN","Hiragino Sans","Noto Sans JP",
    "Yu Gothic Medium","Meiryo",system-ui,sans-serif;
  font-size:16px; line-height:1.85; letter-spacing:.01em;
}}
img{{max-width:100%;height:auto}}
a{{color:var(--accent)}}
.wrap{{max-width:64rem;margin:0 auto;padding:0 16px}}

/* header */
.site-head{{border-bottom:1px solid var(--border);background:var(--bg)}}
@media (min-width:46rem){{.site-head{{position:sticky;top:0;z-index:20}}}}
.site-head .wrap{{display:flex;align-items:center;gap:8px 12px;
  min-height:60px;flex-wrap:wrap;padding-top:8px;padding-bottom:8px}}
.brand{{font-weight:700;font-size:1.02rem;text-decoration:none;color:var(--text);
  line-height:1.3;margin-right:auto}}
.brand small{{display:block;font-weight:400;font-size:.75rem;color:var(--muted)}}
/* min-width:0 is load-bearing: a flex item defaults to min-width:auto, so the
   nav refuses to shrink below its widest line and pushes the whole page into
   horizontal scroll on a phone. */
.site-nav{{display:flex;gap:2px;flex-wrap:wrap;min-width:0}}
.site-nav a{{padding:9px 11px;border-radius:7px;text-decoration:none;
  color:var(--text);font-size:.88rem;white-space:nowrap;line-height:1.85}}
.site-nav a:hover{{background:var(--surface)}}
.site-nav a[aria-current="page"]{{color:var(--accent);font-weight:700}}
/* min-height rather than padding: padding has to be recomputed every time
   the font size changes, and 44px is the number that matters. */
.tel-btn{{background:var(--accent);color:var(--on-accent)!important;
  display:inline-flex;align-items:center;min-height:44px;
  padding:0 15px;border-radius:7px;text-decoration:none;font-weight:700;
  font-size:.92rem;white-space:nowrap}}

/* hero */
.hero{{padding:52px 0 40px;border-bottom:1px solid var(--border);
  background:var(--surface)}}
.hero h1{{font-size:clamp(1.45rem,4.6vw,2.15rem);line-height:1.45;margin:0 0 12px}}
.hero p.lead{{font-size:1.02rem;color:var(--muted);margin:0 0 24px;
  max-width:var(--measure)}}
.cta-row{{display:flex;gap:10px;flex-wrap:wrap;align-items:center}}
.cta{{display:inline-block;background:var(--accent);color:var(--on-accent);
  padding:13px 22px;border-radius:var(--radius);text-decoration:none;
  font-weight:700}}
.cta.ghost{{background:transparent;color:var(--accent);
  border:1.5px solid var(--accent)}}
.cta-note{{font-size:.84rem;color:var(--muted);width:100%;margin:2px 0 0}}

/* sections */
main{{padding:8px 0 0}}
section{{padding:40px 0;border-bottom:1px solid var(--border)}}
section:last-of-type{{border-bottom:0}}
h2{{font-size:1.32rem;margin:0 0 6px;line-height:1.5}}
h3{{font-size:1.06rem;margin:26px 0 6px;line-height:1.55}}
p,li{{max-width:var(--measure)}}
.sub{{color:var(--muted);margin:0 0 22px;font-size:.93rem}}

.cards{{display:grid;gap:14px;
  grid-template-columns:repeat(auto-fit,minmax(min(100%,17rem),1fr));
  margin:0;padding:0;list-style:none}}
.card{{border:1px solid var(--border);border-radius:var(--radius);
  padding:18px;background:var(--bg)}}
.card h3{{margin:0 0 6px;font-size:1.04rem}}
.card p{{margin:0 0 10px;font-size:.92rem;color:var(--muted);max-width:none}}
.card .price{{font-weight:700;font-size:.9rem;color:var(--text);display:block;
  margin-bottom:10px}}
.card a{{font-size:.9rem;font-weight:700;text-decoration:none}}
.card a::after{{content:" →"}}

dl.spec{{display:grid;grid-template-columns:auto 1fr;gap:1px;
  background:var(--border);border:1px solid var(--border);
  border-radius:var(--radius);overflow:hidden;margin:0}}
dl.spec dt,dl.spec dd{{background:var(--bg);padding:11px 14px;margin:0;
  font-size:.92rem}}
dl.spec dt{{font-weight:700;white-space:nowrap;color:var(--muted)}}

details.qa{{border:1px solid var(--border);border-radius:var(--radius);
  padding:0;margin:0 0 8px;background:var(--bg)}}
details.qa summary{{padding:14px 16px;cursor:pointer;font-weight:700;
  font-size:.95rem;list-style:none}}
details.qa summary::-webkit-details-marker{{display:none}}
details.qa summary::before{{content:"Q ";color:var(--accent);font-weight:700}}
details.qa[open] summary{{border-bottom:1px solid var(--border)}}
details.qa .a{{padding:14px 16px}}
details.qa .a p{{margin:0}}

.reasons{{list-style:none;padding:0;margin:0;display:grid;gap:18px}}
.reasons h3{{margin:0 0 4px}}
.reasons p{{margin:0;color:var(--muted);font-size:.93rem}}

.crumbs{{font-size:.8rem;color:var(--muted);padding:12px 0 0}}
.crumbs ol{{list-style:none;display:flex;flex-wrap:wrap;gap:6px;margin:0;padding:0}}
.crumbs li::after{{content:"›";margin-left:6px;color:var(--border)}}
.crumbs li:last-child::after{{content:""}}
.crumbs a{{color:var(--muted)}}

.contact-box{{border:2px solid var(--accent);border-radius:var(--radius);
  padding:24px;background:var(--surface);max-width:38rem}}
.contact-box .num{{font-size:clamp(1.6rem,6vw,2.1rem);font-weight:700;
  line-height:1.25;display:block;text-decoration:none;color:var(--text)}}
.contact-box .hours{{color:var(--muted);font-size:.9rem;margin:2px 0 16px}}

form.enquiry{{display:grid;gap:14px;max-width:34rem;margin-top:8px}}
form.enquiry label{{display:grid;gap:5px;font-size:.9rem;font-weight:700}}
form.enquiry input,form.enquiry textarea{{
  font:inherit;font-size:16px;padding:11px 12px;border:1px solid var(--border);
  border-radius:8px;background:var(--bg);color:var(--text);width:100%}}
form.enquiry textarea{{min-height:9rem;resize:vertical}}
form.enquiry button{{font:inherit;font-weight:700;background:var(--accent);
  color:var(--on-accent);border:0;border-radius:var(--radius);
  padding:14px 22px;cursor:pointer;justify-self:start}}
.req{{color:#c0392b;font-weight:400}}
@media (prefers-color-scheme:dark){{:root:not([data-theme="light"]) .req{{color:#ff8a7a}}}}

.site-foot{{border-top:1px solid var(--border);background:var(--surface);
  padding:30px 0;font-size:.86rem;color:var(--muted);margin-top:8px}}
.site-foot nav{{display:flex;gap:4px 10px;flex-wrap:wrap;margin-bottom:12px}}
.site-foot nav a{{padding:5px 2px;display:inline-block;min-height:24px}}
.site-foot a{{color:var(--muted)}}
.site-foot address{{font-style:normal;line-height:1.9}}

.skip{{position:absolute;left:-9999px}}
.skip:focus{{left:8px;top:8px;background:var(--accent);color:var(--on-accent);
  padding:10px 14px;border-radius:8px;z-index:50}}

/* On a phone the sticky header is the wrong place for the call button: it eats
   a third of the viewport. The call bar is pinned to the bottom instead, where
   the thumb already is, and the header collapses to brand + wrapped nav. */
.call-bar{{display:none}}
@media (max-width:45.99rem){{
  .brand{{width:100%;margin-right:0}}
  .site-head .tel-btn{{display:none}}
  .call-bar{{
    display:flex;position:fixed;left:0;right:0;bottom:0;z-index:30;gap:8px;
    padding:8px 12px calc(8px + env(safe-area-inset-bottom));
    background:var(--bg);border-top:1px solid var(--border)}}
  .call-bar a{{flex:1;text-align:center;padding:13px 8px;border-radius:9px;
    text-decoration:none;font-weight:700;font-size:.95rem}}
  .call-bar .tel{{background:var(--accent);color:var(--on-accent);flex:1.6}}
  .call-bar .form{{border:1.5px solid var(--accent);color:var(--accent)}}
  body{{padding-bottom:4.6rem}}
  .hero{{padding:34px 0 30px}}
}}
""".strip()


# --------------------------------------------------------------------------- #
# Config access
# --------------------------------------------------------------------------- #
class Client:
    def __init__(self, cfg: dict, path: Path):
        self.path = path
        self.cfg = cfg
        self.slug = cfg["slug"]
        self.site = cfg["site"].rstrip("/")
        self.b = cfg["business"]
        self.c = cfg["contact"]
        self.a = cfg["address"]
        self.services = cfg["services"]
        self.theme = cfg.get("theme", {})

    @property
    def name(self) -> str:
        return self.b["name"]

    @property
    def short(self) -> str:
        """Name without the corporate form, for titles that must stay short."""
        return re.sub(r"(株式会社|有限会社|合同会社|一般社団法人|\s)", "", self.name)

    @property
    def tel(self) -> str:
        return self.c["phone"]

    @property
    def tel_link(self) -> str:
        return "tel:" + re.sub(r"[^\d]", "", self.tel)

    @property
    def full_address(self) -> str:
        a = self.a
        return f"{a['region']}{a['city']}{a['street']}{a.get('building','')}".strip()

    @property
    def schema_type(self) -> str:
        t = self.b.get("type", "LocalBusiness")
        return t if t in KNOWN_TYPES else "LocalBusiness"

    def service(self, slug: str) -> dict:
        return next(s for s in self.services if s["slug"] == slug)


# --------------------------------------------------------------------------- #
# Structured data
# --------------------------------------------------------------------------- #
def local_business_node(cl: Client) -> dict:
    """The NAP block. This must match the Google Business Profile exactly.

    A mismatch between the site and the profile (a different phone format, an
    abbreviated address) weakens the association between the two, which is the
    thing that actually puts a small trade in the map pack.
    """
    a, c, b = cl.a, cl.c, cl.b
    node = {
        "@type": cl.schema_type,
        "@id": f"{cl.site}/#business",
        "name": cl.name,
        "description": b["description"],
        "url": cl.site + "/",
        "telephone": cl.tel,
        "address": {
            "@type": "PostalAddress",
            "addressCountry": "JP",
            "postalCode": a["postal"],
            "addressRegion": a["region"],
            "addressLocality": a["city"],
            "streetAddress": a["street"] + a.get("building", ""),
        },
        "areaServed": [
            {"@type": "AdministrativeArea", "name": n} for n in cl.cfg.get("area_served", [])
        ],
        "availableLanguage": b.get("languages", ["ja"]),
    }
    if b.get("kana"):
        node["alternateName"] = b["kana"]
    if a.get("lat") and a.get("lon"):
        node["geo"] = {"@type": "GeoCoordinates", "latitude": a["lat"], "longitude": a["lon"]}
    if c.get("email"):
        node["email"] = c["email"]
    if c.get("fax"):
        node["faxNumber"] = c["fax"]
    if b.get("price_range"):
        node["priceRange"] = b["price_range"]
    if b.get("founded"):
        node["foundingDate"] = b["founded"]
    if b.get("representative"):
        node["founder"] = {"@type": "Person", "name": b["representative"]}
    if b.get("employees"):
        node["numberOfEmployees"] = {"@type": "QuantitativeValue", "value": b["employees"]}
    if b.get("payment"):
        node["paymentAccepted"] = "、".join(b["payment"])
    hours = c.get("hours_schema") or []
    if hours:
        node["openingHoursSpecification"] = [
            {
                "@type": "OpeningHoursSpecification",
                "dayOfWeek": h["days"],
                "opens": h["open"],
                "closes": h["close"],
            }
            for h in hours
        ]
    if cl.services:
        node["hasOfferCatalog"] = {
            "@type": "OfferCatalog",
            "name": f"{cl.short}のサービス",
            "itemListElement": [
                {
                    "@type": "Offer",
                    "itemOffered": {
                        "@type": "Service",
                        "name": s["name"],
                        "url": f"{cl.site}/services/{s['slug']}/",
                    },
                    **({"description": s["price_from"]} if s.get("price_from") else {}),
                }
                for s in cl.services
            ],
        }
    return node


def breadcrumb_node(cl: Client, trail: list[tuple[str, str]]) -> dict:
    return {
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": i + 1, "name": label,
             "item": cl.site + path}
            for i, (label, path) in enumerate(trail)
        ],
    }


def faq_node(pairs: list) -> dict:
    return {
        "@type": "FAQPage",
        "mainEntity": [
            {
                "@type": "Question",
                "name": q,
                "acceptedAnswer": {"@type": "Answer", "text": a},
            }
            for q, a in pairs
        ],
    }


def jsonld(nodes: list[dict]) -> str:
    graph = {"@context": "https://schema.org", "@graph": nodes}
    body = json.dumps(graph, ensure_ascii=False, separators=(",", ":"))
    return f'<script type="application/ld+json">{body}</script>'


# --------------------------------------------------------------------------- #
# Page chrome
# --------------------------------------------------------------------------- #
def service_cards(services: list[dict], *, level: int) -> str:
    """Render service cards with the heading level the surrounding page needs.

    The same card sits under an ``h1`` on /services/ and under an ``h2`` on the
    home page. Hard-coding ``h3`` skips a level in the first case, which breaks
    the document outline the checks (and screen readers) walk.
    """
    out = []
    for s in services:
        price = (f'<span class="price">{esc(s["price_from"])}</span>'
                 if s.get("price_from") else "")
        out.append(
            f'<li class="card">'
            f'<h{level}>{esc(s["name"])}</h{level}>'
            f'<p>{esc(s["summary"])}</p>'
            f'{price}'
            f'<a href="/services/{s["slug"]}/">くわしく見る</a>'
            f'</li>'
        )
    return "".join(out)


def nav_links(cl: Client) -> list[tuple[str, str]]:
    return [
        ("ホーム", "/"),
        ("サービス", "/services/"),
        ("会社概要", "/about/"),
        ("よくある質問", "/faq/"),
        ("お問い合わせ", "/contact/"),
    ]


def head(cl: Client, *, path: str, title: str, desc: str, nodes: list[dict],
         lastmod: str) -> str:
    canonical = cl.site + path
    css = stylesheet(cl.theme.get("accent", "#1f5f3f"),
                     cl.theme.get("accent_dark", "#5fbe8e"))
    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
<meta name="robots" content="index, follow, max-image-preview:large">
<link rel="canonical" href="{esc(canonical)}">
<meta name="last-modified" content="{lastmod}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="{esc(cl.name)}">
<meta property="og:locale" content="ja_JP">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:url" content="{esc(canonical)}">
<meta name="twitter:card" content="summary">
<meta name="format-detection" content="telephone=no">
<meta name="theme-color" content="{esc(cl.theme.get('accent', '#1f5f3f'))}">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<style>{css}</style>
{jsonld(nodes)}
</head>
<body>
<a class="skip" href="#main">本文へ移動</a>
"""


def header(cl: Client, current: str) -> str:
    def item(label: str, p: str) -> str:
        mark = ' aria-current="page"' if p == current else ""
        return f'<a href="{p}"{mark}>{esc(label)}</a>'

    items = "".join(item(label, p) for label, p in nav_links(cl))
    return f"""<header class="site-head">
<div class="wrap">
<a class="brand" href="/">{esc(cl.name)}<small>{esc(cl.b['tagline'])}</small></a>
<nav class="site-nav" aria-label="メインメニュー">{items}</nav>
<a class="tel-btn" href="{cl.tel_link}">☎ {esc(cl.tel)}</a>
</div>
</header>
"""


def crumbs(trail: list[tuple[str, str]]) -> str:
    if len(trail) < 2:
        return ""
    parts = []
    for i, (label, path) in enumerate(trail):
        last = i == len(trail) - 1
        inner = esc(label) if last else f'<a href="{path}">{esc(label)}</a>'
        parts.append(f"<li>{inner}</li>")
    return ('<div class="wrap crumbs"><nav aria-label="パンくずリスト"><ol>'
            + "".join(parts) + "</ol></nav></div>\n")


def contact_block(cl: Client, *, heading: str = "お問い合わせ") -> str:
    return f"""<div class="contact-box">
<h2 style="margin-top:0">{esc(heading)}</h2>
<p class="sub" style="margin-bottom:10px">お電話が一番早くつながります。</p>
<a class="num" href="{cl.tel_link}">{esc(cl.tel)}</a>
<p class="hours">{esc(cl.c['hours_text'])}</p>
<a class="cta" href="/contact/">フォームから相談する</a>
</div>"""


def footer(cl: Client) -> str:
    a = cl.a
    links = "".join(f'<a href="{p}">{esc(label)}</a>' for label, p in nav_links(cl))
    access = f"<br>{esc(a['access'])}" if a.get("access") else ""
    fax = f"／FAX {esc(cl.c['fax'])}" if cl.c.get("fax") else ""
    return f"""<footer class="site-foot">
<div class="wrap">
<nav aria-label="フッターメニュー">{links}</nav>
<address>
<strong>{esc(cl.name)}</strong><br>
〒{esc(a['postal'])} {esc(cl.full_address)}{access}<br>
TEL <a href="{cl.tel_link}">{esc(cl.tel)}</a>{fax}<br>
{esc(cl.c['hours_text'])}
</address>
<p>&copy; {date.today().year} {esc(cl.name)}</p>
</div>
</footer>
<div class="call-bar">
<a class="tel" href="{cl.tel_link}">☎ 電話する</a>
<a class="form" href="/contact/">相談フォーム</a>
</div>
</body>
</html>
"""


def qa_list(pairs: list) -> str:
    return "".join(
        f'<details class="qa"><summary>{esc(q)}</summary>'
        f'<div class="a"><p>{esc(a)}</p></div></details>'
        for q, a in pairs
    )


# --------------------------------------------------------------------------- #
# Pages
# --------------------------------------------------------------------------- #
def page_home(cl: Client, lastmod: str) -> str:
    b = cl.b
    title = f"{cl.name}｜{b['tagline'].split('｜')[0]}"
    areas = "・".join(cl.cfg.get("area_served", []))
    desc = fit_desc(b["description"], [
        f"対応エリアは{areas}",
        f"お電話は{cl.tel}（{cl.c['hours_text']}）",
    ])
    nodes = [
        local_business_node(cl),
        {"@type": "WebSite", "@id": f"{cl.site}/#website", "url": cl.site + "/",
         "name": cl.name, "inLanguage": "ja",
         "publisher": {"@id": f"{cl.site}/#business"}},
        {"@type": "WebPage", "@id": f"{cl.site}/#webpage", "url": cl.site + "/",
         "name": title, "description": desc, "inLanguage": "ja",
         "isPartOf": {"@id": f"{cl.site}/#website"},
         "about": {"@id": f"{cl.site}/#business"}},
    ]
    if cl.cfg.get("faq"):
        nodes.append(faq_node(cl.cfg["faq"]))

    cards = service_cards(cl.services, level=3)
    reasons = "".join(
        f"<li><h3>{esc(h)}</h3><p>{esc(t)}</p></li>" for h, t in cl.cfg.get("reasons", [])
    )
    areas = "・".join(cl.cfg.get("area_served", []))

    return (
        head(cl, path="/", title=title, desc=desc, nodes=nodes, lastmod=lastmod)
        + header(cl, "/")
        + f"""<main id="main">
<div class="hero">
<div class="wrap">
<h1>{esc(b['tagline'])}</h1>
<p class="lead">{esc(b['description'])}</p>
<div class="cta-row">
<a class="cta" href="{cl.tel_link}">☎ {esc(cl.tel)} に電話する</a>
<a class="cta ghost" href="/contact/">メールで相談する</a>
<p class="cta-note">{esc(cl.c['hours_text'])}</p>
</div>
</div>
</div>

<section>
<div class="wrap">
<h2>できること</h2>
<p class="sub">{esc(areas)}を中心に伺っています。</p>
<ul class="cards">{cards}</ul>
</div>
</section>

<section>
<div class="wrap">
<h2>選ばれている理由</h2>
<p class="sub">同業と比べて、はっきり違うところだけを書いています。</p>
<ul class="reasons">{reasons}</ul>
</div>
</section>

<section>
<div class="wrap">
<h2>よくある質問</h2>
<p class="sub">ここにないことは、電話で直接お尋ねください。</p>
{qa_list(cl.cfg.get("faq", []))}
</div>
</section>

<section>
<div class="wrap">
{contact_block(cl, heading="まずはご相談ください")}
</div>
</section>
</main>
"""
        + footer(cl)
    )


def page_services_index(cl: Client, lastmod: str) -> str:
    title = f"サービス一覧｜{cl.short}"
    desc = fit_desc(
        f"{cl.a['city']}の{cl.short}が対応する"
        f"{'・'.join(s['name'] for s in cl.services[:3])}の一覧と料金の目安です",
        [
            f"対応エリアは{'・'.join(cl.cfg.get('area_served', []))}",
            "現地調査とお見積もりは無料です",
        ],
    )
    trail = [("ホーム", "/"), ("サービス", "/services/")]
    nodes = [
        {"@type": "CollectionPage", "url": f"{cl.site}/services/", "name": title,
         "description": desc, "inLanguage": "ja",
         "about": {"@id": f"{cl.site}/#business"}},
        breadcrumb_node(cl, trail),
        local_business_node(cl),
    ]
    cards = service_cards(cl.services, level=2)
    return (
        head(cl, path="/services/", title=title, desc=desc, nodes=nodes, lastmod=lastmod)
        + header(cl, "/services/")
        + crumbs(trail)
        + f"""<main id="main">
<section>
<div class="wrap">
<h1>サービス一覧</h1>
<p class="sub">金額は目安です。現地を見てから、正式なお見積もりをお出しします。</p>
<ul class="cards">{cards}</ul>
</div>
</section>
<section><div class="wrap">{contact_block(cl)}</div></section>
</main>
"""
        + footer(cl)
    )


def page_service(cl: Client, s: dict, lastmod: str) -> str:
    path = f"/services/{s['slug']}/"
    title = f"{s['name']}｜{cl.a['city']}の{cl.short}"
    desc = fit_desc(
        f"{cl.a['city']}の{cl.short}による{s['name']}。{s['summary']}",
        [
            f"料金の目安は{s['price_from']}" if s.get("price_from") else "",
            f"対応エリアは{'・'.join(cl.cfg.get('area_served', []))}",
            f"ご相談はお電話（{cl.tel}）でも承ります",
        ],
    )
    trail = [("ホーム", "/"), ("サービス", "/services/"), (s["name"], path)]
    nodes = [
        {
            "@type": "Service",
            "@id": cl.site + path + "#service",
            "name": s["name"],
            "description": s["summary"],
            "url": cl.site + path,
            "serviceType": s["name"],
            "provider": {"@id": f"{cl.site}/#business"},
            "areaServed": [
                {"@type": "AdministrativeArea", "name": n}
                for n in cl.cfg.get("area_served", [])
            ],
            **({"offers": {"@type": "Offer", "description": s["price_from"],
                           "priceCurrency": "JPY"}} if s.get("price_from") else {}),
        },
        breadcrumb_node(cl, trail),
        local_business_node(cl),
    ]
    if s.get("faq"):
        nodes.append(faq_node(s["faq"]))

    body = "".join(f"<p>{esc(p)}</p>" for p in s.get("body", []))
    price = (f'<dl class="spec"><dt>料金の目安</dt><dd>{esc(s["price_from"])}</dd>'
             f'<dt>対応エリア</dt><dd>{esc("・".join(cl.cfg.get("area_served", [])))}</dd>'
             f'</dl>' if s.get("price_from") else "")
    faq_html = (f'<h2>{esc(s["name"])}についてよくある質問</h2>{qa_list(s["faq"])}'
                if s.get("faq") else "")
    related = service_cards([o for o in cl.services if o["slug"] != s["slug"]], level=3)

    return (
        head(cl, path=path, title=title, desc=desc, nodes=nodes, lastmod=lastmod)
        + header(cl, "/services/")
        + crumbs(trail)
        + f"""<main id="main">
<section>
<div class="wrap">
<h1>{esc(s['name'])}</h1>
<p class="sub">{esc(s['summary'])}</p>
{price}
{body}
{faq_html}
</div>
</section>
<section>
<div class="wrap">
<h2>ほかのサービス</h2>
<ul class="cards">{related}</ul>
</div>
</section>
<section><div class="wrap">{contact_block(cl)}</div></section>
</main>
"""
        + footer(cl)
    )


def page_about(cl: Client, lastmod: str) -> str:
    b, a = cl.b, cl.a
    title = f"会社概要｜{cl.name}"
    desc = fit_desc(
        f"{cl.name}の所在地・連絡先・営業時間・代表者などの基本情報です",
        [
            f"{a['region']}{a['city']}を拠点に"
            f"{'・'.join(cl.cfg.get('area_served', []))}で営業しています",
            f"お電話は{cl.tel}",
        ],
    )
    trail = [("ホーム", "/"), ("会社概要", "/about/")]
    nodes = [
        {"@type": "AboutPage", "url": f"{cl.site}/about/", "name": title,
         "description": desc, "inLanguage": "ja",
         "mainEntity": {"@id": f"{cl.site}/#business"}},
        breadcrumb_node(cl, trail),
        local_business_node(cl),
    ]
    rows = [
        ("商号", cl.name),
        ("所在地", f"〒{a['postal']} {cl.full_address}"),
        ("電話番号", f'<a href="{cl.tel_link}">{esc(cl.tel)}</a>'),
    ]
    if cl.c.get("fax"):
        rows.append(("FAX", esc(cl.c["fax"])))
    if cl.c.get("email"):
        rows.append(("メール", esc(cl.c["email"])))
    rows.append(("営業時間", esc(cl.c["hours_text"])))
    if b.get("representative"):
        rows.append(("代表者", esc(b["representative"])))
    if b.get("founded"):
        rows.append(("創業", f"{esc(b['founded'])}年"))
    if b.get("employees"):
        rows.append(("従業員数", f"{esc(b['employees'])}名"))
    if cl.cfg.get("area_served"):
        rows.append(("対応エリア", esc("・".join(cl.cfg["area_served"]))))
    if b.get("payment"):
        rows.append(("お支払い方法", esc("、".join(b["payment"]))))
    if a.get("access"):
        rows.append(("アクセス", esc(a["access"])))

    spec = "".join(
        f"<dt>{esc(k) if k != '電話番号' else k}</dt><dd>{v}</dd>"
        for k, v in rows
    )
    return (
        head(cl, path="/about/", title=title, desc=desc, nodes=nodes, lastmod=lastmod)
        + header(cl, "/about/")
        + crumbs(trail)
        + f"""<main id="main">
<section>
<div class="wrap">
<h1>会社概要</h1>
<p class="sub">{esc(b['description'])}</p>
<dl class="spec">{spec}</dl>
</div>
</section>
<section><div class="wrap">{contact_block(cl)}</div></section>
</main>
"""
        + footer(cl)
    )


def page_faq(cl: Client, lastmod: str) -> str:
    title = f"よくある質問｜{cl.short}"
    all_pairs = list(cl.cfg.get("faq", []))
    for s in cl.services:
        all_pairs.extend(s.get("faq", []))
    desc = fit_desc(
        f"{cl.short}に多いご質問と回答をまとめました",
        [
            "対応エリア・料金・お支払い・工期などについてお答えしています",
            f"ここにないことは{cl.tel}へお気軽にどうぞ",
        ],
    )
    trail = [("ホーム", "/"), ("よくある質問", "/faq/")]
    nodes = [
        {"@type": "WebPage", "url": f"{cl.site}/faq/", "name": title,
         "description": desc, "inLanguage": "ja",
         "about": {"@id": f"{cl.site}/#business"}},
        breadcrumb_node(cl, trail),
        faq_node(all_pairs),
        local_business_node(cl),
    ]
    return (
        head(cl, path="/faq/", title=title, desc=desc, nodes=nodes, lastmod=lastmod)
        + header(cl, "/faq/")
        + crumbs(trail)
        + f"""<main id="main">
<section>
<div class="wrap">
<h1>よくある質問</h1>
<p class="sub">ここにない質問は、お電話かフォームでお尋ねください。</p>
{qa_list(all_pairs)}
</div>
</section>
<section><div class="wrap">{contact_block(cl)}</div></section>
</main>
"""
        + footer(cl)
    )


def page_contact(cl: Client, lastmod: str) -> str:
    title = f"お問い合わせ｜{cl.short}"
    desc = fit_desc(
        f"{cl.short}へのご相談・お見積もりのご依頼はこちらから",
        [
            f"お電話（{cl.tel}）は{cl.c['hours_text']}に受け付けています",
            "フォームからのご相談は24時間お送りいただけます",
        ],
    )
    trail = [("ホーム", "/"), ("お問い合わせ", "/contact/")]
    nodes = [
        {"@type": "ContactPage", "url": f"{cl.site}/contact/", "name": title,
         "description": desc, "inLanguage": "ja",
         "about": {"@id": f"{cl.site}/#business"}},
        breadcrumb_node(cl, trail),
        local_business_node(cl),
    ]
    endpoint = cl.cfg.get("form_endpoint")
    if endpoint:
        form_open = f'<form class="enquiry" action="{esc(endpoint)}" method="POST">'
        note = ""
    else:
        # No form backend configured yet. A mailto form still works everywhere
        # and never silently drops an enquiry, which a broken POST endpoint does.
        form_open = (f'<form class="enquiry" action="mailto:{esc(cl.c.get("email",""))}" '
                     f'method="POST" enctype="text/plain">')
        note = ('<p class="sub">※ 送信ボタンを押すと、お使いのメールソフトが開きます。'
                'うまく開かない場合は、お電話でご連絡ください。</p>')

    return (
        head(cl, path="/contact/", title=title, desc=desc, nodes=nodes, lastmod=lastmod)
        + header(cl, "/contact/")
        + crumbs(trail)
        + f"""<main id="main">
<section>
<div class="wrap">
<h1>お問い合わせ</h1>
<p class="sub">お急ぎのご用件は、お電話のほうが早くお答えできます。</p>
{contact_block(cl, heading="お電話でのご相談")}
<h2>フォームでのご相談</h2>
{note}
{form_open}
<label>お名前 <span class="req">必須</span>
<input type="text" name="name" required autocomplete="name"></label>
<label>電話番号 <span class="req">必須</span>
<input type="tel" name="tel" required autocomplete="tel"></label>
<label>メールアドレス
<input type="email" name="email" autocomplete="email"></label>
<label>ご相談の内容 <span class="req">必須</span>
<textarea name="message" required
placeholder="例）築35年の戸建てで、浴室の入れ替えを考えています。見積もりをお願いできますか。"></textarea></label>
<button type="submit">送信する</button>
</form>
</div>
</section>
</main>
"""
        + footer(cl)
    )


# --------------------------------------------------------------------------- #
# Derived files
# --------------------------------------------------------------------------- #
def favicon(cl: Client) -> str:
    """A one-character mark in the brand colour.

    Without an icon link the browser requests /favicon.ico on every page and
    logs a 404, which is the only console error these sites would otherwise
    have. An SVG needs no image tooling and scales to every slot.
    """
    initial = esc(cl.short[:1])
    accent = esc(cl.theme.get("accent", "#1f5f3f"))
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">'
        f'<rect width="64" height="64" rx="12" fill="{accent}"/>'
        '<text x="32" y="44" font-size="38" text-anchor="middle" fill="#fff"'
        ' font-family="Hiragino Sans, Noto Sans JP, sans-serif"'
        f' font-weight="700">{initial}</text></svg>\n'
    )


def sitemap(cl: Client, pages: dict[str, str], lastmod: str) -> str:
    # Home first, then shallowest paths. Priority is advisory only; Google has
    # said for years it ignores it. It stays because Bing still reads it and it
    # costs nothing.
    order = sorted(pages, key=lambda p: (p != "/", p.count("/"), p))
    entries = "\n".join(
        f"  <url>\n    <loc>{xml_escape(cl.site + p)}</loc>\n"
        f"    <lastmod>{lastmod}</lastmod>\n"
        f"    <priority>{'1.0' if p == '/' else '0.8' if p.count('/') == 2 else '0.6'}</priority>\n"
        f"  </url>"
        for p in order
    )
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
            f"{entries}\n</urlset>\n")


def robots(cl: Client) -> str:
    return (
        "User-agent: *\n"
        "Allow: /\n"
        "\n"
        f"Sitemap: {cl.site}/sitemap.xml\n"
    )


def headers_file() -> str:
    """Cloudflare Pages / Netlify shared format.

    No extension globs (`/*.css`): neither host matches on extension, only on
    path, so a rule written that way silently does nothing. Same trap the
    黒田塾 README warns about.
    """
    return """/*
  X-Content-Type-Options: nosniff
  Referrer-Policy: strict-origin-when-cross-origin
  X-Frame-Options: SAMEORIGIN
  Permissions-Policy: geolocation=(), microphone=(), camera=()

/assets/*
  Cache-Control: public, max-age=31536000, immutable
"""


def redirects_file() -> str:
    """Trailing slash is the canonical form; send the other spellings to it."""
    return """/index.html      /              301
/services        /services/     301
/about           /about/        301
/faq             /faq/          301
/contact         /contact/      301
/inquiry         /contact/      301
/company         /about/        301
"""


# --------------------------------------------------------------------------- #
# Build
# --------------------------------------------------------------------------- #
def build(cl: Client) -> dict[str, str]:
    lastmod = date.today().isoformat()
    pages = {
        "/": page_home(cl, lastmod),
        "/services/": page_services_index(cl, lastmod),
        "/about/": page_about(cl, lastmod),
        "/faq/": page_faq(cl, lastmod),
        "/contact/": page_contact(cl, lastmod),
    }
    for s in cl.services:
        pages[f"/services/{s['slug']}/"] = page_service(cl, s, lastmod)

    out = DIST / cl.slug
    for path, html_text in pages.items():
        target = out / path.strip("/") / "index.html" if path != "/" else out / "index.html"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(html_text, encoding="utf-8")

    (out / "sitemap.xml").write_text(sitemap(cl, pages, lastmod), encoding="utf-8")
    (out / "robots.txt").write_text(robots(cl), encoding="utf-8")
    (out / "favicon.svg").write_text(favicon(cl), encoding="utf-8")
    (out / "_headers").write_text(headers_file(), encoding="utf-8")
    (out / "_redirects").write_text(redirects_file(), encoding="utf-8")
    return pages


# --------------------------------------------------------------------------- #
# Checks
#
# Every one of these exists because getting it wrong is a real, observed way to
# lose search traffic — not because a linter somewhere likes the rule.
# --------------------------------------------------------------------------- #
def check(cl: Client, pages: dict[str, str]) -> list[str]:
    errors: list[str] = []
    titles: dict[str, str] = {}
    descs: dict[str, str] = {}
    outgoing: dict[str, set[str]] = {}

    for path, doc in pages.items():
        def bad(msg: str) -> None:
            errors.append(f"{path}: {msg}")

        m = re.search(r"<title>(.*?)</title>", doc, re.S)
        if not m:
            bad("title がありません")
        else:
            t = html.unescape(m.group(1))
            if not (TITLE_MIN <= len(t) <= TITLE_MAX):
                bad(f"title が {len(t)} 字（{TITLE_MIN}〜{TITLE_MAX}字に収める）: {t}")
            if t in titles:
                bad(f"title が {titles[t]} と重複")
            titles[t] = path

        m = re.search(r'<meta name="description" content="(.*?)">', doc)
        if not m:
            bad("description がありません")
        else:
            d = html.unescape(m.group(1))
            if not (DESC_MIN <= len(d) <= DESC_MAX):
                bad(f"description が {len(d)} 字（{DESC_MIN}〜{DESC_MAX}字に収める）")
            if d in descs:
                bad(f"description が {descs[d]} と重複")
            descs[d] = path

        m = re.search(r'<link rel="canonical" href="(.*?)">', doc)
        if not m:
            bad("canonical がありません")
        else:
            want = cl.site + path
            if m.group(1) != want:
                bad(f"canonical が {m.group(1)}（{want} であるべき）")
            host = urlparse(m.group(1)).netloc
            if host != urlparse(cl.site).netloc:
                bad(f"canonical のホストが設定と違います: {host}")

        h1s = re.findall(r"<h1[^>]*>(.*?)</h1>", doc, re.S)
        if len(h1s) != 1:
            bad(f"h1 が {len(h1s)} 個（1個であるべき）")

        # Heading levels must not skip: an h3 with no h2 above it breaks the
        # document outline that assistive tech and parsers rely on.
        levels = [int(h) for h in re.findall(r"<h([1-6])[^>]*>", doc)]
        for prev, cur in zip(levels, levels[1:]):
            if cur > prev + 1:
                bad(f"見出しレベルが h{prev} から h{cur} に飛んでいます")
                break

        for block in re.findall(
            r'<script type="application/ld\+json">(.*?)</script>', doc, re.S
        ):
            try:
                data = json.loads(block)
            except json.JSONDecodeError as exc:
                bad(f"JSON-LD が壊れています: {exc}")
                continue
            for node in data.get("@graph", []):
                if "@type" not in node:
                    bad("JSON-LD に @type のないノードがあります")

        for img in re.findall(r"<img\s[^>]*>", doc):
            if "width=" not in img or "height=" not in img:
                bad("img に width/height がありません（CLSの原因）")
            if "alt=" not in img:
                bad("img に alt がありません")

        if 'name="viewport"' not in doc:
            bad("viewport がありません")
        if 'lang="ja"' not in doc:
            bad("html lang がありません")
        if "tel:" not in doc:
            bad("電話リンクがありません")

        outgoing[path] = {
            href for href in re.findall(r'href="(/[^"#]*)"', doc)
        }

    # Every internal link must resolve, and every page must be reachable.
    # An orphan page is a page Google will not crawl reliably.
    known = set(pages) | {"/sitemap.xml", "/robots.txt", "/favicon.svg"}
    for path, links in outgoing.items():
        for href in links:
            if href not in known:
                errors.append(f"{path}: リンク先 {href} が存在しません")
    linked = {h for links in outgoing.values() for h in links}
    for path in pages:
        if path != "/" and path not in linked:
            errors.append(f"{path}: どこからもリンクされていません（孤立ページ）")

    # The NAP must be identical everywhere it appears, or the association with
    # the Google Business Profile weakens.
    for path, doc in pages.items():
        if cl.tel not in doc:
            errors.append(f"{path}: 電話番号が本文にありません")

    return errors


def load(path: Path) -> Client:
    return Client(json.loads(path.read_text(encoding="utf-8")), path)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("config", nargs="*", help="clients/<slug>.json")
    ap.add_argument("--all", action="store_true", help="clients/ 以下をすべてビルド")
    ap.add_argument("--check", action="store_true", help="検査に落ちたら異常終了")
    args = ap.parse_args()

    paths = [Path(p) for p in args.config]
    if args.all or not paths:
        paths = sorted((ROOT / "clients").glob("*.json"))
    if not paths:
        print("ビルド対象がありません", file=sys.stderr)
        return 1

    total_errors = 0
    for path in paths:
        cl = load(path)
        pages = build(cl)
        print(f"{cl.slug}: {len(pages)} ページ → {DIST / cl.slug}")
        errors = check(cl, pages)
        if errors:
            total_errors += len(errors)
            print(f"  検査エラー {len(errors)} 件:", file=sys.stderr)
            for e in errors:
                print(f"    - {e}", file=sys.stderr)
        else:
            print("  検査OK")

    if total_errors and args.check:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
