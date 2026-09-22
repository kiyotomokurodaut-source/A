#!/usr/bin/env python3
"""Find businesses that can be emailed legally, and that visibly need the work.

Why this exists
---------------
The first list (``data/out/prospects.csv``) is businesses with no website. It
is a good list — but it cannot be emailed. Only 0.9% of those rows carry an
email address, and that is not a gap in the data, it is the definition: a
company with no web presence has not published an address anywhere. 特定電子
メール法 exempts unsolicited advertising only for **published** addresses of
businesses, so for that segment the legal channels are the phone, fax and post.

The companies an email *can* reach are the ones that already have a site. That
turns out to be the better list anyway, for three reasons:

* they have an address published, so the exemption applies;
* they have already paid for a website once, so the budget exists;
* the pitch is a checkable fact about their own page rather than an offer.

So this script visits each site from ``with_site.csv`` and works out two things:
the address to write to, and whether the site is old enough that saying so is
true.

What counts as "needs the work"
-------------------------------
Every signal here is something the owner can verify in ten seconds, which is
what makes the email land. No judgement calls about taste.

* **No viewport meta** — the page does not adapt to a phone. The single most
  damaging fault, and instantly visible to the owner on their own phone.
* **No HTTPS** — Chrome marks it "保護されていない通信".
* **Table-based layout / frames** — a page built before about 2012.
* **No structured data, no canonical, no Open Graph** — shares look broken and
  the page gives search engines nothing.
* **A stale copyright year** — the clearest "nobody has touched this" signal.

Refusals are honoured
---------------------
A site whose contact page says 営業お断り、セールスお断り、勧誘お断り is
dropped, and never written to. Under 特定電子メール法 that notice removes the
published-address exemption, so mailing them would be an offence rather than a
nuisance. The dropped rows are written out separately so the decision is
auditable.

Usage
-----
    python3 find_email_targets.py                  # data/out/with_site.csv を処理
    python3 find_email_targets.py --limit 200
    python3 find_email_targets.py --min-need 3
"""

from __future__ import annotations

import argparse
import concurrent.futures
import csv
import gzip
import http.client
import io
import re
import socket
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request
import zlib
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "out"
SRC = OUT / "with_site_jp.csv"

# HTTP headers are latin-1 only, so this string must stay ASCII. A Japanese
# User-Agent raises UnicodeEncodeError inside http.client and every fetch
# silently returns None, which reads as "the whole internet is down".
UA = ("Mozilla/5.0 (compatible; smb-site-audit/1.0; "
      "small-business website audit; contact in message body)")
FAILURES: list[str] = []
TIMEOUT = 12
WORKERS = 12          # polite: one small business site at a time, eight at once
MAX_BYTES = 400_000  # a brochure site's homepage; anything larger is not read

# Pages that carry the contact address, in the order worth trying.
CONTACT_PATHS = ["", "/contact/", "/contact.html", "/inquiry/", "/company/",
                 "/about/", "/toiawase/", "/contact/index.html"]

# The notice that removes the published-address exemption. If any of these
# appears anywhere on the pages fetched, the company is never mailed.
REFUSAL = re.compile(
    r"営業[メーmail]*[のはを]?[ご]?[お]?断り|セールス[のはを]?[ご]?[お]?断り"
    r"|勧誘[のはを]?[ご]?[お]?断り|営業目的[のでは].{0,8}お断り"
    r"|営業。?メール.{0,6}お断り|売り込み.{0,6}お断り"
    r"|no[- ]?solicitation|営業行為[はを].{0,6}禁[じし]"
)

EMAIL_RE = re.compile(
    r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")

# Addresses that belong to the site's builder, a form service, or a template
# the owner never replaced. "mail@yourmail.com" is a placeholder from a theme
# and turns up verbatim on real sites; writing to it reaches nobody.
EMAIL_SKIP = re.compile(
    r"^(example|test|sample|noreply|no-reply|donotreply|webmaster@|postmaster@"
    r"|your[-_]?(mail|email|name)@|email@|admin@localhost)"
    r"|@(example|sentry|wixpress|sample|yourmail|yourdomain|domain\.com"
    r"|email\.com|test\.)", re.I)

# Universities, schools, government bodies and local authorities. They appear
# in the data because they have a phone and an ageing site, but they are not
# buying a 30,000 yen website from a cold email — procurement does not work
# that way — and mailing them is purely a waste of both sides' time.
PUBLIC_DOMAIN = re.compile(r"\.(ac|go|lg|ed)\.jp$|\.(gov|edu)$", re.I)

# Mailbox providers a small Japanese business plausibly uses as its own
# contact address. Anything outside these that does not match the site's own
# domain is almost certainly somebody else's address picked up off the page —
# a supplier, a listing site, the agency that built it. Writing to those
# reaches the wrong company: one run produced naya@recruit.co.jp for a studio
# whose site is studio-naya.co.jp.
CONSUMER_MAIL = {
    "gmail.com", "yahoo.co.jp", "ybb.ne.jp", "outlook.com", "outlook.jp",
    "hotmail.com", "hotmail.co.jp", "icloud.com", "me.com", "live.jp",
    "nifty.com", "ocn.ne.jp", "biglobe.ne.jp", "so-net.ne.jp", "plala.or.jp",
    "dion.ne.jp", "auone.jp", "ezweb.ne.jp", "docomo.ne.jp", "softbank.ne.jp",
    "jcom.home.ne.jp", "jcom.zaq.ne.jp", "zaq.ne.jp", "kcn.jp", "wakwak.com",
    "tiki.ne.jp", "sannet.ne.jp", "mopera.net", "ne.jp", "or.jp",
}


def registrable(host: str) -> str:
    """A rough eTLD+1 for comparing a mail domain with a site domain."""
    parts = host.lower().removeprefix("www.").split(".")
    if len(parts) >= 3 and parts[-2] in ("co", "or", "ne", "ac", "go", "lg", "gr"):
        return ".".join(parts[-3:])
    return ".".join(parts[-2:])


def tidy_url(url: str) -> str:
    """Repair the ways a URL gets mistyped into OSM, or give up cleanly."""
    url = url.strip().split()[0] if url.strip() else ""
    url = re.sub(r"^h?ttps?[;:]?//", lambda m: "https://" if "s" in m.group(0)
                 else "http://", url, flags=re.I)
    if url and not url.startswith(("http://", "https://")):
        url = "http://" + url.lstrip("/")
    return url


def fetch(url: str) -> tuple[str, str] | None:
    """Return (final_url, text) or None. Never raises."""
    # A small business site often has a certificate that is expired or issued
    # for a different name. That is itself a finding, not a reason to give up
    # on reading the page, so verification is relaxed for this read only.
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": UA,
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "ja,en;q=0.7",
            "Accept-Encoding": "identity",
        })
        with urllib.request.urlopen(req, timeout=TIMEOUT, context=ctx) as resp:
            raw = resp.read(MAX_BYTES)
            if resp.headers.get("Content-Encoding") == "gzip":
                # Some servers gzip regardless of Accept-Encoding. A truncated
                # read cannot be inflated, so take whatever decoded cleanly.
                try:
                    raw = gzip.GzipFile(fileobj=io.BytesIO(raw)).read()
                except (OSError, EOFError):
                    try:
                        raw = zlib.decompressobj(16 + zlib.MAX_WBITS).decompress(raw)
                    except zlib.error:
                        return None
            charset = resp.headers.get_content_charset()
            final = resp.geturl()
    except (urllib.error.URLError, urllib.error.HTTPError, socket.timeout,
            ssl.SSLError, ConnectionError, OSError, ValueError,
            http.client.HTTPException) as exc:
        FAILURES.append(f"{url}: {type(exc).__name__}: {exc}")
        return None
    except Exception as exc:                      # noqa: BLE001
        # Anything unexpected is a bug in this script, not in their site.
        # Swallowing it silently once cost an entire run.
        FAILURES.append(f"{url}: BUG {type(exc).__name__}: {exc}")
        return None

    if not charset:
        head = raw[:2000].decode("ascii", "ignore").lower()
        m = re.search(r'charset=["\']?([\w\-]+)', head)
        charset = m.group(1) if m else "utf-8"
    for enc in (charset, "utf-8", "cp932", "euc-jp"):
        try:
            return final, raw.decode(enc)
        except (UnicodeDecodeError, LookupError):
            continue
    return final, raw.decode("utf-8", "replace")


def find_emails(html: str, host: str) -> list[str]:
    """Prefer an address on the company's own domain; drop obvious noise."""
    found = []
    for m in re.finditer(r'mailto:([^"\'?>\s]+)', html):
        found.append(urllib.parse.unquote(m.group(1)))
    found.extend(EMAIL_RE.findall(html))
    # Sites often write the address as "info(at)example.jp" to dodge scrapers.
    # That is a request not to be harvested; it is honoured by not decoding it.
    clean, seen = [], set()
    domain = host.removeprefix("www.")
    for e in found:
        e = e.strip().strip(".,;:)")
        low = e.lower()
        if low in seen or EMAIL_SKIP.search(low) or len(e) > 100:
            continue
        mail_host = low.split("@")[-1]
        if PUBLIC_DOMAIN.search(mail_host):
            continue
        # Keep it only if it is the company's own domain, or a mailbox provider
        # a small firm would actually use. Otherwise it belongs to someone else.
        if (registrable(mail_host) != registrable(host)
                and mail_host not in CONSUMER_MAIL
                and registrable(mail_host) not in CONSUMER_MAIL):
            continue
        if not EMAIL_RE.fullmatch(e):
            continue
        seen.add(low)
        clean.append(e)
    clean.sort(key=lambda e: (domain not in e.lower(),
                              not e.lower().startswith(("info@", "mail@",
                                                        "contact@"))))
    return clean[:3]


def audit(html: str, final_url: str) -> tuple[int, list[str]]:
    """Score how badly the site needs replacing, and say why in plain words."""
    need, why = 0, []
    low = html.lower()

    if not re.search(r'<meta[^>]+name=["\']?viewport', low):
        need += 3
        why.append("スマホ対応なし（viewportの指定がない）")
    if final_url.startswith("http://"):
        need += 3
        why.append("常時SSL化されていない（Chromeで「保護されていない通信」と出る）")
    if re.search(r"<frameset|<frame\s", low):
        need += 3
        why.append("フレーム構造（2000年代前半の作り）")
    elif len(re.findall(r"<table", low)) >= 6 and "grid-template" not in low:
        need += 2
        why.append("テーブルレイアウト（2010年頃までの作り）")
    if "application/ld+json" not in low:
        need += 1
        why.append("構造化データなし")
    if not re.search(r'rel=["\']?canonical', low):
        need += 1
        why.append("canonicalなし")
    if "og:title" not in low:
        need += 1
        why.append("OGP なし（SNSで共有すると中身が出ない）")
    if re.search(r"\.swf|shockwave-flash", low):
        need += 3
        why.append("Flashが残っている（2020年に全ブラウザで廃止済み）")

    years = [int(y) for y in re.findall(
        r"(?:©|&copy;|copyright)[^0-9]{0,20}((?:19|20)\d{2})", low)]
    if years:
        newest = max(years)
        age = date.today().year - newest
        if age >= 3:
            need += 2
            why.append(f"著作権表記が{newest}年のまま（{age}年放置）")
    return need, why


def check(row: dict) -> dict | None:
    """Audit one site. Returns a row whatever happens — never raises.

    pool.map propagates the first exception and discards the rest of the run,
    so every failure has to be turned into data here.
    """
    try:
        return _check(row)
    except Exception as exc:                      # noqa: BLE001
        FAILURES.append(f"{row.get('サイト','')}: BUG {type(exc).__name__}: {exc}")
        row["判定"] = "調査中にエラー（電話向け）"
        row["メール"] = ""
        row["必要度"] = 0
        return row


def _check(row: dict) -> dict | None:
    url = tidy_url(row["サイト"])
    if not url:
        row["判定"] = "URLが空（電話向け）"
        row["メール"] = ""
        row["必要度"] = 0
        return row
    host = urllib.parse.urlparse(url).netloc.lower()
    # Keep the URL the business itself published. Following redirects can land
    # on a shared-hosting root — several of these sites live at addresses like
    # http://www.ksky.ne.jp/~ihara/ — and quoting that root back to them as
    # "your page" is both wrong and obviously careless.
    row["掲載URL"] = url

    got = fetch(url)
    if not got:
        # A site that will not load at all is the strongest pitch there is,
        # but there is no address to write to, so it goes to the phone list.
        row["判定"] = "サイトが表示できない（電話向け）"
        row["メール"] = ""
        row["必要度"] = 99
        return row

    final, html = got
    pages = [html]
    emails = find_emails(html, host)

    # Only go looking for a contact page if the homepage had no address.
    if not emails:
        base = f"{urllib.parse.urlparse(final).scheme}://{urllib.parse.urlparse(final).netloc}"
        for path in CONTACT_PATHS[1:4]:
            more = fetch(base + path)
            if more:
                pages.append(more[1])
                emails = find_emails(more[1], host)
                if emails:
                    break

    joined = "".join(pages)
    if REFUSAL.search(joined):
        row["判定"] = "営業お断りの表示あり → 送信しない"
        row["メール"] = ""
        row["必要度"] = -1
        return row

    need, why = audit(html, final)
    row["メール"] = emails[0] if emails else ""
    row["メール候補"] = " / ".join(emails[1:])
    row["必要度"] = need
    row["根拠"] = " / ".join(why)
    row["最終URL"] = final
    row["判定"] = "送付可" if emails else "アドレス見つからず（電話向け）"
    return row


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--src", type=Path, default=SRC)
    ap.add_argument("--limit", type=int, help="先頭からこの件数だけ調べる")
    ap.add_argument("--min-need", type=int, default=2,
                    help="この必要度未満は送付先にしない（既定2）")
    args = ap.parse_args()

    if not args.src.exists():
        sys.exit(f"{args.src} がありません。先に harvest_osm.py を実行してください")
    with args.src.open(encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh))
    if args.limit:
        rows = rows[: args.limit]
    print(f"{len(rows)} 件のサイトを確認します", flush=True)

    done = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as pool:
        for i, res in enumerate(pool.map(check, rows), 1):
            if res:
                done.append(res)
            if i % 25 == 0:
                print(f"  {i}/{len(rows)}", flush=True)

    refused = [r for r in done if r["必要度"] == -1]
    sendable = [r for r in done
                if r["判定"] == "送付可" and r["必要度"] >= args.min_need]
    phone_only = [r for r in done if r["判定"].endswith("（電話向け）")]
    sendable.sort(key=lambda r: (-r["必要度"], -int(r["スコア"])))

    cols = ["必要度", "スコア", "屋号", "業種", "都道府県", "市区町村",
            "メール", "電話", "根拠", "掲載URL", "最終URL", "住所",
            "メール候補", "判定", "接触状況"]

    def write(name: str, data: list[dict]) -> None:
        path = OUT / name
        with path.open("w", encoding="utf-8-sig", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
            w.writeheader()
            for r in data:
                r.setdefault("接触状況", "")
                w.writerow(r)
        print(f"{name}: {len(data)} 件 → {path}")

    write("email_targets.csv", sendable)
    write("email_excluded.csv", refused)
    write("phone_only.csv", phone_only)

    bugs = [f for f in FAILURES if " BUG " in f]
    if bugs:
        print(f"\n!! スクリプト側の不具合が {len(bugs)} 件:", file=sys.stderr)
        for b in bugs[:3]:
            print(f"   {b}", file=sys.stderr)
    print(f"\n確認 {len(done)} 件 → 送付可 {len(sendable)}"
          f" ／ 営業お断り {len(refused)}"
          f" ／ アドレスなし・不通 {len(phone_only)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
