# 東大理系数学 完全マスター（鉄緑風プリント・非公式）

- `print.pdf` … 完成版（JIS B5・92ページ・全43講＋導入講）
- `print.tex` … LuaLaTeX のソース（1ファイル完結）
- `preview-*.png` … 表紙と本文ページの見本

販売用教材なので `public/`（サイトの公開ディレクトリ）には置いていない。サイトに置くとそのまま無料で配布されてしまう。

## 組み方

```sh
lualatex -interaction=nonstopmode print.tex   # 2回実行する（目次のページ番号と柱が2回目で確定）
lualatex -interaction=nonstopmode print.tex
```

- 必要なもの：LuaLaTeX、`jlreq`、LuaTeX-ja、`tabularray`、`multicolrule`、`tcolorbox`、`luwa-ul`、`KKsymbols`、`keisennote`
- `luwa-ul` / `KKsymbols` / `keisennote` が無い場合は `tlmgr install luwa-ul kksymbols keisennote multicolrule tabularray`
  （TeX Live 2023 など古い環境では、作者の GitHub（KKTeX/luwa-ul・KKsymbols・keisennote）の `.sty` / `.lua` を `~/texmf/tex/latex/` に置けば組める）
- フォントはコンパイル時に自動判定：ヒラギノがあればヒラギノ、無ければ原ノ味（同梱の PDF は原ノ味で組んだもの）
- Overleaf の場合：Compiler を LuaLaTeX、TeX Live version を最新にして `main.tex` に全文を貼る
