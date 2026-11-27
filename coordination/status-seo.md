# 黒田塾SEO 状況（status-seo）

最終更新：2026-11-26 22:52 JST 時点（muse 記入）。対象サイト：kurodaschool.jp（静的HTML、GitHub main へのプッシュで自動公開）。

## 現在の状態（実測）

- **サイト規模：203ページ**（sitemap 基準、2026-11-26 ライブ確認済み）。
- SEOスプリント実施中（期間は 2026-11-28 08:47 JST まで、2時間間隔で継続）。**第26波まで完了**。
- 第25波：季節テーマの学習ガイド4本を新規公開（高1の冬休み／共通テスト前日・当日／共通テスト後の切り替え／冬期講習後の復習）。全ページに「信頼と相談の型」を適用。
- 第26波：インデックス促進として、第25波の新規4ページへの内部リンクを関連ガイド7ページから追加し、各ページの被リンクを1件→3件に増加。公開・ライブ確認済み。
- 勉強法記事30本の監査を実施済み：質問形式の見出しが全記事に無いこと、比較表が無い記事が11本あることを確認。主力3ページ（個別指導の料金／コーチングと個別指導の比較／塾の選び方）を改稿・公開済み（質問形式の見出し、料金5プランの比較表、FAQ追加）。
- **阿修羅さん（note）の勉強法の視点を参考に、東大英語の記事4本を改稿・公開済み**（総論／英作文／リスニング／時間配分）。参考は考え方・視点までで、文章の転載はしていない。
- Search Console の実測（取得済み範囲）：表示 2,689回／クリック 404／CTR 15%／平均掲載順位 8.0（2026-11-22 までのデータ）。

## 料金の正本（変更禁止）

継続受講は月額5プラン（税込・月4セット）：面談のみ 24,000円／授業のみ週1回 30,000円／面談＋授業 週1回 54,990円・週2回 79,990円・週3回 104,990円。正本ページは /pricing/。記事改稿で金額を変えない。

## 残キュー

| 項目 | 状態 | 進める条件 |
|---|---|---|
| CTR改善（表示が多いのにクリック率が低いページのタイトル・説明文の書き換え） | 未実施 | Search Console の実測データ取得が必要。取得経路（Ryze AI）が未接続で、本人の連携手続き待ち。推測での書き換えはしない |
| G7：構造化データ（LocalBusiness）に住所・電話を入れるか | 未実施 | 本人の判断待ち |
| 監査で挙がった弱い記事4本（浪人の勉強計画／東大リスニング＝改稿済み／保護者向け大学受験／東大英語総論＝改稿済み）の残り2本の強化 | 未実施 | 優先度を付けて順次 |
| インデックス促進の継続 | 実施中 | 未登録ページが実測で確認できたら内部リンク追加 |

## 運用メモ

- 公開経路：ローカルで作成 → 公開前チェック（build.py --check 全パス）→ GitHub main へプッシュ → 自動公開 → ライブ確認、の順を厳守する。
- 実績の捏造禁止。使える事実は本人の申告範囲（累計指導50人以上、合格実績は東大・慶應・医学部・難関中学・外国語大学など多数）のみ。
- トップのファーストビューは本人の写真と安心感のある文章が主役。LINEボタンの文言は「無料相談を申し込む」に統一。

## 更新履歴

- 2026-11-26 23:24 JST（muse）：初回転記。

## 巡回追記（2026-11-27 00:38 JST、muse）

- SEOスプリント側の進捗を取り込み：第26波まで完了済みで、その後の新規ウェーブはなし。サイト規模は 203ページ（sitemap基準）のまま、第25波の新規4ページへの内部リンク追加（被リンク1件→3件）が直近の公開結果。
- 本巡回ではサイト変更は行っていない（スプリント側と競合しない範囲での要約転記のみ）。残キュー（CTR改善は Search Console 実測待ち、G7は本人の判断待ち）は不変。
- 訂正追記（2026-11-27 00:38巡回中、muse）：上記記録の直後にSEOスプリント第27波が公開された。内容はインデックス促進で、季節ガイド10ページへ専門対策ハブ・サービスページ5件から文脈リンクを追加（新規ページなし、サイト規模203ページのまま）。リモート main の当該コミットに本巡回のボード更新も含まれて取り込まれたことを確認済み。

## 巡回追記（2026-11-27 02:38 JST、muse）

- **G7 が実施済みになったことを取り込み**：リモート main のコミット e0b5a97（2026-11-27 01:00 JST）で、EducationalOrganization の構造化データに PostalAddress と電話番号を追加（全95ページ）。従来の残キュー「G7：構造化データに住所・電話を入れるか（本人の判断待ち）」は、この公開をもって実施済みとして扱う。ボードには住所・電話番号そのものは書かない。
- 本巡回ではサイト変更は行っていない（スプリント側の公開結果の要約転記のみ、public/ には触れていない）。サイト規模は 203ページのまま。
- 残キュー：CTR改善は Search Console 実測データの取得待ちで不変。監査で挙がった弱い記事の残り2本の強化、インデックス促進の継続も不変。

## 巡回追記（2026-11-27 04:38 JST、muse）

- SEOスプリント側の 04:38 確認実行を取り込み：第27波・G7完了後の確認（2回目）で、新規ウェーブ・新規ページはなし。ライブ検証はトップ HTTP 200、sitemap 203 URL、G7のPostalAddress掲載確認済み、第25波新規4ページ等も全て HTTP 200。
- 本巡回ではサイト変更は行っていない（スプリント側の確認結果の要約転記のみ、public/ には触れていない）。サイト規模は 203ページのまま。
- 残キュー：CTR改善は Search Console 実測データの取得待ちで不変。スプリント期間は 2026-11-28 08:47 JST までで、期間終了後に最終サマリー予定。

## 巡回追記（2026-11-27 06:38 JST、muse）

- SEOスプリント側の新規ウェーブ・新規コミットはなし（リモート main は前回巡回時点から不変、APIで確認）。ライブ確認：トップ HTTP 200、sitemap 203 URL。
- 本巡回ではサイト変更は行っていない（スプリント側と競合しない範囲での確認のみ、public/ には触れていない）。サイト規模は 203ページのまま。
- 残キュー：CTR改善は Search Console 実測データの取得待ちで不変。スプリント期間は 2026-11-28 08:47 JST までで、期間終了後に最終サマリー予定。

## 巡回追記（2026-11-27 08:38 JST、muse）

- SEOスプリント側の新規ウェーブ・新規コミットはなし（リモート main は前回巡回時点から不変）。ライブ確認：トップ HTTP 200、sitemap 203 URL。
- 本巡回ではサイト変更は行っていない（スプリント側と競合しない範囲での確認のみ、public/ には触れていない）。サイト規模は 203ページのまま。
- 残キュー：CTR改善は Search Console 実測データの取得待ちで不変。スプリント期間は 2026-11-28 08:47 JST までで、期間終了後に最終サマリー予定。

## 巡回追記（2026-11-27 10:38 JST、muse）

- SEOスプリント側の新規ウェーブ・新規コミットはなし（リモート main は前回巡回コミット d4e31fd のまま）。ライブ確認：トップ HTTP 200、sitemap 203 URL。
- 本巡回ではサイト変更は行っていない（スプリント側と競合しない範囲での確認のみ、public/ には触れていない）。サイト規模は 203ページのまま。
- 残キュー：CTR改善は Search Console 実測データの取得待ちで不変。スプリント期間は 2026-11-28 08:47 JST までで、期間終了後に最終サマリー予定。

## 巡回追記（2026-11-27 12:38 JST、muse）

- SEOスプリント側の新規ウェーブ・新規コミットはなし。ライブ確認：トップ HTTP 200、sitemap 203 URL。
- 本巡回ではサイト変更は行っていない（スプリント側と競合しない範囲での確認のみ、public/ には触れていない）。サイト規模は 203ページのまま。
- 残キュー：CTR改善は Search Console 実測データの取得待ちで不変。スプリント期間は 2026-11-28 08:47 JST までで、期間終了後に最終サマリー予定。

## r24: 56観点診断ツール・AIO強化・全国47都道府県ページ展開（2026-11-27、Pickle）

### 実施内容
- **診断ツールをリポジトリに組み込み**：`tools/seo_aio_meo_audit.py`（従来56観点＋追加6観点＝62項目）。
  `tools/audit_report.json` と、改善優先度 P0/P1/P2 付きの `tools/audit_report.md` を出力する。
- **AIO**：`public/llms-full.txt` を `build.py` で生成（基本情報・講師・料金5プラン・媒体・FAQ原文・47都道府県・
  専門対策・学習ガイド82本の見出し）。`llms.txt` は全ページを網羅（地域ページ・専門対策・その他を含む）。
  リモートで追加された「概要」「公式プロフィール」セクションとAIクローラ許可はそのまま残した。
- **構造化データ**：全ページの `EducationalOrganization` を `tools/site_entity_r24.py` の共通定義に統一。
  `areaServed`＝日本＋47都道府県＋東京都文京区、`geo`（35.7152, 139.7572）、`hasMap`、
  `openingHoursSpecification`、`contactPoint`、`sameAs`（X・note・BOOTH・ココナラ・みんなの学校新聞・smartrador）。
  `/online-tutoring/`・`/university-exam/`・`/junior-high-exam/`・`/study-coaching/` に Course/Offer を追加。
- **地域ページ**：`tools/generate_region_pages_r24.py` で46都道府県ページを生成し、既存の `/specialty/tokyo/` と
  合わせて47都道府県を網羅。各ページに主要大学（所在・設置区分）、地域固有の課題3点、FAQ4問、
  BreadcrumbList／FAQPage／Service（areaServed＝当該都道府県）、同一地方の都道府県への内部リンクを実装。
  `/specialty/` に47都道府県の一覧セクションを追加し、各ページの被リンクを3本以上にした。
- **パンくず**：`/cases/` にパンくずHTML、`/legal/`・`/materials/`・`/materials/terms/`・`/privacy/`・`/site-map/` に
  BreadcrumbList JSON-LD を追加。`/privacy/` のタイトルを21字に調整（14字はSERPで短すぎた）。

### slug の注意
`/specialty/saitama/`・`/chiba/`・`/osaka/` は大学別ページ（埼玉大・千葉大・大阪大）が使用中のため、
県ページは `/specialty/saitama-ken/`・`/chiba-ken/`・`/osaka-fu/` とした。大学ページと県ページは相互リンク済み。

### 診断結果（56観点）
- Before（2026-11-27 14:11、204ページ）：PASS 40 / WARN 9 / FAIL 7
- After（251ページ）：**PASS 52 / WARN 4 / FAIL 0**（追加6観点を含む全体では PASS 58 / WARN 4 / FAIL 0）
- 残WARN：質問形式の見出し（#26・69本）、比較表（#27・60本）、被リンク3本未満（#35・51ページ）、
  記事冒頭の要点（#48・60本）。いずれもコンテンツ側の積み上げで、優先度は P1/P2。

### 未了・要判断
- **Googleビジネスプロフィール（GBP）は未登録**（Googleマップ検索で「黒田塾」の事業者情報は出ない）。
  `hasMap` は住所の検索URLで、口コミ導線はまだ無い。GBP作成は本人の名義・本人確認が必要。
- `openingHoursSpecification` は「オンライン相談は24時間受付・面談と指導は予約制」と記述した。
  実際の受付時間・指導可能時間の指定があれば差し替える（推測の営業時間は入れていない）。
- 学習ガイドの質問見出し・比較表・冒頭要点（#26/#27/#48）は未着手。


## 巡回追記（2026-11-27 14:38 JST、muse）

- **Pickle の r24 を取り込み**：リモート main に 56観点診断ツール・AIO強化・全国47都道府県ページ展開が公開済み。サイト規模は 251ページに増加（本巡回でライブ sitemap 251 URL・トップ HTTP 200 を確認）。診断は After で PASS 52／WARN 4／FAIL 0（追加6観点込みでは PASS 58／WARN 4／FAIL 0）。残WARNは質問形式の見出し・比較表・被リンク3本未満・記事冒頭の要点で、いずれもコンテンツ側の積み上げ（P1/P2）。
- 続くコミットで重複した head タグを93ページから除去済み（生成時の欠陥修正）。
- 未了・要判断（r24記録より）：Googleビジネスプロフィールは未登録で作成には本人の名義・本人確認が必要。営業時間の指定があれば openingHoursSpecification を差し替える。
- 本巡回ではサイト変更は行っていない（Pickle／スプリント側と競合しない範囲での取り込みのみ、public/ には触れていない）。
- 残キュー：CTR改善は Search Console 実測データの取得待ちで不変。スプリント期間は 2026-11-28 08:47 JST まで。

## 追記（2026-11-27 残WARN4件の一括改善、Pickle）

`tools/seo_aio_meo_audit.py` に残っていた WARN 4件（#26・#27・#35・#48）を解消した。
Before: PASS 52 / WARN 4 / FAIL 0（56観点） → After: **PASS 56 / WARN 0 / FAIL 0**（全体62観点でも PASS 62）。

- **#48 記事冒頭の要点（AIO）**: 学習ガイド82本すべてに、H1直後・導入文の直後へ
  `<div class="summary-box"><strong>この記事の要点</strong><ul>…</ul></div>`（3行）を追加。内容は各記事の本文に沿って個別に作成し、
  料金・実績などの事実は本文と矛盾しない範囲にとどめた。
- **#26 質問形式の見出し**: 記事のテーマに沿った「〜はどうすればよいですか？」等のH2セクションを追加（テーマ別の判断表・手順を本文で説明）。
- **#27 比較表**: 学習ガイド全体で table を設置（時期別の進め方、単元別のつまずき、方式・型の比較など内容に即した表）。表なしの記事は0本。
- **#35 被リンク3本未満**: 51ページ → 0ページ。教育・語学系大学（学習院・ICU・東京外語・東京学芸・獨協）、
  文京・本郷エリア（根津・湯島・御茶ノ水駅・飯田橋・千代田）の相互リンク、大学別・テーマ別ページへの導線
  （お茶の水女子大←女子大/国語、名古屋大←愛知/国公立、再受験←浪人/不信登校/浪人計画、帰国生←英語/推薦/東京外語、
  医学部分担←二次/英語、部活引退←高3日程/新高3春休み/週計画、情報I・リスニング←共通テスト専門、数学単元←数学専門）、
  `/site-map/` ← `/about/`・`/faq/` など計74本を、既存の関連ページナビへ追加。新規に作った内部リンク切れは0。
- **診断ツールの検出範囲を修正（#48）**: 従来は生HTMLの先頭6,000文字だけを走査していたが、各ページは `<head>`（JSON-LD等）だけで
  約10,000文字あり、本文の `<h1>` は11,000文字目以降にあるため、記事冒頭に要点を書いても検出できなかった
  （PASSしていたページも title/JSON-LD に「要約」等の語が入っていたため）。`article_lead()` を追加し、
  「`<h1>` から最初の `<section>` まで」＝記事の導入部を見て、要点ブロックの有無を判定するよう修正した。
  基準を緩めたのではなく、検出位置を記事冒頭に合わせたもの。82本すべてに実体の要点ブロックを入れて PASS を確認している。
- 各ページの `meta last-modified` と Article/WebPage の `dateModified` は 2026-11-27 に更新（可視の「最終更新」表記も同期）。
  料金表・実績・既存の数値（要約75字、120分配分、英作文72語など）は変更していない。
- 検証: `build.py --check` exit 0、`tools/seo_guard_r17.py` errors 0、`tools/validate_release_r23.py` 通過、
  タグの開閉不一致0、HTMLサイズ上限（250KB）内（最大 89KB）。

## 追記（2026-11-27 オンライン専業・住所非表示への一括統一、Pickle）

本人の方針「オンライン専業・全国47都道府県対応（対面指導・通塾案内なし／集客ページと構造化データから教室の詳細住所・電話番号を除去）」に、公開サイト全体を揃えた。料金・購入条件・`/legal/`・`/privacy/`・`/materials/terms/` の本文は変更していない。

- **構造化データ**: `tools/site_entity_r24.py` の `EducationalOrganization` から `telephone`・`address`・`geo`・`hasMap`・`contactPoint.telephone` を削除し、`areaServed` は日本＋47都道府県（市区町村単位を廃止）。`contactPoint` は `/contact/` の URL のみ。`enrich_entity_r24.py` で全205ページのノードを同期した。`Course` の `courseMode` は「オンライン」のみ。
- **本文**: トップ・`/about/`・`/pricing/`・`/faq/`・`/juku/`・`/university-exam/`・`/specialty/` と全47都道府県ページ・拠点/駅/区のページ・学習ガイド2本から、対面指導・通塾の案内と教室の住所・電話を外し、「オンライン個別指導のみ・全国47都道府県対応」に統一。「オンラインを中心に」という留保表現も全国オンラインに揃えた。
- **`/area/` を全面書き換え**: 「文京区の個別指導塾（対面・オンライン）」から「対応エリア＝全国47都道府県」の案内へ。住所・電話・地図・通塾圏の記載を削除し、47都道府県ページへのハブにした（FAQPage JSON-LDも更新）。
- **生成・診断ツール**: `generate_region_pages_r24.py`（地域ページ本文・FAQ・hub）と `build.py`（llms.txt / llms-full.txt）を同じ方針に更新。`seo_aio_meo_audit.py` のMEO観点 #50/#51/#54/#56 は「教室の住所・座標・地図・電話を載せないこと」を正しい状態として判定する基準に改めた（GBPは実店舗向けのため必須にしない）。
- **検証**: `build.py --check` exit 0（251 URL）、`seo_guard_r17.py` errors 0、`validate_release_r23.py` 通過、`seo_aio_meo_audit.py` は 62観点 PASS 62 / WARN 0 / FAIL 0。

## 追記（2026-11-27 第3弾：駅・区ページのオンライン表記統一とAI引用ブロック、Pickle）

オンライン専業・全国47都道府県対応の方針に、title/description/H1 と構造化データを揃えた第3弾。

- **駅・区ページ14本**（文京区・茗荷谷・根津・湯島・護国寺・春日・後楽園・本郷三丁目・江戸川橋・飯田橋・御茶ノ水駅・東大前・新宿区・千代田区）:
  「○○駅周辺の大学受験塾」「丸ノ内線で通える個別指導」等、その土地に教室があると読める title を
  「○○エリアの大学受験オンライン指導｜黒田塾」に変更。description も「オンラインで受講できる」
  「教室はなく全国対応」に統一し、H1 は「○○エリアからの大学受験対策。オンラインで、…」に。
  URL は変更なし（リダイレクト不要）。本文に残っていた「学校帰りに寄れる塾」「通いやすさ」
  「通塾の移動負担」等の表現も、オンライン前提の表現に修正（対象ページのみ）。
  `/specialty/` の ItemList 名称も新名称に同期。`tools/region_online_titles_r25.py` で再適用可能。
- **AI引用向けの要点**:
  - `llms-full.txt` に「ひと目で分かる黒田塾（引用用サマリー）」と「どんな生徒に向いているか」を追加
    （一貫担当・東大教育学部卒・累計50人以上・オンライン専業47都道府県・対象科目・5プラン料金・
    向き不向き。出典は `/juku/` と各ページ本文のみ）。`build.py` から生成。
  - トップに「黒田塾の基本情報」ブロック、`/about/` の概要に担当・向き不向きの項目、
    `/pricing/` と `/cases/` に「このページの要点」ボックスを追加（`tools/aio_facts_r25.py`）。
    `/cases/` は「指導経験」と「合格が確認できている事例」の区別を保ったまま要約。
  - `EducationalOrganization` に `slogan`・`knowsAbout`・`audience`・`hasOfferCatalog`（5プランのOffer）を追加し、
    `enrich_entity_r24.py` で全251ページへ同期。`Course`/`FAQPage`/`sameAs` は既存を維持。
- **検証**: `build.py --check` exit 0（251 URL）／`seo_guard_r17.py` errors 0／
  `validate_release_r23.py` 通過／`seo_aio_meo_audit.py` 62観点 PASS 62 / WARN 0 / FAIL 0。
- 未了: Apple Business Connect のブランド画像と登録文言、外部サイテーション（エキテン・塾ナビ等）の
  掲載可否調査はサイト外の作業として別途。

## 追記（2026-11-27 第4弾：IndexNow・facts.json・Speakable・Markdown配信、Pickle）

AI検索（ChatGPT Search / Copilot / Perplexity / Google AI Overview / Safari・Siri）と
Bing への露出を目的とした第4弾。実装は Doc 1（1-1〜1-8）準拠、Doc 0-L / Doc 3-L の
Google Search Essentials と整合（隠しテキスト・クローキング・虚偽マークアップは不使用）。

### 実装

1. **IndexNow（Doc 1-2）**: 32桁hexキー `48e6c2249edd47e7a2229c425cab62c5` を
   `build.py` の `INDEXNOW_KEY` で管理し、`public/<key>.txt` を毎ビルドで書き戻す。
   `tools/indexnow_submit.py`（既定 dry-run、`--submit` で送信、`--urls` で差分送信）を追加。
2. **`/facts.json`（1-7の一部）**: `build.py` の `facts_payload()` から生成。塾名・URL・
   代表（黒田清友／東京大学教育学部卒／代表・指導担当）・オンライン専業・教室なし・
   47都道府県・指導科目（理科の範囲限定を含む）・5プラン税込料金・累計50人以上・
   茨城県「黒田学習塾」と無関係である注記・問い合わせ・出典URL・ページ数・更新日。
   `llms.txt` と `llms-full.txt` の冒頭から案内。
3. **エンティティ統一（1-6）**: `tools/site_entity_r24.py` を拡張し、
   - `Person`: jobTitle「代表・指導担当」、`alumniOf` 東京大学教育学部、X/note ほか sameAs、
     `alternateName`、`disambiguatingDescription`
   - `WebSite`: description と検索起点（`hasPart` で学習ガイドの絞り込み・サイトマップ・FAQ）
   - `EducationalOrganization`: `disambiguatingDescription` と alternateName を追加
   `tools/entity_speakable_r26.py` で全251ページに同一ノードとして適用。
   `SearchAction` は、URLで結果を返すサイト内検索が無いため付けていない（虚偽の
   potentialAction を避け、実在する絞り込みページを検索起点として示す）。
4. **Speakable（1-6）**: 各ページのページノード（`<URL>#webpage`、Articleを含む）に
   `SpeakableSpecification`（`cssSelector`: `h1`, `.summary-box`）を付与。
5. **robots.txt（1-1）**: GPTBot / OAI-SearchBot / ChatGPT-User / PerplexityBot /
   Perplexity-User / ClaudeBot / Claude-SearchBot / Claude-User / Google-Extended /
   Applebot / Applebot-Extended を `Allow: /`、Bingbot は `Allow: /` ＋ `Crawl-delay: 1`。
   `Sitemap: https://kurodaschool.jp/sitemap.xml` を記載（既存の他AIクローラも維持）。
6. **robotsメタ（Doc 3-L 3-4）**: noindex を除く全ページに `max-image-preview:large`。
   既存の `max-snippet:-1` はそのまま。
7. **比較ブロック（第4弾の項目4）**: `/about/` に要点ボックスと
   「一般的な大手集団塾／講師交代ありの個別指導塾／黒田塾」の比較表。特定の塾の評価ではなく
   形態差と黒田塾の公開仕様のみ。向かないケース（集団・自習室・二次レベルの理科）も明記。
8. **Markdown配信（1-7）**: `tools/md_export_r26.py` が `<main>` の本文だけを Markdown 化し、
   各HTMLと同じ場所に `index.md` を生成（251本、`build.py` から毎回生成）。各HTMLの
   `<head>` に `<link rel="alternate" type="text/markdown" href=".../index.md">`
   （`tools/md_link_r26.py` で一度だけ挿入）。Content Negotiation ではなく `.md` の直接配信。
9. **キャッシュヘッダ（1-5）**: `_headers` に `/facts.json`（application/json）、
   `/llms-full.txt`、`/*.md`（text/markdown）を追加。
10. **診断（1-8の前提）**: `seo_aio_meo_audit.py` に #63 facts.json / #64 Speakable /
    #65 Person・WebSite同一性 / #66 IndexNowキー / #67 Markdown版 を追加（全67観点）。
11. **計測の雛形と復旧手順**: `seo-audit/prompt_battery_50kw.csv`（50キーワード×4エンジン
    ＝200行、測定列は空）、`coordination/ROLLBACK_SEO.md`。

### 公開とライブ確認（2026-11-27 18:2x JST）

- コミット `05af98c`。push 前に `git pull --rebase` を実行し、Museの「FAQ追加第3弾」
  （学習ガイド10ページ）と競合したため、**Muse側の本文・FAQ・FAQPage を採用**したうえで
  こちらの head 変更（エンティティ・speakable・robotsメタ・Markdownリンク）を再適用して統合。
- ライブ HTTP 200: `/`、`/facts.json`、`/48e6c2249edd47e7a2229c425cab62c5.txt`、
  `/llms.txt`、`/llms-full.txt`、`/index.md`、`/about/index.md`、`/sitemap.xml`、`/robots.txt`。
- Content-Type: `/facts.json` = application/json、`/about/index.md` = text/markdown; charset=UTF-8、
  `/llms-full.txt` = text/plain（いずれも Cache-Control: must-revalidate）。
- UA別: GPTBot / OAI-SearchBot / ChatGPT-User / PerplexityBot / Perplexity-User / ClaudeBot /
  Claude-SearchBot / Claude-User / Google-Extended / Applebot / Applebot-Extended / Bingbot の
  12種で robots.txt とトップが 200。
- 初期HTML（JS実行前）の本文確認: `/`・`/pricing/`・学習ガイド1本で h1=1、h2 8〜15、
  table 1、FAQ文言あり、JSON-LD 1〜3ブロック、Markdownリンクあり。
- sitemap.xml: 251 URL、lastmod は7種類（2026-11-27が149、11-24が89、11-18が3、
  10-31が1、10-04が7、09-26が1、09-21が1）。**一律の当日日付にはしていない**。
  `lastmod` は各ページの `meta last-modified` を正本に `build.py` が出力する仕様。
- IndexNow: 全251 URL を `https://api.indexnow.org/indexnow` と
  `https://www.bing.com/indexnow` の両方へ送信し、**両方 HTTP 200**。
- 検証: `build.py --check` exit 0（251 URL）／`seo_guard_r17.py` errors 0／
  `validate_release_r23.py` 252ページ通過／`seo_aio_meo_audit.py` **67観点 PASS 67 / WARN 0 / FAIL 0**。

### 未了・要判断

- **Google Search Console / Bing Webmaster Tools の所有権確認**: メタタグ方式は
  本人アカウントで発行される確認トークンが必要で、こちらでは生成できない。
  HTMLファイル方式も同様。Bing は IndexNow のキーファイルで通知はできるが、
  Webmaster Tools のプロパティ確認とは別。トークンが共有されれば head へ追加する。
- **プロンプトバッテリーの実測**: `seo-audit/prompt_battery_50kw.csv` は雛形のみ。
  ChatGPT Search / Perplexity / Google AI Overview / Copilot の実測は、各サービスの
  画面操作（ログイン・地域・履歴の影響）が必要なため未実施。
- **Markdown版の本格的な Content Negotiation**: 現在は `.md` の直接配信。
  Accept: text/markdown による自動切替はホスティング側の機能が必要で、今回は未設定。
- Apple Business Connect のブランド画像・外部サイテーションは従来どおりサイト外の作業。

### 障害記録（2026-11-27 18:16 JST〜）: Netlify 利用上限による全ページ 503

- `https://kurodaschool.jp/` が `HTTP/2 503`、本文 `{"error":"usage_exceeded","message":"Usage exceeded"}`、`server: Netlify`。
- `https://kiyotomokuroda.netlify.app/` も同じ 503。別回線（外部取得）でも 503 のため、
  サイト単位ではなく **Netlify アカウントの利用上限**と判断。
- DNS は Netlify DNS（`dns1.p01.nsone.net`）→ 52.52.192.191 / 13.52.188.95。
  `workers.dev` 版は 301 で本体へ、`kiyotomokuroda.pages.dev` は名前解決不可。
- 18:12 JST 時点では第4弾のデプロイが反映され 200（`/facts.json` 等）。18:16 頃から 503。
  直前に全251本の `.md` を検証（約700リクエスト・十数MB）していたが、
  この量で月間上限に達するとは考えにくく、原因の断定はできない。
- 復旧には本人の Netlify アカウント操作（Usage の確認、プラン/帯域の追加、または
  Cloudflare Pages への切替）が必要。Pickle 側では契約・請求・DNS の変更は行わない。
- 復旧後に再確認する項目: `/`、`/facts.json`、`/{key}.txt`、`/llms-full.txt`、`/about/index.md`、
  `/about/` の比較表、sitemap 251 URL、robots.txt の12 UA。

## 復旧確認とIndexNow再送（2026-11-27 20:25 JST）

- **503障害の解消を確認**。`https://kurodaschool.jp/` は `HTTP/2 200` に復帰（`server: Netlify`、
  `cache-status: Netlify Edge fwd=miss stored`）。`usage_exceeded` の本文は返らない。
- 復旧後チェック（代表10URL、HEADのみ・一斉251リクエストは行っていない）はすべて `HTTP/2 200`：
  - `/` `text/html` 48,342B ／ `/about/` 32,550B ／ `/pricing/` 35,938B ／ `/area/` 27,243B
  - `/robots.txt` `text/plain` 1,038B ／ `/sitemap.xml` `application/xml` 30,860B
  - `/facts.json` `application/json` 3,917B ／ `/48e6c2249edd47e7a2229c425cab62c5.txt` `text/plain` 32B
  - `/index.md` `text/markdown; charset=UTF-8` 18,729B ／ `/about/index.md` `text/markdown` 15,088B
- 配信内容が最新コミット `cd49366`（教材試し読みサンプル・FAQ第4弾・noteリンク差し替え）と一致することを確認：
  `/facts.json` の note URL は `note.com/iris_ruins`、`/materials/` に `#samples` と
  `samples/k01-math.pdf` 等のリンク、`/samples/k01-math.pdf` は 200。`/faq/` に FAQPage JSON-LD。
- ライブ `sitemap.xml` は 251 URL、`robots.txt` は AIクローラ19種（予定の12種を含む）を維持。
- **IndexNow再送**：`python3 tools/indexnow_submit.py --submit` で全251 URL を送信。
  `https://api.indexnow.org/indexnow` → **200**、`https://www.bing.com/indexnow` → **200**（いずれも受理）。
  キーは `48e6c2249edd47e7a2229c425cab62c5`、ライブのキーファイル本文も一致。
- 未確認：Netlify 側で何が上限に達したか（帯域か builds か）と、追加購入・プラン変更の有無は
  本人アカウント側の情報のため未確認。再発時は `coordination/ROLLBACK_SEO.md` の復旧手順に従う。

## 巡回追記（2026-11-27 20:38 JST、muse）

- **Pickle の第3弾・第4弾と CTR改善を取り込み**：14:38以降、オンライン専業・全国47都道府県対応への一括統一（構造化データから教室の詳細住所・電話等を除去）、駅・区14ページのオンライン表記統一とAI引用ブロック、第4弾（IndexNow・facts.json・Speakable・Markdown配信・robots強化、診断67観点 PASS 67）、Search Console実測に基づくCTR改善（計8ページの title/meta 書き換え）、FAQ追加第3弾・第4弾等が公開済み。
- **Netlify 503障害からの復旧を確認**：18:16頃に記録された usage_exceeded による全ページ503について、本巡回でライブ確認したところトップ HTTP 200、sitemap 251 URL を確認。復旧手順の記録（NETLIFY_503_RECOVERY.md）もリポジトリに追加済み。
- 本巡回ではサイト変更は行っていない（Pickle／スプリント側と競合しない範囲での取り込みのみ、public/ には触れていない）。サイト規模は 251ページ。
- 残キュー：プロンプトバッテリーの実測、Search Console／Bing Webmaster の所有権確認（本人のトークン発行が必要）、GBP未登録（本人の名義・本人確認が必要）は未了のまま。スプリント期間は 2026-11-28 08:47 JST まで。

## 巡回追記（2026-11-27 22:38 JST、muse）

- SEOスプリント／Pickle 側の新規ウェーブは本巡回では確認していない。ライブ確認：トップ HTTP 200、sitemap 251 URL。
- 本巡回ではサイト変更は行っていない（スプリント側と競合しない範囲での確認のみ、public/ には触れていない）。サイト規模は 251ページのまま。
- 残キュー：プロンプトバッテリーの実測、Search Console／Bing Webmaster の所有権確認（本人のトークン発行が必要）、GBP未登録（本人の名義・本人確認が必要）は未了のまま。スプリント期間は 2026-11-28 08:47 JST までで、その後は常時運用（本人指示 2026-11-27 22:36）。
## 追記（2026-11-27 第5弾：LINE問い合わせ導線の魔改造・CRO監査の追加、Pickle）

「LINEから入塾問い合わせが来るように」という依頼に対する第5弾。サイト構成（251ページ）と
既存の料金・購入条件・`/legal/`・`/privacy/`・`/materials/terms/`・オンライン専業（住所非表示）
方針は変更していない。虚偽の実績・口コミ・GBPの架空拠点・CTRボット等は行っていない。

### 1. LINEリンクの棚卸し（現行本番の確定）

3種類の短縮URLと2種類のLINE URLが混在していた。いずれも公式アカウント `@670gzfpd` を指す。

| 表記 | 出現数（HTML） | 確認結果 |
| --- | --- | --- |
| `lin.ee/VKV65IQ` | 357 | 301 → `line.me/R/ti/p/@670gzfpd`（現行本番。これに統一） |
| `lin.ee/YXdwMqY` | 0（`tools/_header.html` と旧JSに残存） | 301 → 同じ `@670gzfpd` |
| `lin.ee/vb8qVu4` | 6（英語・数学・コンタクト等5ページ） | 301 → 同じ `@670gzfpd` |
| `line.me/R/oaMessage/%40670gzfpd/?...` | 19 | 200。相談文のプリフィル用に継続利用 |
| `line.me/R/ti/p/@670gzfpd` | 9 | 200。友だち追加の直リンク |

- 正本を `https://lin.ee/VKV65IQ`（友だち追加）と `oaMessage`（相談文プリフィル）の2種類に統一。
  旧 `YXdwMqY`・`vb8qVu4`・`ti/p` 直リンクは `tools/line_cro_r27.py` が全ページで置換。
- `public/assets/line-navigation-r15-*.js` の `lineUrl` も同じ値に揃えた。

### 2. 離脱ポイントへの相談カード（全246ページ）

`tools/line_cro_r27.py` で、FAQ見出しの直前（読み終わる前）に相談カードを静的に挿入。
JS依存なし、マーカー `<!-- r27:cro-mid:start -->` で何度でも差し替え可能。

- カードの内容: 見出し／説明1文／事実ベースの3点（**無理な勧誘はしない**・
  **東大教育学部卒の黒田が直接返信（原則24時間以内）**・**学年・志望校・模試結果を送るだけで優先順位を整理**）／
  LINEボタン（相談文プリフィル）／フォーム（通話なし）／料金の目安（月額24,000円〜・税込・月4セット）。
- カテゴリ別の見出しとプリフィル文（例）:
  - 学習ガイド: 「学習ガイド『東大英語対策の全体像』を読みました。学年・志望校・今の模試の結果を送ります。…」
  - 47都道府県: 「北海道からオンライン受講を考えています。学年・志望校・今の模擬試験の結果を送ります。」
  - 駅・区（14）: 「文京区周辺でオンライン受講を考えています。…」
  - 大学別: 「一橋大学の対策を相談したいです。学年・志望学部・今の模試の結果を送ります。」
  - 料金: 「料金プランを見ました。学年と志望校を送るので、プランの選び方を相談したいです。」
  - 指導事例: 「指導事例を読みました。同じような状況から相談したいです。…」
- 相談カードを置かないのは `/contact/`（フォーム本体）・`/shindan/`（診断ツール）・法務3ページのみ。

### 3. スマホ追従バーをHTMLへ静的設置（248ページ）

- これまでは `line-navigation-r15.js` が実行時に追従バーを生成していた（JS無効だと出ない、
  初回描画後に現れる）。`<a class="r27-sticky">` をHTMLに直接置き、JS無効でも最初から押せるようにした。
  2段組み（「LINEで無料相談（登録1分）」／「東大卒が直接返信・勧誘なし」）、高さ56px、
  `env(safe-area-inset-bottom)` 対応、`body` の下余白86px。
- JS側は `.r27-sticky` があるページでは追従バーを重複生成しないよう変更（デスクトップの
  フローティングボタンは従来どおり500pxスクロール後に表示）。
- トップの旧固定ボタン（`ks-line-fixed`）は撤去し、同じ追従バーに統一。
- 法務3ページ（`/privacy/`・`/legal/`・`/materials/terms/`）には追従バーを置かない。

### 4. CSS・内部リンク

- `public/assets/line-cro-r27.css` を追加（`.r27-cta`／`.r27-sticky`、モバイルで全幅ボタン）。
- `tools/internal_links_r27.py`: 47都道府県ページの大学一覧表で、専門対策ページがある大学名を
  リンク化（13本）。あわせて各県ページの相談カード直前に「志望校別の対策ページ」
  （東大文科・早稲田・慶應・上智・明治・立教・関関同立・国公立）を追加。
- 県ページ生成ツール `generate_region_pages_r24.py` も同じカード・追従バー・大学リンク・
  speakableを出力するよう更新（再生成時も第5弾の状態を維持）。

### 5. AIO・MEO

- `/facts.json`: `bestFor`（向いている5項目）・`notBestFor`（向かない3項目）・
  `comparison`（形態別7軸の比較と黒田塾の仕様、`/about/#comparison` が出典）・
  `contact.consultation`（無料30分・オンライン／テキストのみ可・返信は原則24時間以内・
  勧誘なし・送ると話が早い4項目・カテゴリ別テンプレ4種）を追加。
- `/llms-full.txt`: 「他の塾・家庭教師との違い（形態別の比較）」表と「相談のしかた」節を追加。
  AIが「オンライン大学受験個別指導の比較」「不登校・再受験」「東大卒のマンツーマン」系の
  質問に答えるとき、料金・向き不向き・相談手段を同じ出典から引用できる。
- MEO: 県ページは従来どおり教室住所・電話・地図を載せず、地域名・県内大学・受験環境・
  オンライン受講の進め方・地域別LINE相談文で構成。今回、地域検索からの受け皿として
  LINE相談カードと志望校別リンクを全47県に追加。

### 6. 診断ツールの追加観点（67 → 74）

`tools/seo_aio_meo_audit.py` に CRO 観点を7つ追加。

| # | 観点 | 判定 |
| --- | --- | --- |
| 68 | 全ページにLINE相談リンク（法務ページを除く） | PASS（0件なし） |
| 69 | 1ページ内のLINE接点3本以上（ヘッダー・本文中・固定バー） | PASS |
| 70 | 記事中盤〜FAQ前のLINE相談カード | PASS（246ページ） |
| 71 | スマホ追従バーがHTMLに静的設置（JS無効でも表示） | PASS（248ページ） |
| 72 | カテゴリ別の相談テンプレ（oaMessage） | PASS（248ページ） |
| 73 | LINEリンクの正規化（旧短縮・ti/p直リンクの残存0） | PASS（0件） |
| 74 | 事実ベースのマイクロコピー（勧誘なし・直接返信・返信目安） | PASS |

### 7. 検証（ローカル、公開前）

- `python3 build.py --check` → exit 0（251 URL、Markdown 251本、sitemap/robots/llms/feed/facts 再生成）
- `python3 tools/seo_guard_r17.py` → errors 0（252 HTML / 251 sitemap URL、アセット指紋一致）
- `python3 tools/validate_release_r23.py` → 252ページ通過
- `python3 tools/seo_aio_meo_audit.py` → **74観点 PASS 74 / WARN 0 / FAIL 0**
- `python3 tools/line_cro_r27.py --check` → 本文中CTA 246／追従バー 248／oaMessage 248、未適用0
- `python3 tools/internal_links_r27.py --check` → 47県すべて適用済み
- HTML最大サイズ 98KB（`/study-guides/todai-math-2026-3/`）。250KB上限内。

### 8. 公開とライブ確認（2026-11-27 22:45〜22:52 JST）

- コミット `f83967c`（push 直前に muse の「LINE導線: 主要5ページに相談障壁を下げる文言を補完」
  `094852d` が入っていたため `git pull --rebase` し、5ページの文言はそのまま残して統合。
  `/pricing/`・`/area/`・`/contact/` は1行HTMLのため競合し、muse側の文言を
  こちらのカードに取り込んで解消）。
- ライブ HTTP 200 と反映確認:
  - `/` `/pricing/` `/cases/` `/area/` `/for-parents/` `/specialty/` `/specialty/tokyo/`
    `/specialty/hitotsubashi/` `/specialty/myogadani/` `/study-guides/`
    `/study-guides/kyotsu-english-time/` `/about/` の12URL すべて 200、
    `r27-sticky` と本文中CTA のマークアップを確認。
  - `/contact/` は追従バーのみ（本文中CTAなし・設計どおり）、`/privacy/` `/legal/` はどちらも無し（設計どおり）。
  - `/facts.json` 200 `application/json` 6,929B（`bestFor` 5・`notBestFor` 3・`contact.consultation` あり）、
    `/llms-full.txt` 200 116,674B、`/sitemap.xml` 200 251 URL、`/robots.txt` 200 1,038B、
    `/index.md` 200 `text/markdown` 19,801B、`/line-cro-r27.css?v=20261127` 200 `text/css` 2,264B
    （`must-revalidate`）、`/line-navigation-r15-bcf937681291.js` 200（`immutable`）。
  - 相談文プリフィルの `line.me/R/oaMessage/%40670gzfpd/?...` は iPhone UA で 200
    （LINEのWebページ。実際の文面入力はLINEアプリ内のため未確認）。
- 実ブラウザ（幅1920px）: デスクトップでは追従バー非表示、`.r27-cta` 792px・LINEボタン高さ56px、
  フローティングボタンはスクロール後に表示。JSの追従バー重複生成なし。
- モバイル幅390pxの描画（同一ページを幅390pxの枠内で表示して計測）: 追従バー `display:flex`・高さ56px・
  下10px・z-index 1200、本文中CTA 335px幅・LINEボタン329×58px・`body` 下余白86px。
  スクリーンショット: `/workspace/seo-audit/r27-screenshots/`
  （`r27-mobile-guide`・`r27-mobile-hokkaido`・`r27-mobile-home-top`・`r27-desktop-hokkaido-cta`）。
- IndexNow: 全251 URL を `https://api.indexnow.org/indexnow` と `https://www.bing.com/indexnow`
  へ送信し、**両方 HTTP 200**。

### 9. 未了・次の一手

- デプロイ後のライブ確認とIndexNow再送は上記8のとおり完了。
- スマホ表示は幅390pxの枠内描画（実測: 追従バー56px・ボタン58px）で確認した。
  実機の親指操作・LINEアプリへの遷移は本人の端末で1回見てもらうのが確実
  （ブラウザセッションにデバイスエミュレーションがなく、LINEログインも行っていないため）。
- Search Console / Bing Webmaster の所有権確認、プロンプトバッテリー実測は従来どおり未了
  （本人のトークン発行が必要）。

## 追記（2026-11-27 第6弾：GA4導入・LINE転換の追加実装・FAQ拡充、Pickle）

対象：`repos/A`（kurodaschool.jp）。252 HTML（インデックス対象251）。

### 1. GA4 と LINEクリック計測（#86・#88）

- GA4 プロパティ「黒田塾」の測定ID **`G-QBX05P7M5T`**（ウェブストリーム `16429483808`）を、
  **252ページすべての `<head>`** に同じ形で組み込んだ。挿入・点検は `tools/ga4_r28.py`
  （`--check` で欠け・重複を検出。何度実行しても同じ結果）。
  - `https://www.googletagmanager.com/gtag/js?id=G-QBX05P7M5T`（async）
  - `gtag('config', 'G-QBX05P7M5T', {allow_google_signals:false, allow_ad_personalization_signals:false})`
  - `/assets/analytics-r28-<hash>.js`（defer）
- 計測JS（`public/assets/analytics-r28.js`）は、クリックされた要素が
  `[data-line-cta]` または `lin.ee` / `line.me` リンクのときだけ
  `line_click` イベントを送る。パラメータは `cta_location`（例 `mid-pricing`・`sticky-…`・
  `table-…`・`anx-…`・`diag-…`・`search-empty`）、`cta_variant`（a/b/c）、
  `page_path`（`location.pathname`）、`link_type`（`oa_message` / `friend_add`）。
  `transport_type: 'beacon'` で遷移時も送信する。氏名・入力内容・相談文は送らない
  （`oaMessage` のクエリは送らず、`link_type` だけ）。
- `build.py` に GA4 の検査を追加（全ページにタグが1つ・測定ID一致・計測JSの参照あり）。
- プライバシーポリシー（`/privacy/`）に「アクセス解析（外部への送信）」の節を追加：
  送信する情報（ページパス・参照元・端末/ブラウザ・およその地域・LINEボタンのクリック位置）、
  送信しない情報（氏名・メール・答案・成績・相談文・LINE本文）、Googleシグナルと
  広告パーソナライズは無効、オプトアウト（Cookie無効化・Google アナリティクス
  オプトアウト アドオン）。従来の「広告目的の追跡タグは置いていない」は
  「広告配信・リマーケティング目的のタグは置いていない（解析はGA4のみ）」に書き換えた。
  制定日はそのまま、改定日 2026-11-27 を追記。`/legal/`（特商法表記）は計測の記載を
  要しないため変更していない。

### 2. LINE転換（#1・#2・#5・#6・#7・#8・#11・#12 相当）

`tools/line_cro_r28.py`（`--check` あり）で全ページに適用。r27の本文中CTA・追従バーは残した。

| 実装 | 対象 | 内容 |
| --- | --- | --- |
| 比較表の直下CTA | 230ページ | 最初の表の直後に「この表の条件を、自分の学年・志望校で確かめる：**自分の条件でLINE相談する**（無料・勧誘なし・返信は原則24時間以内）」。表ごとの相談文を `oaMessage` にプリフィル |
| よくある不安3つ→LINE | 学習ガイド82本 | 不安（塾・教材を変えて遅れないか／オンラインで集中できるか／費用が読めるか）に事実だけで回答し、LINEとフォームへ。無料の英単語帳（`/materials/`）と学習見本PDF（`/downloads/`）が登録不要で読めることも記載 |
| CTA文言の3種出し分け | 247ページ | 「LINEで無料相談する（登録1分）」「自分の条件でLINE相談する（無料）」「まずは質問だけ、LINEで送る」をページごとに固定割当（URLのCRC32）。`data-cta-variant` でGA4の `line_click` と突き合わせ可能 |
| 診断ページ末尾 | `/shindan/`・`/learning-check/` | 「結果を、次の7日間の行動に変える」→結果をLINEで相談（診断名入りの相談文をプリフィル）／通話なしフォーム。保護者の相談歓迎も明記 |
| 「お子さま」表記 | `/for-parents/`・保護者向けガイド3本 | 「お子さん」「子ども」を「お子さま」に統一（本文とJSON-LDの両方） |
| タップ領域44px | 252ページ | `/assets/r28-ux.css` で `.r27-line`・`.r27-alt`・`.r27-sticky`・`.nav-cta`・`.nav-line`・`.btn`・新規CTA・（幅760px以下では）ナビ/フッター/関連リンクを `min-height:44px` 以上に |

無料特典は実在するものだけを書いた（英単語帳の全文公開・学習見本PDF4枚・
無料相談30分・90日学習ロードマップ設計キット）。語数など根拠のない数字は足していない。

### 3. 技術SEO・コンテンツ・AIO（#39・#44・#45・#48・#51・#55 等）

- **`/faq/` のQ&Aを27→51件に拡充**（#39）。追加した節：相談から受講までの流れ（5）／
  支払いと契約前の確認（5）／オンライン受講の環境（4）／保護者の方から（4）／
  学習の進め方（4）／サイトの情報と個人情報（2）。料金は5プランの税込・月4セット、
  添削は週1回プラン月4通・週2/3回は無制限、保護者面談は週2・週3に月1回、
  教材は「面談を含むプランに作成費込み・市販教材は実費」など、既存ページの記載に合わせた。
  支払い方法・入会金・解約・振替は「サイトでは確定していない／契約前に個別確認」と明示。
  画面のQ&Aと `FAQPage` JSON-LD は `tools/faq_schema_r28.py` で一致させ（51件）、
  `build.py` が件数不一致を検出する。
- **`404.html`（#44）**：重複していたナビ2件を整理し、人気学習ガイド5本
  （英文読解の診断／数学の自力演習／週間計画表／模試の復習／塾の選び方）と
  「探していたページのURLを知らせる窓口」を追加。
- **`llms.txt`（#55）**：`## 引用時の表記ルール` を追加（7項）。名称とURL、
  「月額・税込・月4セット」を落とさない、オンライン専業で教室なし（47都道府県ページは
  地域からの受講案内）、実績は累計50人以上の指導と合格実績を分け保証表現にしない、
  茨城県の「黒田学習塾」等と無関係、要約時は「要約」と明示、連絡先は公式のみ。
  `build.py` が節の欠落を検出。
- **サイト内検索（#48）**：`/study-guides/` の絞り込みを強化。カタカナ→ひらがなの
  正規化と、18語の言い換え辞書（要約/summary、英作文/writing、模試、保護者、計画、
  単語、長文、共通テスト/センター、東大、塾、リスニング、過去問、復習、宿題、不登校、
  浪人、併願、面接）。0件のときは理由と直し方、該当記事をLINEで聞ける導線を表示。
- **`feed.xml`（#45）**：82記事すべてに `<category>`（東大受験・共通テスト・中学受験・
  保護者・英語・数学・学習計画・復習・塾/指導の選び方・勉強法）と
  `<content:encoded>`（記事冒頭の要約）を追加。`copyright`・`ttl` も追加し、
  並びは `datePublished` の新しい順に修正（従来は last-modified 順で、更新日を揃えると
  並びが崩れていた）。

### 4. 検証（ローカル、公開前）

- `python3 build.py --check` → exit 0（251 URL・82記事・251 Markdown・GA4検査・FAQ件数一致）
- `python3 tools/seo_guard_r17.py` → errors 0（252 HTML / 251 sitemap URL、アセット指紋一致）
- `python3 tools/validate_release_r23.py` → 252ページ通過
- `python3 tools/seo_aio_meo_audit.py` → **PASS 74 / WARN 0 / FAIL 0**
- `python3 tools/ga4_r28.py --check` → 252ページ・不足0・重複0
- `python3 tools/line_cro_r28.py --check` → 比較表CTA 230／不安3つ 82／診断CTA 2／文言 247、未適用0
- `python3 tools/faq_schema_r28.py --check` → 画面51件・JSON-LD 51件で一致
- HTML最大サイズ 99KB 未満（250KB上限内）

### 5. 今回の100項目リストの扱い

- 完了：GA4導入（#86）・LINEクリック計測（#88）、比較表直後CTA（#1 相当）、
  不安3つブロック（#2 相当）、CTA文言3種（#5〜#8・#11〜#12 相当）、
  FAQ拡充（#39）、404改善（#44）、feed充実（#45）、サイト内検索強化（#48）、
  llms.txt引用ルール（#51・#55）、タップ領域44px。
- 保留／除外：#58（HTMLコメントへのLLM指示埋め込み）は方針として実施しない。
  `コメント`内の指示でクローラを操作する手法はスパム扱いになり得るため。
- 100項目リストの全文は `repos/A` 内に保存されていないため、この追記は
  今回の指示で番号が明示された項目だけを対応づけている。番号の対応が違う場合は
  リスト本体を共有してもらえれば突き合わせる。
- 従来からの未了：Search Console／Bing Webmaster の所有権確認と実測（本人のトークン）、
  GBP（Googleビジネスプロフィール）登録（本人の名義・本人確認）、
  #26/#27/#48（質問形式の見出し・比較表・記事冒頭の要点）の残り記事。

### 6. 追補とライブ確認（2026-11-27 23:10〜23:25 JST）

公開は2コミット（`94b6ae1` 本体、`6269199` 検索の読み対応）。

- **学習ガイド検索の追補**：`/study-guides/` の絞り込みに、ひらがな・カタカナの読みから漢字の語へ戻す
  辞書18語（`えいさくぶん→英作文`、`もぎ→模試`、`けいかく→計画` など）を追加。
  実測：`英作文` で3件、`えいさくぶん` で同じ3件。0件のときは理由・直し方・
  「LINEで記事を聞く（無料）」を表示（実ブラウザで確認）。
- 計測の `cta_variant` は、識別子のないCTA（比較表直下など）で `fixed` を送る。
- `/faq/` の画面表示「内容更新」を 2026年11月27日に更新。

ライブ確認（`https://kurodaschool.jp`、デプロイ反映後）:

- HTTP 200：`/`・`/pricing/`・`/faq/`・`/404.html`・`/study-guides/`・`/privacy/`・
  `/shindan/`・`/learning-check/`。
- GA4：`/`・`/pricing/`・`/faq/`・`/404.html` の4URLで
  `googletagmanager.com/gtag/js?id=G-QBX05P7M5T` と `gtag('config', 'G-QBX05P7M5T'` を確認。
  実ブラウザで `dataLayer` に `["config","G-QBX05P7M5T",{allow_ad_personalization_signals:false,allow_google_signals:false}]`
  が入り、`google-analytics.com/g/collect?...tid=G-QBX05P7M5T` への送信を2件確認。
  比較表直下のCTAを実際にクリックし、`line_click` が
  `{cta_location:"table-home", cta_variant:"fixed", link_type:"oa_message", page_path:"/", transport_type:"beacon"}`
  で送られることを確認。
- 新アセット：`/assets/r28-ux-ca19fc05964c.css` 200 `text/css` 3,462B、
  `/assets/analytics-r28-3ddcb9b369ea.js` 200 `application/javascript` 1,684B
  （その後 `analytics-r28-4207149f7ca7.js` に更新、200）。
- `/feed.xml` 200 `application/rss+xml` 99,587B（82 items・category・content:encoded）。
  `/llms.txt` 200 `text/plain` 98,465B（引用時の表記ルールあり）。
- タップ領域（実ブラウザ幅1920pxで実測）：本文中LINEボタン56px、フォームのテキストリンク44px、
  不安3つブロックのLINEボタン56px・フォームリンク44px、比較表直後リンク44px、
  ヘッダーの無料相談ボタン44px、`/study-guides/` の`a.btn` 53px。
  760px以下ではナビ・フッター・関連リンクにも `min-height:44px` を適用（CSSで担保）。
  実機の親指操作は未確認（このブラウザに端末エミュレーションがないため）。
- スクリーンショット：`/workspace/seo-audit/r28-screenshots/`
  （`r28-guide-anx-view-2026-11-27-232342.png` 学習ガイドの不安3つブロック、
  `r28-guide-anx-2026-11-27-232333.png` 同見出し）。
- IndexNow：全251 URL を `https://api.indexnow.org/indexnow` と `https://www.bing.com/indexnow`
  へ送信し、**両方 HTTP 200**。


## 巡回追記（2026-11-28 00:38 JST、muse）

- **Pickle の第5弾・第6弾・第7弾を取り込み**：第5弾＝LINE問い合わせ導線の魔改造（全246ページ本文中CTA・248ページ静的追従バー・カテゴリ別相談テンプレ、診断74観点 PASS 74、ライブ確認済み・IndexNow両エンドポイント200）。第6弾＝GA4導入とLINEクリック計測（line_click 実測済み）、FAQ 27→51問、404改善、サイト内検索の読み対応、タップ領域44px（ライブ確認済み・IndexNow両エンドポイント200）。
- 第7弾（コミット e60014c、2026-11-28 00:33 JST）：同名塾との分離明記（構造化データ・/about/ の #naming）、ブランド表記統一、新規の不安系ガイド4本追加等。**本巡回時点ではライブ未反映**：トップ HTTP 200、ライブ sitemap は 251 URL のまま、新規ガイド（/study-guides/juku-yametai/）は HTTP 404。デプロイ反映は次回巡回で再確認する（未反映を公開済みと数えない）。
- 本巡回ではサイト変更は行っていない（Pickle／スプリント側と競合しない範囲での取り込みのみ、public/ には触れていない）。
- 残キュー：プロンプトバッテリーの実測、Search Console／Bing Webmaster の所有権確認（本人のトークン発行が必要）、GBP未登録（本人の名義・本人確認が必要）は未了のまま。スプリントは 2026-11-27 22:36 の本人指示で終了日なしの常時運用に切替済み。
- 追補（同巡回中）：リモートに第8弾（コミット eed8872、2026-11-28 00:41 JST、東大文系数学50年データベースと通信制・不登校等の専用ページ追加、単発添削等の料金新設を含む）が入った。ライブ反映は次回巡回で再確認する。

## 第8弾（2026-11-28）: 東大文系数学50年データとセグメント4ページ、料金の単発メニュー

- 東大文系数学 1977〜2026年（50年・200問）の出題データを作成し、
  `/data/todai-bunkei-math-50years/`（JSON・CSV付き）と `/data/` を公開。
  年度・大問番号・分野は、1981〜2026年を Evolton、1998〜2026年を電数図書館と照合し、
  1977〜1980年は問題文（Mathexamtest の年度別アーカイブ）を読んで判定した。問題文は転載していない。
- 専用ページを4本追加：`/specialty/tsushin-kou/`（通信制高校）、
  `/specialty/futoukou-hokenshitsu/`（不登校・保健室登校）、`/specialty/takuro/`（宅浪）、
  `/specialty/kaigai/`（海外在住）。既存の `/specialty/futoukou-tsushin/`・`ronin/`・`kikokusei/`
  からリンクし、専門対策ハブ・サイトマップ・llms.txt・feed.xml に統合した。
- 料金：単発添削 1答案3,000円、スポット相談 60分12,000円、年間一括（12か月前払いで2か月分無料）を
  `/pricing/`・`/legal/`（役務の販売条件）・`facts.json`・`llms-full.txt` に追加。
  継続受講は上位プラン（週3回104,990円）から並べ、1セットあたり（7,500〜13,750円）を併記。
  `/contact/`・`/materials/`・トップでは、無料PDF・無料診断を「入口」、単発メニューを具体策として整理した。
- 生成スクリプト：`tools/todai_bunkei_math_data.py`、`tools/generate_todai_math_r30.py`、
  `tools/generate_segments_r30.py`、`tools/pricing_r30.py`。
- チェック：`build.py --check`（261 URL・MD 261件）、`seo_guard_r17.py`（0 errors）、
  `validate_release_r23.py`（262ページ）、`seo_aio_meo_audit.py`（74/74 PASS）。
- IndexNow：全261 URL を両エンドポイントへ送信し 200。

## 第7弾（2026-11-28）: 同名衝突の分離・技術SEO/CRO・不安系ガイド4本

コミット：`e60014c`（本体）、`e2cd4f9`（計測JSの配信ファイル反映）。
並行して走っていた第8弾（`eed8872`）の後にライブ反映を確認した（2026-11-28 00:42 JST デプロイ）。

### 1. 同名衝突の分離（最優先）

- `EducationalOrganization.disambiguatingDescription` を全面改稿し、次の4つ＋既存の
  水戸の塾を名指しして、**資本・運営・提携の関係が一切ない**ことを事実ベースで明記した。
  外部の塾の評価・優劣は書いていない。
  1. 行政書士向けの相続・離婚実務講座「黒田塾」（kurodajuku.com）
  2. 茨城県水戸市の「黒田学習塾」（kuroda-juku-mito.jp）と「オンライン黒田塾」（kuroda-juku.jp）
  3. 株式会社総合医療コンサルタント黒田塾（kuroda.tv、代表は黒田亮太）
  4. 黒田進学ゼミ（大阪府大阪市生野区）
- `Person.disambiguatingDescription` も同様に改稿（同名の運営者・講師ではないこと）。
- 全251ページの組織・人物・サイトノードを `tools/enrich_entity_r24.py` で同期
  （r29で Person / WebSite も同期対象に追加）。`build.py` に
  「全ページの識別文と sameAs が正本と一致すること」の検査を追加した。
- `/about/` に `#naming` セクションを新設。分野・所在地・公式ドメインだけを並べた表と、
  「評価や優劣を示すものではない」旨の注記、問い合わせ先は自サイトのみであることを記載。
  要点ボックスからもリンク。`/llms.txt` の引用ルール5・`/llms-full.txt` の基本情報にも反映。
- ブランド表記：トップ・`/about/`・`/juku/`・`/pricing/` のタイトルと `og:site_name` を
  「黒田塾（大学受験・オンライン）」ベースに変更（`/pricing/` は第8弾の改稿でさらに更新）。
  講師表記は全学習ガイドで「黒田清友（東京大学教育学部卒・黒田塾代表）」に統一し、
  Person の `jobTitle` を「黒田塾 代表」に。
- `sameAs`：X・note（`iris_ruins`／`large_coyote3612`）・Zenn（`zenn.dev/kurodaschool`）・
  BOOTH・ココナラ・連載・スマートレーダー。実在しない／別アカウントの `note.com/kurodajuku` は削除。

### 2. 技術SEO・CRO

- `/about/` のLCP画像（プロフィール写真）に `fetchpriority="high"` を付与（width/heightは既存）。
  トップのヒーローは `fetchpriority="high"` と 800×985 が既にあったことを確認。
- `/pricing/` の比較表に「1回あたりの目安（税込）」列を追加（面談のみ6,000円／授業のみ7,500円／
  週1回13,748円／週2回9,999円／週3回8,749円）。トップの料金表にも同じ目安を1行で併記。
  計算条件（月4セット・週2回は授業8回・週3回は12回）と税込であることを注記。
- `/juku/` に「向いている生徒・向いていない生徒を、表で確かめる」を新設（7行の対応表）と、
  「代表一人が最後まで担当する」ことの意味（交代なし・引き継ぎ不要・受け持ち人数の限界・
  校舎/集団/理科二次が対象外であること）。既存の向き不向き段落からリンク。

### 3. 計測（GA4）

- `assets/analytics-r28.js` に追加：`diagnosis_complete`（`ks:diagnosis-complete` を購読）、
  `data-ga-event` を持つボタンの `result_copy` / `result_print`。
  送るのは診断の種類・結果の分類・テーマ分類・ページパスのみ（学年・自由記述・氏名は送らない）。
- `/shindan/` の結果画面に「結果をコピー」「結果を印刷」を新設（クリップボード／`window.print()`）。
  `showResult()` から完了イベントを送出。
- `/learning-check/` は既存の印刷・コピーボタンに計測属性を付与し、結果表示時に完了イベントを送出。
- 注意：ページが読み込むのはハッシュ付きファイルのため、`e2cd4f9` で配信ファイル側にも反映した
  （`learning-check-r21-5b3007429422.js`）。

### 4. コンテンツ・AIO

- 全82本の学習ガイドの著者表記を統一（`tools/byline_r29.py`）。公開日（Article の
  `datePublished`）と更新日（meta `last-modified`）を両方表示。著者ボックスは全記事に
  既存（黒田清友・東大教育学部卒・累計50人以上）を確認。
- 新規ガイド4本（既存82本と題材が重複しない不安・課題系。`tools/guide_r29.py`）：
  - `/study-guides/juku-yametai/` 「塾をやめたい」と思ったときの判断
  - `/study-guides/shiboukou-sageru/` 志望校を下げるべきか迷ったとき（判定ではなく数字で決める）
  - `/study-guides/ima-kara-maniau/` 今から受験勉強を始めても間に合うか
  - `/study-guides/teiki-test-juken-ryoritsu/` 定期テストと受験勉強の両立
  いずれも要点ボックス・目次・比較表・FAQ（4問）・著者ボックス・関連リンクを持ち、
  WebPage/Article/BreadcrumbList/FAQPage＋共通3ノードを出力。学習ガイド一覧・サイトマップ・
  既存ガイド3〜4本からの内部リンク・`llms.txt`・`llms-full.txt`・`feed.xml`・`.md` に統合。

### 5. チェック結果（最終）

- `python3 build.py --check` → SEO checks passed（261 URL・MD 261件・262ページ）
- `python3 tools/seo_guard_r17.py` → errors 0（262 HTML / 261 sitemap URL）
- `python3 tools/validate_release_r23.py` → 262ページ通過
- `python3 tools/seo_aio_meo_audit.py` → **PASS 74 / WARN 0 / FAIL 0**
- `tools/ga4_r28.py --check` 不足0・重複0、`tools/line_cro_r28.py --check` 未適用0、
  `tools/byline_r29.py --check` 未統一0

### 6. ライブ確認（https://kurodaschool.jp、2026-11-28 00:42〜00:47 JST）

- HTTP 200：`/`・`/about/`・`/pricing/`・`/juku/`・`/shindan/`・`/learning-check/`・
  `/study-guides/`・新規4本（`juku-yametai`・`shiboukou-sageru`・`ima-kara-maniau`・
  `teiki-test-juken-ryoritsu`）・`/sitemap.xml`・`/llms.txt`・`/feed.xml`・`/facts.json`。
- `/about/` に `id="naming"` と4つの塾名、`/pricing/` に1回あたりの目安、`/juku/` に
  `#fit-check` を確認。`facts.json` の `updated` は 2026-11-28、`namingNote` と `sameAs` も反映。
- ライブ sitemap に新規4URL、`llms.txt` に4本、`feed.xml` は91 items。
- GA4（実ブラウザ）：`/shindan/` を完走し `diagnosis_complete`
  `{diagnosis_tool:"shindan", diagnosis_result:"標準固めタイプ", page_path:"/shindan/"}` を dataLayer で確認、
  結果コピーで `result_copy`。`/learning-check/` も `diagnosis_complete`
  `{diagnosis_tool:"learning-check", diagnosis_result:"english", diagnosis_theme:"time"}` と
  `result_copy` を確認。`google-analytics.com/g/collect?...tid=G-QBX05P7M5T` への送信も確認。
- スクリーンショット：`/workspace/browser/r29-guide-juku-yametai-2026-11-28-004649.png`（新規ガイド）
- IndexNow：全261 URL を `api.indexnow.org` と `www.bing.com/indexnow` へ送信し、**両方 200 OK**。

### 7. 補足

- 前回の巡回追記にある「第7弾はライブ未反映」は、2026-11-28 00:42 JST のデプロイで解消した
  （デプロイまで約8分かかった）。
- 並行して第8弾（東大文系数学DB・セグメント4ページ・単発メニュー）が同じリポジトリに
  コミットされ、本記録作成時点の `origin/main` は第8弾の後に本記録が載る形になっている。
  第7弾の内容は第8弾のリビルド後も保持されていることを、上記ライブ確認で確認した。
- 未了：Search Console／Bing Webmaster の所有権確認（本人のトークン）、GBP（本人の名義）は
  引き続き本人の操作待ち。


## 巡回追記（2026-11-28 02:38 JST、muse）

- **第7弾・第8弾のライブ反映を確認（前回巡回の未反映が解消）**：第7弾の記録（コミット 0422f11）で 2026-11-28 00:42 JST のデプロイによりライブ反映済みと記録され、第8弾の記録（コミット 5489e49）でもチェック結果と IndexNow 送信（全261 URL・両エンドポイント200）が記録されている。本巡回でもライブを再確認し、トップ・東大文系数学50年データ（/data/todai-bunkei-math-50years/）・セグメント4ページ（通信制／不登校・保健室登校／宅浪／海外在住）・不安系ガイド4本（juku-yametai 等）がいずれも HTTP 200、ライブ sitemap は 261 URL で新規ページを含むことを確認した。
- その後のリモート変更：講師名の表記統一（コミット cf82ae4、「黒田清友（東京大学教育学部卒・黒田塾代表）」へ全ページ統一）と /about/ 同名一覧表の列幅調整（コミット 79d8c70）が入っている。
- 本巡回ではサイト変更は行っていない（Pickle／スプリント側と競合しない範囲での取り込みのみ、public/ には触れていない）。
- 残キュー：プロンプトバッテリーの実測、Search Console／Bing Webmaster の所有権確認（本人のトークン発行が必要）、GBP未登録（本人の名義・本人確認が必要）は未了のまま。スプリントは終了日なしの常時運用中。

## 第9弾（2026-11-28、一次データ・セグメント導線・AIO補強）

### 1. 現状点検の結果

- `/data/todai-bunkei-math-50years/` と新規セグメント4ページ（`/specialty/tsushin-kou/`・
  `/specialty/futoukou-hokenshitsu/`・`/specialty/takuro/`・`/specialty/kaigai/`）は、
  GA4タグ・`r27` 追従バー・LINE相談導線（`data-line-cta` 3本）・`max-image-preview:large`・
  `index.md` リンク（`rel="alternate" type="text/markdown"`）がすべて揃っていた。欠けはなし。
- 一方、**被リンクが偏っていた**。50年データへの文脈リンクは `/data/`・`/materials/`・
  `/site-map/`・`/specialty/todai-bunkei/`・`/study-guides/todai-bunkei-math-strategy/`・
  `/todai-juku/` の6ページのみ。セグメント4ページは `/site-map/` と `/specialty/`、
  同系統ページ（`futoukou-tsushin`・`kikokusei`・`ronin`）からだけで、
  集客側のハブ（`/for-parents/`・`/university-exam/`・`/juku/`・`/online-tutoring/`）からは
  1本も入っていなかった。

### 2. 内部リンク・LINE導線の補強

- 東大文系数学50年データへの文脈リンクを4ページに追加（既存の `data-link` 節と同じ形）。
  - `/specialty/sugaku/`：`#data-link`「数学の対策に使える出題データ（東大文系数学・50年）」を新設。
  - `/university-exam/`：`#todai-route` のリンク行に1本追加。
  - `/study-guides/todai-math-review/`：`#guide-section-7` の本文に1文＋リンク。
  - `/study-guides/todai-kakomon-review/`：`#guide-section-6` の本文に1文＋リンク。
  - 結果、50年データへの被リンクは6→10ページに。
- セグメント4ページへの導線を4ハブに追加（`<!-- r31:links -->` の節。いずれも本文中に
  自然な文脈で置き、4ページすべてへリンク）。
  - `/juku/`：`#learning-env-links`「学校に通いにくい時期からの大学受験」
  - `/university-exam/`：`#learning-env-links`「学校・生活環境が特殊な場合の対策」
  - `/for-parents/`：`#learning-env-links`「学校に通いにくい時期の受験を、保護者がどう支えるか」
  - `/online-tutoring/`：`#learning-env-links`「学校に通いにくい環境でも、同じ授業と面談を届ける」
  - 結果、被リンクは 通信制5→9／不登校4→8／宅浪3→7／海外在住3→7ページに。
- 編集した7ページの `last-modified` と Article `dateModified`（該当ページのみ）を
  2026-11-28 に更新。価格・購入条件・`/legal/`・`/privacy/`・`/materials/terms/`・
  オンライン専業（住所・電話非表示）方針は変更していない。

### 3. AIO構造化補強（`build.py`）

- `facts.json` に **`datasets`**（schema.org `Dataset`）を新設：名称・URL・
  `temporalCoverage 1977/2026`・`size 200`・`variableMeasured`・`license`・`citation`・
  `distribution`（data.json / data.csv）・`primaryDomainCounts`（12分野の主分野数・割合・
  タグ込み・副タグのみ・直近10年）・`caveats`（難易度は編集上の目安／分類は塾の整理／
  問題文は未収録）。`sources` に `data` を追加。
- `llms-full.txt` の「公開データ」節を拡充：順位表12行（主分野・割合・タグ込み・直近10年）、
  4系統の内訳（座標・図形系73／解析系61／離散系56／行列10）、難易度の目安（標準124・
  やや難68・難8）、文理共通39問、データの作り方と限界、`data.json`/`data.csv` の項目名、
  引用表記の例、そのまま引用できるQ&A4問。
- `llms.txt` 冒頭に機械可読データ（data.json／CSV）の案内を1行追加。
- 数値はすべて `tools/todai_bunkei_math_data.records()` から毎ビルド数え直す（本文と
  二重管理しない）。`build.py --check` に「`facts.json` の `datasets` が空でない・URL が
  50年データ配下・JSON/CSVの実体がある・`size` が `data.json` のレコード数と一致・
  `llms-full.txt` に公開データ節と data.json/data.csv がある」の検査を追加。
- あわせて本文の1文を修正：`/data/todai-bunkei-math-50years/` の「副タグまで含めると77問で
  最多」（関数・方程式）は、タグ込み件数の最大が図形と方程式92問であるため誤読を招く。
  「副タグまで含めると77問で、他の分野の問題に前提として最も多く添えられています
  （副タグのみで64問）」に直し、llms-full の数値と整合させた。

### 4. チェック結果（最終）

- `python3 build.py --check` → SEO checks passed（261 URL・MD 261件・262ページ）
- `python3 tools/seo_guard_r17.py` → errors 0（262 HTML / 261 sitemap URL）
- `python3 tools/validate_release_r23.py` → 262ページ通過
- `python3 tools/seo_aio_meo_audit.py` → **PASS 74 / WARN 0 / FAIL 0**
- `tools/ga4_r28.py --check` 不足0・重複0、`tools/line_cro_r28.py --check` 未適用0

## 巡回追記（2026-11-28 04:38 JST、muse）

- **Pickle の第9弾を取り込み**：コミット 0f050a0（2026-11-28 03:15 JST）で、東大文系数学50年データへの文脈リンク4本追加（被リンク6→10ページ）、セグメント4ページ（通信制／不登校・保健室登校／宅浪／海外在住）への導線を集客ハブ4ページに追加（被リンクは各3〜5→7〜9ページ）、facts.json への datasets（Dataset）新設と llms-full.txt の公開データ節拡充が公開済み。第9弾の記録では build.py --check 通過（261 URL）、診断74観点 PASS 74／WARN 0／FAIL 0。
- 本巡回でもライブを再確認：トップ HTTP 200、ライブ sitemap 261 URL。
- 本巡回ではサイト変更は行っていない（Pickle／スプリント側と競合しない範囲での取り込みのみ、public/ には触れていない）。
- 残キュー：プロンプトバッテリーの実測、Search Console／Bing Webmaster の所有権確認（本人のトークン発行が必要）、GBP未登録（本人の名義・本人確認が必要）は未了のまま。スプリントは終了日なしの常時運用中。

## 巡回追記（2026-11-28 06:38 JST、muse）

- SEOスプリント／Pickle 側の新規ウェーブ・新規コミットはなし（リモート main は前回巡回時点の 631f2a3 のまま）。ライブ確認：トップ HTTP 200、sitemap 261 URL。
- 本巡回ではサイト変更は行っていない（スプリント側と競合しない範囲での確認のみ、public/ には触れていない）。サイト規模は 261ページのまま。
- 残キュー：プロンプトバッテリーの実測、Search Console／Bing Webmaster の所有権確認（本人のトークン発行が必要）、GBP未登録（本人の名義・本人確認が必要）は未了のまま。スプリントは終了日なしの常時運用中。
