#!/usr/bin/env python3
"""『理解する古文単語帳 500』を data/*.txt から組み立てる。

    python3 build.py            # dist/kobun-tango-500.html を書き出す
    python3 build.py --check    # 書き出し＋データ検査（500語・各DAY20語など）に失敗したら終了コード1
    python3 build.py --fragment PATH   # <html>/<head>/<body> を含まない版も書き出す

標準ライブラリのみ。PDF は tools/make_pdf.mjs（Playwright）で作る。
"""

from __future__ import annotations

import argparse
import html
import json
import math
import random
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

import sections as S

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
SRC = ROOT / "src"
DIST = ROOT / "dist"

TITLE = "理解する古文単語帳 500"
AUTHOR = "黒田清友"
WORDS_PER_DAY = 20
TOTAL_WORDS = 500
MARUNUM = "①②③④⑤⑥⑦⑧⑨⑩"
FIRST = ' class="first"'


def esc(s: str) -> str:
    return html.escape(s, quote=True)


# --------------------------------------------------------------------------- #
# データ
# --------------------------------------------------------------------------- #
@dataclass
class Word:
    head: str
    kanji: str
    pos: str
    rank: int
    day: int = 0
    no: int = 0
    means: list[str] = field(default_factory=list)
    parts: list[tuple[str, str, bool]] = field(default_factory=list)
    core: str = ""
    origin: str = ""
    syn: list[str] = field(default_factory=list)
    ant: list[str] = field(default_factory=list)
    der: list[str] = field(default_factory=list)
    examples: list[tuple[str, str, str]] = field(default_factory=list)
    point: str = ""
    modern: str = ""
    reading: str = ""
    src_line: str = ""

    @property
    def id(self) -> str:
        return f"w{self.no:04d}"


@dataclass
class Day:
    no: int
    theme: str
    tags: list[str]
    part: int
    words: list[Word] = field(default_factory=list)


@dataclass
class Part:
    no: int
    name: str
    desc: str
    days: list[Day] = field(default_factory=list)


def split_list(s: str) -> list[str]:
    s = s.strip()
    if not s or s in {"—", "-"}:
        return []
    return [x.strip() for x in s.split("、") if x.strip()]


def parse() -> list[Part]:
    parts: list[Part] = []
    cur_day: Day | None = None
    cur: Word | None = None
    for path in sorted(DATA.glob("*.txt")):
        for ln, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            line = raw.rstrip()
            where = f"{path.name}:{ln}"
            if not line.strip():
                continue
            if line.startswith("% "):
                no, name, desc = [x.strip() for x in line[2:].split("|")]
                parts.append(Part(int(no), name, desc))
                continue
            m = re.match(r"^# (\d{2}) \|(.*)$", line)
            if m:
                theme, tags = [x.strip() for x in m.group(2).split("|")]
                cur_day = Day(int(m.group(1)), theme, [t.strip() for t in tags.split("／") if t.strip()], parts[-1].no)
                parts[-1].days.append(cur_day)
                cur = None
                continue
            if line.startswith("#"):
                continue
            if line.startswith("@ "):
                f = [x.strip() for x in line[2:].split("|")]
                if len(f) != 4:
                    raise SystemExit(f"{where}: 見出し行は4項目: {line}")
                cur = Word(f[0], "" if f[1] in {"—", "-"} else f[1], f[2], int(f[3]), src_line=where)
                cur.day = cur_day.no
                cur_day.words.append(cur)
                continue
            key, _, val = line.partition(" ")
            val = val.strip()
            if cur is None:
                raise SystemExit(f"{where}: 見出し行より前にフィールドがある: {line}")
            if key == "=":
                cur.means = [x.strip() for x in val.split("／") if x.strip()]
            elif key == "b":
                for p in val.split(" + "):
                    star = p.startswith("*")
                    p = p.lstrip("*")
                    a, _, b = p.partition("|")
                    cur.parts.append((a.strip(), b.strip(), star))
            elif key == "c":
                cur.core = val
            elif key == "o":
                cur.origin = val
            elif key == "r":
                cur.syn = split_list(val)
            elif key == "a":
                cur.ant = split_list(val)
            elif key == "d":
                cur.der = split_list(val)
            elif key == "e":
                f = val.split("|")
                if len(f) == 2:
                    f.append("")
                if len(f) != 3:
                    raise SystemExit(f"{where}: 例文は「本文|訳|出典」: {line}")
                cur.examples.append((f[0].strip(), f[1].strip(), f[2].strip()))
            elif key == "p":
                cur.point = val
            elif key == "m":
                cur.modern = val
            elif key == "y":
                cur.reading = val
            else:
                raise SystemExit(f"{where}: 不明なフィールド {key!r}")
    no = 0
    for p in parts:
        for d in p.days:
            for w in d.words:
                no += 1
                w.no = no
    return parts


# --------------------------------------------------------------------------- #
# 歴史的仮名遣い → 現代仮名遣い（見出し語の読み表示用。例外は data の y 行で指定）
# --------------------------------------------------------------------------- #
_ROW_A = dict(zip("かさたなはまやらわがざだばぱあ", "こそとのほもよろおごぞどぼぽお"))
_ROW_E = dict(zip("けせてねめれげぜでへべ", "きしちにみりぎじぢひび"))
_ROW_I = set("きしちにひみりぎじぢびぴ")


def modern_reading(w: str) -> str:
    s = w.replace("ゐ", "い").replace("ゑ", "え").replace("を", "お")
    out: list[str] = []
    i = 0
    while i < len(s):
        c = s[i]
        nxt = s[i + 1] if i + 1 < len(s) else ""
        nxt2 = s[i + 2] if i + 2 < len(s) else ""
        if c in _ROW_I and nxt in "やよ" and nxt2 == "う":
            out.append(c + "ょう")
            i += 3
            continue
        if c in _ROW_A and nxt == "う":
            out.append(_ROW_A[c] + "う")
            i += 2
            continue
        if c in _ROW_E and nxt == "う":
            base = _ROW_E[c]
            out.append(base + "ょう")
            i += 2
            continue
        if c == "い" and nxt == "う":
            out.append("ゆう")
            i += 2
            continue
        if i > 0 and c in "はひふへほ":
            out.append("わいうえお"["はひふへほ".index(c)])
            i += 1
            continue
        out.append({"ぢ": "じ", "づ": "ず"}.get(c, c))
        i += 1
    return "".join(out)


def reading_of(w: Word) -> str:
    r = w.reading or modern_reading(w.head)
    return "" if r == w.head else r


# --------------------------------------------------------------------------- #
# 検査
# --------------------------------------------------------------------------- #
def check(parts: list[Part], strict: bool) -> list[str]:
    errs: list[str] = []
    words = [w for p in parts for d in p.days for w in d.words]
    heads = {w.head for w in words}
    seen: dict[tuple[str, str], str] = {}
    for w in words:
        k = (w.head, w.pos)
        if k in seen:
            errs.append(f"{w.src_line}: 見出し語が重複（{w.head} / {w.pos}）: {seen[k]}")
        seen[k] = w.src_line
        if not w.means:
            errs.append(f"{w.src_line}: 意味（=）がない: {w.head}")
        if not w.examples:
            errs.append(f"{w.src_line}: 例文（e）がない: {w.head}")
        for jp, tr, _ in w.examples:
            if "〔" not in jp or "〕" not in jp:
                errs.append(f"{w.src_line}: 例文に〔 〕がない: {w.head}")
            if not tr:
                errs.append(f"{w.src_line}: 例文の訳がない: {w.head}")
        if not (w.parts or w.origin or w.core):
            errs.append(f"{w.src_line}: 語構成・由来・コアのどれもない: {w.head}")
        if not 1 <= w.rank <= 3:
            errs.append(f"{w.src_line}: 重要度は1〜3: {w.head}")
    for p in parts:
        for d in p.days:
            if strict and len(d.words) != WORDS_PER_DAY:
                errs.append(f"DAY {d.no:02d}: {len(d.words)}語（{WORDS_PER_DAY}語であること）")
    if strict and len(words) != TOTAL_WORDS:
        errs.append(f"収録語数 {len(words)}（{TOTAL_WORDS}語であること）")
    days = [d.no for p in parts for d in p.days]
    if days != list(range(1, len(days) + 1)):
        errs.append(f"DAY番号が連番でない: {days}")
    if strict:
        for fam in S.FAMILIES + S.THEMES:
            for m in fam[4] if len(fam) == 5 else fam[3]:
                if m not in heads:
                    errs.append(f"図の語が本文にない: {m}（{fam[0]}）")
        for _, _, ws in S.EMOTIONS:
            for m in ws:
                if m not in heads:
                    errs.append(f"心情語マップの語が本文にない: {m}")
        for _, _, adj, _ in S.VERB_ADJ:
            if adj not in heads:
                errs.append(f"対応図の語が本文にない: {adj}")
    return errs


# --------------------------------------------------------------------------- #
# 描画ヘルパ
# --------------------------------------------------------------------------- #
class Ctx:
    def __init__(self, parts: list[Part]):
        self.parts = parts
        self.words = [w for p in parts for d in p.days for w in d.words]
        self.by_head: dict[str, Word] = {}
        for w in self.words:
            self.by_head.setdefault(w.head, w)

    def link(self, name: str, cls: str = "") -> str:
        """見出し語なら本文カードへのリンクにする。「〜（…）」の注記は外して照合。"""
        base = re.sub(r"（.*?）", "", name).strip()
        w = self.by_head.get(base)
        c = f' class="{cls}"' if cls else ""
        if w:
            return f'<a href="#{w.id}"{c}>{esc(name)}</a>'
        return f"<span{c}>{esc(name)}</span>" if cls else esc(name)


def mark_target(s: str, cls: str = "tgt") -> str:
    return re.sub(r"〔(.*?)〕", lambda m: f'<em class="{cls}">{esc(m.group(1))}</em>', esc(s).replace("&#x27;", "'"))


def plain_example(s: str) -> str:
    return s.replace("〔", "").replace("〕", "")


def stars(n: int) -> str:
    return f'<span class="stars" aria-label="重要度{n}">' + "★" * n + '<span class="dim">' + "★" * (3 - n) + "</span></span>"


# --------------------------------------------------------------------------- #
# 単語カード
# --------------------------------------------------------------------------- #
def render_card(w: Word, ctx: Ctx) -> str:
    o: list[str] = []
    kokon = ' <span class="badge kokon" title="古今異義語">古今</span>' if w.modern else ""
    reading = reading_of(w)
    o.append(f'<article class="card" id="{w.id}" data-no="{w.no}">')
    o.append(
        f'<header class="card-top"><span class="num">{w.no:04d}</span>{stars(w.rank)}'
        f'<span class="pos">{esc(w.pos)}</span></header>'
    )
    o.append('<div class="head">')
    o.append(f'<h3 class="hw">{esc(w.head)}</h3>')
    if w.kanji:
        o.append(f'<span class="kanji">{esc(w.kanji)}</span>')
    if reading:
        o.append(f'<span class="yomi">{esc(reading)}</span>')
    o.append(kokon)
    o.append(
        '<span class="checks" aria-label="3回チェック">'
        + "".join(f'<button type="button" class="chk" data-k="{w.no}:{i}" aria-label="{i+1}回目"></button>' for i in range(3))
        + "</span>"
    )
    o.append("</div>")
    # 意味（赤字＝赤シートで隠れる）
    if len(w.means) == 1:
        o.append(f'<p class="mean sheet"><span>{esc(w.means[0])}</span></p>')
    else:
        items = "".join(
            f'<li{FIRST if i == 0 else ""}><span class="mk">{MARUNUM[i]}</span>{esc(m)}</li>'
            for i, m in enumerate(w.means)
        )
        o.append(f'<ol class="mean sheet">{items}</ol>')
    if w.parts:
        boxes = []
        for i, (a, b, star) in enumerate(w.parts):
            if i:
                boxes.append('<span class="plus">+</span>')
            boxes.append(f'<span class="box{" root" if star else ""}"><b>{esc(a)}</b><small>{esc(b)}</small></span>')
        o.append(f'<div class="parts">{"".join(boxes)}</div>')
    if w.origin:
        o.append(f'<p class="origin"><span class="lbl">由来</span>{esc(w.origin)}</p>')
    if w.core:
        o.append(f'<p class="core">{esc(w.core)}</p>')
    rel = []
    rel.append('<span class="tag syn">類</span>' + (" · ".join(ctx.link(x) for x in w.syn) or "—"))
    rel.append('<span class="tag ant">反</span>' + (" · ".join(ctx.link(x) for x in w.ant) or "—"))
    if w.der:
        rel.append('<span class="tag der">関</span>' + " · ".join(ctx.link(x) for x in w.der))
    o.append('<div class="rel">' + "".join(f"<span class=\"rel-i\">{r}</span>" for r in rel) + "</div>")
    for jp, tr, src in w.examples:
        srcs = f'<span class="src">{esc(src)}</span>' if src else '<span class="src sakurei">作例</span>'
        o.append(
            f'<div class="ex"><p class="ex-jp">{mark_target(jp)}{srcs}</p>'
            f'<p class="ex-tr sheet"><span>{esc(tr)}</span></p></div>'
        )
    foot = []
    if w.modern:
        foot.append(f'<p class="modern"><span class="lbl">現代語では</span>{esc(w.modern)}</p>')
    if w.point:
        foot.append(f'<p class="point"><span class="lbl">入試</span>{esc(w.point)}</p>')
    o.append("".join(foot))
    o.append("</article>")
    return "".join(o)


# --------------------------------------------------------------------------- #
# 図（SVG）
# --------------------------------------------------------------------------- #
def svg_radial(center: str, sub: str, members: list[str], ctx: Ctx, idx: int) -> str:
    W, H = 460, 360
    cx, cy = W / 2, H / 2
    n = len(members)
    R = 128 if n > 8 else 112
    r0 = 46
    o = [f'<svg viewBox="0 0 {W} {H}" class="radial" role="img" aria-label="{esc(center)}の語源ファミリー">']
    for i, m in enumerate(members):
        ang = -math.pi / 2 + 2 * math.pi * i / n
        ca, sa = math.cos(ang), math.sin(ang)
        x1, y1 = cx + ca * (r0 + 4), cy + sa * (r0 + 4)
        x2, y2 = cx + ca * (R - 10), cy + sa * (R - 10)
        tx, ty = cx + ca * R, cy + sa * R
        anchor = "start" if ca > 0.3 else "end" if ca < -0.3 else "middle"
        dy = 5 if abs(sa) < 0.5 else (14 if sa > 0 else -2)
        o.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" class="spoke"/>')
        w = ctx.by_head.get(m)
        label = f'<text x="{tx:.1f}" y="{ty + dy:.1f}" text-anchor="{anchor}" class="leaf">{esc(m)}</text>'
        o.append(f'<a href="#{w.id}">{label}</a>' if w else label)
    fs = 26 if len(center) <= 2 else 21 if len(center) <= 3 else 17
    o.append(f'<circle cx="{cx}" cy="{cy}" r="{r0}" class="hub"/>')
    o.append(f'<text x="{cx}" y="{cy + 2}" text-anchor="middle" class="hub-t" style="font-size:{fs}px">{esc(center)}</text>')
    o.append(f'<text x="{cx}" y="{cy + 22}" text-anchor="middle" class="hub-s">{esc(sub)}</text>')
    o.append("</svg>")
    return "".join(o)


def svg_timeline() -> str:
    n = len(S.TIMELINE)
    W, H = 900, 190
    x0, x1 = 40, W - 40
    step = (x1 - x0) / (n - 1)
    o = [f'<svg viewBox="0 0 {W} {H}" class="timeline" role="img" aria-label="夜から朝への時間語">']
    o.append('<defs><linearGradient id="sky" x1="0" x2="1" y1="0" y2="0">'
             '<stop offset="0" class="sky-a"/><stop offset=".45" class="sky-b"/><stop offset="1" class="sky-c"/></linearGradient></defs>')
    o.append(f'<rect x="{x0}" y="70" width="{x1 - x0}" height="14" rx="7" fill="url(#sky)"/>')
    for i, (kana, kan, gloss) in enumerate(S.TIMELINE):
        x = x0 + step * i
        up = i % 2 == 0
        o.append(f'<circle cx="{x:.1f}" cy="77" r="6" class="tl-dot"/>')
        if up:
            o.append(f'<text x="{x:.1f}" y="18" text-anchor="middle" class="tl-g">{esc(gloss)}</text>')
            o.append(f'<text x="{x:.1f}" y="42" text-anchor="middle" class="tl-k">{esc(kana)}</text>')
            o.append(f'<text x="{x:.1f}" y="60" text-anchor="middle" class="tl-j">{esc(kan)}</text>')
        else:
            o.append(f'<text x="{x:.1f}" y="110" text-anchor="middle" class="tl-k">{esc(kana)}</text>')
            o.append(f'<text x="{x:.1f}" y="128" text-anchor="middle" class="tl-j">{esc(kan)}</text>')
            o.append(f'<text x="{x:.1f}" y="148" text-anchor="middle" class="tl-g">{esc(gloss)}</text>')
    o.append(f'<text x="{x0}" y="178" class="tl-edge">← 夜</text>')
    o.append(f'<text x="{x1}" y="178" text-anchor="end" class="tl-edge">朝 →</text>')
    o.append("</svg>")
    return "".join(o)


def svg_junishi() -> str:
    W = H = 420
    cx = cy = 210
    ro, ri = 190, 92
    o = [f'<svg viewBox="0 0 {W} {H}" class="junishi" role="img" aria-label="十二支の時刻と方位">']
    o.append(f'<circle cx="{cx}" cy="{cy}" r="{ro}" class="ring"/>')
    o.append(f'<circle cx="{cx}" cy="{cy}" r="{ri}" class="ring-in"/>')
    for i, (shi, yomi, t, d) in enumerate(S.JUNISHI):
        # 子を真上（北）に置き、時計回り。各区画の境界は ±15°
        a = math.radians(-90 + 30 * i)
        b = math.radians(-90 + 30 * i - 15)
        o.append(f'<line x1="{cx + math.cos(b) * ri:.1f}" y1="{cy + math.sin(b) * ri:.1f}" '
                 f'x2="{cx + math.cos(b) * ro:.1f}" y2="{cy + math.sin(b) * ro:.1f}" class="sep"/>')
        rx, ry = cx + math.cos(a) * 150, cy + math.sin(a) * 150
        o.append(f'<text x="{rx:.1f}" y="{ry + 2:.1f}" text-anchor="middle" class="js-shi{" main" if d else ""}">{shi}</text>')
        o.append(f'<text x="{rx:.1f}" y="{ry + 17:.1f}" text-anchor="middle" class="js-yomi">{yomi}</text>')
        tx, ty = cx + math.cos(a) * 112, cy + math.sin(a) * 112
        o.append(f'<text x="{tx:.1f}" y="{ty + 4:.1f}" text-anchor="middle" class="js-t">{t.replace("時", "")}</text>')
    o.append(f'<text x="{cx}" y="{cy - 24}" text-anchor="middle" class="js-c">北＝子</text>')
    o.append(f'<text x="{cx}" y="{cy - 4}" text-anchor="middle" class="js-c">東＝卯　西＝酉</text>')
    o.append(f'<text x="{cx}" y="{cy + 16}" text-anchor="middle" class="js-c">南＝午</text>')
    o.append(f'<text x="{cx}" y="{cy + 38}" text-anchor="middle" class="js-c2">正午＝午の刻の真ん中</text>')
    o.append("</svg>")
    return "".join(o)


def svg_keigo_direction() -> str:
    return """<svg viewBox="0 0 640 250" class="kdir" role="img" aria-label="敬意の方向">
<rect x="250" y="16" width="140" height="48" rx="6" class="kd-box me"/>
<text x="320" y="38" text-anchor="middle" class="kd-t">話し手・書き手</text>
<text x="320" y="55" text-anchor="middle" class="kd-s">（会話文なら話し手）</text>
<rect x="30" y="176" width="160" height="56" rx="6" class="kd-box"/>
<text x="110" y="200" text-anchor="middle" class="kd-t">動作をする人</text>
<text x="110" y="220" text-anchor="middle" class="kd-s">（主語）</text>
<rect x="240" y="176" width="160" height="56" rx="6" class="kd-box"/>
<text x="320" y="200" text-anchor="middle" class="kd-t">動作を受ける人</text>
<text x="320" y="220" text-anchor="middle" class="kd-s">（目的語・相手）</text>
<rect x="450" y="176" width="160" height="56" rx="6" class="kd-box"/>
<text x="530" y="200" text-anchor="middle" class="kd-t">聞き手・読み手</text>
<text x="530" y="220" text-anchor="middle" class="kd-s">（会話の相手）</text>
<path d="M280 64 L130 172" class="kd-a son"/><path d="M320 64 L320 172" class="kd-a ken"/><path d="M360 64 L510 172" class="kd-a tei"/>
<text x="160" y="110" text-anchor="end" class="kd-l son">尊敬語</text>
<text x="330" y="126" class="kd-l ken">謙譲語</text>
<text x="480" y="110" class="kd-l tei">丁寧語</text>
</svg>"""


# --------------------------------------------------------------------------- #
# 巻頭・資料
# --------------------------------------------------------------------------- #
def render_cover(ctx: Ctx) -> str:
    n_parts = sum(1 for w in ctx.words if w.parts)
    n_fam = len(S.FAMILIES)
    n_real = sum(1 for w in ctx.words for e in w.examples if e[2])
    stats = [(f"{len(ctx.words):,}", "収録語"), (str(sum(len(p.days) for p in ctx.parts)), "DAY"),
             (str(n_parts), "語構成図"), (str(n_fam), "語源ファミリー"), (str(n_real), "古典本文の例文")]
    st = "".join(f'<div class="stat"><b>{a}</b><span>{b}</span></div>' for a, b in stats)
    return f"""<section class="cover" id="cover">
<p class="eyebrow">KANJI &amp; CORE IMAGES</p>
<p class="en-title">Understanding Classical Japanese Vocabulary</p>
<h1 class="title">理解する<br>古文単語帳 <span class="t-num">500</span></h1>
<p class="subtitle">語源・漢字・由来 再構成版</p>
<blockquote class="lead">古文単語を「分解して、納得して」覚えるための一冊。すべての語に漢字・語源・由来のいずれかを添え、
語構成の分解図、語源ファミリー図、接頭語・接尾語マップ、心情語マップ、敬語マップを収録した。
例文は古典本文を中心に、見出し語が働く一文を選んで現代語訳を付けている。</blockquote>
<div class="stats">{st}</div>
<div class="seal">図解版</div>
<p class="author">{AUTHOR}</p>
</section>"""


def render_toc(ctx: Ctx) -> str:
    front = [("howto", "本書の使い方"), ("method", "古文単語を理解する4つの鍵"), ("families", "01 語源ファミリー図"),
             ("themes", "02 言い換えネットワーク"), ("affixes", "03 接頭語・接尾語マップ"), ("verbadj", "04 動詞→形容詞 対応図"),
             ("emotions", "05 心情語マップ"), ("time", "06 時間・暦・方位"), ("keigo", "07 敬語マップ"), ("kokon", "08 古今異義語一覧")]
    fl = "".join(f'<li><a href="#{a}">{esc(b)}</a></li>' for a, b in front)
    pl = []
    for p in ctx.parts:
        ds = "".join(
            f'<li><a href="#day{d.no:02d}"><span class="d">DAY {d.no:02d}</span><span class="t">{esc(d.theme)}</span>'
            f'<span class="r">{d.words[0].no:04d}–{d.words[-1].no:04d}</span></a>'
            f'<span class="prog" data-day="{d.no}" aria-hidden="true"><i></i></span></li>'
            for d in p.days if d.words
        )
        pl.append(f'<div class="toc-part"><h3><span>PART {p.no}</span>{esc(p.name)}</h3><ol>{ds}</ol></div>')
    back = [("answers", "確認テスト・総合演習 解答"), ("log", "学習記録表"), ("index", "索引（五十音順）")]
    bl = "".join(f'<li><a href="#{a}">{esc(b)}</a></li>' for a, b in back)
    return f"""<section class="sec toc" id="toc">
<h2 class="sec-h"><span class="sec-n">目次</span>CONTENTS</h2>
<div class="toc-grid"><div class="toc-front"><div class="toc-g"><h3>巻頭資料</h3><ul>{fl}</ul></div><div class="toc-g"><h3>巻末</h3><ul>{bl}</ul></div></div>
<div class="toc-body">{"".join(pl)}</div></div>
</section>"""


def render_howto(ctx: Ctx) -> str:
    sample = ctx.words[0]
    rows = "".join(f"<tr><th>{a}</th><td class=\"n\">{b}</td><td>{esc(c)}</td><td>{esc(d)}</td></tr>" for a, b, c, d in S.SCHEDULE)
    return f"""<section class="sec" id="howto">
<h2 class="sec-h"><span class="sec-n">00</span>本書の使い方</h2>
<div class="howto">
<div class="howto-card">
<h3>1枚のカードの読み方</h3>
<ol class="anatomy">
<li><b>見出し語・漢字・読み</b>　歴史的仮名遣いの見出しに、漢字表記と現代仮名遣いの読みを添えた。</li>
<li><b>意味（赤字）</b>　①が最重要。赤字なので、赤シートをのせると隠れる。Web版は「赤シート」ボタンで隠せる。</li>
<li><b>語構成の分解図</b>　赤い箱が意味の核、灰色の箱が形を作る要素。分解できない語は「由来」で成り立ちを示す。</li>
<li><b>コアイメージ</b>　複数の意味を一本につなぐ原イメージ。意味を忘れたら、ここから作り直す。</li>
<li><b>類・反・関</b>　類義語・対義語・関連語。本書に載っている語はリンクになっている。</li>
<li><b>例文</b>　出典のあるものは古典本文、「作例」は本書で作った例文。訳も赤字。</li>
<li><b>入試</b>　設問で狙われる点。「現代語では」は古今異義語の注意。</li>
<li><b>□□□</b>　3回チェック欄。言えなかった回に印を付ける。</li>
</ol>
</div>
<div class="howto-card">
<h3>効率のよい回し方</h3>
<table class="sched"><thead><tr><th>段階</th><th>期間</th><th>やること</th><th>ねらい</th></tr></thead><tbody>{rows}</tbody></table>
<p class="note">各DAYの最後に<b>確認テスト</b>（意味の4択10問・例文の訳5問・漢字と語源5問）、5DAYごとに<b>総合演習</b>（100語から20問）がある。解答は巻末にまとめた。</p>
<p class="note">Web版では、画面上部のボタンから<b>暗記カード</b>（覚えた／あやしい／まだ を記録）と<b>4択クイズ</b>が使える。記録はこの端末のブラウザに保存される。</p>
</div>
</div>
</section>"""


def render_method() -> str:
    keys = [
        ("漢字をあてる", "かなで書かれた古語に漢字をあてると、意味の骨格が見える。",
         "「あやし」は「怪し」なら不思議だ、「賤し」なら身分が低い。漢字の違いが意味の違いになる。"),
        ("分解する", "「心＋もとなし」「有り＋難し」のように、形容詞の多くは二つの要素でできている。",
         "「ありがたし」＝存在することが難しい＝めったにない。感謝の意味はここからは出てこない。"),
        ("コアイメージでつなぐ", "多義語は、ばらばらの訳語を暗記せず、一本の原イメージからたどる。",
         "「ゆかし」＝そこへ行きたい → 見たい・聞きたい・知りたい。対象に合わせて訳を選ぶ。"),
        ("現代語との違いを意識する", "現代語と同じ形の語ほど誤訳しやすい。入試はそこを狙う。",
         "「うつくし」はかわいらしい、「やさし」は恥ずかしい、「ありがたし」はめったにない。"),
    ]
    items = "".join(
        f'<div class="key"><span class="key-n">{i}</span><h3>{esc(a)}</h3><p>{esc(b)}</p><p class="key-ex">{esc(c)}</p></div>'
        for i, (a, b, c) in enumerate(keys, 1)
    )
    return f"""<section class="sec" id="method">
<h2 class="sec-h"><span class="sec-n">00</span>古文単語を理解する4つの鍵</h2>
<p class="sec-lead">古文単語は、英単語のように接頭辞と語根がはっきり分かれてはいない。そのかわり、<b>漢字</b>と<b>もとの動詞</b>と<b>イメージ</b>が意味の手がかりになる。本書のカードは、次の4つの鍵のどれかで一語一語を説明している。</p>
<div class="keys">{items}</div>
</section>"""


def render_families(ctx: Ctx) -> str:
    cells = []
    for i, (core, kan, gloss, desc, mem) in enumerate(S.FAMILIES):
        cells.append(
            f'<figure class="fam">{svg_radial(core, kan, mem, ctx, i)}'
            f'<figcaption><b>{esc(core)}</b>（{esc(kan)}＝{esc(gloss)}）<span class="cnt">{len(mem)}語</span>'
            f'<small>{esc(desc)}</small></figcaption></figure>'
        )
    return f"""<section class="sec" id="families">
<h2 class="sec-h"><span class="sec-n">01</span>語源ファミリー図</h2>
<p class="sec-lead">同じ要素を含む語を放射状に並べた。中心の要素の意味がわかれば、まわりの語の意味は半分わかったことになる。語をタップすると本文のカードへ移動する。</p>
<div class="fam-grid">{"".join(cells)}</div>
</section>"""


def render_themes(ctx: Ctx) -> str:
    cells = []
    for i, (core, sub, desc, mem) in enumerate(S.THEMES):
        cells.append(
            f'<figure class="fam theme">{svg_radial(core, sub, mem, ctx, 100 + i)}'
            f'<figcaption><b>{esc(core)}</b><span class="cnt">{len(mem)}語</span><small>{esc(desc)}</small></figcaption></figure>'
        )
    return f"""<section class="sec" id="themes">
<h2 class="sec-h"><span class="sec-n">02</span>言い換えネットワーク</h2>
<p class="sec-lead">古文は大事なことほど遠回しに言う。「死ぬ」「出家する」「恋をする・結婚する」の言い換えをまとめて押さえると、物語の山場を読み落とさない。</p>
<div class="fam-grid">{"".join(cells)}</div>
</section>"""


def render_affixes(ctx: Ctx) -> str:
    cols = []
    for title, color, rows in S.PREFIXES:
        lis = "".join(f'<li><span class="afx">{esc(a)}</span><span class="afx-m">{esc(b)}</span><span class="afx-e">{esc(c)}</span></li>' for a, b, c in rows)
        cols.append(f'<div class="afx-col {color}"><h3>{esc(title)}</h3><ul>{lis}</ul></div>')
    sl = "".join(f'<li><span class="afx">{esc(a)}</span><span class="afx-m">{esc(b)}</span><span class="afx-e">{esc(c)}</span></li>' for a, b, c in S.SUFFIXES)
    return f"""<section class="sec" id="affixes">
<h2 class="sec-h"><span class="sec-n">03</span>接頭語・接尾語マップ</h2>
<p class="sec-lead">接頭語は語の<b>気分</b>を、接尾語は語の<b>品詞と様子</b>を決める。「うち-」「かき-」のように意味をほとんど持たないものは、訳すときに無視してよい。</p>
<div class="afx-grid">{"".join(cols)}</div>
<div class="afx-col suffix"><h3>接尾語</h3><ul class="two">{sl}</ul></div>
</section>"""


def render_verbadj(ctx: Ctx) -> str:
    rows = []
    for v, vg, a, ag in S.VERB_ADJ:
        rows.append(
            f'<li><span class="va-v"><b>{esc(v)}</b><small>{esc(vg)}</small></span><span class="va-arrow" aria-hidden="true"></span>'
            f'<span class="va-a">{ctx.link(a)}<small>{esc(ag)}</small></span></li>'
        )
    return f"""<section class="sec" id="verbadj">
<h2 class="sec-h"><span class="sec-n">04</span>動詞 → 形容詞 対応図</h2>
<p class="sec-lead">シク活用の形容詞には、動詞から生まれたものが多い。もとの動詞を思い出せば、形容詞の意味は「その動作をしたくなる／してしまう状態」として復元できる。</p>
<ul class="va">{"".join(rows)}</ul>
</section>"""


def render_emotions(ctx: Ctx) -> str:
    cells = []
    for title, tone, ws in S.EMOTIONS:
        chips = "".join(ctx.link(w, "chip") for w in ws)
        cells.append(f'<div class="emo {tone}"><h3>{esc(title)}</h3><div class="chips">{chips}</div></div>')
    return f"""<section class="sec" id="emotions">
<h2 class="sec-h"><span class="sec-n">05</span>心情語マップ</h2>
<p class="sec-lead">心情語は、プラスかマイナスかを先に決めると訳を外さない。傍線部の心情を問われたら、まずこの地図のどの区画に入るかを考える。</p>
<div class="emo-legend"><span class="plus">プラス</span><span class="neutral">どちらにも</span><span class="minus">マイナス</span></div>
<div class="emo-grid">{"".join(cells)}</div>
</section>"""


def render_time(ctx: Ctx) -> str:
    months = "".join(
        f'<tr class="{ {"春": "sp", "夏": "su", "秋": "au", "冬": "wi"}[s] }"><td class="n">{m}月</td><th>{esc(k)}</th><td>{esc(y)}</td><td>{s}</td></tr>'
        for m, k, y, s in S.MONTHS
    )
    return f"""<section class="sec" id="time">
<h2 class="sec-h"><span class="sec-n">06</span>時間・暦・方位</h2>
<p class="sec-lead">平安の一日は夜から始まる。男が女のもとを訪ねるのは「よひ」、帰るのは「あかつき」、手紙が届くのは「つとめて」。時間語は恋の場面の時計でもある。</p>
<figure class="wide">{svg_timeline()}</figure>
<div class="time-grid">
<figure>{svg_junishi()}<figcaption>十二支の時刻と方位。一刻は2時間。「丑三つ」は丑の刻を4つに分けた3番目（午前2時〜2時半ごろ）。北東は「うしとら（艮）」、南東は「たつみ（巽）」。</figcaption></figure>
<div><h3 class="sub-h">月の異名</h3><table class="months"><thead><tr><th>月</th><th>異名</th><th>読み</th><th>季節</th></tr></thead><tbody>{months}</tbody></table>
<p class="note">陰暦では1〜3月が春、4〜6月が夏、7〜9月が秋、10〜12月が冬。「如月（2月）」の花は梅、「弥生（3月）」は桜。現代の季節感より約1か月早い。</p></div>
</div>
</section>"""


def render_keigo(ctx: Ctx) -> str:
    def cell(s: str) -> str:
        if s == "—":
            return '<span class="none">—</span>'
        out = []
        for part in s.split("／"):
            items = []
            for x in part.split("・"):
                m = re.match(r"^(.*?)(（.*?）)?$", x)
                items.append(ctx.link(m.group(1)) + (f"<small>{esc(m.group(2))}</small>" if m.group(2) else ""))
            out.append("・".join(items))
        return "<br>".join(out)

    rows = "".join(f"<tr><th>{esc(a)}</th><td>{cell(b)}</td><td>{cell(c)}</td></tr>" for a, b, c in S.KEIGO)
    return f"""<section class="sec" id="keigo">
<h2 class="sec-h"><span class="sec-n">07</span>敬語マップ</h2>
<p class="sec-lead">敬語は「誰から誰への敬意か」を問われる。尊敬語は動作をする人を、謙譲語は動作を受ける人を、丁寧語は聞き手を高める。敬意の出発点は、地の文なら作者、会話文なら話し手。</p>
<div class="keigo-top"><figure>{svg_keigo_direction()}</figure>
<div class="keigo-note"><h3 class="sub-h">注意したい3語</h3>
<p><b>たまふ</b>　四段活用なら尊敬（お与えになる／〜なさる）。下二段活用なら謙譲（いただく／〜させていただく）。下二段は会話文・手紙で「思ふ・見る・聞く」につく。</p>
<p><b>まゐる・たてまつる</b>　謙譲（参上する・差し上げる）が基本。身分の高い人が主語で、飲食・衣服・乗り物の文脈なら尊敬（召し上がる・お召しになる・お乗りになる）。</p>
<p><b>はべり・さぶらふ</b>　貴人のそばに「お仕えする」なら謙譲、会話文で「あります・おります・〜です」なら丁寧。</p></div></div>
<div class="scroll"><table class="keigo"><thead><tr><th>普通の語</th><th>尊敬語</th><th>謙譲語</th></tr></thead><tbody>{rows}</tbody></table></div>
<p class="note">丁寧語：はべり・さぶらふ（〜です・〜ます・あります・おります）。二方面への敬語「〜きこえたまふ」は、謙譲語で受け手を、尊敬語で動作主を同時に高める。</p>
</section>"""


def render_kokon(ctx: Ctx) -> str:
    rows = "".join(
        f'<tr><th>{ctx.link(w.head)}</th><td class="k">{esc(w.means[0])}</td><td class="m">{esc(w.modern)}</td><td class="n">{w.no:04d}</td></tr>'
        for w in ctx.words if w.modern
    )
    return f"""<section class="sec" id="kokon">
<h2 class="sec-h"><span class="sec-n">08</span>古今異義語一覧</h2>
<p class="sec-lead">現代語にもある形で、意味がずれている語。入試の選択肢は「現代語の意味」をわなとして置くことが多い。左の意味を言えるまで、この表だけで繰り返す。</p>
<div class="scroll"><table class="kokon"><thead><tr><th>古語</th><th>古文での中心の意味</th><th>現代語の意味</th><th>番号</th></tr></thead><tbody>{rows}</tbody></table></div>
</section>"""


# --------------------------------------------------------------------------- #
# DAY 本文とテスト
# --------------------------------------------------------------------------- #
def render_day(d: Day, p: Part, ctx: Ctx) -> str:
    tags = "".join(f'<span class="dtag">{esc(t)}</span>' for t in d.tags)
    cards = "".join(render_card(w, ctx) for w in d.words)
    return f"""<section class="day" id="day{d.no:02d}" data-day="{d.no}">
<div class="runhead"><span>DAY {d.no:02d}</span><span>{TITLE}｜図解版</span></div>
<header class="day-h"><div class="day-l"><span class="day-k">DAY</span><span class="day-n">{d.no:02d}</span>
<span class="day-r">{d.words[0].no:04d} – {d.words[-1].no:04d}</span><span class="day-c">{len(d.words)} words</span></div>
<div class="day-t"><h2>{esc(d.theme)}</h2><div class="dtags">{tags}</div></div></header>
<div class="cards">{cards}</div>
{render_test(d, ctx)}
</section>"""


def pick_distractors(w: Word, pool: list[Word], rng: random.Random, k: int = 3) -> list[str]:
    used = {w.means[0]}
    cands = [x for x in pool if x.head != w.head and x.means[0] not in used]
    rng.shuffle(cands)
    # 品詞が近いものを優先
    cands.sort(key=lambda x: 0 if x.pos[:1] == w.pos[:1] else 1)
    out = []
    for x in cands:
        if x.means[0] not in used:
            out.append(x.means[0])
            used.add(x.means[0])
        if len(out) == k:
            break
    return out


TESTS: list[dict] = []   # 解答編用に貯める


def render_test(d: Day, ctx: Ctx) -> str:
    rng = random.Random(1000 + d.no)
    ws = list(d.words)
    pool = [w for w in ctx.words if abs(w.day - d.no) <= 6]
    # A：意味の4択（10問）
    qa = rng.sample(ws, min(10, len(ws)))
    a_items, a_ans = [], []
    for i, w in enumerate(qa, 1):
        opts = [w.means[0]] + pick_distractors(w, pool, rng)
        rng.shuffle(opts)
        correct = opts.index(w.means[0])
        lis = "".join(
            f'<li><button type="button" class="opt" data-ok="{1 if j == correct else 0}"><span class="ol">{"アイウエ"[j]}</span>{esc(o)}</button></li>'
            for j, o in enumerate(opts)
        )
        a_items.append(f'<li><p class="q"><span class="qn">{i}</span><a href="#{w.id}" class="qw">{esc(w.head)}</a></p><ol class="opts">{lis}</ol></li>')
        a_ans.append((i, w, "アイウエ"[correct], w.means[0]))
    # B：例文の傍線部訳（5問）
    rest = [w for w in ws if w not in qa] or ws
    qb = rng.sample(rest, min(5, len(rest)))
    b_items, b_ans = [], []
    for i, w in enumerate(qb, 1):
        jp, tr, src = w.examples[0]
        b_items.append(
            f'<li><p class="q"><span class="qn">{i}</span><span class="qjp">{mark_target(jp, "ul")}</span></p>'
            f'<p class="reveal"><button type="button" class="rv">訳を見る</button><span class="rv-a" hidden>{esc(tr)}</span></p></li>'
        )
        b_ans.append((i, w, tr))
    # C：漢字と語源（5問）
    kan = [w for w in ws if w.kanji and re.search(r"[一-龥]", w.kanji)]
    rng.shuffle(kan)
    qc = kan[:5]
    c_items, c_ans = [], []
    for i, w in enumerate(qc, 1):
        hint = "・".join(p[1] for p in w.parts if p[2]) if w.parts else ""
        hint_html = f'<span class="hint">ヒント：{esc(hint)}</span>' if hint else ""
        c_items.append(
            f'<li><p class="q"><span class="qn">{i}</span><b class="qw">{esc(w.head)}</b>{hint_html}</p>'
            f'<p class="reveal"><button type="button" class="rv">答え</button><span class="rv-a" hidden>{esc(w.kanji)}（{esc(w.means[0])}）</span></p></li>'
        )
        c_ans.append((i, w, w.kanji))
    TESTS.append({"day": d.no, "a": a_ans, "b": b_ans, "c": c_ans})
    return f"""<section class="test" id="test{d.no:02d}">
<header class="test-h"><span class="test-k">CHECK</span><h3>DAY {d.no:02d} 確認テスト</h3><span class="score" data-score></span></header>
<div class="test-grid">
<div class="tq"><h4>A　次の語の意味として最も適当なものを選べ。<small>各1点</small></h4><ol class="qa">{"".join(a_items)}</ol></div>
<div class="tq"><h4>B　傍線部を現代語訳せよ。<small>各2点</small></h4><ol class="qb">{"".join(b_items)}</ol>
<h4>C　漢字をあてよ（あわせて意味も言えること）。<small>各1点</small></h4><ol class="qc">{"".join(c_items)}</ol></div>
</div>
<p class="test-foot">解答は <a href="#ans{d.no:02d}">巻末</a>。20点満点中16点未満なら、このDAYをもう一度。</p>
</section>"""


REVIEWS: list[dict] = []


def render_review(block: int, days: list[Day], ctx: Ctx) -> str:
    rng = random.Random(5000 + block)
    ws = [w for d in days for w in d.words]
    q = rng.sample(ws, min(20, len(ws)))
    q.sort(key=lambda w: w.no)
    items = "".join(
        f'<li><span class="qn">{i}</span><b>{esc(w.head)}</b><span class="rvw-n">{w.no:04d}</span>'
        f'<span class="line"></span><button type="button" class="rv">答</button><span class="rv-a" hidden>{esc(w.means[0])}</span></li>'
        for i, w in enumerate(q, 1)
    )
    REVIEWS.append({"block": block, "from": days[0].no, "to": days[-1].no, "q": q})
    return f"""<section class="review" id="review{block}">
<header class="test-h"><span class="test-k">REVIEW</span><h3>総合演習 {block}　DAY {days[0].no:02d}–{days[-1].no:02d}</h3></header>
<p class="sec-lead">次の語の意味を答えよ（各5点・100点満点）。80点に届かなければ、間違えた語の DAY を2周目のやり方でやり直す。</p>
<ol class="rvw">{items}</ol>
</section>"""


def render_answers() -> str:
    out = []
    for t in TESTS:
        a = "".join(f'<li><span class="qn">{i}</span>{c}　<span class="m">{esc(m)}</span></li>' for i, w, c, m in t["a"])
        b = "".join(f'<li><span class="qn">{i}</span>{esc(tr)}</li>' for i, w, tr in t["b"])
        c = "".join(f'<li><span class="qn">{i}</span>{esc(w.head)}＝{esc(k)}</li>' for i, w, k in t["c"])
        out.append(f'<div class="ans" id="ans{t["day"]:02d}"><h3>DAY {t["day"]:02d}</h3><p class="al">A</p><ol class="ans-a">{a}</ol>'
                   f'<p class="al">B</p><ol>{b}</ol><p class="al">C</p><ol>{c}</ol></div>')
    rv = []
    for r in REVIEWS:
        li = "".join(f'<li><span class="qn">{i}</span>{esc(w.head)}：{esc(w.means[0])}</li>' for i, w in enumerate(r["q"], 1))
        rv.append(f'<div class="ans"><h3>総合演習 {r["block"]}</h3><ol>{li}</ol></div>')
    return f"""<section class="sec answers" id="answers">
<h2 class="sec-h"><span class="sec-n">解答</span>確認テスト・総合演習</h2>
<div class="ans-grid">{"".join(out)}{"".join(rv)}</div>
</section>"""


def render_log(ctx: Ctx) -> str:
    rows = "".join(
        f'<tr><td class="n">DAY {d.no:02d}</td><td>{esc(d.theme)}</td><td></td><td></td><td></td><td class="sc">/20</td></tr>'
        for p in ctx.parts for d in p.days
    )
    return f"""<section class="sec" id="log">
<h2 class="sec-h"><span class="sec-n">記録</span>学習記録表</h2>
<p class="sec-lead">学習した日付を書き込む。3周目まで日付が埋まり、確認テストがすべて16点以上になれば完成。</p>
<div class="scroll"><table class="log"><thead><tr><th>DAY</th><th>テーマ</th><th>1周目</th><th>2周目</th><th>3周目</th><th>テスト</th></tr></thead><tbody>{rows}</tbody></table></div>
</section>"""


GOJUON = [("あ", "あいうえお"), ("か", "かきくけこがぎぐげご"), ("さ", "さしすせそざじずぜぞ"), ("た", "たちつてとだぢづでど"),
          ("な", "なにぬねの"), ("は", "はひふへほばびぶべぼぱぴぷぺぽ"), ("ま", "まみむめも"), ("や", "やゆよ"),
          ("ら", "らりるれろ"), ("わ", "わゐゑを")]


def render_index(ctx: Ctx) -> str:
    groups: dict[str, list[Word]] = {g: [] for g, _ in GOJUON}
    for w in ctx.words:
        for g, chars in GOJUON:
            if w.head[0] in chars:
                groups[g].append(w)
                break
    cols = []
    for g, ws in groups.items():
        if not ws:
            continue
        ws.sort(key=lambda w: (w.head, w.no))
        lis = "".join(f'<li><a href="#{w.id}">{esc(w.head)}</a><span class="n">{w.no:04d}</span></li>' for w in ws)
        cols.append(f'<div class="idx-g"><h3>{g}</h3><ul>{lis}</ul></div>')
    return f"""<section class="sec" id="index">
<h2 class="sec-h"><span class="sec-n">索引</span>五十音順</h2>
<div class="idx">{"".join(cols)}</div>
</section>"""


# --------------------------------------------------------------------------- #
# 組み立て
# --------------------------------------------------------------------------- #
FONTS = ("https://fonts.googleapis.com/css2?family=Shippori+Mincho+B1:wght@500;700;800"
         "&family=Noto+Sans+JP:wght@400;500;700&family=Cormorant+Garamond:wght@500;600&display=swap")


def app_data(ctx: Ctx) -> str:
    rows = []
    for w in ctx.words:
        jp, tr, src = w.examples[0]
        rows.append({"n": w.no, "h": w.head, "k": w.kanji, "p": w.pos, "d": w.day, "r": w.rank, "m": w.means,
                     "c": w.core, "e": plain_example(jp), "t": tr, "s": src, "y": reading_of(w)})
    return json.dumps(rows, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")


def build(parts: list[Part]) -> tuple[str, str]:
    ctx = Ctx(parts)
    TESTS.clear()
    REVIEWS.clear()
    body: list[str] = []
    body.append(render_cover(ctx))
    body.append(render_toc(ctx))
    body.append(render_howto(ctx))
    body.append(render_method())
    body.append(render_families(ctx))
    body.append(render_themes(ctx))
    body.append(render_affixes(ctx))
    body.append(render_verbadj(ctx))
    body.append(render_emotions(ctx))
    body.append(render_time(ctx))
    body.append(render_keigo(ctx))
    body.append(render_kokon(ctx))
    all_days = [d for p in parts for d in p.days if d.words]
    for p in parts:
        body.append(f'<section class="part-h" id="part{p.no}"><span class="part-k">PART</span><span class="part-n">{p.no}</span>'
                    f'<h2>{esc(p.name)}</h2><p>{esc(p.desc)}</p>'
                    f'<p class="part-r">DAY {p.days[0].no:02d}–{p.days[-1].no:02d}</p></section>')
        for d in p.days:
            if not d.words:
                continue
            body.append(render_day(d, p, ctx))
            if d.no % 5 == 0:
                block = d.no // 5
                body.append(render_review(block, all_days[(block - 1) * 5: block * 5], ctx))
    body.append(render_answers())
    body.append(render_log(ctx))
    body.append(render_index(ctx))

    css = (SRC / "style.css").read_text(encoding="utf-8")
    js = (SRC / "app.js").read_text(encoding="utf-8")
    toolbar = (SRC / "toolbar.html").read_text(encoding="utf-8")
    head = f"""<title>{TITLE}</title>
<meta name="description" content="語源・漢字・由来から理解する大学入試古文単語500語。語構成図・語源ファミリー図・心情語マップ・敬語マップ・確認テスト付き。">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="{FONTS}">
<style>{css}</style>"""
    main = f"""{toolbar}
<main class="book">{"".join(body)}</main>
<script id="kobun-data" type="application/json">{app_data(ctx)}</script>
<script>{js}</script>"""
    full = f"""<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
{head}
</head>
<body>
{main}
</body>
</html>
"""
    fragment = f"{head}\n{main}\n"
    return full, fragment


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="500語そろっていることまで検査する")
    ap.add_argument("--fragment", help="<html>等を含まない版の出力先")
    args = ap.parse_args()
    parts = parse()
    errs = check(parts, strict=args.check)
    full, fragment = build(parts)
    DIST.mkdir(exist_ok=True)
    out = DIST / "kobun-tango-500.html"
    out.write_text(full, encoding="utf-8")
    if args.fragment:
        Path(args.fragment).write_text(fragment, encoding="utf-8")
    n = sum(len(d.words) for p in parts for d in p.days)
    print(f"{out.relative_to(ROOT)}: {n}語 / {len(full.encode()) // 1024} KB")
    for e in errs:
        print("  !", e, file=sys.stderr)
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
