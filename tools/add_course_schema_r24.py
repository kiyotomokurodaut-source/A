#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""r24: 主要サービスページに Course / Offer 構造化データを補う。

料金は build.py の正本（月額・税込・月4セット）と同じ値だけを使う。
既に Course ノードを持つページ（/ と /pricing/）には何もしない。
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "public"
SITE = "https://kurodaschool.jp"

PRICING = [
    ("面談のみ", 24000, "面談30分・月4セット"),
    ("授業のみ（週1回）", 30000, "90分授業を週1回（定期面談なし）"),
    ("面談＋授業（週1回）", 54990, "週1回の30分面談＋90分授業を週1回"),
    ("面談＋授業（週2回）", 79990, "週1回の30分面談＋90分授業を週2回"),
    ("面談＋授業（週3回）", 104990, "週1回の30分面談＋90分授業を週3回"),
]

TARGETS = {
    "online-tutoring/index.html": (
        "黒田塾のオンライン個別指導（継続受講）",
        "90分の個別授業と30分の学習面談を組み合わせた月額制の継続受講。"
        "指導は原則オンラインで全国47都道府県から受講できる。理科は対象外。",
    ),
    "university-exam/index.html": (
        "黒田塾の大学受験個別指導（継続受講）",
        "志望校の出題形式から逆算した大学受験の個別指導。英語・数学・国語・社会・"
        "小論文・面接に対応し、答案添削と週次の学習管理を含む月額制。",
    ),
    "junior-high-exam/index.html": (
        "黒田塾の中学受験個別指導（継続受講）",
        "中学受験の算数・国語・理科・社会に対応する個別指導。塾の宿題と解き直しを"
        "週単位の計画に落とし、保護者との分担も面談で確認する月額制。",
    ),
    "study-coaching/index.html": (
        "黒田塾の学習管理・受験コーチング",
        "授業を持たずに、30分の面談と週次の計画更新で学習を管理する月額制プラン。"
        "答案の確認とLINEでの質問対応を含む。",
    ),
}


def course_node(url: str, name: str, description: str) -> dict:
    return {
        "@context": "https://schema.org",
        "@type": "Course",
        "name": name,
        "description": description,
        "url": url,
        "provider": {"@id": f"{SITE}/#organization"},
        "inLanguage": "ja",
        "hasCourseInstance": {
            "@type": "CourseInstance",
            "courseMode": ["オンライン"],
            "location": {"@type": "VirtualLocation", "url": url},
            "offers": [
                {
                    "@type": "Offer",
                    "name": plan,
                    "price": price,
                    "priceCurrency": "JPY",
                    "category": "月額（税込・月4セット分）",
                    "description": note,
                    "availability": "https://schema.org/InStock",
                    "url": f"{SITE}/pricing/",
                }
                for plan, price, note in PRICING
            ],
        },
        "offers": {
            "@type": "AggregateOffer",
            "lowPrice": 24000,
            "highPrice": 104990,
            "priceCurrency": "JPY",
            "offerCount": len(PRICING),
            "url": f"{SITE}/pricing/",
        },
    }


def main() -> int:
    done = 0
    for rel, (name, desc) in TARGETS.items():
        path = PUBLIC / rel
        if not path.exists():
            print(f"missing: {rel}")
            continue
        text = path.read_text(encoding="utf-8")
        if '"@type": "Course"' in text or '"@type":"Course"' in text:
            print(f"already has Course: {rel}")
            continue
        url = f"{SITE}/" + rel.removesuffix("index.html")
        block = (
            '<script type="application/ld+json">\n'
            + json.dumps(course_node(url, name, desc), ensure_ascii=False, indent=2)
            + "\n</script>\n"
        )
        idx = text.find("</head>")
        if idx < 0:
            print(f"no </head>: {rel}")
            continue
        path.write_text(text[:idx] + block + text[idx:], encoding="utf-8")
        done += 1
    print(f"added Course to {done} pages")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
