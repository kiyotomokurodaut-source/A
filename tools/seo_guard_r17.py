#!/usr/bin/env python3
"""Additional deterministic checks. No external network or ranking claims."""
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlsplit, unquote
import collections
import hashlib
import json
import re
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
SITE = 'https://kurodaschool.jp'

class Page(HTMLParser):
    def __init__(self, raw):
        super().__init__(convert_charrefs=True)
        self.ids = []; self.canonical = []; self.meta = {}; self.refs = []; self.links = []
        self.jsonld = []; self._script = None; self._buf = []
        self.feed(raw)
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if a.get('id'): self.ids.append(a['id'])
        if tag == 'meta': self.meta[a.get('name', a.get('property', ''))] = a.get('content', '')
        if tag == 'link' and 'canonical' in a.get('rel', '').split(): self.canonical.append(a.get('href', ''))
        if tag == 'link' and 'stylesheet' in a.get('rel', '').split(): self.refs.append(a.get('href', ''))
        if tag in {'img', 'script'} and a.get('src'): self.refs.append(a['src'])
        if tag == 'a' and a.get('href'): self.links.append(a['href'])
        if tag == 'script' and a.get('type') == 'application/ld+json': self._script = True; self._buf = []
    def handle_data(self, text):
        if self._script: self._buf.append(text)
    def handle_endtag(self, tag):
        if tag == 'script' and self._script:
            self.jsonld.append(json.loads(''.join(self._buf))); self._script = None

def route(p, public):
    r = p.relative_to(public).as_posix()
    return '/' if r == 'index.html' else '/' + r[:-10] if r.endswith('/index.html') else '/' + r

def local_target(ref, origin_path, public):
    from urllib.parse import urljoin
    url = urlsplit(urljoin(SITE + origin_path, ref))
    if url.netloc != 'kurodaschool.jp': return None
    p = public / unquote(url.path).lstrip('/')
    return p / 'index.html' if p.is_dir() else p

def validate(root: Path) -> dict:
    public = root / 'public'; errors = []; pages = {}; indexable = set()
    for p in sorted(public.rglob('*.html')):
        raw = p.read_text(encoding='utf-8'); url = route(p, public)
        try: parsed = Page(raw)
        except Exception as e: errors.append(f'{url}: HTML/JSON-LD parsing failed: {e}'); continue
        pages[url] = parsed
        if 'noindex' not in parsed.meta.get('robots', '').lower():
            indexable.add(SITE + url)
            if parsed.canonical != [SITE + url]: errors.append(f'{url}: wrong/multiple canonical')
        if 'r17-' in raw:
            dup = [i for i,c in collections.Counter(parsed.ids).items() if c > 1]
            if dup: errors.append(f'{url}: duplicate ids: {dup}')
        for ref in parsed.refs:
            if not ref or ref.startswith(('data:', 'blob:')): continue
            target = local_target(ref, url, public)
            if target is not None and not target.is_file(): errors.append(f'{url}: missing asset {ref}')
        for block in parsed.jsonld:
            roots = block if isinstance(block, list) else [block]
            for obj in roots:
                nodes = obj.get('@graph', [obj]) if isinstance(obj, dict) else []
                for node in nodes:
                    if not isinstance(node, dict): continue
                    for key in ('url', '@id'):
                        v = node.get(key, '')
                        if isinstance(v, str) and 'kiyotomokuroda.pages.dev' in v: errors.append(f'{url}: legacy schema URL')
    site_map = ET.parse(public / 'sitemap.xml')
    listed = [e.text for e in site_map.findall('{http://www.sitemaps.org/schemas/sitemap/0.9}url/{http://www.sitemaps.org/schemas/sitemap/0.9}loc')]
    if len(listed) != len(set(listed)) or set(listed) != indexable: errors.append('Sitemap URLs do not match indexable HTML pages')
    # Check the exact asset copies and guard against stale content under immutable URLs.
    manifest_path = root / 'tools/r17_assets.json'
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text())
        for url, digest in manifest.items():
            p = public / url.lstrip('/')
            if not p.exists() or hashlib.sha256(p.read_bytes()).hexdigest() != digest: errors.append('Asset fingerprint mismatch: ' + url)
    summary = public / 'study-guides/todai-english-summary/index.html'
    if summary.exists():
        m = re.search(r'<p[^>]*id="summary-model-answer"[^>]*>(.*?)</p>', summary.read_text(), re.S)
        if not m or len(re.sub('<[^>]+>', '', m.group(1))) != 75: errors.append('Previously corrected 75-character summary changed')
    timing = public / 'study-guides/todai-english-time-allocation/index.html'
    if timing.exists():
        durations = [int(v) for v in re.findall(r'data-duration="(\d+)"', timing.read_text())]
        if sum(durations) != 120: errors.append('Previously corrected 120-minute plan changed')
    writing = public / 'study-guides/todai-english-writing/index.html'
    if writing.exists():
        m = re.search(r'<p[^>]*id="r17-writing-model"[^>]*>(.*?)</p>', writing.read_text(), re.S)
        if not m or len(re.sub('<[^>]+>', '', m.group(1)).split()) != 72: errors.append('English model answer is not 72 words')
    if 'kiyotomokuroda.pages.dev' in (root / 'tools/normalize_seo.py').read_text(): errors.append('Legacy domain remains in normalizer')
    if errors: raise RuntimeError('\n'.join(errors))
    return {'html_pages': len(pages), 'sitemap_urls': len(listed), 'errors': 0}

if __name__ == '__main__':
    try: print(json.dumps(validate(ROOT), ensure_ascii=False, indent=2))
    except Exception as exc: print(str(exc), file=sys.stderr); raise SystemExit(1)
