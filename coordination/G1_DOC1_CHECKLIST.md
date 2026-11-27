# Doc 1 / Doc 1-L 受け入れ基準チェックリスト（G1 提出資料）

作成：2026-11-27（第4弾の完了時、Pickle）
対象：`repos/A` / https://kurodaschool.jp/
実装コミット：`05af98c`（記録追記 `4740044`）

判定は「充足」＝実装とライブ確認の両方が済んでいるもの、「部分充足」＝仕組みは用意したが
実測・設定が残るもの、「未充足」＝今回の作業範囲外または本人の操作が必要なもの。

## Doc 1（1-1〜1-8）

| 項目 | 受け入れ基準 | 状態 | 根拠・備考 |
| --- | --- | --- | --- |
| 1-1 robots.txt 強化 | GPTBot / OAI-SearchBot / ChatGPT-User / PerplexityBot / Perplexity-User / ClaudeBot / Claude-SearchBot / Claude-User / Google-Extended / Applebot / Applebot-Extended を Allow: /、Bingbot は Crawl-delay: 1、Sitemap 記載 | 充足 | `build.py` の `AI_CRAWLERS` / `CRAWL_DELAY`。ライブ `/robots.txt` に12種すべて記載。12種のUAで robots.txt と `/` が HTTP 200（2026-11-27 実測） |
| 1-2 IndexNow | 32桁hexキー、`/{key}.txt` が 200、全251 URL を api.indexnow.org と bing.com/indexnow へ送信し 200/202、差分送信用ツール | 充足 | キー `48e6c2249edd47e7a2229c425cab62c5`。`/48e6…t5.txt` 200。251 URL 送信 → api.indexnow.org **200**、www.bing.com/indexnow **200**。`tools/indexnow_submit.py`（既定 dry-run、`--submit`、`--urls`） |
| 1-3 静的HTML出力の検証 | build.py の初期HTMLに本文・H2・表・FAQが含まれることを任意3ページで curl 検証 | 充足 | `/`（h2 15・table 1・FAQ文言）、`/pricing/`（h2 8・table 1・FAQ）、学習ガイド1本（h2 14・table 1・FAQ）。いずれも JS 実行前のHTMLで確認 |
| 1-4 キャッシュヘッダ | `_headers` で Cache-Control を設定・確認 | 充足 | `_headers` に `/facts.json`（application/json）、`/llms-full.txt`、`/*.md`（text/markdown）を追加。ライブで `Cache-Control: must-revalidate` と各 Content-Type を確認 |
| 1-5 配信形式・MIME | JSON / Markdown / テキストが正しい Content-Type で返る | 充足 | `/facts.json` = application/json、`/about/index.md` = text/markdown; charset=UTF-8、`/llms-full.txt` = text/plain |
| 1-6 JSON-LD 整合 | Person（黒田清友）/ WebSite / SpeakableSpecification / EducationalOrganization を全ページで整合 | 充足 | `site_entity_r24.py` を拡張し `entity_speakable_r26.py` で251ページに同一適用。診断 #58（組織同一）・#64（Speakable）・#65（Person/WebSite同一）すべて PASS。SearchAction は URL で結果を返す検索が無いため付けず、`hasPart` で検索起点（学習ガイド絞り込み・サイトマップ・FAQ）を示す |
| 1-7 LLM向け配信 | llms.txt / llms-full.txt / facts.json に加え、各ページ本文の `.md` を生成し、head に alternate リンク。ライブ200 | 充足（Content Negotiation を除く） | `tools/md_export_r26.py` が251本の `index.md` を生成（build.py から毎ビルド）。`tools/md_link_r26.py` が head に `<link rel="alternate" type="text/markdown">`。`/index.md`・`/about/index.md`・`/pricing/index.md`・`/specialty/hokkaido/index.md` などライブ200。Accept による自動切替は未設定 |
| 1-8 計測基盤 | 50KW プロンプトバッテリー雛形（chatgpt-search / perplexity / google-ai-overview / copilot）、ロールバック手順、受け入れチェックリスト | 部分充足 | `seo-audit/prompt_battery_50kw.csv`（50KW×4エンジン＝200行、測定列は空）を作成。`coordination/ROLLBACK_SEO.md` を作成。本ファイルがチェックリスト。各エンジンの実測は画面操作が必要なため未実施 |

## Doc 1-L（正統版・Google Search Essentials 準拠）での追加確認

| 項目 | 状態 | 根拠 |
| --- | --- | --- |
| robots.txt に Claude-User を含む12種 | 充足 | ライブ `/robots.txt` に記載、UA 200 |
| 全ページの robots メタに `max-image-preview:large` | 充足 | `tools/robots_meta_r26.py` で noindex 以外の251ページに付与。`build.py` の検査でも必須化（欠落はビルド失敗） |
| sitemap の lastmod が実更新日を反映 | 充足 | 251 URL・lastmod 7種類（2026-11-27: 149 / 11-24: 89 / 11-18: 3 / 10-31: 1 / 10-04: 7 / 09-26: 1 / 09-21: 1）。一律の当日付与はしていない。正本は各ページの `meta last-modified` で、`build.py` がそのまま出力 |
| 虚偽マークアップ・隠しテキスト・クローキングなし | 充足 | 比較表は一般的な形態差と自社仕様のみ。Review/AggregateRating は実在しないため不使用。UA・地域による出し分けなし |

## 検証コマンドの結果（2026-11-27）

```
python3 build.py --check              → exit 0（251 URL / 251 markdown）
python3 tools/seo_guard_r17.py        → errors 0
python3 tools/validate_release_r23.py → 252 HTML pages 通過
python3 tools/seo_aio_meo_audit.py    → 67観点 PASS 67 / WARN 0 / FAIL 0
                                        （従来56観点も PASS 56 / WARN 0 / FAIL 0）
```

## 残る作業（G1 以降）

1. Google Search Console / Bing Webmaster Tools の所有権確認（本人アカウントの確認トークンが必要）。
2. プロンプトバッテリーの実測（4エンジン × 50KW）。
3. Apple Business Connect のブランド情報、外部サイテーション（エキテン・塾ナビ等）。
