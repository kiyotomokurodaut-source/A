#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""r24: 全ページの EducationalOrganization ノードを共通定義に揃える。

* areaServed に47都道府県と日本を入れる（オンライン指導の全国対応）
* geo / hasMap / openingHoursSpecification / contactPoint を補う
* sameAs を実在確認できた公式URL（X・みんなの学校新聞の連載・外部プロフィール）に揃える

JSON-LD ブロックを解析して該当ノードだけを差し替え、元の区切り文字の流儀で
書き戻す。本文のHTMLには触らない。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import site_entity_r24 as E  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "public"
OPEN = '<script type="application/ld+json">'
CLOSE = "</script>"
ORG_ID = f"{E.SITE}/#organization"


def separators(body: str) -> tuple[str, str]:
    """元のブロックが空白入りか詰め書きかを判定して同じ流儀で書き戻す。"""
    if '": ' in body and '", "' in body:
        return ", ", ": "
    return ",", ":"


def main() -> int:
    changed = 0
    errors: list[str] = []
    for path in sorted(PUBLIC.rglob("*.html")):
        text = path.read_text(encoding="utf-8")
        if OPEN not in text:
            continue
        out = []
        cursor = 0
        page_changed = False
        org_nodes = 0
        while True:
            start = text.find(OPEN, cursor)
            if start < 0:
                out.append(text[cursor:])
                break
            body_start = start + len(OPEN)
            end = text.find(CLOSE, body_start)
            if end < 0:
                out.append(text[cursor:])
                break
            body = text[body_start:end]
            out.append(text[cursor:body_start])
            try:
                data = json.loads(body)
            except json.JSONDecodeError as exc:
                errors.append(f"{path}: invalid JSON-LD ({exc})")
                out.append(body)
                cursor = end
                continue
            nodes = data.get("@graph") if isinstance(data, dict) else None
            target = nodes if isinstance(nodes, list) else (
                data if isinstance(data, list) else [data]
            )
            for i, node in enumerate(target):
                if isinstance(node, dict) and node.get("@id") == ORG_ID:
                    org_nodes += 1
                    if node != E.ORG_NODE:
                        target[i] = E.ORG_NODE
                        page_changed = True
            sep = separators(body)
            out.append(
                json.dumps(data, ensure_ascii=False, separators=sep)
            )
            cursor = end
        if org_nodes == 0:
            continue
        new_text = "".join(out)
        if page_changed:
            path.write_text(new_text, encoding="utf-8")
            changed += 1

    # 構造検証
    for path in sorted(PUBLIC.rglob("*.html")):
        text = path.read_text(encoding="utf-8")
        robots = text.lower()
        if OPEN not in text:
            if "noindex" not in robots:
                errors.append(f"{path}: no JSON-LD")
            continue
        found = 0
        for chunk in text.split(OPEN)[1:]:
            body = chunk.split(CLOSE)[0]
            try:
                data = json.loads(body)
            except json.JSONDecodeError as exc:
                errors.append(f"{path}: {exc}")
                continue
            nodes = data.get("@graph", [data]) if isinstance(data, dict) else data
            for node in nodes:
                if isinstance(node, dict) and node.get("@id") == ORG_ID:
                    found += 1
                    if node != E.ORG_NODE:
                        errors.append(f"{path}: organization node differs")
        if found != 1 and "noindex" not in robots:
            errors.append(f"{path}: {found} organization nodes")
    print(f"updated {changed} pages")
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
