#!/usr/bin/env python3
"""Repair the audited duplicate FAQ anchor; never alter text or existing links.

Keeps the first id="consult" so the existing table of contents still works.
Only the second occurrence is renamed. No validation rules are disabled.
"""
from __future__ import annotations

from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
import json
import re

OLD_ID = "consult"
NEW_ID = "consult-secondary"


class Markup(HTMLParser):
    def __init__(self, raw: str) -> None:
        super().__init__(convert_charrefs=True)
        self.offsets = [0]
        for match in re.finditer("\n", raw):
            self.offsets.append(match.end())
        self.elements: list[tuple[str, int, str]] = []
        self.text: list[str] = []
        self.links: list[str] = []
        self.feed(raw)
        self.close()

    def handle_starttag(self, tag: str, attrs) -> None:
        attributes = dict(attrs)
        if attributes.get("id"):
            line, column = self.getpos()
            self.elements.append((attributes["id"], self.offsets[line - 1] + column, self.get_starttag_text()))
        if tag == "a" and attributes.get("href"):
            self.links.append(attributes["href"])

    def handle_data(self, data: str) -> None:
        self.text.append(data)


ID_ATTRIBUTE = re.compile(r'''(?i)(?<!\S)id\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s>]+))''')


def repair(raw: str) -> tuple[str, dict]:
    before = Markup(raw)
    ids = [identifier for identifier, _, _ in before.elements]
    occurrences = [item for item in before.elements if item[0] == OLD_ID]
    if len(occurrences) == 1:
        return raw, {"changed": False, "reason": "consult is already unique"}
    if len(occurrences) != 2:
        raise ValueError(f"Expected one or two consult anchors, found {len(occurrences)}; review the FAQ before proceeding")
    if NEW_ID in ids:
        raise ValueError("The replacement anchor already exists; stop rather than create another duplicate")

    _, offset, tag = occurrences[1]
    attributes = [m for m in ID_ATTRIBUTE.finditer(tag) if next((v for v in m.groups() if v is not None), None) == OLD_ID]
    if len(attributes) != 1:
        raise ValueError("The duplicate opening tag has an unexpected id attribute")
    match = attributes[0]
    # Change only the value, preserving its quote style, all text and other attributes.
    group = next(i for i in (1, 2, 3) if match.group(i) is not None)
    start, end = match.span(group)
    updated = raw[:offset + start] + NEW_ID + raw[offset + end:]
    after = Markup(updated)
    after_ids = [identifier for identifier, _, _ in after.elements]
    if after_ids.count(OLD_ID) != 1 or after_ids.count(NEW_ID) != 1:
        raise AssertionError("Anchor correction did not produce unique names")
    if before.text != after.text or before.links != after.links:
        raise AssertionError("FAQ text or link destinations were changed")
    remaining = {k: v for k, v in Counter(after_ids).items() if v > 1}
    if remaining:
        raise ValueError(f"Other duplicate FAQ anchors require review: {remaining}")
    return updated, {"changed": True, "preserved_anchor": OLD_ID, "renamed_second_anchor": NEW_ID,
                     "text_unchanged": True, "links_unchanged": True, "duplicate_ids_remaining": 0}


def main() -> None:
    root = Path.cwd()
    path = root / "public/faq/index.html"
    original = path.read_text(encoding="utf-8")
    updated, report = repair(original)
    if updated != original:
        path.write_text(updated, encoding="utf-8")
    report["file"] = "public/faq/index.html"
    (root / "r17-faq-anchor-fix.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
