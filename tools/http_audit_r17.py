#!/usr/bin/env python3
"""Read-only production smoke checks. Distinguishes HTTP redirects from meta refresh."""
import argparse,json,time,urllib.request,urllib.error
from pathlib import Path
from urllib.parse import urljoin,urlsplit

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):return None

def response(url):
    opener=urllib.request.build_opener(NoRedirect())
    request=urllib.request.Request(url,headers={'User-Agent':'KurodaSchool-DeploymentCheck/17','Cache-Control':'no-cache'})
    try:r=opener.open(request,timeout=20)
    except urllib.error.HTTPError as e:r=e
    with r:
        body=r.read(1_000_000).decode('utf-8','replace')
        return r.code,dict(r.headers.items()),body

def follow(url):
    chain=[]
    for _ in range(6):
        status,headers,body=response(url)
        location=next((v for k,v in headers.items() if k.lower()=='location'),None)
        chain.append({'url':url,'status':status,'location':location})
        if status not in {301,302,303,307,308} or not location:return chain,body,headers
        nxt=urljoin(url,location)
        allowed={'kurodaschool.jp','www.kurodaschool.jp','kurodaschool.com','www.kurodaschool.com','kiyotomokuroda.netlify.app','lively-cake-2d04.kiyotomokurodaut.workers.dev'}
        if urlsplit(nxt).hostname not in allowed:raise RuntimeError('Unexpected redirect destination: '+nxt)
        url=nxt
    raise RuntimeError('Too many redirects')

def main():
    p=argparse.ArgumentParser();p.add_argument('--wait',type=int,default=0);args=p.parse_args()
    start=time.monotonic();ready=False;last=''
    while True:
        try:
            st,_,b=response('https://kurodaschool.jp/study-guides/')
            ready=st==200 and 'data-r17-finder' in b
        except Exception as e:last=str(e)
        if ready or time.monotonic()-start>=args.wait:break
        time.sleep(10)
    result={'r17_catalogue_live':ready,'checks':[],'note':'Only these public URLs are tested; this does not verify Google indexing or ranking.'}
    cases=[
      ('https://kurodaschool.jp/',200,'https://kurodaschool.jp/'),
      ('https://kurodaschool.com/pricing/',301,'https://kurodaschool.jp/pricing/'),
      ('https://www.kurodaschool.com/',301,'https://kurodaschool.jp/'),
      ('https://www.kurodaschool.jp/',301,'https://kurodaschool.jp/'),
      ('https://kiyotomokuroda.netlify.app/',301,'https://kurodaschool.jp/'),
      ('https://lively-cake-2d04.kiyotomokurodaut.workers.dev/',301,'https://kurodaschool.jp/'),
      ('https://lively-cake-2d04.kiyotomokurodaut.workers.dev/pricing/',301,'https://kurodaschool.jp/pricing/'),
      ('https://kurodaschool.jp/__r17_missing_page_check__/',404,'https://kurodaschool.jp/__r17_missing_page_check__/'),
    ]
    for url,status,dest in cases:
        try:
            chain,body,headers=follow(url)
            ok=chain[0]['status']==status and chain[-1]['url']==dest and chain[-1]['status']==(404 if status==404 else 200)
            robots=next((v for k,v in headers.items() if k.lower()=='x-robots-tag'),'')
            if status!=404 and 'noindex' in robots.lower():ok=False
            result['checks'].append({'url':url,'ok':ok,'chain':chain,'x_robots_tag':robots})
        except Exception as e:result['checks'].append({'url':url,'ok':False,'error':str(e)})
    if last:result['initial_fetch_note']=last
    Path('r17-http-audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False,indent=2))
    if not ready or not all(c['ok'] for c in result['checks']):
        print('::warning::Publication/HTTP check incomplete. Inspect r17-http-audit.json; do not infer success from a browser URL alone.')
        raise SystemExit(1)
if __name__=='__main__':main()
