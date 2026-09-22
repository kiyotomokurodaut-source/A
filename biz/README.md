# ホームページ制作の飛び込み営業：一式

東京の「ホームページがない会社」にサイトを作って売る事業の、
**見込み客リスト・制作の仕組み・営業の道具**をまとめたものです。

既存の黒田塾サイト（リポジトリのルート）とは独立しています。
ただし中身は地続きで、`build.py` と `SEO.md` でやったこと
—— 構造化データ、canonical、配信ヘッダ、生成物の回帰検査 ——
をそのまま量産用に組み直したものが `kit/` です。

```
biz/
  README.md            ← いまここ
  PRICING.md           3万円という値づけを数字で検証する
  BUSINESS-MODELS.md   他のビジネスモデルを全部出して順位をつける
  prospecting/         見込み客を集める
    harvest_pbf.py       日本全国を一括で（PBFをローカル処理・本命）
    harvest_osm.py       市区町村を指定して（Overpass・小回りが利く）
    harvest_places.py    Google Places API から（最も正確・要APIキー）
    make_callsheet.py    その日の架電リストに切り出す
  outreach/            メールを送る
    find_email_targets.py  サイトを持つ会社を訪問し、アドレスと「古さ」を調べる
    make_drafts.py         Gmailの下書きを作る（Apps Script経由）
    sender.json            送信者情報（法律上の必須項目）
  kit/                 サイトを作る
    build_site.py        設定JSON → SEO済みの静的サイト＋検査
    check_render.py      実ブラウザで表示崩れを検査
    clients/*.json       クライアントごとの設定
    dist/<slug>/         生成物（そのまま Cloudflare Pages に置ける）
  sales/               売る
    phone-script.md      電話台本
    email-templates.md   メール・FAXの文面
    hearing-sheet.md     15分で必要事項を聞き切る
    contract-template.md 注文書・契約書・保守覚書
    legal.md             どこまでやってよいか
  data/                生成される（git管理外）
```

---

## 30秒で試す

```sh
# 1. サンプルのサイトを生成して、2種類の検査にかける
python3 kit/build_site.py kit/clients/sample-koumuten.json --check
pip install playwright        # 表示検査だけ必要
python3 kit/check_render.py kit/dist/sample-koumuten

# 2. 全国の見込み客リストを作る（PBFを落として一括処理）
pip install osmium
curl -L -o data/pbf/japan-latest.osm.pbf \
     https://download.openstreetmap.fr/extracts/asia/japan-latest.osm.pbf
python3 prospecting/harvest_pbf.py data/pbf/japan-latest.osm.pbf

# 3. 今日かける18件を切り出す
python3 prospecting/make_callsheet.py --day 1 --n 18
```

### 電話とメール、どちらで行くか

**「サイトがない会社」には、メールは届きません。** 0.9%しかアドレスが取れず、
それは採取の不備ではなく定義上そうなります（サイトがない＝どこにも公表していない）。
特定電子メール法が同意なしの送信を認めるのは**公表されたアドレス**だけなので、
この層は電話・FAX・郵送しか手段がありません。

**メールで行くなら、狙う相手を「サイトはあるが古い会社」に変えてください。**
公表アドレスがあり、一度払った予算があり、
「御社のサイト、スマホで崩れています」という**確かめられる事実**から入れます。
手順は `outreach/README.md` にあります。

---

## リストの現状

`harvest_pbf.py` で日本全国を一括処理した結果です（2026-09-22時点のOSMデータ）。

| | |
| --- | --- |
| 電話番号つきの事業所（チェーン・分類不能を除く） | 36,000件超 |
| **うちウェブサイトなし**（電話・FAX・郵送向け） | **20,823件** |
| **うちウェブサイトあり**（メール向け） | **14,745件** |

サイトなし20,823件の業種内訳（上位）:

| 件数 | 業種 | 使えるか |
| --- | --- | --- |
| 10,132 | 飲食 | 母数は最大。ただし単価が低く、食べログで足りていると言われる |
| 1,853 | 美容・理容・エステ | |
| 1,498 | 食品小売 | |
| 1,281 | クリニック | 医療広告ガイドラインの制約が大きい |
| 991 | 歯科 | 同上 |
| 962 | 一般企業・専門事務所 | **採用ページの需要が大きい**（`BUSINESS-MODELS.md` A-5） |
| 793 | 薬局・調剤 | |
| **662** | **自動車・バイク整備** | **筋がいい。検索で探される業種** |
| **392** | **整体・接骨・鍼灸** | 広告規制あり。要注意 |
| **322** | **建設・職人（工務店ほか）** | **最も筋がいい** |
| **317** | **不動産** | **筋がいい** |
| 221 | 製造・町工場 | |
| **156** | **塾・教室・習い事** | `BUSINESS-MODELS.md` B-1 の本命 |
| **97** | **士業・コンサル** | **筋がいい** |

都道府県の上位は 宮城県4,683／東京都2,993／神奈川県1,600／大阪府1,290／岡山県1,176。
**宮城県が東京を上回るのはOSM側の事情**です（震災後の大規模なマッピングで
仙台周辺の登録密度が全国でも突出している）。データは本物ですが、
「宮城に需要が集中している」という意味ではありません。

### なぜ全国一括に切り替えたか

最初は Overpass API に市区町村を1つずつ問い合わせていました。
東京33市区は通りましたが、**全国111市区では2時間で2件しか進まず**、
ほとんどが504で返ってきました。公共のサーバに全国分を投げるのは、
そもそもそういう使い方ではありません。

Geofabrik が同じデータをファイルで配っているので、**一度落としてローカルで処理**
する方式に変えました。全国分の抽出が**2分弱**で終わり、
手で書いた市名リストでは漏れる町まで入ります。

```sh
pip install osmium
curl -L -o data/pbf/japan-latest.osm.pbf \
     https://download.openstreetmap.fr/extracts/asia/japan-latest.osm.pbf
python3 prospecting/harvest_pbf.py data/pbf/japan-latest.osm.pbf
```

処理は C++ 側のタグフィルタで絞ってから Python に渡しています。
`SimpleHandler` で1億超のノードすべてに Python のコールバックを回すと終わりません。

### OSMの限界（変わっていません）

OSMは**店舗は熱心に登録されるが、看板のない事務所や作業場は登録されない**
という偏りがあります。全国でも工務店322件・士業97件で、実数には遠く及びません。
より網羅的にやるなら、次の `harvest_places.py` を使ってください。

### だから `harvest_places.py` があります

Google Places API (New) には `websiteUri` フィールドがあり、
**「サイトがない」がデータとして確定します**（OSMのように「誰も登録していないだけ」ではない）。
そして工務店も税理士事務所も全部載っています。

費用は無料枠に収まります。

- `websiteUri` と電話番号は **Enterprise SKU**（[Google のフィールド階層](https://developers.google.com/maps/documentation/places/web-service/data-fields)）
- Enterprise は **月1,000コール無料**（[料金ページ](https://mapsplatform.google.com/pricing/)）
- 1コールで最大20件返るので、**月2万件まで無料**
- 23区 × 30業種を全部回して **690コール**（`--dry-run` で確認できます）

```sh
export GOOGLE_PLACES_KEY=...        # Places API (New) を有効化して発行
python3 prospecting/harvest_places.py --all --dry-run   # コール数の確認
python3 prospecting/harvest_places.py --all
```

`make_callsheet.py` は両方のCSVを読んで電話番号で重複を除くので、
**OSM版で始めて、あとからGoogle版を足す**という進め方ができます。
同じ番号が両方にある場合はGoogle側を採用します（「サイトがない」の確度が高いため）。

さらに `harvest_places.py` は、**公式サイトがInstagramやペライチしかない会社も拾います。**
これは見込み客として優秀です。すでに「見つけてほしい」と思っていて、
借り物のページの限界にぶつかっている相手だからです。

---

## 制作の仕組み（`kit/`）

`clients/<slug>.json` を1つ書くと、**8ページの静的サイトが出ます。**

生成されるすべてのページが持つもの：

- **LocalBusiness の構造化データ**（NAP・営業時間・対応エリア・地理座標・サービス一覧）
  —— 地域の商売でいちばん効くのはこれです。Googleビジネスプロフィールと結びつきます
- ページごとに固有の `title` / `description`（**日本語のSERP表示幅に合わせた長さで自動調整**）
- `canonical`・`BreadcrumbList`・`FAQPage`・`Service` の各構造化データ
- `sitemap.xml` / `robots.txt` / `favicon.svg` / `_headers` / `_redirects`
- ウェブフォントなし・JSフレームワークなし・CSSは埋め込み（**描画をブロックする通信がゼロ**）
- スマホでは画面下に固定の発信バー（この手のサイトの成約は**電話**で起きるため）

そして**2つの検査が通らないと出せません。**

```sh
python3 kit/build_site.py kit/clients/foo.json --check   # HTMLの検査
python3 kit/check_render.py kit/dist/foo                 # 実ブラウザでの検査
```

| `build_site.py --check` | `check_render.py` |
| --- | --- |
| title・description の長さと重複 | 横スクロールの発生（320/390/768/1280px） |
| canonical の有無とホストの一致 | タップ領域（WCAG 2.2 AA の24px、主要CTAは44px） |
| h1が1つ・見出しレベルの飛び | 12px未満の文字 |
| JSON-LD が壊れていないか | コンソールエラー |
| 内部リンク切れ・孤立ページ | |
| 画像の width/height・alt | |
| 電話リンクの存在 | |

**canonicalのホスト一致を検査する理由は `../SEO.md` の第0章にあります。**
canonicalが存在しないホストを指していたせいで、
公開済みのページが丸ごとインデックスから外れていた、という実例がこのリポジトリにあります。
同じ事故を量産しないための検査です。

---

## 読む順番

1. **`PRICING.md`** —— 3万円のままだと何が起きるか。**先にこれを読んでください**
2. **`BUSINESS-MODELS.md`** —— 他の型。とくに「A-1 補助金」は初日から使えます
3. `sales/legal.md` —— 電話とメールでやってよい線
4. `sales/phone-script.md` —— 台本
5. `sales/hearing-sheet.md` —— 受注後、15分で聞き切る

---

## 3行でまとめると

- **リストは取れました**（2,751件）。ただし**高単価の業種はOSMに載っていない**ので、
  本気でやるなら `harvest_places.py` に無料のAPIキーを挿してください
- **制作はほぼ自動化できました。**限界費用がほぼゼロなので、
  **電話の前にサイトを作ってしまう**のが最大の武器になります
- **3万円の売り切りは、労働としては成立しますが事業としては積み上がりません。**
  補助金（実質負担は同じで単価3.3倍）と月額（3年LTVが4.6倍）を、
  **最初から**メニューに入れてください
