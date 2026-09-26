#!/usr/bin/env python3
"""Build a crawlable, locally searchable catalogue of the existing guide URLs."""
from pathlib import Path
from html import escape, unescape
from html.parser import HTMLParser
import json
import re

ROOT = Path(__file__).resolve().parents[1]
SITE = 'https://kurodaschool.jp'
GROUPS = {'english':'英語','math':'数学','planning':'計画・復習','choice':'塾・指導の選び方','support':'保護者・学習支援'}
class Metadata(HTMLParser):
    def __init__(self, raw):
        super().__init__(convert_charrefs=True); self.meta = {}; self.ids = []
        self.feed(raw)
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if a.get('id'): self.ids.append(a['id'])
        if tag == 'meta': self.meta[a.get('name', a.get('property',''))] = a.get('content','')

def category(slug):
    if 'english' in slug or 'listening' in slug: return 'english'
    if 'math' in slug: return 'math'
    if any(t in slug for t in ('choos','agency','coaching-vs','tutoring-vs')): return 'choice'
    if 'parents' in slug: return 'support'
    return 'planning'

def entries(root):
    out=[]
    for p in sorted((root/'public/study-guides').glob('*/index.html')):
        raw=p.read_text(encoding='utf-8'); parsed=Metadata(raw)
        if 'noindex' in parsed.meta.get('robots','').lower(): continue
        t=re.search(r'<title>(.*?)</title>',raw,re.S|re.I)
        if not t: raise ValueError('Guide without a title: '+str(p))
        title=unescape(re.sub('<[^>]+>','',t.group(1))).strip()
        out.append({'title':title.removesuffix('｜黒田塾'),'description':parsed.meta.get('description',''), 'url':'/study-guides/'+p.parent.name+'/', 'category':category(p.parent.name)})
    return out

def render(items):
    opts=''.join(f'<option value="{k}">{v}</option>' for k,v in GROUPS.items())
    cards=''.join('<article class="r17-guide-card" data-r17-card data-category="'+escape(i['category'])+'"><span class="r17-category">'+GROUPS[i['category']]+'</span><h3><a href="'+escape(i['url'])+'">'+escape(i['title'])+'</a></h3><p>'+escape(i['description'])+'</p></article>' for i in items)
    return '''<main class="detail r17-hub" id="main-content"><nav aria-label="パンくずリスト"><ol class="breadcrumbs"><li><a href="/">黒田塾</a></li><li aria-current="page">学習ガイド</li></ol></nav><h1>無料の受験勉強ガイドを、困りごとから探す</h1><p class="intro">英語・数学の例題、答案の直し方、週間計画、塾選びをまとめています。まず今の困りごとに合う一つを読み、例題や記入シートで自分の状況を確かめてください。本文は会員登録・LINE登録なしで読めます。</p>
<nav class="r17-quicklinks" aria-label="よく使う学習ガイド"><a href="/study-guides/english-reading-diagnosis/">単語は分かるのに読めない</a><a href="/study-guides/math-self-solve/">解説は分かるが解けない</a><a href="/study-guides/weekly-study-plan/">一週間の計画を直したい</a><a href="/study-guides/coaching-vs-private-tutoring/">どの支援が必要か迷う</a></nav>
<div class="r17-guide-controls" data-r17-finder><div class="r17-guide-fields"><label>キーワード<input type="search" id="r17-guide-search" data-r17-query placeholder="例：要約、英作文、模試、保護者" autocomplete="off" aria-describedby="r17-search-note"/></label><label>分類<select data-r17-category><option value="">すべての分野</option>'''+opts+'''</select></label><button type="button" data-r17-reset>条件をクリア</button></div><p class="r17-note" id="r17-search-note">絞り込みはこの端末のブラウザ内で行います。検索語をこの機能から外部へ送信しません。</p><p class="r17-status" data-r17-status role="status" aria-live="polite">'''+str(len(items))+'''件のガイドを掲載しています。</p><noscript><p>JavaScriptが無効のため絞り込みは使えません。下の一覧からすべての記事を開けます。</p></noscript></div>
<h2 id="r17-guide-list">テーマ別の学習ガイド一覧</h2><div class="r17-guides">'''+cards+'''</div><p data-r17-empty hidden>一致する記事がありません。キーワードを短くするか、分類を「すべての分野」に戻してください。</p>
<section id="r17-howto"><h2>読むだけで終えず、例題・記録・再テストへ</h2><p>例題は解答を開く前に取り組み、誤答したら、知らなかった知識と取り違えた条件を分けます。計画シートは予定だけでなく、実際にかかった時間も記録します。掲載する架空例と実際の指導事例は区別してください。</p><p><a href="/downloads/english-reading-check-6.pdf">英語の例題6問・解説PDF</a>も利用できます。個別の答案や計画について相談する場合は、<a href="/contact/">30分の無料相談の内容</a>と<a href="/pricing/">料金・指導範囲</a>を確認してください。</p></section></main>'''

def refresh(root:Path):
    p=root/'public/study-guides/index.html'; raw=p.read_text(encoding='utf-8')
    old=re.search(r'<main\b[^>]*>.*?</main>',raw,re.S|re.I)
    if not old: raise ValueError('Guide hub has no main element')
    items=entries(root); body=render(items)
    existing=set(Metadata(old.group()).ids); new=set(Metadata(body).ids)
    # Keep established fragment links working. No hidden keywords are introduced.
    aliases=''.join('<span id="'+escape(i,quote=True)+'" aria-hidden="true"></span>' for i in sorted(existing-new))
    body=body.replace('<h1>',aliases+'<h1>',1)
    raw=raw[:old.start()]+body+raw[old.end():]
    def patch_schema(m):
        data=json.loads(m.group(2)); roots=data if isinstance(data,list) else [data]
        for r in roots:
            for n in r.get('@graph',[r]):
                if n.get('@type')=='ItemList' and str(n.get('@id','')).endswith('#resources'):
                    n['numberOfItems']=len(items)
                    n['itemListElement']=[{'@type':'ListItem','position':pos,'name':i['title'],'url':SITE+i['url']} for pos,i in enumerate(items,1)]
        return m.group(1)+json.dumps(data,ensure_ascii=False,separators=(',',':'))+m.group(3)
    raw=re.sub(r'(<script\b[^>]*type="application/ld\+json"[^>]*>)(.*?)(</script>)',patch_schema,raw,flags=re.S|re.I)
    p.write_text(raw,encoding='utf-8'); return len(items)
if __name__=='__main__': print('Refreshed guide catalogue:',refresh(ROOT))
