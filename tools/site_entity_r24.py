# -*- coding: utf-8 -*-
"""サイト共通のエンティティ定義（r24）。

EducationalOrganization / Person / WebSite のノードを1か所で定義し、
全ページの JSON-LD と地域ページ生成の両方から同じ内容を使う。
値は公開済みの事実のみ（拠点・電話・座標・営業方針・実在URL）。
"""
import json

SITE = "https://kurodaschool.jp"
ADDRESS = {
    "@type": "PostalAddress",
    "postalCode": "113-0024",
    "addressCountry": "JP",
    "addressRegion": "東京都",
    "addressLocality": "文京区",
    "streetAddress": "西片2-22-7 シャローム西片305",
}
# Google Maps のジオコード結果（東京都文京区西片2-22-7 シャローム西片）
GEO = {"@type": "GeoCoordinates", "latitude": 35.7152, "longitude": 139.7572}
HAS_MAP = (
    "https://www.google.com/maps/search/?api=1&query="
    "%E6%9D%B1%E4%BA%AC%E9%83%BD%E6%96%87%E4%BA%AC%E5%8C%BA%E8%A5%BF%E7%89%872-22-7"
)

PREF_NAMES = [
    "北海道", "青森県", "岩手県", "宮城県", "秋田県", "山形県", "福島県",
    "茨城県", "栃木県", "群馬県", "埼玉県", "千葉県", "東京都", "神奈川県",
    "新潟県", "富山県", "石川県", "福井県", "山梨県", "長野県", "岐阜県",
    "静岡県", "愛知県", "三重県",
    "滋賀県", "京都府", "大阪府", "兵庫県", "奈良県", "和歌山県",
    "鳥取県", "島根県", "岡山県", "広島県", "山口県",
    "徳島県", "香川県", "愛媛県", "高知県",
    "福岡県", "佐賀県", "長崎県", "熊本県", "大分県", "宮崎県", "鹿児島県", "沖縄県",
]

AREA_SERVED = [{"@type": "Country", "name": "日本"}] + [
    {"@type": "AdministrativeArea", "name": name} for name in PREF_NAMES
] + [{"@type": "AdministrativeArea", "name": "東京都文京区"}]

SAME_AS = [
    "https://x.com/kurodaschool",
    "https://note.com/kurodajuku",
    "https://kurodajuku.booth.pm/",
    "https://coconala.com/users/6410593",
    "https://np-schools.com/news/29554/",
    "https://smartrador.com/teachers/6039e30a-2e2d-4d77-ab60-97ac663f2b05/",
]

ORG_NODE = {
    "@type": "EducationalOrganization",
    "@id": f"{SITE}/#organization",
    "name": "黒田塾",
    "alternateName": ["Kuroda School", "黒田清友のオンライン個別指導"],
    "url": f"{SITE}/",
    "telephone": "090-8473-2403",
    "address": ADDRESS,
    "geo": GEO,
    "hasMap": HAS_MAP,
    "openingHoursSpecification": [
        {
            "@type": "OpeningHoursSpecification",
            "dayOfWeek": [
                "Monday", "Tuesday", "Wednesday", "Thursday",
                "Friday", "Saturday", "Sunday",
            ],
            "opens": "00:00",
            "closes": "23:59",
            "description": (
                "オンライン相談の受付（Webフォーム・メール・LINE）。"
                "面談と指導は予約制で、拠点は東京都文京区西片2-22-7。"
                "各都道府県に教室はありません。"
            ),
        }
    ],
    "areaServed": AREA_SERVED,
    "founder": {"@id": f"{SITE}/#teacher"},
    "logo": f"{SITE}/favicon.png",
    "image": f"{SITE}/og-card.png",
    "publishingPrinciples": f"{SITE}/about/#editorial-policy",
    "availableLanguage": "ja",
    "knowsLanguage": "ja",
    "sameAs": SAME_AS,
    "contactPoint": {
        "@type": "ContactPoint",
        "contactType": "customer support",
        "telephone": "090-8473-2403",
        "availableLanguage": "ja",
        "areaServed": "JP",
    },
}

PERSON_NODE = {
    "@type": "Person",
    "@id": f"{SITE}/#teacher",
    "name": "黒田清友",
    "jobTitle": "プロ家庭教師・受験コーチ",
    "url": f"{SITE}/about/",
    "image": f"{SITE}/profile.jpg",
    "alumniOf": {"@type": "CollegeOrUniversity", "name": "東京大学"},
    "worksFor": {"@id": f"{SITE}/#organization"},
    "knowsAbout": [
        "東京大学受験", "東大英語", "東大数学", "大学受験", "中学受験",
        "学習計画", "受験コーチング", "英語", "数学", "国語", "社会",
    ],
    "sameAs": SAME_AS + [
        "https://jp.linkedin.com/in/%E6%B8%85%E5%8F%8B-%E9%BB%92%E7%94%B0-405187284",
        "https://mee-coo.com/jp_tutor/science/%E7%90%86%E7%A7%91/jp/10020/teacher_info_profile",
    ],
}

WEBSITE_NODE = {
    "@type": "WebSite",
    "@id": f"{SITE}/#website",
    "name": "黒田塾",
    "alternateName": ["Kuroda School", "黒田清友の個別指導塾", "黒田清友の家庭教師"],
    "url": f"{SITE}/",
    "inLanguage": "ja",
    "publisher": {"@id": f"{SITE}/#organization"},
}


def compact(node) -> str:
    """サイト既存の JSON-LD と同じ区切り文字で1行に整形する。"""
    return json.dumps(node, ensure_ascii=False, separators=(", ", ": "))
