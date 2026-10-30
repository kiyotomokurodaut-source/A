#!/usr/bin/env python3
"""Validate the checked-in production snapshot without rewriting its pages."""
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit, unquote
from xml.etree import ElementTree
import json
import sys

ROOT = Path(__file__).resolve().parents[1] / 'public'
ORIGIN = 'https://kurodaschool.jp'


class Page(HTMLParser):
    def __init__(self, path):
        super().__init__(convert_charrefs=True)
        self.path = path
        self.ids, self.links, self.meta = [], [], {}
        self.canonical = None
        self.h1_count = 0
        self.schema_blocks = []
        self.in_schema = False
        self.schema = ''
        self.feed(path.read_text(encoding='utf-8'))

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if 'id' in a:
            self.ids.append(a['id'])
        if tag == 'h1':
            self.h1_count += 1
        if tag == 'meta':
            self.meta[a.get('name', a.get('property', ''))] = a.get('content', '')
        if tag == 'link' and a.get('rel') == 'canonical':
            self.canonical = a.get('href')
        if tag in {'a', 'link', 'script', 'img', 'source', 'video'}:
            ref = a.get('href') or a.get('src')
            if ref:
                self.links.append(ref)
        if tag == 'script' and a.get('type') == 'application/ld+json':
            self.in_schema, self.schema = True, ''

    def handle_data(self, text):
        if self.in_schema:
            self.schema += text

    def handle_endtag(self, tag):
        if tag == 'script' and self.in_schema:
            self.schema_blocks.append(self.schema)
            self.in_schema = False


def target(path, reference):
    u = urlsplit(reference)
    if u.scheme and u.netloc != 'kurodaschool.jp':
        return None, ''
    if reference.startswith('//'):
        return None, ''
    name = unquote(u.path)
    p = ROOT / name.lstrip('/') if name.startswith('/') else path.parent / name
    if not name:
        p = path
    if p.is_dir():
        p /= 'index.html'
    return p.resolve(), unquote(u.fragment)


def main():
    pages = {p.resolve(): Page(p) for p in ROOT.rglob('*.html')}
    errors = []
    for path, page in pages.items():
        rel = path.relative_to(ROOT.resolve()).as_posix()
        label = '/' + rel.removesuffix('index.html')
        if page.h1_count != 1:
            errors.append(f'{label}: expected one h1')
        duplicates = [k for k, n in Counter(page.ids).items() if n > 1]
        if duplicates:
            errors.append(f'{label}: duplicate ids {duplicates}')
        if path.name != '404.html' and page.canonical != ORIGIN + label:
            errors.append(f'{label}: unexpected canonical {page.canonical}')
        if not page.meta.get('description'):
            errors.append(f'{label}: missing description')
        for block in page.schema_blocks:
            try:
                json.loads(block)
            except ValueError:
                errors.append(f'{label}: invalid JSON-LD')
        for ref in page.links:
            dest, fragment = target(path, ref)
            if dest is None:
                continue
            if not dest.is_file():
                errors.append(f'{label}: missing target {ref}')
            elif fragment and dest in pages and fragment not in pages[dest].ids:
                errors.append(f'{label}: missing fragment {ref}')
    sitemap = ElementTree.parse(ROOT / 'sitemap.xml')
    for loc in sitemap.findall('.//{*}loc'):
        dest, _ = target(ROOT / 'index.html', loc.text)
        if dest is None or not dest.is_file():
            errors.append(f'sitemap: missing URL {loc.text}')
    if errors:
        print('\n'.join(errors), file=sys.stderr)
        return 1
    print(f'Validated {len(pages)} HTML pages, canonical URLs, structured data, links and sitemap.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
