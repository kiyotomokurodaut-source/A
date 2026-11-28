# 黒田塾 深掘りSEO/AIO診断（第11弾・新観点）

- 実行日: 2026-11-28 / 計測: Before（第11弾・同一観点）
- 対象: インデックス対象 261ページ（総HTML 262）
- 観点: 62（既存82観点とは重複しない新観点。PASS 41 / WARN 14 / FAIL 7）

## カテゴリ別

| カテゴリ | PASS | WARN | FAIL |
| --- | --- | --- | --- |
| Delivery | 3 | 4 | 4 |
| Crawl | 9 | 0 | 1 |
| On-Page | 5 | 6 | 0 |
| Schema | 7 | 2 | 1 |
| AIO | 6 | 1 | 1 |
| CRO | 5 | 1 | 0 |
| Quality | 6 | 0 | 0 |

## P0 — FAIL（検索・AI検索への流入に直結）（7件）

- **#101 [Delivery] サードパーティ（GTM）への preconnect / dns-prefetch** — 未設定 261/261ページ（外部ホスト: www.googletagmanager.com）（例: /about/／/area/／/cases/）
- **#102 [Delivery] LCP画像の preload（トップのヒーロー画像）** — preload なし（LCP候補: /images/kuroda-hero.webp）
- **#1051 [Delivery] 未使用スタイルシートを読み込まない（安全に外せるもの）** — 未使用CSSのあるページ 252/262（r17-components-3ce7c136239f.css×252ページ, growth-r20-669164207105.css×1ページ）（例: r17-components-3ce7c136239f.css: 252ページ／growth-r20-669164207105.css: 1ページ）
- **#107 [Delivery] 参照アセット全てに Cache-Control 規則** — 規則なし 4件（例: /assets/analytics-r28-11bca319c6aa.js／/assets/learning-check-r21-5b3007429422.js／/assets/r17-components-57293ff87914.js）
- **#115 [Crawl] 更新日の三重一致（last-modified・sitemap・dateModified）** — 不一致 2件（例: / (JSON-LD ['2026-11-28'] / meta 2026-11-27)／/materials/ (JSON-LD ['2026-11-28'] / meta 2026-11-27)）
- **#131 [Schema] パンくずの JSON-LD が画面の名称・URLと一致** — 不一致 154件（例: /contact/ (無料相談・お問い合わせ / 無料受験戦略診断)／/juku/ (個別指導塾 / 個別指導塾の選び方【大学受験】料金・講師・添削の比べ方｜黒田塾)／/specialty/aichi/ (専門対策 / 大学受験の専門対策)）
- **#147 [AIO] .md・facts.json・llms-full.txt の Content-Type 明示** — 未設定 3件（例: /*.md／/facts.json／/llms-full.txt）

## P1 — WARN（改善余地）（14件）

- **#103 [Delivery] 大きい画像の srcset（モバイルへの過大配信を避ける）** — srcset なし 6件（例: /about/ (/profile-600.webp 600px)／/contact/ (/assets/consultation-strategy-kit-preview.webp 900px)／/ (/images/kuroda-hero.webp 800px)）
- **#104 [Delivery] 1ページの参照CSS合計 ≤ 70KB** — 超過 1件（中央値 63KB）（例: /contact/ (70KB)）
- **#106 [Delivery] インラインJS（JSON-LD以外）≤ 1KB/ページ** — 超過 1件（例: /shindan/ (26150 bytes)）
- **#110 [Delivery] モバイルでの初期表示の総重量 ≤ 220KB（srcsetの最小版で見積り）** — 超過 5件（最大 238KB / /、中央値 110KB）（例: /english-support/ (224KB)／/for-parents/ (233KB)／/ (238KB)）
- **#121 [On-Page] title の表示幅 ≤ 66（SERPで切れない）** — 66超 15件（最大 78）（例: /study-guides/english-reading-diagnosis/ (78) 英語長文が読めない原因3つ｜単語は分かるのに止まる人の診断法（例題6／/study-guides/parents-mock-exam-bad-result/ (75) 模試の結果が悪かったら？ 保護者がやるべきこと・やってはいけないこと／/study-guides/juku-yametai/ (75) 「塾をやめたい」と思ったときの判断｜大学受験で辞める前に確認する5点）
- **#122 [On-Page] description ≤ 120字（読み切れる長さ）** — 120字超 8件（最大 130字）（例: /study-guides/materials-catalog/ (130字)／/study-guides/parents-mock-exam-bad-result/ (127字)／/study-guides/chugaku-juken-12gatsu-shutsugan/ (127字)）
- **#123 [On-Page] H1 が title の主題語（3文字n-gram）を含む** — 不一致 5件（例: /area/ (対応エリア / 教室はありません。全国47都道府)／/for-parents/ (保護者の方へ / 授業を増やす前に、今の困りごとと)／/learning-check/ (無料学習チェック / 学習のつまずきを、3つの質問で整)）
- **#124 [On-Page] 1ページ内で H2 が重複しない** — 重複 1件（例: /study-guides/gap-year-study-plan/: 浪人生の1週間は、どう組み立てればよいですか？）
- **#125 [On-Page] 学習ガイド本文 3,000字以上** — 不足 2/86（例: /study-guides/gap-year-study-plan/ (2922字)／/study-guides/todai-listening/ (2950字)）
- **#1271 [On-Page] 公的・学術の一次情報を引くガイドが10本以上** — 公式参照あり 4/86本（例: /study-guides/kyotsu-english-time/／/study-guides/todai-english-summary/／/study-guides/todai-english-time-allocation/）
- **#135 [Schema] FAQ回答が30字以上（AIが引用できる完結した文）** — 30字未満 40件（40字未満は 77件）（例: /shindan/ (29字) 診断に費用や登録は必要ですか？／/specialty/chiba-ken/ (26字) 県南部からでも受講できますか？／/specialty/edogawabashi/ (20字) オンラインだけでも受講できますか）
- **#137 [Schema] Service に serviceType / provider / areaServed** — 156件中 不足 156件（例: /area/ (欠: serviceType)／/juku/ (欠: serviceType)／/junior-high-exam/ (欠: serviceType)）
- **#142 [AIO] llms-full.txt が全ページのURLを網羅** — 未収録 15/261（例: /area/／/cases/／/english-support/）
- **#152 [CRO] 入力欄のフォント16px以上（iOSの自動ズーム防止）** — 16px未満の指定 3件（入力欄のあるページ 18）（例: .95／.87／.8）

## 全項目

| # | 分類 | 観点 | 判定 | 詳細 |
| --- | --- | --- | --- | --- |
| 101 | Delivery | サードパーティ（GTM）への preconnect / dns-prefetch | FAIL | 未設定 261/261ページ（外部ホスト: www.googletagmanager.com） |
| 102 | Delivery | LCP画像の preload（トップのヒーロー画像） | FAIL | preload なし（LCP候補: /images/kuroda-hero.webp） |
| 103 | Delivery | 大きい画像の srcset（モバイルへの過大配信を避ける） | WARN | srcset なし 6件 |
| 104 | Delivery | 1ページの参照CSS合計 ≤ 70KB | WARN | 超過 1件（中央値 63KB） |
| 1051 | Delivery | 未使用スタイルシートを読み込まない（安全に外せるもの） | FAIL | 未使用CSSのあるページ 252/262（r17-components-3ce7c136239f.css×252ページ, growth-r20-669164207105.css×1ページ） |
| 105 | Delivery | インラインCSS ≤ 6KB/ページ | PASS | 超過 0件 |
| 106 | Delivery | インラインJS（JSON-LD以外）≤ 1KB/ページ | WARN | 超過 1件 |
| 107 | Delivery | 参照アセット全てに Cache-Control 規則 | FAIL | 規則なし 4件 |
| 108 | Delivery | ハッシュ付きCSS/JSは immutable キャッシュ | PASS | immutable でない 0件 |
| 109 | Delivery | レンダリングを止める外部JSがない（defer/async） | PASS | ブロッキング 0件 |
| 110 | Delivery | モバイルでの初期表示の総重量 ≤ 220KB（srcsetの最小版で見積り） | WARN | 超過 5件（最大 238KB / /、中央値 110KB） |
| 111 | Crawl | トップから3クリック以内に全ページ | PASS | 4クリック以上 0件 / 到達不能 0件 （最大深度 3） |
| 112 | Crawl | ページ内アンカー（#id）の到達性 | PASS | 行き先なし 0件 |
| 113 | Crawl | canonical = og:url（厳密一致） | PASS | 不一致 0件 |
| 114 | Crawl | canonical が sitemap.xml の loc と一致 | PASS | 不一致 0件 |
| 115 | Crawl | 更新日の三重一致（last-modified・sitemap・dateModified） | FAIL | 不一致 2件 |
| 116 | Crawl | sitemap の lastmod が ISO 形式・未来日なし | PASS | 不備 0件 |
| 117 | Crawl | target=_blank の外部リンクに rel=noopener | PASS | noopener なし 0件 |
| 118 | Crawl | 公的・学術ドメイン（go.jp/ac.jp）への一次情報参照 | PASS | 3ドメイン: www.dnc.ac.jp, www.s.u-tokyo.ac.jp, www.u-tokyo.ac.jp |
| 119 | Crawl | 404ページの noindex と回遊リンク（20本以上） | PASS | noindex=あり / 内部リンク 54本 |
| 120 | Crawl | 本文（main）内からの被リンク2本以上（ナビ・フッター依存の解消） | PASS | 2本未満 0/261 |
| 121 | On-Page | title の表示幅 ≤ 66（SERPで切れない） | WARN | 66超 15件（最大 78） |
| 122 | On-Page | description ≤ 120字（読み切れる長さ） | WARN | 120字超 8件（最大 130字） |
| 123 | On-Page | H1 が title の主題語（3文字n-gram）を含む | WARN | 不一致 5件 |
| 124 | On-Page | 1ページ内で H2 が重複しない | WARN | 重複 1件 |
| 125 | On-Page | 学習ガイド本文 3,000字以上 | WARN | 不足 2/86 |
| 126 | On-Page | ガイドに執筆者・公開日・更新日が画面上で読める（E-E-A-T） | PASS | 不足 0/86 |
| 127 | On-Page | ガイドに外部の出典リンクがある | PASS | 出典なし 0/86本 |
| 1271 | On-Page | 公的・学術の一次情報を引くガイドが10本以上 | WARN | 公式参照あり 4/86本 |
| 128 | On-Page | 主要ページの説明文に具体数値（料金・分数・回数） | PASS | 数値なし 0/12 |
| 129 | On-Page | 本文の H2 が5つ以上（構造化された本文） | PASS | 5未満 0件 |
| 130 | On-Page | 400字超の長段落が3つ以下（読みやすさ） | PASS | 超過 0件 |
| 131 | Schema | パンくずの JSON-LD が画面の名称・URLと一致 | FAIL | 不一致 154件 |
| 132 | Schema | JSON-LD の @id 参照が同一ページ内で解決する | PASS | 未解決 0件 |
| 133 | Schema | JSON-LD の @id が重複しない | PASS | 重複 0件 |
| 134 | Schema | FAQPage の質問が画面上にも表示されている | PASS | 非表示 0件 |
| 135 | Schema | FAQ回答が30字以上（AIが引用できる完結した文） | WARN | 30字未満 40件（40字未満は 77件） |
| 136 | Schema | Article の必須6プロパティ | PASS | 91記事中 不足 0件 |
| 137 | Schema | Service に serviceType / provider / areaServed | WARN | 156件中 不足 156件 |
| 138 | Schema | Course の offers に price / priceCurrency | PASS | 14件中 不足 0件 |
| 139 | Schema | 構造化データの料金が料金ページの本文と一致 | PASS | Offer価格 5種 / 本文にない額 0件 |
| 140 | Schema | 全JSON-LDがパースでき @context を持つ | PASS | @context欠 0件 / パース不能 0件 |
| 141 | AIO | llms.txt の各リンク行に説明文 | PASS | 260行中 説明なし 0件 |
| 142 | AIO | llms-full.txt が全ページのURLを網羅 | WARN | 未収録 15/261 |
| 143 | AIO | facts.json のQ&A 出典URLが実在ページ | PASS | 11問中 不達 0件 |
| 144 | AIO | facts.json の料金が料金ページと一致 | PASS | facts 5件 / 料金ページにない額 0件 |
| 145 | AIO | 全ページの .md があり見出し数が一致（±2） | PASS | 不備 0件 |
| 146 | AIO | .md に title / description / updated のフロントマター | PASS | 不足 0件 |
| 147 | AIO | .md・facts.json・llms-full.txt の Content-Type 明示 | FAIL | 未設定 3件 |
| 148 | AIO | Markdown版のカバレッジ（全インデックス対象ページ） | PASS | 261/261ページ |
| 149 | CRO | viewport でピンチズームを禁止していない | PASS | 禁止 0件 |
| 150 | CRO | スマホ追従バーと本文の重なりを回避（bodyの下余白） | PASS | body padding-bottom あり |
| 151 | CRO | 主要CTAのタップ領域44px以上（CSS） | PASS | min-height 44px以上の宣言 51件 |
| 152 | CRO | 入力欄のフォント16px以上（iOSの自動ズーム防止） | WARN | 16px未満の指定 3件（入力欄のあるページ 18） |
| 153 | CRO | ヘッダーの主要ナビが7項目以下 | PASS | 7項目超 0件 |
| 154 | CRO | 主要ページのファーストビュー内にCTA | PASS | 4,000文字以降 0件 |
| 155 | Quality | 隠しテキスト・キーワード詰め込みがない | PASS | 疑い 0件 |
| 156 | Quality | HTMLコメントに検索/AI向けの指示がない | PASS | 疑い 0件 |
| 157 | Quality | 画像 alt が内容を説明している | PASS | 不備 0件 |
| 158 | Quality | 表に th 見出しがある（読み上げ・構造理解） | PASS | th なし 0件 |
| 159 | Quality | 広告・アフィリエイトリンクに rel=sponsored | PASS | rel なし 0件 |
| 160 | Quality | 主要タグの開閉が揃っている | PASS | 不備 0件 |

