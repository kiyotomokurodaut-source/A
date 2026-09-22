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
    harvest_osm.py       OpenStreetMap から（無料・鍵不要）
    harvest_places.py    Google Places API から（本命・要APIキー）
    make_callsheet.py    その日の架電リストに切り出す
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

# 2. 見込み客リストを作る（初回は Overpass から取得するので20〜30分）
python3 prospecting/harvest_osm.py

# 3. 今日かける18件を切り出す
python3 prospecting/make_callsheet.py --day 1 --n 18
```

---

## リストの現状と、正直な限界

`harvest_osm.py` を東京都全域（23区＋多摩10市）で走らせた結果です。

| | |
| --- | --- |
| 「電話番号あり・ウェブサイトなし」の総数 | **2,751件** |
| うち電話番号が確実なもの | **2,553件**（残り198件は `メモ` に「要確認」と入れ、順位を下げてあります） |

業種の内訳：

| 件数 | 業種 | 使えるか |
| --- | --- | --- |
| 1,337 | 飲食 | 母数は最大。ただし単価が低く、食べログで足りていると言われる |
| 250 | 歯科 | 医療広告ガイドラインの制約が大きい |
| 226 | 美容・理容・エステ | |
| 225 | クリニック | 同上 |
| 151 | 専門小売 | |
| 128 | 食品小売 | |
| 97 | 薬局・調剤 | |
| **76** | **整体・接骨・鍼灸** | 広告規制あり。要注意 |
| **54** | **不動産** | **筋がいい** |
| 34 | 動物病院 | |
| 29 | クリーニング | |
| 26 | 花・造園 | |
| 20 | 一般企業・専門事務所 | 採用ページの需要が大きい |
| **17** | **建設・職人** | **最も筋がいい。しかし17件しかない** |
| **12** | **士業・コンサル** | **筋がいい。しかし12件しかない** |
| 12 | スポーツ・ジム | |
| 11 | 自動車・バイク整備 | |
| 10 | 塾・教室・習い事 | `BUSINESS-MODELS.md` B-1 の本命だが、OSMには10件しかない |
| ほか | 食品製造9／葬祭7／衣料修理5／印刷4／運送3 ほか | |

### ここが問題です

**OSMには、東京の工務店も士業も、ほとんど載っていません。**

東京全域で「電話あり・サイトなし」のOSM要素は**5,115件**しかありません。
そのうち屋号に「工務店」を含むものは**2件**。
建設関係は分類しなおしても**17件**、士業は**12件**です。
東京には工務店が数千社、税理士事務所が数千あることを思えば、桁が2つ足りません。

理由ははっきりしています。
**店舗（飲食・美容・歯科）は通りがかりの人が登録しますが、
看板を出していない事務所や作業場は誰も登録しない**からです。

つまり、`PRICING.md` が「単価を上げられる」と結論した業種
（工務店・士業・不動産）が、**このリストにはほぼ入っていません。**
逆に、いちばん多い飲食1,337件は、いちばん売りにくい相手です。

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
