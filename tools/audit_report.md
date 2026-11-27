# 黒田塾 SEO / AIO / MEO 診断レポート

- 実行日: 2026-11-27
- 対象: 251ページ（総HTML 252） / 診断項目 67（うち従来56観点）
- 結果（56観点）: PASS 56 / WARN 0 / FAIL 0
- 結果（全体）: PASS 67 / WARN 0 / FAIL 0

優先度は P0（FAIL: 検索・AI検索への流入に直結）／ P1（WARN: 主要な改善余地）／ P2（WARN: 望ましい改善）です。

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
| 26 | On-Page | 記事見出しへの質問形式（？付きH2/H3）導入 | PASS | - | 質問見出しなし 0/82本 |
| 27 | On-Page | 学習ガイドへの比較表（table）設置 | PASS | - | tableなし 0/82本 |
| 28 | On-Page | img alt 属性設定 | PASS | - | alt欠損 0件 |
| 29 | On-Page | img width/height 明示（CLS防止） | PASS | - | 未指定 0件 |
| 30 | On-Page | 画像最適化（WebP/SVG利用） | PASS | - | 非WebPあり 0件 |
| 31 | On-Page | OGPメタタグ完備 | PASS | - | 不足 0件 |
| 32 | On-Page | Twitter/X Card メタタグ完備 | PASS | - | 不足 0件 |
| 33 | Linking | 下層ページのパンくずHTML設置 | PASS | - | 未設置 0件 |
| 34 | Linking | 下層ページの BreadcrumbList JSON-LD | PASS | - | 未設置 0件 |
| 35 | Linking | 被リンク3本以上（孤立ページ防止） | PASS | - | 被リンク3未満 0件 |
| 36 | Linking | 発リンク3本以上（回遊導線確保） | PASS | - | 発リンク3未満 0件 |
| 37 | Linking | 相談CTAリンク（/contact/ または LINE）設置 | PASS | - | CTAなし 0件 |
| 38 | Linking | 学習ガイドの datePublished/dateModified 明示 | PASS | - | 日付なし 0/82本 |
| 39 | Linking | feed.xml（RSS/Atom）配信 | PASS | - | feed.xml あり |
| 40 | AIO | robots.txt での主要AIクローラ許可 | PASS | - | 未記載 0種 |
| 41 | AIO | llms.txt 設置 | PASS | - | 42194 chars |
| 42 | AIO | llms-full.txt（LLM向け全ページ要約集）設置 | PASS | - | 49029 chars |
| 43 | AIO | llms.txt の全ページ網羅率 | PASS | - | 未掲載 0/251ページ |
| 44 | AIO | FAQPage JSON-LD 展開率 | PASS | - | 実装 226/251ページ |
| 45 | AIO | 組織 sameAs（外部媒体・SNS・書籍・連載リンク） | PASS | - | sameAs 6件 |
| 46 | AIO | 講師 Person スキーマ（学歴・専門領域・sameAs） | PASS | - | alumniOf/knowsAbout=あり, sameAs=8件 |
| 47 | AIO | Course/Offer スキーマ（料金・提供形態） | PASS | - | 実装 6ページ |
| 48 | AIO | 記事冒頭の結論・要点ブロック（AI引用向け） | PASS | - | 冒頭要点なし 0/82本 |
| 49 | AIO | 権威性・実績ファクトの構造的明示（累計50人・連載等） | PASS | - | /about/ での確認結果 |
| 50 | MEO | 教室の詳細住所・電話を構造化データに載せない（オンライン専業） | PASS | - | 住所・電話は非掲載（方針どおり） |
| 51 | MEO | GeoCoordinates（教室の座標）を載せない（オンライン専業） | PASS | - | 非掲載（方針どおり） |
| 52 | MEO | openingHoursSpecification（営業時間）構造化 | PASS | - | あり |
| 53 | MEO | areaServed（日本全国・オンライン対応）構造化 | PASS | - | あり（48地域） |
| 54 | MEO | hasMap（GoogleマップURL）を載せない（オンライン専業） | PASS | - | 非掲載（方針どおり） |
| 55 | MEO | 全国47都道府県の地域別ページ網羅率 | PASS | - | 現在 47/47都道府県 (hokkaido, aomori, iwate, miyagi, akita, yamagata, fukushima, ibaraki, tochigi, gunma...) |
| 56 | MEO | 地図・GBPリンクに頼らず、外部サイテーションで信頼を補う | PASS | - | 地図リンクなし・sameAs 6件 |
| 57 | AIO | llms-full.txt の必須セクション（料金・47都道府県・FAQ） | PASS | - | 49029 chars に主要情報あり |
| 58 | AIO | 全ページの EducationalOrganization 定義が同一 | PASS | - | 1種の定義 |
| 59 | MEO | 47都道府県ページの固有コンテンツ量（1,500字・見出し8以上） | PASS | - | 不足 0/47ページ |
| 60 | MEO | 47都道府県ページの被リンク3本以上 | PASS | - | 3本未満 0/47ページ |
| 61 | MEO | 都道府県ページのタイトル・見出しに地域名 | PASS | - | 地域名あり 47/47ページ |
| 62 | Technical | last-modified が未来日でない | PASS | - | 未来日 0件 |
| 63 | AIO | facts.json（AI向け一次情報のJSON） | PASS | - | 項目 22・料金5プラン |
| 64 | AIO | 全ページの SpeakableSpecification（h1・要点ボックス） | PASS | - | 未実装 0/251件 |
| 65 | AIO | 全ページの Person / WebSite 定義が同一 | PASS | - | Person 1種・WebSite 1種 |
| 66 | Technical | IndexNow キーファイル（32文字・中身一致） | PASS | - | /48e6c2249edd47e7a2229c425cab62c5.txt |
| 67 | AIO | 各ページのMarkdown版（.md）と head の alternate リンク | PASS | - | 未整備 0/251件 |

## 直し方の目安

- P0 は build.py / tools/seo_guard_r17.py が検出しない種類の欠損が中心なので、構造化データと生成物（llms-full.txt・地域ページ）を先に埋める。
- P1 の多くはコンテンツ側（質問見出し・比較表・冒頭要約）の積み上げで、一度に全記事を直すより、検索流入のある記事から順に直すほうが費用対効果が高い。
- WARN は「無くても動くが、AI検索とMEOで差がつく」項目。四半期ごとの見直しで足りる。

