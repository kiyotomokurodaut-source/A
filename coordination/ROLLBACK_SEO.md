# 黒田塾サイト SEO 変更のロールバック手順

対象：`repos/A`（`kiyotomokurodaut-source/A` → https://kurodaschool.jp/）
最終更新：2026-11-27（第4弾の実装時）

公開は GitHub `main` への push で自動反映される。戻すときも同じ経路を使う。
**戻す前に、どのコミットまで戻すのかを必ず確認する**（Muse の SEO スプリントの
コミットを巻き込むと、向こうの改善が消える）。

---

## 0. まず確認する

```sh
cd repos/A
git pull --rebase            # リモートの最新を取り込む
git log --oneline -20        # 戻したいコミットを探す
git status                   # 未コミットの変更が無いことを確認
```

第4弾（Doc 1）のコミットは、件名に「第4弾」または「Doc 1」を含む。
複数コミットに分かれている場合は、**古い順に** revert する。

---

## 1. 第4弾をまとめて戻す（推奨）

```sh
# 例：直前のコミット1つを戻す
git revert --no-edit <commit-sha>

# 複数コミットをまとめて戻す（新しい順に指定する）
git revert --no-edit <newest-sha> <older-sha>

# 競合した場合
git status                   # 競合ファイルを確認
#   競合を手で直したら
git add <file> && git revert --continue
#   やめるときは
git revert --abort
```

戻したら、必ず検証してから push する。

```sh
python3 build.py --check
python3 tools/seo_guard_r17.py
python3 tools/validate_release_r23.py
python3 tools/seo_aio_meo_audit.py --quiet
```

すべて通ったら push。

```sh
git push origin main
```

push 後、ライブで確認する。

```sh
for u in / /about/ /pricing/ /facts.json /llms.txt /llms-full.txt /sitemap.xml /robots.txt; do
  printf '%s %s\n' "$(curl -s -o /dev/null -w '%{http_code}' https://kurodaschool.jp$u)" "$u"
done
```

---

## 2. 一部だけ戻す（ピンポイント）

全体を戻すと他の改善まで消えるため、原因が特定できている場合はファイル単位で戻す。

```sh
# 特定ファイルを、そのコミットの直前の状態に戻す
git checkout <commit-sha>~1 -- public/about/index.html

# 生成物は build.py で作り直す（手で直さない）
python3 build.py
```

| 戻したいもの | 対象 |
| --- | --- |
| /about/ の比較表・要点ボックス | `public/about/index.html`（`id="comparison"` の section と `summary-box`） |
| 構造化データ（Person / WebSite / Speakable） | `tools/site_entity_r24.py` を戻す → `python3 tools/entity_speakable_r26.py` で全ページ再適用 |
| robots メタの max-image-preview | `tools/robots_meta_r26.py` の変更を戻し、`git checkout <sha>~1 -- public` では広すぎるため個別に戻す |
| facts.json | `build.py` の `write_facts` と `facts_payload` を戻し、`public/facts.json` を削除 |
| Markdown版（.md） | `build.py` の `md_export_r26` 呼び出しを戻し、`public/**/*.md` を削除、`tools/md_link_r26.py` で入れた `<link rel="alternate">` を除去 |
| robots.txt の AIクローラ許可 | `build.py` の `AI_CRAWLERS` / `CRAWL_DELAY` を戻す |

生成物（`sitemap.xml` / `llms.txt` / `llms-full.txt` / `feed.xml` / `facts.json` / `*.md`）は
**手で編集しない**。`build.py` を直して再生成する。手で直すと次のビルドで消える。

---

## 3. IndexNow のキーファイルは消さない

`public/<32文字>.txt` は Bing 側のサイト所有確認に使っている。
ロールバックで消すと、以後の IndexNow 通知が 403 になる。
サイトを戻すときも、キーファイルと `tools/indexnow_submit.py` は残す。

---

## 4. 戻したあとの通知

```sh
python3 tools/indexnow_submit.py --limit 5     # 送信内容の確認（dry-run）
python3 tools/indexnow_submit.py --submit      # 全URLを再通知
```

IndexNow は「更新した」ことの通知なので、戻した場合も送ってよい。
Bing のインデックスは次回クロールで更新される（即時反映ではない）。

---

## 5. 触ってはいけないもの

- Muse の SEO スプリントのコミット（`coordination/status-seo.md` に記録がある）。
  戻すと title/description の改善や新規ページが消える。
- `public/legal/`（特定商取引法に基づく表記）と `public/privacy/`（プライバシーポリシー）の本文。
  法令・契約の表示なので、SEO 都合で書き換えない。
- 料金（`/pricing/` と `build.py` の `PRICING`）。金額を変えるときは本人の確認を取る。

---

## 6. 記録

ロールバックしたら `coordination/status-seo.md` に、
日時・戻したコミット・理由・検証結果・ライブ確認の結果を追記する。
