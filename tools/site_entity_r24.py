# -*- coding: utf-8 -*-
"""サイト共通のエンティティ定義（r24 / r25でオンライン専業に更新）。

EducationalOrganization / Person / WebSite のノードを1か所で定義し、
全ページの JSON-LD と地域ページ生成の両方から同じ内容を使う。

r25（2026-11-27）の方針転換:
  黒田塾はオンライン専業・全国47都道府県対応とし、集客ページと構造化データから
  教室としての詳細住所・電話番号・座標・地図URLを外した。特定商取引法に基づく
  表記（/legal/）とプライバシーポリシー（/privacy/）は法令・契約の表示なので
  別管理で、ここからは生成しない。
"""
import json

SITE = "https://kurodaschool.jp"

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

# 日本全国＋47都道府県。オンライン専業のため市区町村単位のareaServedは持たない。
AREA_SERVED = [{"@type": "Country", "name": "日本"}] + [
    {"@type": "AdministrativeArea", "name": name} for name in PREF_NAMES
]

# 料金の正本（site 全体で同じ値だけを使う）。build.py の PRICING と同額。
PLANS = [
    ("面談のみ", 24000, "面談30分・月4セット。学習計画と進捗確認のみ"),
    ("授業のみ（週1回）", 30000, "90分の個別授業を週1回（定期面談なし）"),
    ("面談＋授業（週1回）", 54990, "週1回の30分面談＋90分授業を週1回"),
    ("面談＋授業（週2回）", 79990, "週1回の30分面談＋90分授業を週2回"),
    ("面談＋授業（週3回）", 104990, "週1回の30分面談＋90分授業を週3回"),
]

# 実在を確認した公式URLのみ。note は運用中の2アカウント（黒田／清友黒田）、
# Zenn は 2026-11 に開設した記事アカウント。外部サイトの掲載は「本人の公式
# プロフィール」に限り、第三者の推薦を意味しない（/about/ に注記）。
SAME_AS = [
    "https://x.com/kurodaschool",
    "https://note.com/iris_ruins",
    "https://note.com/large_coyote3612",
    "https://zenn.dev/kurodaschool",
    "https://qiita.com/kiyotomokurodaut-source",
    "https://kurodajuku.booth.pm/",
    "https://coconala.com/users/6410593",
    "https://np-schools.com/news/29554/",
    "https://smartrador.com/teachers/6039e30a-2e2d-4d77-ab60-97ac663f2b05/",
]

# 同名・類似名の塾・法人との識別文（r29）。外部の塾を評価する記述はせず、事実
# （地域・分野・公式ドメイン）と、資本・運営・提携の関係がないことだけを書く。
NAMING_NOTE = (
    "東京大学教育学部卒業の黒田清友が個人で運営する、大学受験・中学受験の"
    "オンライン専業の個別指導塾（公式サイト https://kurodaschool.jp/）。"
    "教室・校舎を持たず、全国47都道府県から受講できる。"
    "次に挙げる同名・類似名の塾や法人とは、資本・運営・提携の関係が一切なく、"
    "黒田清友はこれらの運営者・講師・関係者ではない。"
    "①行政書士向けの相続・離婚実務講座「黒田塾」（kurodajuku.com）、"
    "②茨城県水戸市の小学生から高校生向けの個別指導塾「黒田学習塾」"
    "（kuroda-juku-mito.jp）と「オンライン黒田塾」（kuroda-juku.jp）、"
    "③福岡県福岡市の医療コンサルティング会社「株式会社総合医療コンサルタント黒田塾」"
    "（kuroda.tv、代表は黒田亮太）、"
    "④大阪府大阪市生野区の集団指導塾「黒田進学ゼミ」。"
    "当塾への問い合わせは https://kurodaschool.jp/contact/ のみ。"
)

# 人物についての識別文（同じ「黒田」姓の別の運営者と混同させない）。
PERSON_NAMING_NOTE = (
    "東京大学教育学部卒業の個人指導者・黒田清友。茨城県水戸市の「黒田学習塾」"
    "「オンライン黒田塾」、福岡市の「株式会社総合医療コンサルタント黒田塾」"
    "（代表は黒田亮太）、大阪市の「黒田進学ゼミ」、行政書士向け講座の「黒田塾」"
    "（kurodajuku.com）の運営者・講師・関係者ではない。"
)

ORG_NODE = {
    "@type": "EducationalOrganization",
    "@id": f"{SITE}/#organization",
    "name": "黒田塾",
    "alternateName": [
        "Kuroda School",
        "黒田清友のオンライン個別指導",
        "くろだ塾",
        "黒田清友のオンライン塾",
    ],
    "url": f"{SITE}/",
    "slogan": "代表が一人で、学習計画から答案添削まで担当するオンライン個別指導",
    "description": (
        "東大卒・黒田清友が一人で担当するオンライン専業の個別指導塾。"
        "中学受験・大学受験の指導と学習管理を、全国47都道府県から受講できる。"
    ),
    # 同名の他塾・別法人との混同を避けるための説明（r29で対象を拡充）。
    # 外部の塾を評価する記述ではなく、事実と関係の有無だけを示す。
    "disambiguatingDescription": NAMING_NOTE,
    "knowsAbout": [
        "大学受験", "中学受験", "オンライン個別指導", "学習計画の作成",
        "答案添削", "受験コーチング", "東大受験", "英語", "数学", "国語", "社会",
    ],
    "audience": {
        "@type": "EducationalAudience",
        "educationalRole": "student",
        "audienceType": (
            "中学受験・大学受験を目指す小学生・中学生・高校生・浪人生と、その保護者"
        ),
    },
    "hasOfferCatalog": {
        "@type": "OfferCatalog",
        "name": "継続受講（月額・税込・月4セット）5プラン",
        "itemListElement": [
            {
                "@type": "Offer",
                "name": name,
                "price": price,
                "priceCurrency": "JPY",
                "description": note,
                "url": f"{SITE}/pricing/",
            }
            for name, price, note in PLANS
        ],
    },
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
                "面談と指導はビデオ通話またはテキストで、予約制。"
                "教室・校舎は持たず、全国47都道府県から受講できる。"
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
        "url": f"{SITE}/contact/",
        "availableLanguage": "ja",
        "areaServed": "JP",
    },
}

PERSON_NODE = {
    "@type": "Person",
    "@id": f"{SITE}/#teacher",
    "name": "黒田清友",
    "alternateName": ["Kiyotomo Kuroda", "くろだ きよとも"],
    "jobTitle": "黒田塾 代表",
    "url": f"{SITE}/about/",
    "image": f"{SITE}/profile.jpg",
    "description": (
        "東京大学文科二類に現役合格、東京大学教育学部卒業。"
        "黒田塾の代表として、個別授業・学習計画・答案添削を一人で担当する。"
    ),
    "alumniOf": {"@type": "CollegeOrUniversity", "name": "東京大学教育学部"},
    "disambiguatingDescription": PERSON_NAMING_NOTE,
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
    "description": (
        "中学受験・大学受験のオンライン個別指導「黒田塾」の公式サイト。"
        "料金・学習ガイド・全国47都道府県の案内を掲載している。"
    ),
    "publisher": {"@id": f"{SITE}/#organization"},
    # 検索起点: サイト内にURLで結果を返す検索APIは無いため、SearchAction は付けない。
    # 代わりに、実際に存在する絞り込み・一覧ページを検索の入口として示す。
    "hasPart": [
        {
            "@type": "WebPage",
            "@id": f"{SITE}/study-guides/",
            "name": "学習ガイド（キーワードで絞り込み）",
            "url": f"{SITE}/study-guides/",
        },
        {
            "@type": "WebPage",
            "@id": f"{SITE}/site-map/",
            "name": "サイトマップ（全ページ一覧）",
            "url": f"{SITE}/site-map/",
        },
        {
            "@type": "WebPage",
            "@id": f"{SITE}/faq/",
            "name": "よくある質問",
            "url": f"{SITE}/faq/",
        },
    ],
}


# Safari/Siri・音声検索・AI要約向けに、各ページのh1と要点ボックスを読み上げ対象にする。
# 要点ボックスが無いページでは h1 だけが対象になる（cssSelector は一致する要素だけを指す）。
SPEAKABLE = {
    "@type": "SpeakableSpecification",
    "cssSelector": ["h1", ".summary-box"],
}


def compact(node) -> str:
    """サイト既存の JSON-LD と同じ区切り文字で1行に整形する。"""
    return json.dumps(node, ensure_ascii=False, separators=(", ", ": "))
