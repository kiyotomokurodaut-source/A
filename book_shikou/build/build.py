#!/usr/bin/env python3
"""『思考の主導権』増補解説版のビルド。

src/original.md（著者原稿）と supp/*.md（増補解説）を組み合わせて HTML を作り、
render.js（Chromium）で PDF にする。目次のページ番号は 2 パスで埋める。

使い方: python3 build/build.py
"""
import html
import json
import os
import re
import subprocess
import sys

import pymupdf as fitz

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILD = os.path.join(ROOT, 'build')
SUPP = os.path.join(ROOT, 'supp')
OUT_HTML = os.path.join(BUILD, 'book.html')
OUT_PDF = os.path.join(ROOT, '思考の主導権_増補解説版_黒田清友.pdf')

# ---------------------------------------------------------------- 原稿の分割

PART_IDS = {
    'はじめに': 'hajime', '第1章': 'ch1', '第2章': 'ch2', '第3章': 'ch3', '第4章': 'ch4',
    '第5章': 'ch5', '第6章': 'ch6', '第7章': 'ch7', '第8章': 'ch8', 'おわりに': 'owari',
    '実践編': 'jissen', 'ケーススタディ': 'case', '実践ツール1': 'tool1', '実践ツール2': 'tool2',
    '実践ツール3': 'tool3', 'よくある反論に答える': 'qa', '研究ノート': 'research',
}

# 実践ツール1 のうち、原稿（docx）で引用スタイルだった「AIへの頼み方」の段落
PROMPT_STARTS = [
    '以下は私が自分で考えたメモです。', '完全解答は出さないでください。私の方針のうち',
    '私の解答を採点してください。', '以下は英文と私の訳です。', '次の範囲について、一問ずつ出題してください。',
    '以下は私の未整理メモです。', 'この主張に対して、知的に最も強い反対意見を作ってください。',
    '次の文章について、内容を書き換えず', '私は［テーマ］を調べています。', '以下は私が一次資料AとBを読んで',
    '問題、私の解答、正答、私自身の誤答分析を示します。', '私は現在、［主張］だと考えています。',
    '私の選択肢はAとBです。',
]


def split_label(text):
    """「第1章　タイトル」→ ('第1章', 'タイトル')。全角空白がなければラベルなし。"""
    if '　' in text:
        a, b = text.split('　', 1)
        return a.strip(), b.strip()
    if '――' in text:
        a, b = text.split('――', 1)
        return '', text
    return '', text


def load_parts():
    lines = open(os.path.join(ROOT, 'src', 'original.md'), encoding='utf8').read().split('\n')
    parts, cur = [], None
    for ln in lines:
        if ln.startswith('# '):
            title = ln[2:].strip()
            if title == '目次':
                cur = None
                continue
            label, _ = split_label(title)
            key = label or title.split('――')[0]
            pid = PART_IDS.get(key)
            if pid is None:
                sys.exit(f'unknown part: {title}')
            cur = {'id': pid, 'title': title, 'lines': []}
            parts.append(cur)
            continue
        if cur is None:
            continue
        if ln.strip() == '＊　＊　＊':
            continue
        cur['lines'].append(ln.replace('&amp;', '&'))
    return parts


def load_supp(pid):
    """supp/<pid>.md を「=== ANCHOR」ごとに分ける。"""
    path = os.path.join(SUPP, pid + '.md')
    if not os.path.exists(path):
        return {}
    res, key = {}, None
    for ln in open(path, encoding='utf8').read().split('\n'):
        m = re.match(r'^===\s+(.+?)\s*$', ln)
        if m:
            key = m.group(1)
            res.setdefault(key, [])
            continue
        if key is not None:
            res[key].append(ln)
    return res


def assemble(part):
    """原稿の行に、増補の挿入点を差し込む。"""
    supp = load_supp(part['id'])
    used = set()

    def take(key):
        if key in supp:
            used.add(key)
            return [''] + supp[key] + ['']
        return []

    out = take('START')
    cur_sec = None
    cur_h3 = None
    for ln in part['lines']:
        if ln.startswith('### '):
            if cur_h3:
                out += take('AFTER ' + cur_h3)
            cur_h3 = split_label(ln[4:].strip())[0]
            out.append(ln)
            out += take('IN ' + cur_h3)
            continue
        if ln.startswith('## '):
            if cur_h3:
                out += take('AFTER ' + cur_h3)
                cur_h3 = None
            if cur_sec:
                out += take('AFTER ' + cur_sec)
            label = split_label(ln[3:].strip())[0] or ln[3:].strip()
            out += take('BEFORE ' + label)
            cur_sec = label
            out.append(ln)
            out += take('IN ' + label)
            continue
        out.append(ln)
    if cur_h3:
        out += take('AFTER ' + cur_h3)
    if cur_sec:
        out += take('AFTER ' + cur_sec)
    out += take('END')
    unused = set(supp) - used
    if unused:
        sys.exit(f'{part["id"]}: unused anchors {sorted(unused)}')
    return out


# ---------------------------------------------------------------- Markdown → HTML

def inline(t):
    t = html.escape(t, quote=False)
    t = re.sub(r'\*\*\s*(.+?)\s*\*\*', r'<strong>\1</strong>', t)
    t = re.sub(r'(?<![*])\*(?!\s)(.+?)(?<!\s)\*(?![*])', r'<em>\1</em>', t)
    t = re.sub(r'(https?://[^\s）)]+)', r'<span class="url">\1</span>', t)
    return t


BOX_LABELS = {
    'goal': 'この章で分かること', 'why': 'なぜ？', 'mistake': 'よくある間違い', 'term': '用語',
    'example': '具体例', 'summary': 'まとめ', 'quiz': '確認問題', 'point': '要点', 'prompt': 'AIへの頼み方（例）',
    'bridge': '次へのつながり', 'flow': '図解', 'note': '補足', 'check': 'チェックリスト', 'research': '研究の読み方',
    'howto': '手順', 'caution': '注意', 'guide': 'この部の使い方',
}


class Conv:
    def __init__(self):
        self.h = []
        self.heads = []  # (level, id, text) for TOC
        self.refmode = False

    def para_block(self, buf):
        """段落のまとまり。「」だけの短い行が続くときはメモ風にまとめる。"""
        i = 0
        while i < len(buf):
            ln = buf[i]
            if is_memo(ln):
                j = i
                while j < len(buf) and is_memo(buf[j]):
                    j += 1
                if j - i >= 2:
                    self.h.append('<div class="memo">' + ''.join(
                        f'<p>{inline(x)}</p>' for x in buf[i:j]) + '</div>')
                    i = j
                    continue
            if self.refmode:
                self.h.append(f'<p class="ref">{inline(ln)}</p>')
            elif any(ln.startswith(s) for s in PROMPT_STARTS):
                self.h.append(f'<div class="box prompt"><div class="lab">AIへの頼み方（例）</div><p>{inline(ln)}</p></div>')
            else:
                self.h.append(f'<p>{inline(ln)}</p>')
            i += 1


def is_memo(ln):
    s = ln.strip()
    return s.startswith('「') and s.endswith('」') and len(s) <= 70 and s.count('「') == 1


def render_lines(lines, conv, part_id):
    """原稿＋増補の行リストを HTML に変換する。"""
    i = 0
    para = []

    def flush():
        if para:
            conv.para_block(para)
            para.clear()

    while i < len(lines):
        ln = lines[i]
        s = ln.strip()
        if not s:
            flush()
            i += 1
            continue
        if s in ('<!--refs-->', '<!--/refs-->'):
            flush()
            conv.refmode = s == '<!--refs-->'
            i += 1
            continue
        if s.startswith(':::'):
            flush()
            m = re.match(r'^:::\s*(\w+)\s*(?:\|\s*(.*))?$', s)
            kind, title = m.group(1), (m.group(2) or '').strip()
            j = i + 1
            body = []
            while j < len(lines) and lines[j].strip() != ':::':
                body.append(lines[j])
                j += 1
            render_box(kind, title, body, conv)
            i = j + 1
            continue
        if s.startswith('## '):
            flush()
            t = s[3:].strip()
            conv.refmode = t == '主要参考文献'
            label, rest = split_label(t)
            hid = f'{part_id}-s{len(conv.heads)}'
            conv.heads.append((2, hid, t))
            num = f'<span class="num">{inline(label)}</span>' if label else ''
            conv.h.append(f'<h2 id="{hid}">{num}<span class="ht">{inline(rest)}</span></h2>')
            i += 1
            continue
        if s.startswith('### '):
            flush()
            t = s[4:].strip()
            label, rest = split_label(t)
            num = f'<span class="num3">{inline(label)}</span>' if label else ''
            conv.h.append(f'<h3>{num}{inline(rest)}</h3>')
            i += 1
            continue
        if s.startswith('|'):
            flush()
            j = i
            rows = []
            while j < len(lines) and lines[j].strip().startswith('|'):
                rows.append(lines[j].strip())
                j += 1
            conv.h.append(table(rows))
            i = j
            continue
        if re.match(r'^[-・]\s', s) or re.match(r'^\*\*•\s*\*\*', s):
            flush()
            j = i
            items = []
            while j < len(lines) and (re.match(r'^\s*[-・]\s', lines[j]) or re.match(r'^\*\*•\s*\*\*', lines[j].strip())):
                items.append(re.sub(r'^(\s*[-・]\s|\*\*•\s*\*\*)', '', lines[j].strip()))
                j += 1
            conv.h.append('<ul>' + ''.join(f'<li>{inline(x)}</li>' for x in items) + '</ul>')
            i = j
            continue
        if re.match(r'^\d+\.\s', s):
            flush()
            j = i
            items = []
            while j < len(lines) and re.match(r'^\d+\.\s', lines[j].strip()):
                items.append(re.sub(r'^\d+\.\s', '', lines[j].strip()))
                j += 1
            conv.h.append('<ol>' + ''.join(f'<li>{inline(x)}</li>' for x in items) + '</ol>')
            i = j
            continue
        para.append(s)
        i += 1
    flush()


def table(rows):
    rows = [r for r in rows if not re.match(r'^\|[\s:|-]+\|$', r)]
    cells = [[c.strip() for c in r.strip('|').split('|')] for r in rows]
    h = '<table><thead><tr>' + ''.join(f'<th>{inline(c)}</th>' for c in cells[0]) + '</tr></thead><tbody>'
    for r in cells[1:]:
        h += '<tr>' + ''.join(f'<td>{inline(c)}</td>' for c in r) + '</tr>'
    return h + '</tbody></table>'


def render_box(kind, title, body, conv):
    label = BOX_LABELS.get(kind, kind)
    if kind == 'flow':
        conv.h.append(flow(title, body))
        return
    if kind == 'mistake':
        conv.h.append(mistake(title, body))
        return
    if kind == 'quiz':
        conv.h.append(quiz(title, body))
        return
    if kind == 'term':
        conv.h.append(terms(title, body))
        return
    sub = Conv()
    sub.heads = conv.heads
    render_lines(body, sub, 'x')
    t = f'<span class="bt">{inline(title)}</span>' if title else ''
    conv.h.append(f'<div class="box {kind}"><div class="lab">{label}{t}</div>{"".join(sub.h)}</div>')


def flow(title, body):
    """「ラベル | 説明」の行を、矢印でつないだ段の図にする。"""
    steps = []
    notes = []
    for ln in body:
        s = ln.strip()
        if not s:
            continue
        if s.startswith('※'):
            notes.append(s)
            continue
        if '|' in s:
            a, b = s.split('|', 1)
        else:
            a, b = s, ''
        steps.append((a.strip(), b.strip()))
    vertical = len(steps) > 4 or any(len(b) > 34 for _, b in steps)
    cls = 'flow v' if vertical else 'flow h'
    h = f'<figure class="{cls}"><figcaption>図解　{inline(title)}</figcaption><div class="steps">'
    for k, (a, b) in enumerate(steps):
        if k:
            h += '<div class="arrow">{}</div>'.format('▼' if vertical else '▶')
        h += f'<div class="step"><div class="sa">{inline(a)}</div>'
        if b:
            h += f'<div class="sb">{inline(b)}</div>'
        h += '</div>'
    h += '</div>'
    for n in notes:
        h += f'<p class="fnote">{inline(n)}</p>'
    return h + '</figure>'


def mistake(title, body):
    """✕ / ○ / → の組を並べる。"""
    items, cur = [], None
    extra = []
    for ln in body:
        s = ln.strip()
        if not s:
            continue
        if s.startswith('✕'):
            cur = {'x': s[1:].strip(' :：'), 'o': '', 'w': ''}
            items.append(cur)
        elif s.startswith('○') and cur:
            cur['o'] = s[1:].strip(' :：')
        elif s.startswith('→') and cur:
            cur['w'] += ('' if not cur['w'] else '<br>') + inline(s[1:].strip(' :：'))
        else:
            extra.append(s)
    t = f'<span class="bt">{inline(title)}</span>' if title else ''
    h = f'<div class="box mistake"><div class="lab">よくある間違い{t}</div>'
    for e in extra:
        h += f'<p>{inline(e)}</p>'
    for it in items:
        h += '<div class="mx">'
        h += f'<div class="mrow x"><span class="mk">✕ 間違い</span><span>{inline(it["x"])}</span></div>'
        if it['o']:
            h += f'<div class="mrow o"><span class="mk">○ 正しくは</span><span>{inline(it["o"])}</span></div>'
        if it['w']:
            h += f'<div class="mrow w"><span class="mk">なぜ</span><span>{it["w"]}</span></div>'
        h += '</div>'
    return h + '</div>'


def terms(title, body):
    """「用語：定義」の行を定義リストにする。"""
    h = '<div class="box term"><div class="lab">用語' + (f'<span class="bt">{inline(title)}</span>' if title else '') + '</div><dl>'
    for ln in body:
        s = ln.strip()
        if not s:
            continue
        if '：' in s:
            a, b = s.split('：', 1)
            h += f'<dt>{inline(a)}</dt><dd>{inline(b)}</dd>'
            GLOSSARY.setdefault(a.strip(), b.strip())
        else:
            h += f'<dd>{inline(s)}</dd>'
    return h + '</dl></div>'


GLOSSARY = {}


def quiz(title, body):
    """Q. / A. の組。問題と答えを分けて表示する。"""
    qs, cur = [], None
    for ln in body:
        s = ln.strip()
        if not s:
            continue
        if s.startswith('Q.'):
            cur = {'q': s[2:].strip(), 'a': []}
            qs.append(cur)
        elif s.startswith('A.') and cur:
            cur['a'].append(s[2:].strip())
        elif cur and cur['a']:
            cur['a'].append(s)
        elif cur:
            cur['q'] += '<br>' + inline(s)
    h = '<div class="box quiz"><div class="lab">確認問題<span class="bt">まず答えを隠して、自分で書いてから下の解答を見る</span></div><ol>'
    for q in qs:
        h += f'<li>{inline(q["q"]) if "<br>" not in q["q"] else q["q"]}</li>'
    h += '</ol></div><div class="box answer"><div class="lab">解答と解説</div><ol>'
    for q in qs:
        h += '<li>' + ''.join(f'<p>{inline(a)}</p>' for a in q['a']) + '</li>'
    return h + '</ol></div>'


# ---------------------------------------------------------------- 本全体

def front_matter():
    path = os.path.join(SUPP, 'front.md')
    return open(path, encoding='utf8').read().split('\n') if os.path.exists(path) else []


def back_matter():
    path = os.path.join(SUPP, 'back.md')
    return open(path, encoding='utf8').read().split('\n') if os.path.exists(path) else []


def build_html(toc_pages=None):
    GLOSSARY.clear()
    parts = load_parts()
    conv = Conv()
    body = []
    toc_entries = []

    # 前付け（この本の使い方・全体地図）
    fm = Conv()
    fm.heads = conv.heads
    fl = front_matter()
    if fl:
        render_lines(fl, fm, 'front')

    for p in parts:
        label, rest = split_label(p['title'])
        if not label and '――' in p['title']:
            label, rest = p['title'].split('――')[0], p['title'].split('――', 1)[1]
        hid = p['id']
        conv.heads.append((1, hid, p['title']))
        pc = Conv()
        pc.heads = conv.heads
        lines = assemble(p)
        # START の中身は扉ページに置く
        supp = load_supp(p['id'])
        start = supp.get('START', [])
        opener = Conv()
        opener.heads = conv.heads
        render_lines(start, opener, hid)
        rest_lines = lines[len(start) + 2:] if start else lines
        render_lines(rest_lines, pc, hid)
        body.append(
            f'<section class="part" id="sec-{hid}" data-pid="{hid}">'
            f'<div class="opener pg-{hid}"><div class="olabel">{inline(label)}</div>'
            f'<h1 id="{hid}">{inline(rest)}</h1>{"".join(opener.h)}</div>'
            f'<div class="pbody pg-{hid}">{"".join(pc.h)}</div></section>')

    # 後付け（用語集など）
    bm = Conv()
    bm.heads = conv.heads
    bl = back_matter()
    render_lines(bl, bm, 'back')
    gl = glossary_html()
    if gl:
        conv.heads.append((2, 'back-glossary', '用語集（本文の「用語」欄をまとめたもの）'))

    # 目次
    toc = ['<nav class="toc" id="toc"><h1 class="toch">目次</h1>']
    idx = 0
    for lv, hid, text in conv.heads:
        pg = toc_pages[idx] if toc_pages and idx < len(toc_pages) else '000'
        idx += 1
        label, rest = split_label(text)
        if lv == 1:
            toc.append(f'<a class="t1" href="#{hid}"><span class="tl">{inline(label)}</span>'
                       f'<span class="tt">{inline(rest if label else text)}</span><span class="tp">{pg}</span></a>')
        elif lv == 2 and not hid.startswith('front') and not hid.startswith('back'):
            toc.append(f'<a class="t2" href="#{hid}"><span class="tl">{inline(label)}</span>'
                       f'<span class="tt">{inline(rest if label else text)}</span><span class="tp">{pg}</span></a>')
        elif lv == 2:
            toc.append(f'<a class="t1" href="#{hid}"><span class="tl"></span>'
                       f'<span class="tt">{inline(text)}</span><span class="tp">{pg}</span></a>')
    toc.append('</nav>')

    css = open(os.path.join(BUILD, 'book.css'), encoding='utf8').read()
    page_rules = []
    for p in parts:
        label, rest = split_label(p['title'])
        run = (label + '　' + rest) if label else p['title'].split('――')[0]
        run = run.replace('"', '')
        page_rules.append(
            f'.pg-{p["id"]}{{page:{p["id"]}}}'
            f'@page {p["id"]}{{@top-right{{content:"{run}";font:7.5pt "BIZ UDPGothic";color:#8a8f98}}}}')
    title = open(os.path.join(SUPP, 'title.html'), encoding='utf8').read()
    doc = f'''<!DOCTYPE html><html lang="ja"><head><meta charset="utf-8">
<title>思考の主導権　増補解説版</title><style>{css}{"".join(page_rules)}</style></head><body>
{title}
<div class="frontpg">{"".join(toc)}</div>
<div class="frontpg">{"".join(fm.h)}</div>
{"".join(body)}
<section class="part back pg-back">{"".join(bm.h)}{gl}</section>
</body></html>'''
    open(OUT_HTML, 'w', encoding='utf8').write(doc)
    return conv.heads


def glossary_html():
    if not GLOSSARY:
        return ''
    items = sorted(GLOSSARY.items(), key=lambda kv: kana_key(kv[0]))
    h = '<h2 id="back-glossary" class="gh"><span class="ht">用語集（本文の「用語」欄をまとめたもの）</span></h2><dl class="glossary">'
    for k, v in items:
        h += f'<dt>{inline(k)}</dt><dd>{inline(v)}</dd>'
    return h + '</dl>'


def kana_key(s):
    import unicodedata
    m = re.search(r'（([ぁ-んー・]+)）', s)
    k = m.group(1) if m else s
    return ''.join(c for c in unicodedata.normalize('NFD', k) if not unicodedata.combining(c))


def render_pdf(out):
    subprocess.run(['node', os.path.join(BUILD, 'render.js'), OUT_HTML, out], check=True)


def main():
    heads = build_html()
    tmp = os.path.join(BUILD, 'pass1.pdf')
    render_pdf(tmp)
    doc = fitz.open(tmp)
    toc = doc.get_toc()
    # outline は h1/h2 から作られる。見出しの出現順と対応させる
    wanted = [(lv, text) for lv, _, text in heads]
    pages = []
    ti = 0
    for lv, text in wanted:
        found = None
        while ti < len(toc):
            tl, tt, tp = toc[ti]
            ti += 1
            if norm(tt) == norm(text) or norm(text).endswith(norm(tt)) or norm(tt).endswith(norm(text)):
                found = tp
                break
        pages.append(str(found) if found else '―')
    doc.close()
    build_html(pages)
    render_pdf(OUT_PDF)
    d = fitz.open(OUT_PDF)
    print('pages', d.page_count, 'missing toc', pages.count('―'))


def norm(s):
    return re.sub(r'\s|　', '', s)


if __name__ == '__main__':
    main()
