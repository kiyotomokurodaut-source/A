#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""第11弾（r32）: ``tools/seo_deep_audit_r32.py`` が検出した弱点を一括で直す。

    python3 tools/seo_deep_fix_r32.py            # 適用
    python3 tools/seo_deep_fix_r32.py --dry-run  # 変更点の件数だけ表示

何度実行しても結果が変わらない（冪等）。適用後は

    python3 tools/fingerprint_assets_r17.py   # CSS/JSのURLを更新
    python3 tools/md_export_r26.py            # .md を作り直す
    python3 tools/netlify_prepare_r17.py      # _headers を作り直す
    python3 build.py --check                  # sitemap/llms/feed/facts を再生成

の順で回す。直す内容:

 1. GTM への preconnect / dns-prefetch（全ページ）
 2. トップの LCP 画像 preload と、大きい画像への srcset 付与
 3. 未使用の名前空間付きCSS（r17-components）の読み込み削除
 4. パンくず JSON-LD を画面表示に一致させる
 5. Service ノードへの serviceType 付与
 6. meta last-modified と JSON-LD dateModified の同期
 7. SERPで切れる title と、長すぎる description の短縮
 8. 重複 H2 の改名
 9. og:image:alt の補完
10. H1 にタイトルの主題語を入れる（5ページ）
11. 30字未満のFAQ回答を、事実の範囲で補足
12. /shindan/ のインラインJSを外部ファイル化（defer）
13. 3,000字に届かないガイドの加筆（2本）
14. 公的・学術の一次情報リンクをガイドに追加
15. 入力欄のフォントを16pxに（iOSの自動ズーム防止）
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "public"
SITE = "https://kurodaschool.jp"
GTM = "https://www.googletagmanager.com"


def display_width(text: str) -> int:
    return sum(2 if ord(c) > 0x2E7F else 1 for c in text)


class Fixer:
    def __init__(self, dry: bool):
        self.dry = dry
        self.log: list[str] = []
        self.files: dict[str, Path] = {}
        for p in sorted(PUBLIC.rglob("*.html")):
            r = p.relative_to(PUBLIC).as_posix()
            u = "/" if r == "index.html" else ("/" + r[:-10] if r.endswith("/index.html") else "/" + r)
            self.files[u] = p

    def read(self, u: str) -> str:
        return self.files[u].read_text(encoding="utf-8")

    def write(self, u: str, text: str):
        if not self.dry:
            self.files[u].write_text(text, encoding="utf-8")

    def note(self, msg: str):
        self.log.append(msg)

    # --- 1. preconnect / dns-prefetch ---------------------------------
    def head_hints(self):
        n = 0
        for u in self.files:
            if u in ("/404.html",):
                continue
            s = self.read(u)
            if 'rel="preconnect"' in s or "</head>" not in s:
                continue
            tag = (f'<link rel="preconnect" href="{GTM}"/><link rel="dns-prefetch" href="{GTM}"/>')
            block = f'<link href="{SITE}/" rel="preconnect"/>' if False else ""
            m = re.search(r'<link[^>]*rel="stylesheet"[^>]*>', s)
            if not m:
                continue
            s = s[:m.start()] + tag + s[m.start():]
            self.write(u, s)
            n += 1
        self.note(f"preconnect/dns-prefetch: {n}ページ")

    # --- 2. LCP preload + srcset --------------------------------------
    def make_variant(self, src: str, width: int, suffix: str) -> str | None:
        f = PUBLIC / src.lstrip("/")
        if not f.is_file():
            return None
        out = f.with_name(f"{f.stem}-{suffix}{f.suffix}")
        if not out.is_file() and not self.dry:
            with Image.open(f) as im:
                ratio = width / im.width
                im2 = im.resize((width, max(1, round(im.height * ratio))), Image.LANCZOS)
                im2.save(out, quality=82, method=6)
        return "/" + out.relative_to(PUBLIC).as_posix()

    def lcp_and_srcset(self):
        n_pre = 0
        home = self.read("/")
        if "kuroda-hero" in home and "preload" not in home:
            tag = '<link rel="preload" as="image" href="/images/kuroda-hero.webp" fetchpriority="high"/>'
            m = re.search(r'<link[^>]*rel="stylesheet"[^>]*>', home)
            if m:
                home = home[:m.start()] + tag + home[m.start():]
                self.write("/", home)
                n_pre = 1
        self.note(f"LCP preload: {n_pre}ページ")

        self.make_variant("/images/kuroda-hero.webp", 640, "640w")
        self.make_variant("/images/kuroda-hero.webp", 480, "480w")
        self.make_variant("/assets/consultation-strategy-kit-preview.webp", 560, "560w")
        self.make_variant("/assets/weekly-example-0e8357a075c0.webp", 480, "480w")
        self.make_variant("/assets/english-handout-preview-ea4eb66dc61e.webp", 540, "540w")

        plans = {
            "/images/kuroda-hero.webp": (
                "/images/kuroda-hero-480w.webp 480w, /images/kuroda-hero-640w.webp 640w, "
                "/images/kuroda-hero.webp 800w", "(max-width: 760px) 92vw, 360px"),
            "/profile-600.webp": (
                "/profile-600.webp 600w, /profile-900.webp 900w",
                "(max-width: 760px) 70vw, 300px"),
            "/assets/consultation-strategy-kit-preview.webp": (
                "/assets/consultation-strategy-kit-preview-560w.webp 560w, "
                "/assets/consultation-strategy-kit-preview.webp 900w",
                "(max-width: 760px) 86vw, 420px"),
            "/assets/weekly-example-0e8357a075c0.webp": (
                "/assets/weekly-example-0e8357a075c0-480w.webp 480w, "
                "/assets/weekly-example-0e8357a075c0.webp 792w",
                "(max-width: 760px) 86vw, 420px"),
            "/assets/english-handout-preview-ea4eb66dc61e.webp": (
                "/assets/english-handout-preview-ea4eb66dc61e-540w.webp 540w, "
                "/assets/english-handout-preview-ea4eb66dc61e.webp 893w",
                "(max-width: 760px) 86vw, 420px"),
        }
        n = 0
        for u in self.files:
            s = self.read(u)
            orig = s
            for m in re.finditer(r"<img[^>]*>", s):
                tag = m.group(0)
                if "srcset" in tag:
                    continue
                src = (re.search(r'src="([^"]+)"', tag) or [None, ""])[1]
                if src not in plans:
                    continue
                srcset, sizes = plans[src]
                if tag.endswith("/>"):
                    new = tag[:-2] + f' srcset="{srcset}" sizes="{sizes}"/>'
                else:
                    new = tag[:-1] + f' srcset="{srcset}" sizes="{sizes}">'
                s = s.replace(tag, new, 1)
                n += 1
            if s != orig:
                self.write(u, s)
        self.note(f"srcset: {n}画像")

    # --- 3. 未使用CSSの削除 -------------------------------------------
    def drop_unused_css(self):
        def selectors(path: Path):
            css = path.read_text(encoding="utf-8")
            css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
            out = []
            for sel in re.findall(r"([^{}]+)\{", css):
                for part in sel.split(","):
                    p = part.strip()
                    if p and p[0] not in "@.:#[":
                        out.append(p)
            return set(re.findall(r"\.([A-Za-z][\w-]+)", css)), out

        cache: dict[str, tuple[set, list]] = {}
        removed = 0
        for u in self.files:
            s = self.read(u)
            used = {c for c in re.findall(r'class="([^"]*)"', s) for c in c.split()}
            drop = []
            for m in re.finditer(r'<link[^>]*rel="stylesheet"[^>]*>', s):
                href = (re.search(r'href="([^"]+)"', m.group(0)) or [None, ""])[1]
                if not href.startswith("/assets/"):
                    continue
                f = PUBLIC / href.split("?")[0].lstrip("/")
                if not f.is_file():
                    continue
                key = f.as_posix()
                if key not in cache:
                    cache[key] = selectors(f)
                classes, bare = cache[key]
                if not classes or (classes & used):
                    continue
                if any(b not in ("[hidden]",) and not b.startswith(".") for b in bare):
                    continue          # 要素セレクタを含む＝消すと崩れうる
                drop.append(m.group(0))
            for tag in drop:
                s = s.replace(tag, "", 1)
                removed += 1
            if drop:
                self.write(u, s)
        self.note(f"未使用CSSの読み込み削除: {removed}件")

    # --- 4. パンくず JSON-LD を画面に一致 -----------------------------
    def breadcrumb_ld(self):
        fixed = 0
        for u, path in self.files.items():
            s = self.read(u)
            bc = re.search(r'<nav[^>]*aria-label="パンくず[^"]*"[^>]*>(.*?)</nav>', s, re.S)
            if not bc:
                continue
            items = []
            for m in re.finditer(r"<li([^>]*)>(.*?)</li>", bc.group(1), re.S):
                if "aria-hidden" in m.group(1):
                    continue
                hm = re.search(r'<a[^>]*href="([^"]+)"', m.group(2))
                name = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", m.group(2))).strip()
                items.append((name, hm.group(1) if hm else ""))
            if not items:
                continue
            canon = (re.search(r'<link href="([^"]+)" rel="canonical"', s)
                     or re.search(r'rel="canonical"[^>]*href="([^"]+)"', s)
                     or re.search(r'<link[^>]*rel="canonical"[^>]*href="([^"]+)"', s))
            cur = canon.group(1) if canon else SITE + u
            want = [{"@type": "ListItem", "position": i + 1, "name": n,
                     "item": (SITE + h if h.startswith("/") else h) if h else cur}
                    for i, (n, h) in enumerate(items)]
            changed = False
            for bm in re.finditer(r'(<script type="application/ld\+json">)(.*?)(</script>)', s, re.S):
                try:
                    data = json.loads(bm.group(2))
                except json.JSONDecodeError:
                    continue
                nodes = data.get("@graph") if isinstance(data.get("@graph"), list) else [data]
                hit = False
                for node in nodes:
                    if isinstance(node, dict) and node.get("@type") == "BreadcrumbList":
                        if node.get("itemListElement") != want:
                            node["itemListElement"] = want
                            hit = True
                if not hit:
                    continue
                new_block = bm.group(1) + json.dumps(data, ensure_ascii=False,
                                                     separators=(",", ":")) + bm.group(3)
                s = s[:bm.start()] + new_block + s[bm.end():]
                changed = True
            if changed:
                self.write(u, s)
                fixed += 1
        self.note(f"パンくずJSON-LDの一致: {fixed}ページ")

    # --- 5. Service.serviceType ---------------------------------------
    def service_type(self):
        fixed = 0
        for u in self.files:
            s = self.read(u)
            changed = False
            for bm in re.finditer(r'(<script type="application/ld\+json">)(.*?)(</script>)', s, re.S):
                try:
                    data = json.loads(bm.group(2))
                except json.JSONDecodeError:
                    continue
                nodes = data.get("@graph") if isinstance(data.get("@graph"), list) else [data]
                hit = False
                for node in nodes:
                    if isinstance(node, dict) and node.get("@type") == "Service" and not node.get("serviceType"):
                        name = str(node.get("name", "")).split("｜")[0].strip()
                        if name:
                            node["serviceType"] = name
                            hit = True
                if not hit:
                    continue
                new_block = bm.group(1) + json.dumps(data, ensure_ascii=False,
                                                     separators=(",", ":")) + bm.group(3)
                s = s[:bm.start()] + new_block + s[bm.end():]
                changed = True
            if changed:
                self.write(u, s)
                fixed += 1
        self.note(f"Service.serviceType: {fixed}ページ")

    # --- 6. last-modified の同期 ---------------------------------------
    def lastmod_sync(self):
        fixed = 0
        for u in self.files:
            s = self.read(u)
            lm = re.search(r'<meta[^>]*name="last-modified"[^>]*>', s)
            if not lm:
                continue
            lm_tag = lm.group(0)
            lm_val = re.search(r'content="([\d-]+)"', lm_tag)
            if not lm_val:
                continue
            dates = set(re.findall(r'"dateModified"\s*:\s*"([\d-]+)"', s))
            if not dates:
                continue
            newest = max(dates)
            if newest <= lm_val.group(1):
                continue
            s = s.replace(lm_tag, lm_tag.replace(lm_val.group(1), newest, 1), 1)
            self.write(u, s)
            fixed += 1
        self.note(f"last-modified 同期: {fixed}ページ")

    # --- 7. title / description ----------------------------------------
    TITLES = {
        "/specialty/joshi/": "女子大受験の専門対策｜津田塾・東京女子・日本女子｜黒田塾",
        "/about/": "講師紹介｜黒田清友（東大教育学部卒）｜黒田塾",
        "/study-guides/parents-kyotsu-6-weeks/": "共通テストまで6週間、保護者ができること｜黒田塾",
        "/study-guides/todai-juku-choosing/": "東大受験の塾の選び方｜集団・個別・オンラインの7項目｜黒田塾",
        "/study-guides/parents-mock-exam-bad-result/": "模試の結果が悪いとき、保護者がやるべきこと｜黒田塾",
        "/study-guides/parents-kyotsu-exam-day/": "共通テスト前日・当日、保護者ができること｜黒田塾",
        "/study-guides/parents-mock-exam-hantei/": "模試の判定・偏差値を保護者はどう読むか｜E判定の読み方｜黒田塾",
        "/study-guides/juku-yametai/": "「塾をやめたい」と思ったときの判断｜辞める前に確認する5点｜黒田塾",
        "/study-guides/todai-english-writing/": "東大英語の自由英作文の書き方｜型と72語の答案例｜黒田塾",
        "/study-guides/chugaku-juken-12gatsu-shutsugan/": "中学受験2027｜12月出願の学校一覧とチェックリスト｜黒田塾",
        "/study-guides/shiboukou-sageru/": "志望校を下げるべきか｜判定ではなく数字で決める順番｜黒田塾",
        "/study-guides/ima-kara-maniau/": "今から受験勉強を始めても間に合うか｜学年別の始め方｜黒田塾",
        "/study-guides/todai-english-review/": "東大英語の復習法｜読解・要約・英作文を次の1題へ｜黒田塾",
        "/study-guides/todai-math-review/": "東大数学の復習法｜白紙で方針を再現するやり直し｜黒田塾",
        "/study-guides/english-reading-diagnosis/": "英語長文が読めない原因3つ｜診断法と例題6問｜黒田塾",
        "/study-guides/todai-math-2026-3/": "東大理系数学2026第3問｜球面・重心・弦の通過範囲｜黒田塾",
    }
    DESCRIPTIONS = {
        "/university-exam/": (
            "大学受験の個別指導なら黒田塾。東大卒の黒田清友が、志望校から逆算した学習計画と、"
            "英語・数学・国語・社会・小論文・面接の指導、答案添削を一人で担当。月額24,000円〜、"
            "全国対応、30分の無料相談あり。"),
        "/specialty/": (
            "志望校が決まったら、対策は大学ごとに分かれます。東大・早稲田・慶應・MARCHの専門対策を、"
            "東大教育学部卒の講師が個別指導。出題傾向から逆算した計画と答案添削で得点を取ります。"
            "30分の無料相談あり。"),
        "/shindan/": (
            "黒田塾の簡易AI診断。学年・志望校・困っている教科と理解度、学習時間に答えるだけで、"
            "今のタイプと優先課題、おすすめ教材をその場で案内します。登録不要・無料。"
            "結果に応じてLINE相談も選べます。"),
        "/study-guides/parents-mock-exam-bad-result/": (
            "模試の結果が悪かったとき、保護者がやってはいけない関わり方と、やるべきことを整理します。"
            "科目別に「あと何点」を見る方法、失点原因の4つの分け方、次の模試までの重点の決め方を"
            "まとめました。"),
        "/study-guides/materials-catalog/": (
            "黒田塾のオリジナルPDF教材のカタログです。完全対策講座（1科目20,000円）、文系数学、"
            "大学別・国公立二次対策、共通テスト・推薦対策の商品名と価格を紹介。販売はBOOTH"
            "「東大黒田塾」です。"),
        "/study-guides/chugaku-juken-12gatsu-shutsugan/": (
            "2027年度中学入試で出願が12月に始まる学校を、千葉・埼玉・東京・神奈川の都県別に"
            "開始日順で一覧化しました。出願締切も併記。出願前のチェックリストとあわせて整理します。"),
        "/study-guides/todai-english-time-allocation/": (
            "東大英語の時間配分を、試験開始からの経過時刻つきの配表で示します。全体確認3分・"
            "英作文15分・要約12分・和訳10分・リスニング30分・長文18分。大問ごとに次へ進む時刻を"
            "決める手順まで解説。"),
        "/juku/": (
            "大学受験の個別指導塾の選び方を、料金の決まり方・担当講師が途中で変わらないか・"
            "学習計画と答案添削の体制で解説します。黒田塾は代表が全回担当し、面談のみ月額24,000円〜。"
            "30分の無料相談あり。"),
    }

    def rewrite_title_desc(self):
        titles = {}
        for u in self.files:
            m = re.search(r"<title>(.*?)</title>", self.read(u), re.S)
            titles[u] = m.group(1) if m else ""
        new_titles = dict(titles)
        for u, t in self.TITLES.items():
            new_titles[u] = t
            assert len(t) <= 40, (u, len(t), t)
            assert display_width(t) <= 66, (u, display_width(t), t)
        dup = [t for t, c in __import__("collections").Counter(new_titles.values()).items() if c > 1]
        assert not dup, dup
        n = 0
        for u, new in self.TITLES.items():
            old = titles[u]
            if old == new:
                continue
            s = self.read(u)
            # 古いタイトルは「完全な値」としてだけ置換する（別文字列の一部を壊さない）
            for m in re.finditer(re.escape(old), s):
                a = s.rfind('"', 0, m.start())
                b = s.find('"', m.end())
                if not (s[m.start() - 1:m.start()] in ('"', ">") or s[m.start() - 3:m.start()] == "<ti"):
                    raise SystemExit(f"title appears inside another string: {u}")
            s = s.replace(old, new)
            self.write(u, s)
            n += 1
        self.note(f"title 短縮: {n}ページ")

        n = 0
        for u, new in self.DESCRIPTIONS.items():
            assert 60 <= len(new) <= 130, (u, len(new))
            s = self.read(u)
            m = (re.search(r'name="description" content="([^"]*)"', s)
                 or re.search(r'content="([^"]*)" name="description"', s))
            old = m.group(1)
            if old == new:
                n_skip = True
                continue
            for mm in re.finditer(re.escape(old), s):
                prev = s[max(0, mm.start() - 1):mm.start()]
                nxt = s[mm.end():mm.end() + 1]
                if prev != '"' or nxt != '"':
                    raise SystemExit(f"description appears inside another string: {u}")
            s = s.replace(old, new)
            self.write(u, s)
            n += 1
        self.note(f"description 短縮: {n}ページ")

    # --- 8. 重複 H2 ----------------------------------------------------
    def dup_h2(self):
        u = "/study-guides/gap-year-study-plan/"
        s = self.read(u)
        old = "<section id=\"gap-year-study-plan-week-table\"><h2>浪人生の1週間は、どう組み立てればよいですか？</h2>"
        new = "<section id=\"gap-year-study-plan-week-table\"><h2>1週間の予定表は、どう作れば崩れにくいですか？</h2>"
        if old in s:
            self.write(u, s.replace(old, new, 1))
            self.note("重複H2: 1ページ")

    # --- 9. og:image:alt ----------------------------------------------
    def og_alt(self):
        n = 0
        for u in self.files:
            s = self.read(u)
            if "og:image:alt" in s or "og:image" not in s:
                continue
            h1 = re.search(r"<h1[^>]*>(.*?)</h1>", s, re.S)
            alt = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", h1.group(1))).strip() if h1 else ""
            if not alt:
                continue
            m = re.search(r'<meta[^>]*property="og:image"[^>]*/>', s) or \
                re.search(r'<meta[^>]*property="og:image"[^>]*>', s)
            if not m:
                continue
            tag = f'<meta content="{alt}" property="og:image:alt"/>'
            s = s[:m.end()] + tag + s[m.end():]
            self.write(u, s)
            n += 1
        self.note(f"og:image:alt: {n}ページ")

    # --- 10. H1 に主題語 -----------------------------------------------
    H1 = {
        "/area/": ("<h1>教室はありません。<br/>全国47都道府県、どこからでも同じ指導を。</h1>",
                   "<h1>対応エリアは全国47都道府県。<br/>教室はなく、どこからでも同じ指導を。</h1>"),
        "/for-parents/": ("<h1>授業を増やす前に、<br/>今の困りごとと必要な支援を。</h1>",
                          "<h1>保護者の方へ。<br/>授業を増やす前に、今の困りごとと必要な支援を。</h1>"),
        "/learning-check/": ("<h1>学習のつまずきを、<br/>3つの質問で整理する。</h1>",
                             "<h1>無料の学習チェック。<br/>つまずきを3つの質問で整理する。</h1>"),
        "/materials/": ("<h1>完全対策講座<span>必要な科目を、<br>自分で学べる教材一式に。</span></h1>",
                        "<h1>教材プラン<span>必要な科目を、<br>自分で学べる完全対策講座の一式に。</span></h1>"),
        "/study-guides/mensetsu-taisaku/": (
            "<h1>面接は「人柄の審査」ではなく、志望理由を言葉にする確認の場</h1>",
            "<h1>大学受験の面接対策は「人柄の審査」ではなく、志望理由を言葉にする場</h1>"),
    }

    def h1_fix(self):
        n = 0
        for u, (old, new) in self.H1.items():
            s = self.read(u)
            if old not in s:
                if new in s:
                    continue
                raise SystemExit(f"H1 text not found: {u}")
            self.write(u, s.replace(old, new, 1))
            n += 1
        self.note(f"H1の主題語: {n}ページ")

    # --- 11. 短いFAQ回答の補足 -----------------------------------------
    FAQ = {
        "はい。不足分だけを担当する分担が可能です。":
            "はい。不足分だけを担当する分担が可能です。学校や予備校の進度を前提に、必要な単元だけを追加する形で計画を組みます。",
        "はい。オンラインなので県内どこからでも受講できます。":
            "はい。オンラインなので県内どこからでも受講できます。教室への移動は不要で、通信環境があれば同じ授業と添削を受けられます。",
        "はい。オンラインなので、県内どの地域からでも受講できます。":
            "はい。オンラインなので、県内どの地域からでも受講できます。教室への移動は不要で、通信環境があれば同じ授業を受けられます。",
        "はい。オンラインで全国から受講できます。":
            "はい。オンラインで全国から受講できます。教室は持たず、全国47都道府県から同じ料金で受講できます。",
        "はい。志望学部の過去問を見て、科目配分を組みます。":
            "はい。志望学部の過去問を見て、科目配分を組みます。配点と時間配分から、優先する単元を決めます。",
        "はい。志望学部の過去問から、科目配分を組みます。":
            "はい。志望学部の過去問から、科目配分を組みます。出題形式と配点に合わせて、演習の順番まで決めます。",
        "はい。学部ごとの形式と配点を確認したうえで対策を組みます。":
            "はい。学部ごとの形式と配点を確認したうえで対策を組みます。複数学部を併願する場合も、共通する科目から固めます。",
        "はい。私立も入試形式と配点に合わせて対策を組みます。":
            "はい。私立も入試形式と配点に合わせて対策を組みます。併願校が多い場合は、共通する出題形式を先に固めます。",
        "はい。学部ごとの形式に合わせて対策を組みます。":
            "はい。学部ごとの形式に合わせて対策を組みます。私立専願でも、配点の高い科目から順に計画を組みます。",
        "はい。都内の私立も学部ごとの形式に合わせて対策を組みます。":
            "はい。都内の私立も学部ごとの形式に合わせて対策を組みます。併願校の日程も並べて、時期ごとの配分を決めます。",
        "はい。高1・高2は基礎の順番を決めるところから始めます。":
            "はい。高1・高2は基礎の順番を決めるところから始めます。志望校が未定でも、教科ごとの優先順位を先に決められます。",
        "いいえ。無料で、会員登録も不要です。何度でも受け直せます。":
            "いいえ。無料で、会員登録も不要です。何度でも受け直せます。回答はブラウザの中だけで処理されます。",
    }

    def faq_answers(self):
        n = 0
        for u in self.files:
            s = self.read(u)
            hit = False
            for old, new in self.FAQ.items():
                if f'"{old}"' in s:
                    s = s.replace(f'"{old}"', f'"{new}"')
                    hit = True
                if f">{old}</" in s:
                    s = s.replace(f">{old}</", f">{new}</")
                    hit = True
            if hit:
                self.write(u, s)
                n += 1
        self.note(f"FAQ回答の補足: {n}ページ")

    # --- 12. /shindan/ のインラインJS -----------------------------------
    def shindan_script(self):
        u = "/shindan/"
        s = self.read(u)
        m = re.search(r"<script>\n?\(function\(\)\{(.*?)\}\)\(\);\n?</script>", s, re.S)
        if not m:
            return
        body = m.group(0)
        js = "(function(){" + m.group(1) + "})();\n"
        out = PUBLIC / "assets" / "shindan-diagnosis-r32.js"
        if not self.dry:
            out.write_text(js, encoding="utf-8")
        s = s.replace(body, '<script defer src="/assets/shindan-diagnosis-r32.js"></script>', 1)
        self.write(u, s)
        self.note("shindan: インラインJS 1本を外部化（defer）")

    # --- 13. ガイドの加筆 ----------------------------------------------
    ADD = {
        "/study-guides/gap-year-study-plan/": (
            "<section><h2>1週間の予定表を、崩れても戻せる形にするには？</h2>"
            "<p>予定表は「埋める」より「戻せる」ことが大事です。遅れた日に取り返す時間を、"
            "あらかじめ週の後半に1コマだけ空けておくと、崩れた翌日から同じリズムに戻れます。"
            "穴を埋めるための予備の時間を最初から置いておく、という発想です。</p></section>",
            "予定表を、崩れても戻せる形"),
        "/study-guides/todai-listening/": (
            "<section><h2>リスニングの記録は、何を残せば次に効きますか？</h2>"
            "<p>解き終えたら、正誤ではなく「聞き取れなかった箇所の音」を1つだけ書き残します。"
            "音と語のつながりが取れなかったのか、語彙が抜けたのか、集中が切れたのかで、"
            "次にやることが変わります。記録が3回分たまると、自分の崩れ方の傾向が見えます。</p></section>",
            "リスニングの記録"),
    }

    def thin_guides(self):
        n = 0
        for u, (block, anchor) in self.ADD.items():
            s = self.read(u)
            if anchor in s:
                continue
            marker = '<!-- r31:related-guides:start -->'
            if marker in s:
                s = s.replace(marker, block + "\n" + marker, 1)
            else:
                s = s.replace("</main>", block + "</main>", 1)
            self.write(u, s)
            n += 1
        self.note(f"ガイド加筆: {n}本")

    # --- 14. 公的・学術の一次情報 ---------------------------------------
    OFFICIAL = {
        "dnc-kyotsu": ("https://www.dnc.ac.jp/kyotsu/",
                       "大学入試センター 大学入学共通テスト（公式）",
                       "共通テストの教科・科目と実施要項は公式ページで確認できます。"),
        "dnc-kakomondai": ("https://www.dnc.ac.jp/kyotsu/kakomondai/index.html",
                           "大学入試センター 過去3年分の試験問題（公式）",
                           "共通テストの出題形式は、公式の過去問題で確認できます。"),
        "todai": ("https://www.u-tokyo.ac.jp/ja/admissions/",
                  "東京大学 入学案内（公式）",
                  "東大の入試科目・配点・募集要項は公式の入学案内が一次情報です。"),
        "eiken": ("https://www.eiken.or.jp/eiken/",
                  "日本英語検定協会 英検（公式）",
                  "英検の級・試験日程・配点は公式サイトが一次情報です。"),
    }
    GUIDE_SOURCES = {
        "kyotsu-6weeks-student": "dnc-kyotsu",
        "kyotsu-after-switch": "dnc-kyotsu",
        "kyotsu-english-time": "dnc-kakomondai",
        "kyotsu-listening": "dnc-kakomondai",
        "kyotsu-riyo-nyushi": "dnc-kyotsu",
        "kyotsu-self-scoring": "dnc-kakomondai",
        "kyotsu-test-final-stage": "dnc-kyotsu",
        "kyotsu-test-last-week": "dnc-kyotsu",
        "kyotsu-zenjitsu-tojitsu": "dnc-kyotsu",
        "parents-kyotsu-6-weeks": "dnc-kyotsu",
        "parents-kyotsu-exam-day": "dnc-kyotsu",
        "joho-1-taisaku": "dnc-kyotsu",
        "todai-bunkei-math-strategy": "todai",
        "todai-english-review": "todai",
        "todai-english-strategy": "todai",
        "todai-english-summary": "todai",
        "todai-english-time-allocation": "todai",
        "todai-english-writing": "todai",
        "todai-juku-choosing": "todai",
        "todai-kakomon-review": "todai",
        "todai-listening": "todai",
        "todai-math-review": "todai",
        "todai-study-plan": "todai",
        "eigo-gaibu-kentei-nyushi": "eiken",
    }

    def official_sources(self):
        n = 0
        for slug, key in self.GUIDE_SOURCES.items():
            u = f"/study-guides/{slug}/"
            if u not in self.files:
                continue
            s = self.read(u)
            if 'id="r32-sources"' in s:
                continue
            url, label, why = self.OFFICIAL[key]
            para = (f'<p class="r32-sources" id="r32-sources"><strong>参考（一次情報）:</strong> '
                    f'<a href="{url}" rel="noopener" target="_blank">{label}</a> — {why}</p>')
            m = re.search(r'<section id="author-profile">.*?</section>', s, re.S)
            if not m:
                continue
            s = s[:m.end()] + para + s[m.end():]
            self.write(u, s)
            n += 1
        self.note(f"公的一次情報リンク: {n}本")

    # --- 15. 入力欄のフォント -------------------------------------------
    def input_font(self):
        css = PUBLIC / "assets" / "materials.css"
        s = css.read_text(encoding="utf-8")
        new = re.sub(r"(textarea\{[^}]*?font-size:)(?:\.\d+|\d)rem", r"\g<1>1rem", s)
        new = re.sub(r"(textarea\{[^}]*?font-size:)(?:\.\d+|\d)rem", r"\g<1>1rem", new)
        if new != s:
            if not self.dry:
                css.write_text(new, encoding="utf-8")
            self.note("入力欄のフォント: 16px以上に変更")

    # --- 実行 ----------------------------------------------------------
    def run(self):
        self.head_hints()
        self.lcp_and_srcset()
        self.drop_unused_css()
        self.breadcrumb_ld()
        self.service_type()
        self.lastmod_sync()
        self.rewrite_title_desc()
        self.dup_h2()
        self.og_alt()
        self.h1_fix()
        self.faq_answers()
        self.shindan_script()
        self.thin_guides()
        self.official_sources()
        self.input_font()
        print(("=== dry-run ===" if self.dry else "=== applied ==="))
        for line in self.log:
            print(" -", line)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    Fixer(args.dry_run).run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
