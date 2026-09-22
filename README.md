# 黒田塾サイト（kiyotomokuroda.pages.dev）

黒田塾の静的サイト一式と、SEO用の生成・検査スクリプト。

> **⚠️ `kiyotomokuroda.pages.dev` は、現時点でDNSが引けません。**
> 一方で公開中の内容は canonical・sitemap をすべてこのドメインに向けています。
> そのため**いま公開されているページは検索結果に出ません。**
> Cloudflare で Pages プロジェクト（名前は `kiyotomokuroda`）を作るのが最優先です。
> 手順と3ホストの整理は [SEO.md の第0章](SEO.md) にあります。

## 構成

```
public/          公開ディレクトリ（そのまま配信される）
  index.html     各ページは手書きのHTML。ここが内容の一次情報
  assets/        CSS・JS・画像（ファイル名にハッシュ付き＝1年キャッシュ）
  og/            ページ別のSNSシェアカード（生成物・固定名なので/assets/の外）
  sitemap.xml    ┐
  robots.txt     │ build.py が生成。直接編集しない
  llms.txt       │
  feed.xml       ┘
  _headers       HTTPヘッダ（Cloudflare Pages / Netlify 共通形式）
  _redirects     打ち間違い・旧URLからの301
build.py         生成ファイルの出力とSEO検査（標準ライブラリのみ）
tools/           開発時だけ使うスクリプト
bbs/             東大生向けの情報交換掲示板アプリ（このサイトとは独立）
netlify.toml     旧ホスト netlify.app を pages.dev へ301で送るための設定
SEO.md           SEOの診断結果・変更記録・所有者向けTODO
```

## 掲示板アプリ（`bbs/`）

`bbs/` は静的サイトとは別のアプリです。匿名の投稿（テキスト・画像）、フォロー、DM、
いいね、リポストがあり、R18 相当の画像はアップロード時に止まります。
`public/` の配信には関係しないので、Cloudflare Pages のビルドには含まれません。

```sh
pip install -r bbs/requirements.txt
python3 -m bbs.server --demo      # 動作確認用のデータ
python3 -m bbs.server             # http://127.0.0.1:8787/
python3 -m unittest discover -s bbs/tests -t .
```

詳しい仕様と、本番に出す前にやることは [bbs/README.md](bbs/README.md) にあります。

## デプロイ設定（Cloudflare Pages）

| 項目 | 値 |
| --- | --- |
| Production branch | `main` |
| Build command | `python3 build.py --check` |
| Build output directory | `public` |

ビルドコマンドは検査のためだけにあります。生成ファイルはコミット済みなので、
空にしても動きますが、その場合は回帰検査が働きません。

## 使い方

### ページを追加・編集したあと

```sh
python3 tools/normalize_seo.py   # head・構造化データ・ナビを統一（何度実行しても同じ結果）
python3 build.py --check         # 生成ファイルを更新し、SEO検査に通るか確認
```

`build.py --check` が失敗したら、その内容を直してから commit してください。
同じコマンドをデプロイ側が実行するので、失敗したままでは本番に出ません。

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

- **`public/` のHTMLが内容の一次情報です。** テンプレートエンジンはありません。
  HTMLを直接編集します。
- **`sitemap.xml` / `robots.txt` / `llms.txt` / `feed.xml` は編集しません。**
  `build.py` が上書きします。内容を変えたいときは `build.py` を変えます。
- **シェアカードを `/assets/` に移さないでください。** `/assets/*` は1年 immutable で
  キャッシュします。ハッシュ付きファイルだから成立する設定で、固定名のカードを
  そこに置くと、再生成しても古い画像が1年返り続けます。
- **ヘッダ規則に拡張子グロブ（`/*.webp` など）を使わないでください。**
  Cloudflare も Netlify もパス単位でマッチするため、確実に効きません。
- **料金・指導条件は本文が基準です。** 振替・解約・支払いなど公表していない条件を、
  確定した条件として書かないでください。
- **実績の書き方を変えないでください。** 「指導経験」と「合格実績」の区別は
  意図的なものです。理由は `/about/#editorial-policy` にあります。
- **ホストを変えるときは** `SITE` 定数（`build.py`、`tools/*.py`）と各ページの
  `canonical` / `og:url` を一括置換し、旧ホストから301を張ってください。
  301なしで切り替えると、積んだ評価がゼロに戻ります。
