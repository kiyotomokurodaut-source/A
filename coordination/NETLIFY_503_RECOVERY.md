# 復旧手順：Netlify「usage_exceeded」で全ページ 503（2026-11-27）

## 症状

```
$ curl -sI https://kurodaschool.jp/
HTTP/2 503
server: Netlify

$ curl -s https://kurodaschool.jp/
{"error":"usage_exceeded","message":"Usage exceeded","request_id":"..."}
```

- `https://kiyotomokuroda.netlify.app/` も同じ 503 → サイト単位ではなく **Netlify アカウントの利用上限**。
- DNS は Netlify DNS（`dns1.p01.nsone.net`）→ 52.52.192.191 / 13.52.188.95。
- 2026-11-27 18:12 JST までは 200、18:16 頃から 503。

## 原因の確認（本人のアカウント）

1. https://app.netlify.com/ にログイン
2. チーム（`kiyotomokuroda` のアカウント）→ **Usage**（または Billing）
3. どの上限かを確認する
   - **Bandwidth**（月間転送量）: 無料枠を超えると 503。月末または請求サイクルでリセット
   - **Build minutes**: ビルド失敗が続く場合はこちら
   - **Forms / Functions**: このサイトは未使用のため通常は無関係

## 復旧の選択肢

### A. Netlify のまま（最短）

- Usage 画面から **帯域の追加（Add bandwidth）** またはプラン変更。
- 請求サイクルのリセット待ちでも復旧するが、日付までは保証されない。
- 復旧したら下の「復旧後の確認」を実行。

### B. Cloudflare Pages へ移す（恒久的な帯域対策）

このリポジトリは Cloudflare Pages でもそのまま動く（`public/_headers`・`public/_redirects` を使用）。

1. Cloudflare ダッシュボード → Workers & Pages → Create → Pages → GitHub の `kiyotomokurodaut-source/A` を接続
2. 設定
   - Production branch: `main`
   - Build command: `python3 build.py --check`
   - Build output directory: `public`
   - 環境変数: 不要（Python は標準ライブラリのみ使用）
3. まず `*.pages.dev` で表示確認（この時点では DNS を変えない）
4. 問題なければ `kurodaschool.jp` を Pages のカスタムドメインに追加し、
   Cloudflare DNS で CNAME/ALIAS を Pages へ向ける
5. **旧 Netlify からの 301** は `netlify.toml` の設定を使う（ホストを分けたまま残す場合）

注意:
- DNS を切り替える前に Pages の表示確認を済ませる（切り替え中のダウンを避ける）。
- Search Console のプロパティはドメインが同じなら継続。ホストが変わっても canonical は `https://kurodaschool.jp/` のままでよい。
- ビルドは `build.py --check` が失敗するとデプロイを止める（意図した安全装置）。

## 復旧後の確認

```sh
cd repos/A
python3 build.py --check              # exit 0
python3 tools/seo_guard_r17.py        # errors 0
python3 tools/validate_release_r23.py # 通過
python3 tools/seo_aio_meo_audit.py --quiet  # PASS 67 / WARN 0 / FAIL 0

for u in / /facts.json /llms.txt /llms-full.txt /sitemap.xml /robots.txt \
         /about/ /about/index.md /index.md; do
  printf '%s %s\n' "$(curl -s -o /dev/null -w '%{http_code}' https://kurodaschool.jp$u)" "$u"
done

# AIクローラのUAで robots.txt とトップが 200 か
for ua in GPTBot OAI-SearchBot ChatGPT-User PerplexityBot Perplexity-User \
          ClaudeBot Claude-SearchBot Claude-User Google-Extended \
          Applebot Applebot-Extended Bingbot; do
  printf '%s %s\n' "$ua" "$(curl -s -o /dev/null -w '%{http_code}' -A "$ua" https://kurodaschool.jp/)"
done

# 復旧後に更新を再通知（停止中にクロールされた分の取り直し）
python3 tools/indexnow_submit.py          # dry-run で確認
python3 tools/indexnow_submit.py --submit
```

## SEO への影響と注意

- 503 は一時的な障害として扱われるが、長引くとクロール頻度が下がる。復旧を優先する。
- 停止中に IndexNow を再送しても意味がない（クロール先が 503 のため）。**復旧後に送る。**
- 復旧後に、Search Console の「ページ」レポートで 5xx の増加が戻るかを見る。
- 再デプロイを連打しない（Build minutes をさらに消費する）。
