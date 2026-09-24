#!/usr/bin/env python3
"""出版企画書 PDF を作る。使い方: python3 kikaku/build_kikaku.py"""
import os, subprocess, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'build'))
import build as B

conv = B.Conv()
B.render_lines(open(os.path.join(ROOT, 'kikaku', 'kikaku.md'), encoding='utf8').read().split('\n'), conv, 'k')
css = open(os.path.join(ROOT, 'build', 'book.css'), encoding='utf8').read()
css = css.replace('思考の主導権　増補解説版', '出版企画書『思考の主導権』　黒田清友')
css += '''@page { @top-right { content: "企画書"; font: 7.5pt "BIZ UDPGothic"; color: #8a8f98; } }
.khead { border-bottom: 3px solid var(--accent); padding-bottom: 4mm; margin-bottom: 4mm; }
.khead .k1 { font: 700 10pt "BIZ UDPGothic"; color: var(--accent); letter-spacing: .2em; }
.khead .k2 { font: 700 24pt/1.3 "BIZ UDPGothic"; margin: 2mm 0 1mm; }
.khead .k3 { font: 700 11.5pt "BIZ UDPGothic"; color: #3a3f4c; }
h2 { margin-top: 6mm; }
@page :first { margin: 22mm 19mm 20mm 21mm; }'''
html = f'''<!DOCTYPE html><html lang="ja"><head><meta charset="utf-8"><title>出版企画書 思考の主導権</title><style>{css}</style></head><body>
<div class="khead"><div class="k1">出版企画書</div><div class="k2">思考の主導権</div><div class="k3">書き殴る、AIに整理させる、そして自分で決める。</div></div>
{"".join(conv.h)}</body></html>'''
out_html = os.path.join(ROOT, 'kikaku', 'kikaku.html')
open(out_html, 'w', encoding='utf8').write(html)
out = os.path.join(ROOT, '企画書_思考の主導権_黒田清友.pdf')
subprocess.run(['node', os.path.join(ROOT, 'build', 'render.js'), out_html, out], check=True)
print(out)
