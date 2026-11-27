#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""r26: 全ページのエンティティ（組織・代表・サイト）を共通定義に揃え、
Safari/Siri・音声検索・AI要約向けの SpeakableSpecification を各ページに付ける。

* EducationalOrganization / Person / WebSite のノードを site_entity_r24.py の
  定義で置き換える（ページごとの表記ゆれを残さない）。
* ページ自身のノード（@id が `<ページURL>#webpage`）に speakable を追加する。
  cssSelector は h1 と .summary-box。既存のノードの他の項目は変えない。
* JSON-LD ブロックは元の区切り文字の流儀（空白入り／詰め書き）で書き戻す。

    python3 tools/entity_speakable_r26.py            # 適用
    python3 tools/entity_speakable_r26.py --check    # 検証のみ（書き込まない）
"""
from __future__ import annotations

import argparse
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
PERSON_ID = f"{E.SITE}/#teacher"
WEBSITE_ID = f"{E.SITE}/#website"

CANONICAL_NODES = {ORG_ID: E.ORG_NODE, PERSON_ID: E.PERSON_NODE, WEBSITE_ID: E.WEBSITE_NODE}


def page_url(path: Path) -> str:
    rel = path.relative_to(PUBLIC).as_posix()
    if rel == "index.html":
        return f"{E.SITE}/"
    if rel.endswith("/index.html"):
        return f"{E.SITE}/{rel[: -len('index.html')]}"
    return f"{E.SITE}/{rel}"


def separators(body: str) -> tuple[str, str]:
    if '": ' in body and '", "' in body:
        return ", ", ": "
    return ",", ":"


def with_speakable(node: dict) -> dict:
    """ページノードに speakable を足す。他の項目と順序はそのまま。"""
    if node.get("speakable") == E.SPEAKABLE:
        return node
    out: dict = {}
    placed = False
    for key, value in node.items():
        out[key] = value
        if key == "inLanguage":
            out["speakable"] = E.SPEAKABLE
            placed = True
    if not placed:
        out["speakable"] = E.SPEAKABLE
    return out


def process(text: str) -> tuple[str, int, int, int, int]:
    """Return (new_text, org, person, website, speakable) counts."""
    counts = {"org": 0, "person": 0, "website": 0, "speakable": 0}
    out: list[str] = []
    cursor = 0
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
        except json.JSONDecodeError:
            out.append(body)
            cursor = end
            continue
        nodes = data.get("@graph") if isinstance(data, dict) else None
        target = nodes if isinstance(nodes, list) else (data if isinstance(data, list) else [data])
        for i, node in enumerate(target):
            if not isinstance(node, dict):
                continue
            nid = node.get("@id")
            if nid in CANONICAL_NODES:
                if node != CANONICAL_NODES[nid]:
                    target[i] = CANONICAL_NODES[nid]
                if nid == ORG_ID:
                    counts["org"] += 1
                elif nid == PERSON_ID:
                    counts["person"] += 1
                else:
                    counts["website"] += 1
                continue
            if isinstance(nid, str) and nid.endswith("#webpage"):
                target[i] = with_speakable(node)
                if target[i].get("speakable") == E.SPEAKABLE:
                    counts["speakable"] += 1
        sep = separators(body)
        out.append(json.dumps(data, ensure_ascii=False, separators=sep))
        cursor = end
    return "".join(out), counts["org"], counts["person"], counts["website"], counts["speakable"]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="verify without writing")
    args = ap.parse_args()

    changed = 0
    problems: list[str] = []
    totals = {"org": 0, "person": 0, "website": 0, "speakable": 0}
    for path in sorted(PUBLIC.rglob("*.html")):
        text = path.read_text(encoding="utf-8")
        noindex = "noindex" in text.lower()
        if OPEN not in text:
            if not noindex:
                problems.append(f"{page_url(path)}: no JSON-LD")
            continue
        new_text, org, person, website, speakable = process(text)
        url = page_url(path)
        if noindex:
            totals["org"] += org
            continue
        for label, n in (("organization", org), ("person", person), ("website", website)):
            if n != 1:
                problems.append(f"{url}: {n} {label} node(s), expected 1")
        if speakable != 1:
            problems.append(f"{url}: {speakable} page node(s) with speakable, expected 1")
        totals["org"] += org
        totals["person"] += person
        totals["website"] += website
        totals["speakable"] += speakable
        if new_text != text:
            changed += 1
            if not args.check:
                path.write_text(new_text, encoding="utf-8")

    print(
        f"{'would update' if args.check else 'updated'} {changed} pages; "
        f"org {totals['org']}, person {totals['person']}, website {totals['website']}, "
        f"speakable {totals['speakable']}"
    )
    if problems:
        print("\n".join(problems), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
