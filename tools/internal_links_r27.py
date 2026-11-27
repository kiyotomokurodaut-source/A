#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""r27: 47都道府県ページから大学別ページへの内部リンクを張る。

    python3 tools/internal_links_r27.py          # 適用
    python3 tools/internal_links_r27.py --check  # 点検のみ（書き込みなし）

* 都道府県ページの大学一覧表で、専門対策ページがある大学名をリンクにする。
* 各都道府県ページの本文末（相談カードの直前）に、志望校別ページへの
  リンクブロックを置く。地名だけの量産ページにしないための回遊導線。
* 何度実行しても同じ結果になる（マーカー間を差し替える）。
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "public"
sys.path.insert(0, str(Path(__file__).resolve().parent))

import line_cro_r27 as C  # noqa: E402

START = "<!-- r27:uni-links:start -->"
END = "<!-- r27:uni-links:end -->"

# 志望校別ページ（全国から辿れる主要どころ）。ラベルとパスは実在するページのみ。
FLAGSHIP = [
    ("/specialty/todai-bunkei/", "東大（文科）の専門対策"),
    ("/specialty/waseda/", "早稲田大学の専門対策"),
    ("/specialty/keio/", "慶應義塾大学の専門対策"),
    ("/specialty/sophia/", "上智大学の専門対策"),
    ("/specialty/meiji/", "明治大学の専門対策"),
    ("/specialty/rikkyo/", "立教大学の専門対策"),
    ("/specialty/kankandoritsu/", "関関同立の専門対策"),
    ("/specialty/kokkouritsu/", "国公立大学の専門対策"),
]

# 大学名 → 大学別ページ（表のリンク用。ページが存在するものだけ）
UNI_ALIASES = {
    "東京大学": "/specialty/todai-bunkei/",
}


def uni_pages() -> dict[str, str]:
    """specialtyページのtitle「◯◯大学の専門対策」から大学名→パスを作る。"""
    mapping = dict(UNI_ALIASES)
    for path in sorted((PUBLIC / "specialty").glob("*/index.html")):
        raw = path.read_text(encoding="utf-8")
        title = re.search(r"<title>(.*?)</title>", raw)
        if not title:
            continue
        name = title.group(1).split("｜")[0]
        name = re.sub(r"の(大学受験)?専門対策$", "", name).strip()
        if name.endswith("大学"):
            mapping.setdefault(name, f"/specialty/{path.parent.name}/")
    return mapping


def link_block() -> str:
    links = "".join(f'<a href="{href}">{label}</a>' for href, label in FLAGSHIP)
    return (
        f'{START}<section id="related-university">'
        "<h2>志望校別の対策ページ</h2>"
        "<p>同じサイト内の大学別ページです。志望校の出題形式から逆算した"
        "科目配分と答案の見方をまとめています。</p>"
        f'<nav aria-label="大学別の対策ページ" class="jump-links">{links}</nav>'
        '<p><a href="/specialty/">大学受験の専門対策トップ（全ページ一覧）</a></p>'
        f"</section>{END}"
    )


def link_table(raw: str, mapping: dict[str, str]) -> str:
    def repl(match: re.Match[str]) -> str:
        name = match.group(1)
        href = mapping.get(name)
        if not href:
            return match.group(0)
        return f'<td><a href="{href}">{name}</a></td>'

    # 大学一覧表の1列目だけを対象にする（<td>大学名</td>）
    return re.sub(r"<td>([^<]{2,24}大学)</td>", repl, raw)


def apply_page(path: Path, mapping: dict[str, str]) -> tuple[str, bool]:
    raw = path.read_text(encoding="utf-8")
    new = link_table(raw, mapping)
    block = link_block()
    if START in new and END in new:
        head, _, rest = new.partition(START)
        _, _, tail = rest.partition(END)
        new = head + block + tail
    else:
        for anchor in ('<!-- r27:cro-mid:start -->', '<section id="faq"', "</main>"):
            idx = new.find(anchor)
            if idx > 0:
                new = new[:idx] + block + "\n" + new[idx:]
                break
        else:
            raise SystemExit(f"{path}: 挿入位置が見つからない")
    if new != raw:
        path.write_text(new, encoding="utf-8")
        return new, True
    return new, False


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    mapping = uni_pages()
    targets = [
        p for p in sorted((PUBLIC / "specialty").glob("*/index.html"))
        if p.parent.name in C.PREF_NAMES
    ]
    changed, missing, linked = 0, [], 0
    for path in targets:
        raw = path.read_text(encoding="utf-8")
        if args.check:
            if START not in raw:
                missing.append(C.route(path))
            continue
        new, did = apply_page(path, mapping)
        changed += 1 if did else 0
        linked += len(re.findall(r'<td><a href="/specialty/', new))
    print(f"r27 内部リンク: 対象 {len(targets)} ページ / 更新 {changed} / 表内リンク {linked} / 未適用 {len(missing)}")
    if missing:
        print("\n".join(missing[:10]), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
