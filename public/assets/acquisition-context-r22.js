/* Recognised campaign labels only. No identifiers, storage, requests or automatic sends. */
(() => {
 'use strict';
 const sources={x:'X（Twitter）',youtube:'YouTube',note:'note',instagram:'Instagram',referral:'知人・紹介',line:'LINE',google:'Google検索',googleads:'Google広告'};
 const contents={p01:'英語の悩み',p02:'英語の一文の例題',p03:'英語の時間配分',p04:'数学の方針',p05:'数学の条件変更',p06:'数学の復習',p07:'中学受験の宿題',p08:'算数の割合',p09:'学習計画',p10:'保護者の案内',p11:'無料の学習見本',p12:'相談の進め方',pinned:'固定の案内',profile:'プロフィールの案内',n01:'英語の無料記事',n02:'数学の無料記事',n03:'宿題の無料記事',share:'紹介用の案内'};
 const query=new URLSearchParams(location.search);
 const key=(query.get('utm_source')||query.get('src')||query.get('source')||'').toLowerCase();
 const source=Object.hasOwn(sources,key)?key:'';
 const content=Object.hasOwn(contents,query.get('utm_content')||'')?query.get('utm_content'):'';
 const tagged=query.get('utm_campaign')==='growth_202610';
 const inherit=a=>{
  if(source&&a){
   const raw=a.getAttribute('href');
   if(!raw||raw.startsWith('#')||a.hasAttribute('download'))return;
   let url;try{url=new URL(raw,location.href);}catch(_){return;}
   if(url.origin!==location.origin||!url.pathname.endsWith('/'))return;
   if(url.searchParams.has('utm_source')||url.searchParams.has('src'))return;
   url.searchParams.set('utm_source',source);
   if(tagged)url.searchParams.set('utm_campaign','growth_202610');
   if(content)url.searchParams.set('utm_content',content);
   a.href=url.href;
  }
 };
 document.querySelectorAll('a[href]').forEach(inherit);
 const setSource=field=>{
  if(!field)return;
  Object.values(sources).forEach(label=>{if(![...field.options].some(o=>o.value===label))field.add(new Option(label,label));});
  if(source&&!field.value)field.value=sources[source];
 };
 setSource(document.getElementById('consult-source'));
 const checkSource=document.getElementById('check-source');
 setSource(checkSource);
 const form=document.getElementById('learning-check-form');
 if(form&&checkSource){
  checkSource.addEventListener('change',()=>{document.getElementById('check-result').hidden=true;});
  form.addEventListener('submit',()=>{
   ['check-result-guide','check-result-service'].forEach(id=>inherit(document.getElementById(id)));
   const result=document.getElementById('check-result'),field=document.getElementById('check-result-copy');
   if(result.hidden||!field||!checkSource.value)return;
   field.value+='\n黒田塾を知ったきっかけ：'+checkSource.value;
   if(source&&checkSource.value===sources[source]&&content)field.value+='\n見ていた案内：'+contents[content];
  });
 }
})();
