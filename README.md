# 黒田塾サイト（kiyotomokuroda.netlify.app）

<https://kiyotomokuroda.netlify.app/> の静的サイト一式と、SEO用の生成・検査スクリプト。

> **注意：このリポジトリは、調査時点では本番の Netlify サイトに接続されていません。**
> push しただけでは本番に反映されません。接続手順と前提の確認事項は
> [SEO.md の冒頭](SEO.md#0-先に読んでほしいこのリポジトリは本番に繋がっていません) を読んでください。

## 構成

```
public/          公開ディレクトリ（そのまま配信される）
  index.html     各ページは手書きのHTML。ここが内容の一次情報
  assets/        CSS・JS・画像（ファイル名にハッシュ付き＝1年キャッシュ）
  assets/og/     ページ別のSNSシェアカード（生成物）
  sitemap.xml    ┐
  robots.txt     │ build.py が生成。直接編集しない
  llms.txt       │
  feed.xml       ┘
  _redirects     打ち間違いURLの301
build.py         生成ファイルの出力とSEO検査（標準ライブラリのみ）
tools/           開発時だけ使うスクリプト
netlify.toml     publishディレクトリ、ビルドコマンド、HTTPヘッダ
SEO.md           SEOの診断結果・変更記録・所有者向けTODO
```

## 使い方

### ページを追加・編集したあと

```sh
python3 tools/normalize_seo.py   # head・構造化データ・ナビを統一（何度実行しても同じ結果）
python3 build.py --check         # 生成ファイルを更新し、SEO検査に通るか確認
```

`build.py --check` が失敗したら、その内容を直してから commit してください。
同じコマンドを Netlify のビルドが実行するので、失敗したままでは本番に出ません。

新しいページを追加したときは、あわせて次をやります。

1. `tools/normalize_seo.py` の `LASTMOD` に URL と日付を追加。
2. `tools/make_og_cards.py` の `CARDS` にシェアカードの文面を追加し、
   `python3 tools/make_og_cards.py` を実行。
3. どこか既存のページからリンクする（孤立ページは検査で落ちます）。

### ローカルで見る

```sh
cd public && python3 -m http.server 8765   # http://127.0.0.1:8765/
```

### 開発用の依存

`build.py` は標準ライブラリだけで動きます（デプロイを pip に依存させないため）。
`tools/` の一部はライブラリが必要です。

```sh
pip install -r requirements-dev.txt   # beautifulsoup4, lxml
pip install pillow                    # シェアカードの生成に必要
```

シェアカードの生成には日本語フォント（IPAゴシック、
`/usr/share/fonts/opentype/ipafont-gothic/`）を使います。

## 編集するときの約束

- **`public/` のHTMLが内容の一次情報です。** ページを生成するテンプレートエンジンは
  ありません。HTMLを直接編集します。
- **`sitemap.xml` / `robots.txt` / `llms.txt` / `feed.xml` は編集しません。**
  `build.py` が上書きします。内容を変えたいときは `build.py` を変えます。
- **料金・指導条件は本文が基準です。** 振替・解約・支払いなど公表していない条件を、
  確定した条件として書かないでください（既存ページがその方針で書かれています）。
- **実績の書き方を変えないでください。** 「指導経験」と「合格実績」の区別は
  意図的なものです。理由は `public/cases/index.html` の「事例の書き方について」と
  `/about/#editorial-policy` にあります。
