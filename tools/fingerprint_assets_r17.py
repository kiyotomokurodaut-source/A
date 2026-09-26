#!/usr/bin/env python3
"""Refresh CSS/JS filenames after content edits, preserving legacy URLs."""
from pathlib import Path
from html.parser import HTMLParser
import hashlib,json,re
ROOT=Path(__file__).resolve().parents[1]
class Refs(HTMLParser):
 def __init__(self,raw):
  super().__init__();self.assets=[];self.feed(raw)
 def handle_starttag(self,tag,attrs):
  a=dict(attrs);ref=None
  if tag=='script':ref=a.get('src')
  if tag=='link' and 'stylesheet' in a.get('rel','').split():ref=a.get('href')
  if ref and ref.startswith('/assets/'):self.assets.append(ref)

def refresh(root):
 public=root/'public';html=list(public.rglob('*.html'));refs=set()
 for p in html:refs.update(Refs(p.read_text(encoding='utf-8')).assets)
 mapping={}
 for ref in sorted(refs):
  if '?' in ref or '#' in ref:continue
  p=public/ref.lstrip('/')
  if p.suffix not in {'.css','.js'}:continue
  if not p.is_file():raise ValueError('Missing CSS/JS source: '+ref)
  digest=hashlib.sha256(p.read_bytes()).hexdigest()[:12]
  stem=re.sub(r'-[0-9a-f]{12}$','',p.stem)
  new=p.with_name(stem+'-'+digest+p.suffix)
  if new!=p:new.write_bytes(p.read_bytes());mapping[ref]='/'+new.relative_to(public).as_posix()
 for p in html+list((root/'tools').glob('_*.html')):
  raw=p.read_text(encoding='utf-8')
  for old,new in mapping.items():raw=raw.replace(old,new)
  p.write_text(raw,encoding='utf-8')
 refs=set()
 for p in html:refs.update(Refs(p.read_text(encoding='utf-8')).assets)
 hashes={ref:hashlib.sha256((public/ref.lstrip('/')).read_bytes()).hexdigest() for ref in sorted(refs) if '?' not in ref and '#' not in ref}
 (root/'tools/r17_assets.json').write_text(json.dumps(hashes,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 return len(mapping)
if __name__=='__main__':print('Updated asset URLs:',refresh(ROOT))
