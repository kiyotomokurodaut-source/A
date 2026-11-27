#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""r26: 各ページの本文だけを Markdown にする（/about/index.md など）。

LLM・AIエージェントは HTML のナビゲーションやスクリプトを落とすための
ヒューリスティックを持たないことがあり、本文だけを素直に読める形で
置いておくと引用の精度が上がる。生成物はビルドのたびに作り直す。

* 対象は <main> の中の本文。ヘッダ・フッタ・パンくず・メニュー・スクリプト・
  フォーム部品は含めない。
* 見出し・段落・リスト・表・定義リストを Markdown に変換する。
* リンクはサイト内の相対URLを絶対URLにする（引用元をたどれるように）。
* 先頭に title / url / description / updated の front matter を置く。

    python3 tools/md_export_r26.py            # 生成
    python3 tools/md_export_r26.py --check    # 生成せずに件数だけ確認
"""
from __future__ import annotations

import argparse
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

SITE = "https://kurodaschool.jp"
PUBLIC = Path(__file__).resolve().parents[1] / "public"

SKIP_TAGS = {
    "script", "style", "svg", "noscript", "template", "iframe",
    "header", "footer", "nav", "form", "button", "input", "select",
    "textarea", "option", "canvas", "video", "audio", "picture", "source",
}
VOID_TAGS = {
    "br", "img", "input", "meta", "link", "hr", "source", "area",
    "base", "col", "embed", "param", "track", "wbr",
}


def absolute(href: str) -> str:
    if not href or href.startswith(("#", "mailto:", "tel:", "javascript:", "data:")):
        return href
    if href.startswith("http://") or href.startswith("https://"):
        return href
    if href.startswith("/"):
        return SITE + href
    return href


class Markdown(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.blocks: list[str] = []
        self.buf: list[str] = []
        self.kind: str | None = None
        self.prefix = ""
        self.skip = 0
        self.in_main = False
        self.main_seen = False
        self.lists: list[list] = []  # [tag, counter, indent]
        self.link_stack: list[bool] = []
        self.table: list[list[str]] | None = None
        self.row: list[str] | None = None
        self.cell: list[str] | None = None
        self.caption: str | None = None
        self.strong = 0
        self.em = 0
        self.code = 0
        self.summary = 0
        self.pending_dt = False
        self.hidden = 0

    # -- helpers --------------------------------------------------------- #
    def target(self) -> list[str]:
        return self.cell if self.cell is not None else self.buf

    def flush(self) -> None:
        if self.kind is None:
            return
        text = "".join(self.buf)
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{2,}", "\n", text).strip()
        if text:
            if self.kind.startswith("h"):
                level = int(self.kind[1])
                self.blocks.append("#" * level + " " + text)
            elif self.kind == "dt":
                self.blocks.append(f"**{text}**")
                self.pending_dt = True
            elif self.kind == "dd" and self.pending_dt and self.blocks:
                self.blocks[-1] += "：" + text
                self.pending_dt = False
            else:
                self.pending_dt = False
                line = f"{self.prefix}{text}" if self.prefix else text
                self.blocks.append(line)
        self.buf = []
        self.kind = None
        self.prefix = ""

    def ensure_block(self, kind: str = "p", prefix: str = "") -> None:
        if self.kind is None:
            self.kind, self.prefix = kind, prefix
        elif kind.startswith("h"):
            self.flush()
            self.kind, self.prefix = kind, prefix

    # -- parser ---------------------------------------------------------- #
    def handle_starttag(self, tag, attrs):  # noqa: ANN001
        a = {k.lower(): (v or "") for k, v in attrs}
        if tag in SKIP_TAGS:
            if tag in VOID_TAGS:
                return
            self.skip += 1
            return
        if a.get("aria-hidden") == "true":
            if tag not in VOID_TAGS:
                self.hidden += 1
            return
        if self.skip or self.hidden:
            return
        if tag == "main":
            self.in_main = True
            self.main_seen = True
            return
        if not self.in_main:
            return
        if tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            self.flush()
            self.kind = tag
            self.prefix = ""
        elif tag == "p":
            self.flush()
            self.kind = "p"
        elif tag == "blockquote":
            self.flush()
            self.kind = "p"
            self.prefix = "> "
        elif tag in ("ul", "ol"):
            self.flush()
            self.lists.append([tag, 0, len(self.lists)])
        elif tag == "li":
            self.flush()
            if self.lists:
                entry = self.lists[-1]
                entry[1] += 1
                indent = "  " * (len(self.lists) - 1)
                marker = "- " if entry[0] == "ul" else f"{entry[1]}. "
                self.kind = "li"
                self.prefix = indent + marker
            else:
                self.kind = "li"
                self.prefix = "- "
        elif tag == "table":
            self.flush()
            self.table = []
            self.caption = None
        elif tag == "caption":
            self.flush()
            self.kind = "p"
        elif tag == "tr":
            self.flush()
            self.row = []
        elif tag in ("th", "td"):
            self.flush()
            self.cell = []
        elif tag == "dl":
            self.flush()
        elif tag in ("dt", "dd"):
            self.flush()
            self.kind = tag
        elif tag == "summary":
            self.flush()
            self.kind = "p"
            self.summary = 1
        elif tag == "br":
            if self.cell is not None:
                self.cell.append(" ")
            else:
                self.ensure_block()
                self.buf.append("\n")
        elif tag == "hr":
            self.flush()
            self.blocks.append("---")
        elif tag == "a":
            self.ensure_block()
            if self.buf and not self.buf[-1].endswith((" ", "\n", "[", "（")):
                self.buf.append(" ")
            href = absolute(a.get("href", ""))
            self.target().append("[")
            self.link_stack.append(bool(href))
            self._href = href
        elif tag in ("strong", "b"):
            self.ensure_block()
            self.target().append("**")
            self.strong += 1
        elif tag in ("em", "i"):
            self.ensure_block()
            self.target().append("*")
            self.em += 1
        elif tag == "code":
            self.ensure_block()
            self.target().append("`")
            self.code += 1
        elif tag == "img":
            alt = a.get("alt", "").strip()
            if alt:
                self.ensure_block()
                self.target().append(f"（画像: {alt}）")

    def handle_endtag(self, tag):  # noqa: ANN001
        if tag in SKIP_TAGS:
            if tag in VOID_TAGS:
                return
            if self.skip:
                self.skip -= 1
            return
        if self.hidden:
            self.hidden -= 1
            return
        if self.skip:
            return
        if tag == "main":
            self.flush()
            self.in_main = False
            return
        if not self.in_main:
            return
        if tag in ("h1", "h2", "h3", "h4", "h5", "h6", "p", "blockquote", "li", "summary", "dt", "dd"):
            if tag == "summary":
                self.summary = 0
                self.flush()
                return
            self.flush()
        elif tag in ("ul", "ol"):
            self.flush()
            if self.lists:
                self.lists.pop()
        elif tag in ("th", "td"):
            if self.cell is not None and self.row is not None:
                text = re.sub(r"\s+", " ", "".join(self.cell)).strip()
                self.row.append(text.replace("|", "\\|"))
                self.cell = None
        elif tag == "tr":
            if self.row is not None and self.table is not None and self.row:
                self.table.append(self.row)
                self.row = None
        elif tag == "caption":
            text = re.sub(r"\s+", " ", "".join(self.buf)).strip()
            self.caption = text or None
            self.buf = []
            self.kind = None
        elif tag == "table":
            if self.table:
                lines = []
                if self.caption:
                    lines.append(f"*{self.caption}*")
                    lines.append("")
                header = self.table[0]
                lines.append("| " + " | ".join(header) + " |")
                lines.append("|" + "|".join([" --- "] * len(header)) + "|")
                for row in self.table[1:]:
                    row = row + [""] * (len(header) - len(row))
                    lines.append("| " + " | ".join(row[: len(header)]) + " |")
                self.blocks.append("\n".join(lines))
            self.table = None
            self.caption = None
        elif tag == "a":
            href = getattr(self, "_href", "")
            self.target().append(f"]({href})" if href else "]")
            if self.link_stack:
                self.link_stack.pop()
        elif tag in ("strong", "b"):
            self.target().append("**")
            self.strong = max(0, self.strong - 1)
        elif tag in ("em", "i"):
            self.target().append("*")
            self.em = max(0, self.em - 1)
        elif tag == "code":
            self.target().append("`")
            self.code = max(0, self.code - 1)
        elif tag in ("div", "dl", "section", "article", "aside"):
            self.flush()

    def handle_data(self, data):  # noqa: ANN001
        if self.skip or not self.in_main:
            return
        if self.cell is None and self.table is not None and self.row is None:
            # text directly inside <table> (whitespace) is noise
            if not data.strip():
                return
        if self.cell is None and self.kind is None:
            if not data.strip():
                return
            self.ensure_block()
        text = re.sub(r"\s+", " ", data)
        self.target().append(text)

    # -- output ---------------------------------------------------------- #
    def markdown(self) -> str:
        self.flush()
        merged: list[str] = []
        item = re.compile(r"^\s*(?:- |\d+\. )")
        for block in self.blocks:
            if not block.strip():
                continue
            if merged and item.match(block) and item.match(merged[-1]) or (
                merged and item.match(block) and item.match(merged[-1].split("\n")[-1])
            ):
                merged[-1] += "\n" + block
            else:
                merged.append(block)
        text = "\n\n".join(merged)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()


def meta_of(raw: str) -> dict:
    def find(pattern: str) -> str:
        m = re.search(pattern, raw, re.S)
        return m.group(1).strip() if m else ""

    return {
        "title": find(r"<title>(.*?)</title>"),
        "description": find(r'<meta[^>]*name="description"[^>]*content="([^"]*)"')
        or find(r'<meta[^>]*content="([^"]*)"[^>]*name="description"'),
        "lastmod": find(r'<meta[^>]*name="last-modified"[^>]*content="([^"]*)"')
        or find(r'<meta[^>]*content="([^"]*)"[^>]*name="last-modified"'),
        "canonical": find(r'<link[^>]*rel="canonical"[^>]*href="([^"]*)"')
        or find(r'<link[^>]*href="([^"]*)"[^>]*rel="canonical"'),
    }


def to_markdown(raw: str) -> str:
    md = Markdown()
    md.feed(raw)
    return md.markdown()


def url_path(path: Path) -> str:
    rel = path.relative_to(PUBLIC).as_posix()
    if rel == "index.html":
        return "/"
    if rel.endswith("/index.html"):
        return "/" + rel[: -len("index.html")]
    return "/" + rel


def convert_file(path: Path) -> str:
    raw = path.read_text(encoding="utf-8")
    meta = meta_of(raw)
    url = f"{SITE}{url_path(path)}"
    body = to_markdown(raw)
    front = [
        "---",
        f'title: "{meta["title"].replace(chr(34), chr(39))}"',
        f'url: "{url}"',
        f'description: "{meta["description"].replace(chr(34), chr(39))}"',
        f'updated: "{meta["lastmod"]}"',
        'source: "このMarkdownはHTML版から自動生成しています。表示はHTML版が正本です。"',
        "---",
        "",
    ]
    return "\n".join(front) + body + "\n"


def write_all(public: Path = PUBLIC) -> int:
    count = 0
    for path in sorted(public.rglob("*.html")):
        if path.name == "404.html":
            continue
        raw_head = path.read_text(encoding="utf-8")
        if "<main" not in raw_head:
            continue
        md = convert_file(path)
        path.with_suffix(".md").write_text(md, encoding="utf-8")
        count += 1
    return count


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    if args.check:
        n = sum(1 for p in PUBLIC.rglob("*.html") if p.name != "404.html")
        print(f"would write {n} markdown files")
        return 0
    n = write_all()
    print(f"wrote {n} markdown files")
    return 0


if __name__ == "__main__":
    sys.exit(main())
