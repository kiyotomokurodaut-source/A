# ほんごうねむり 公式サイト

VTuber「ほんごうねむり」（[@hongounemuri](https://x.com/hongounemuri)）の個人サイト一式。
同じリポジトリにある黒田塾のサイト（`/public`）とは**別のサイト**です。ドメインも
ビルドも分かれていて、互いに影響しません。

```
vtuber/
  site.json     サイトの内容。編集するのは基本ここだけ
  build.py      site.json から public/ を作る。標準ライブラリのみ
  assets/       CSS・JS・画像の原本（build.py がハッシュ名にして公開する）
  art/          元絵。ここから assets/img/ を作る
  tools/        画像とシェアカードの生成（Pillow が必要）
  public/       公開ディレクトリ。生成物だが、デプロイのためにコミットしている
```

## さわる前に

内容はすべて `site.json` にあります。HTMLを直接編集しないでください
（`build.py` が `public/` を作り直すときに消えます）。

```sh
# 1. site.json を編集する
# 2. 作り直して検査する
python3 build.py --check
# 3. ローカルで見る
cd public && python3 -m http.server 8765   # http://127.0.0.1:8765/
```

`build.py --check` は、タイトルや説明文の長さ、`<h1>` の数、canonical、OGP、
内部リンクの行き先、画像の `alt` と `width`/`height` を検査します。
落ちたまま公開すると直しづらいので、コミット前に必ず通してください。

## 公開前に埋めてほしいところ

`site.json` で `null` になっている項目は、**事実が確認できていないので空にしてあります。**
ビルドすると「注意」として一覧が出ます。ページ側では「近日公開」と表示され、
リンクは押せない状態になります。

| 項目 | 何を入れるか |
| --- | --- |
| `talent.birthday` / `height` | 誕生日・身長 |
| `talent.debut_date` | 初配信の日付（`2026-10-04` の形式） |
| `talent.fan_name` / `oshi_mark` | ファンネーム・推しマーク |
| `talent.credits[].name` | イラスト・モデリング・ロゴの担当者名 |
| `highlight.datetime` / `url` | 初配信の日時（`2026-10-04T21:00`）と配信URL |
| `links[].url` | YouTube・マシュマロ・BOOTH のURL |
| `contact.email` | お仕事用の連絡先 |

## 公開後に有効化するもの

次の2つは、**中身が決まるまで表示しない**作りにしてあります。
それらしい見本を出すと、ファンがその通りに動いてしまうためです。

### ファンアート等のタグ

`guidelines.tags` の3つを埋めると、ガイドラインのページに表が出ます。
空のあいだは「まだ決まっていません」と表示されます。

```json
"tags": { "fanart": "#ねむりあーと", "clip": "#ねむりきりぬき", "stream": "#ねむログ" }
```

### 週の配信スケジュール

`schedule.published` を `true` にし、`slots` を埋めると表が出ます。
`false` のあいだは「曜日と時間は準備中です」のカードだけが出ます。
`kind` は見た目の色で、`study` / `talk` / `game` / `off` が使えます。

```json
"published": true,
"slots": [
  { "day": "月", "time": null,    "title": "おやすみ",     "kind": "off" },
  { "day": "火", "time": "22:00", "title": "もくもく自習", "kind": "study" }
]
```

## 下書きのまま置いてあるもの

次のものは**こちらで用意した案**です。実際の設定と違っていたら差し替えてください。
表示はされますが、事実というより人物紹介の文章です。

- `talent.intro` / `likes` / `dislikes` / `design_notes` — キャラクターの紹介文。
  キービジュアルと「受験には受かった。朝には勝てない。」から書き起こした下書きです。
- `contents` — 配信の4つの枠。「やっていく予定」という書き方にしてあります。

`talent.name` は、キービジュアルの表記に合わせて**ひらがな**にしてあります。
漢字表記があるなら `site.json` の `name` を変えてください（`name_latin` も合わせて）。

## デプロイ（Cloudflare Pages）

黒田塾のサイトとは**別のプロジェクト**として作ります。同じリポジトリから
2つのプロジェクトを作れます。

| 項目 | 値 |
| --- | --- |
| プロジェクト名 | `hongounemuri` ← これが `hongounemuri.pages.dev` になります |
| Production branch | `main` |
| Root directory | `vtuber` |
| Build command | `python3 build.py --check` |
| Build output directory | `public` |

**プロジェクト名は `hongounemuri` にしてください。** `site.json` の `site.host`、
各ページの canonical、OGP、sitemap、llms.txt がすべてこのホスト名を指しています。
別の名前にする場合は `site.host` を直して `python3 build.py` を実行し直してください。

生成物はコミット済みなので、ビルドコマンドを空にしても配信はできます。
その場合は回帰検査が働きません。

公開後にホストを変えるときは、旧ホストから301を張ってください。
301なしで切り替えると、積んだ評価がゼロに戻ります。

## 画像を作り直す

元絵を差し替えたときだけ必要です。

```sh
pip install pillow
python3 tools/make_images.py      # art/ から assets/img/ を作る
python3 tools/make_og_cards.py    # public/og/ のシェアカードを作る
python3 build.py --check
```

シェアカードの日本語はIPAゴシック
（`/usr/share/fonts/opentype/ipafont-gothic/`）で描いています。

## 決めごと

- **シェアカードを `/assets/` に置かないでください。** `/assets/*` は1年 immutable で
  キャッシュします。ハッシュ付きの名前だから成立する設定で、固定名のカードを
  そこに置くと、作り直しても古い画像が1年返り続けます。
- **「バーチャル東京大学」はキャラクターの設定です。** 実在する大学の卒業資格や
  学歴として読める書き方にしないでください。プロフィールとFAQに注記があります。
  `llms.txt` にも同じ断りを入れています。
- **JavaScriptは補助だけです。** 切っても全ページ読めて、リンクも全部動きます。
  スクロール表示は `prefers-reduced-motion` を見て止まります。
