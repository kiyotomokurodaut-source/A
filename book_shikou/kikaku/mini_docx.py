#!/usr/bin/env python3
"""メール添付用の小さな Word ファイルを作る（フォントを埋め込まず、最小限の部品だけで構成）。
使い方: python3 kikaku/mini_docx.py"""
import os, re, zipfile
from xml.sax.saxutils import escape
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CT = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
      '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/>'
      '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
      '<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/></Types>')
RELS = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>')
DRELS = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
         '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/></Relationships>')
W = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"'
LINKS = []  # 本文中のハイパーリンク先（write() が関係ファイルに書き出す）
DRIVE = 'https://drive.google.com/drive/folders/1AUOR56s8bT1EBTEnFTPJt_517ApaUHPq'
M, G = '游明朝', '游ゴシック'


def sty(i, name, font, sz, bold=False, before=0, after=120, center=False, ol=None):
    jc = '<w:jc w:val="center"/>' if center else ''
    lvl = f'<w:outlineLvl w:val="{ol}"/>' if ol is not None else ''
    b = '<w:b/>' if bold else ''
    return (f'<w:style w:type="paragraph" w:styleId="{i}"><w:name w:val="{name}"/><w:basedOn w:val="Normal"/><w:pPr>'
            f'<w:spacing w:before="{before}" w:after="{after}"/>{jc}{lvl}<w:keepNext/></w:pPr>'
            f'<w:rPr><w:rFonts w:ascii="{font}" w:eastAsia="{font}" w:hAnsi="{font}"/>{b}<w:sz w:val="{sz}"/></w:rPr></w:style>')


STYLES = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:styles {W}><w:docDefaults><w:rPrDefault><w:rPr>'
          f'<w:rFonts w:ascii="{M}" w:eastAsia="{M}" w:hAnsi="{M}"/><w:sz w:val="21"/></w:rPr></w:rPrDefault>'
          '<w:pPrDefault><w:pPr><w:spacing w:after="80" w:line="360" w:lineRule="auto"/><w:jc w:val="both"/></w:pPr></w:pPrDefault></w:docDefaults>'
          '<w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/></w:style>'
          + sty('Title', 'Title', G, 40, True, 0, 120, True) + sty('Subtitle', 'Subtitle', G, 24, False, 0, 480, True)
          + sty('Heading1', 'heading 1', G, 30, True, 480, 240, False, 0) + sty('Heading2', 'heading 2', G, 24, True, 300, 120, False, 1)
          + '</w:styles>')


def runs(t):
    out = []
    for part in re.split(r'(\*\*.+?\*\*|\[[^\]]+\]\([^)]+\))', t):
        if not part:
            continue
        m = re.fullmatch(r'\[([^\]]+)\]\(([^)]+)\)', part)
        if m:
            LINKS.append(m.group(2))
            out.append(f'<w:hyperlink r:id="rIdL{len(LINKS)}"><w:r><w:rPr><w:color w:val="0563C1"/><w:u w:val="single"/></w:rPr>'
                       f'<w:t xml:space="preserve">{escape(m.group(1))}</w:t></w:r></w:hyperlink>')
            continue
        b = part.startswith('**')
        part = part.strip('*') if b else part
        out.append(f'<w:r>{"<w:rPr><w:b/></w:rPr>" if b else ""}<w:t xml:space="preserve">{escape(part)}</w:t></w:r>')
    return ''.join(out)


def para(t, style=None, indent=True, brk=False):
    ppr = ''
    if style or brk or indent:
        ppr = '<w:pPr>' + (f'<w:pStyle w:val="{style}"/>' if style else '') + ('<w:pageBreakBefore/>' if brk else '') + \
              ('<w:ind w:firstLineChars="100" w:firstLine="210"/>' if indent and not style else '') + '</w:pPr>'
    return f'<w:p>{ppr}{runs(t)}</w:p>'


def table(rows):
    rows = [r for r in rows if not re.match(r'^\|[\s:|-]+\|$', r)]
    cells = [[c.strip() for c in r.strip('|').split('|')] for r in rows]
    b = '<w:tblBorders>' + ''.join(f'<w:{s} w:val="single" w:sz="4" w:color="999999"/>' for s in ('top', 'left', 'bottom', 'right', 'insideH', 'insideV')) + '</w:tblBorders>'
    x = f'<w:tbl><w:tblPr><w:tblW w:w="5000" w:type="pct"/>{b}</w:tblPr>'
    for i, r in enumerate(cells):
        tcs = ''
        for c in r:
            txt = f'**{c}**' if i == 0 and c else c
            tcs += f'<w:tc><w:p><w:pPr><w:spacing w:after="0"/></w:pPr>{runs(txt)}</w:p></w:tc>'
        x += f'<w:tr>{tcs}</w:tr>'
    return x + '</w:tbl><w:p/>'


def md_to_body(lines, h1break=True):
    out, first = [], True
    i = 0
    while i < len(lines):
        s = lines[i].strip()
        i += 1
        if not s or s.startswith('＊'):
            continue
        if s.startswith('|'):
            rows = [s]
            while i < len(lines) and lines[i].strip().startswith('|'):
                rows.append(lines[i].strip()); i += 1
            out.append(table(rows)); continue
        if s.startswith('# '):
            out.append(para(s[2:], 'Heading1', brk=h1break and not first)); first = False; continue
        if s.startswith('## '):
            out.append(para(s[3:], 'Heading2')); continue
        if s.startswith('### '):
            out.append(para(s[4:], 'Heading2')); continue
        m = re.match(r'^(?:[-・]|\d+\.)\s+(.*)$', s)
        if m:
            out.append(para('・' + m.group(1), indent=False)); continue
        out.append(para(s))
    return ''.join(out)


def write(path, title, subtitle, body_xml):
    doc = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:document {W}><w:body>'
           + para(title, 'Title') + para(subtitle, 'Subtitle') + body_xml +
           '<w:sectPr><w:pgSz w:w="11906" w:h="16838"/><w:pgMar w:top="1701" w:right="1587" w:bottom="1587" w:left="1587" w:header="851" w:footer="851" w:gutter="0"/></w:sectPr></w:body></w:document>')
    drels = DRELS.replace('</Relationships>', ''.join(
        f'<Relationship Id="rIdL{i}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink" '
        f'Target="{escape(u)}" TargetMode="External"/>' for i, u in enumerate(LINKS, 1)) + '</Relationships>')
    LINKS.clear()
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for n, d in (('[Content_Types].xml', CT), ('_rels/.rels', RELS), ('word/_rels/document.xml.rels', drels),
                     ('word/document.xml', doc), ('word/styles.xml', STYLES)):
            z.writestr(n, d)
    print(path, os.path.getsize(path))


# 企画書
k = open(os.path.join(ROOT, 'kikaku', 'kikaku.md'), encoding='utf8').read().split('\n')
k = [l.replace('原稿全文をPDFで添付（Word形式もご用意できます）', f'原稿全文はGoogleドライブでご覧いただけます（[資料フォルダを開く]({DRIVE})）。PDF版もご用意できます')
      .replace('Web：https://kiyotomokuroda.pages.dev/', 'Web：[kiyotomokuroda.pages.dev](https://kiyotomokuroda.pages.dev/)') for l in k]
k = [f'■資料一式（原稿全文・Word）：[Googleドライブの資料フォルダを開く]({DRIVE})　※ログイン不要で閲覧できます', ''] + k
write(os.path.join(ROOT, 'send', '企画書_思考の主導権_黒田清友.docx'), '出版企画書『思考の主導権』',
      '書き殴る、AIに整理させる、そして自分で決める。　黒田清友', md_to_body(k, h1break=False))

# 原稿サンプル（はじめに・第1章）
src = open(os.path.join(ROOT, 'src', 'original.md'), encoding='utf8').read().split('\n')
a = src.index('# はじめに　AIに答えを聞く前に')
b = next(j for j, l in enumerate(src) if l.startswith('# 第2章'))
note = [f'（原稿サンプル：はじめに・第1章。全編約7万字は脱稿済みです。原稿全文：[Googleドライブの資料フォルダを開く]({DRIVE})）']
write(os.path.join(ROOT, 'send', '原稿サンプル_思考の主導権_はじめに・第1章_黒田清友.docx'), '思考の主導権',
      '書き殴る、AIに整理させる、そして自分で決める。　黒田清友', md_to_body(note + src[a:b]))
