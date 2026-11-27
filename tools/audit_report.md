# 黒田塾 SEO / AIO / MEO 診断レポート

- 実行日: 2026-11-27
- 対象: 251ページ（総HTML 252） / 診断項目 62（うち従来56観点）
- 結果（56観点）: PASS 52 / WARN 4 / FAIL 0
- 結果（全体）: PASS 58 / WARN 4 / FAIL 0

優先度は P0（FAIL: 検索・AI検索への流入に直結）／ P1（WARN: 主要な改善余地）／ P2（WARN: 望ましい改善）です。

## P1 — 次に直す（1件）

- **#35 [Linking] 被リンク3本以上（孤立ページ防止）** — 被リンク3未満 51件（例: /site-map/ (1)／/specialty/bukatsu-intai/ (2)／/specialty/chiyoda/ (2)）

## P2 — 余力で直す（3件）

- **#26 [On-Page] 記事見出しへの質問形式（？付きH2/H3）導入** — 質問見出しなし 69/82本（例: /study-guides/careless-mistake/／/study-guides/chugaku-juken-12gatsu-shutsugan/／/study-guides/dokugaku-susumekata/）
- **#27 [On-Page] 学習ガイドへの比較表（table）設置** — tableなし 60/82本（例: /study-guides/careless-mistake/／/study-guides/dokugaku-susumekata/／/study-guides/eigo-gaibu-kentei-nyushi/）
- **#48 [AIO] 記事冒頭の結論・要点ブロック（AI引用向け）** — 冒頭要点なし 60/82本（例: /study-guides/careless-mistake/／/study-guides/choosing-a-juku/／/study-guides/chugaku-juken-12gatsu-shutsugan/）

## 全項目

| # | 分類 | 観点 | 判定 | 優先度 | 詳細 |
| --- | --- | --- | --- | --- | --- |
| 01 | Technical | robots.txt 存在 | PASS | - | robots.txt あり |
| 02 | Technical | sitemap.xml 妥当性 | PASS | - | 251 URLs |
| 03 | Technical | インデックス対象ページのサイトマップ網羅 | PASS | - | 未登録 0件 |
| 04 | Technical | サイトマップ内のnoindex/不要URL混入 | PASS | - | 不一致 0件 |
| 05 | Technical | canonical 設定有無 | PASS | - | 未設定 0件 |
| 06 | Technical | canonical 自己参照・HTTPS正規化 | PASS | - | 不一致 0件 |
| 07 | Technical | canonical 重複なし | PASS | - | 重複 0件 |
| 08 | Technical | robots メタタグ設定 | PASS | - | 未設定 0件 |
| 09 | Technical | html lang='ja' 設定 | PASS | - | 未設定 0件 |
| 10 | Technical | viewport 設定（モバイル対応） | PASS | - | 未設定 0件 |
| 11 | Technical | UTF-8 charset 明示 | PASS | - | 未設定 0件 |
| 12 | Technical | 内部リンク切れなし | PASS | - | リンク切れ 0件 |
| 13 | Technical | ローカルアセット（画像/CSS/JS）切れなし | PASS | - | 欠損 0件 |
| 14 | Technical | HTML id 重複なし | PASS | - | 重複あり 0件 |
| 15 | Technical | HTMLサイズ肥大化なし（250KB未満） | PASS | - | 超過 0件 |
| 16 | On-Page | title タグ設定 | PASS | - | 未設定 0件 |
| 17 | On-Page | title 文字数適正（15〜65字） | PASS | - | 範囲外 0件 |
| 18 | On-Page | title 重複なし | PASS | - | 重複 0種 |
| 19 | On-Page | meta description 設定 | PASS | - | 未設定 0件 |
| 20 | On-Page | meta description 文字数適正（50〜165字） | PASS | - | 範囲外 0件 |
| 21 | On-Page | meta description 重複なし | PASS | - | 重複 0種 |
| 22 | On-Page | h1 が各ページ1つ | PASS | - | 違反 0件 |
| 23 | On-Page | h1 重複なし | PASS | - | 重複 0種 |
| 24 | On-Page | 見出し階層（h1→h2→h3）飛びなし | PASS | - | レベル飛び 0件 |
| 25 | On-Page | シンコンテンツ回避（600字以上） | PASS | - | 600字未満 0件 |
| 26 | On-Page | 記事見出しへの質問形式（？付きH2/H3）導入 | WARN | P2 | 質問見出しなし 69/82本 |
| 27 | On-Page | 学習ガイドへの比較表（table）設置 | WARN | P2 | tableなし 60/82本 |
| 28 | On-Page | img alt 属性設定 | PASS | - | alt欠損 0件 |
| 29 | On-Page | img width/height 明示（CLS防止） | PASS | - | 未指定 0件 |
| 30 | On-Page | 画像最適化（WebP/SVG利用） | PASS | - | 非WebPあり 0件 |
| 31 | On-Page | OGPメタタグ完備 | PASS | - | 不足 0件 |
| 32 | On-Page | Twitter/X Card メタタグ完備 | PASS | - | 不足 0件 |
| 33 | Linking | 下層ページのパンくずHTML設置 | PASS | - | 未設置 0件 |
| 34 | Linking | 下層ページの BreadcrumbList JSON-LD | PASS | - | 未設置 0件 |
| 35 | Linking | 被リンク3本以上（孤立ページ防止） | WARN | P1 | 被リンク3未満 51件 |
| 36 | Linking | 発リンク3本以上（回遊導線確保） | PASS | - | 発リンク3未満 0件 |
| 37 | Linking | 相談CTAリンク（/contact/ または LINE）設置 | PASS | - | CTAなし 0件 |
| 38 | Linking | 学習ガイドの datePublished/dateModified 明示 | PASS | - | 日付なし 0/82本 |
| 39 | Linking | feed.xml（RSS/Atom）配信 | PASS | - | feed.xml あり |
| 40 | AIO | robots.txt での主要AIクローラ許可 | PASS | - | 未記載 0種 |
| 41 | AIO | llms.txt 設置 | PASS | - | 41786 chars |
| 42 | AIO | llms-full.txt（LLM向け全ページ要約集）設置 | PASS | - | 47158 chars |
| 43 | AIO | llms.txt の全ページ網羅率 | PASS | - | 未掲載 0/251ページ |
| 44 | AIO | FAQPage JSON-LD 展開率 | PASS | - | 実装 206/251ページ |
| 45 | AIO | 組織 sameAs（外部媒体・SNS・書籍・連載リンク） | PASS | - | sameAs 6件 |
| 46 | AIO | 講師 Person スキーマ（学歴・専門領域・sameAs） | PASS | - | alumniOf/knowsAbout=あり, sameAs=7件 |
| 47 | AIO | Course/Offer スキーマ（料金・提供形態） | PASS | - | 実装 6ページ |
| 48 | AIO | 記事冒頭の結論・要点ブロック（AI引用向け） | WARN | P2 | 冒頭要点なし 60/82本 |
| 49 | AIO | 権威性・実績ファクトの構造的明示（累計50人・連載等） | PASS | - | /about/ での確認結果 |
| 50 | MEO | NAP情報（住所・電話）のJSON-LD構造化 | PASS | - | PostalAddress & telephone あり |
| 51 | MEO | GeoCoordinates（緯度・経度）設定 | PASS | - | あり |
| 52 | MEO | openingHoursSpecification（営業時間）構造化 | PASS | - | あり |
| 53 | MEO | areaServed（日本全国・オンライン対応）構造化 | PASS | - | あり（49地域） |
| 54 | MEO | hasMap（GoogleマップURL）紐付け | PASS | - | あり |
| 55 | MEO | 全国47都道府県の地域別ページ網羅率 | PASS | - | 現在 47/47都道府県 (hokkaido, aomori, iwate, miyagi, akita, yamagata, fukushima, ibaraki, tochigi, gunma...) |
| 56 | MEO | 外部MEO/Googleマップ・口コミ導線リンク | PASS | - | サイト内にGoogleマップ/GBPリンクあり |
| 57 | AIO | llms-full.txt の必須セクション（料金・47都道府県・FAQ） | PASS | - | 47158 chars に主要情報あり |
| 58 | AIO | 全ページの EducationalOrganization 定義が同一 | PASS | - | 1種の定義 |
| 59 | MEO | 47都道府県ページの固有コンテンツ量（1,500字・見出し8以上） | PASS | - | 不足 0/47ページ |
| 60 | MEO | 47都道府県ページの被リンク3本以上 | PASS | - | 3本未満 0/47ページ |
| 61 | MEO | 都道府県ページのタイトル・見出しに地域名 | PASS | - | 地域名あり 47/47ページ |
| 62 | Technical | last-modified が未来日でない | PASS | - | 未来日 0件 |

## 直し方の目安

- P0 は build.py / tools/seo_guard_r17.py が検出しない種類の欠損が中心なので、構造化データと生成物（llms-full.txt・地域ページ）を先に埋める。
- P1 の多くはコンテンツ側（質問見出し・比較表・冒頭要約）の積み上げで、一度に全記事を直すより、検索流入のある記事から順に直すほうが費用対効果が高い。
- WARN は「無くても動くが、AI検索とMEOで差がつく」項目。四半期ごとの見直しで足りる。

