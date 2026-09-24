#!/usr/bin/env python3
"""対策パックの形式チェック（標準ライブラリのみ）。

STYLE.md の「ファイル構成」に沿っているかを機械的に確かめる。
内容の正しさは見ない（それは人と検証担当の仕事）。

    python3 exam-prep/tools/check_packs.py          # 一覧表示
    python3 exam-prep/tools/check_packs.py --strict # 問題があれば終了コード1
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# 見出し「## 0.」〜「## 8.」を必須とする。
REQUIRED_SECTIONS = range(0, 9)
MIN_CHARS = 12000
MIN_CHECKLIST = 15


def check(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    problems: list[str] = []

    first = text.lstrip().splitlines()[0] if text.strip() else ""
    tag = "【共通テスト】" if path.parent.name == "kyotsu" else "【二次・記述】"
    if not first.startswith("# ") or tag not in first:
        problems.append(f"1行目の見出しに {tag} がない")

    found = {int(m) for m in re.findall(r"^## (\d+)\.", text, flags=re.M)}
    missing = [n for n in REQUIRED_SECTIONS if n not in found]
    if missing:
        problems.append("節が足りない: " + ", ".join(f"## {n}." for n in missing))

    order = [int(m) for m in re.findall(r"^## (\d+)\.", text, flags=re.M)]
    if order != sorted(order):
        problems.append(f"節の順序が崩れている: {order}")

    chars = len(text)
    if chars < MIN_CHARS:
        problems.append(f"分量が少ない: {chars}字")

    checklist = len(re.findall(r"^\s*[-*]?\s*□", text, flags=re.M))
    if checklist < MIN_CHECKLIST:
        problems.append(f"直前チェックリストが {checklist} 項目（{MIN_CHECKLIST}以上）")

    # 数式の $ の数が奇数なら閉じ忘れ（コードブロック内とエスケープは除外）
    body = re.sub(r"```.*?```", "", text, flags=re.S)
    body = body.replace(r"\$", "")
    if body.count("$") % 2:
        problems.append("$ の数が奇数（数式の閉じ忘れの可能性）")

    return problems


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--strict", action="store_true")
    args = ap.parse_args()

    files = sorted((ROOT / "kyotsu").glob("*.md")) + sorted((ROOT / "niji").glob("*.md"))
    bad = 0
    for f in files:
        probs = check(f)
        rel = f.relative_to(ROOT)
        size = len(f.read_text(encoding="utf-8"))
        status = "OK " if not probs else "NG "
        print(f"{status}{rel}  ({size:,}字)")
        for p in probs:
            print(f"     - {p}")
        bad += bool(probs)
    print(f"\n{len(files)}ファイル中 {bad} ファイルに指摘あり")
    return 1 if (args.strict and bad) else 0


if __name__ == "__main__":
    sys.exit(main())
