/* Only visible, editable referral labels. No cookies, visitor IDs, or automatic message sending. */
(() => {
 'use strict';
 const output=document.getElementById('quick-message');if(!output)return;
 const qs=new URLSearchParams(location.search);
 const campaign=qs.get('utm_campaign')||'';
 const source=qs.get('utm_source')||qs.get('src')||'';
 const labels={google:'Google検索',x:'X',youtube:'YouTube',line:'公式LINE',referral:'紹介'};
 const codes={kuroda_consult_20260927:'G27',x_consult_20260927:'X27',youtube_consult_20260927:'Y27',line_consult_20260927:'L27'};
 const label=Object.hasOwn(labels,source)?labels[source]:'';
 const code=Object.hasOwn(codes,campaign)?codes[campaign]:'';
 if(label||code)output.value+='\n見た案内：'+[label,code].filter(Boolean).join('／');
 const status=document.getElementById('quick-status');
 document.getElementById('quick-copy').addEventListener('click',async()=>{
  if(!output.value.trim()){status.textContent='相談文を入力してください。';return;}
  status.textContent='コピーしています…';
  try{await Promise.race([navigator.clipboard.writeText(output.value),new Promise((_,reject)=>setTimeout(()=>reject(Error('copy timeout')),1500))]);status.textContent='コピーしました。LINEを開き、貼り付けて送信してください。';}
  catch(_){output.focus();output.select();status.textContent='文章を選択しました。端末のコピー操作をお使いください。';}
 });
 const fullOutput=document.getElementById('consult-output');
 const fullBuild=document.getElementById('consult-build');
 if(fullBuild&&fullOutput&&code)fullBuild.addEventListener('click',()=>{if(fullOutput.value.trim())fullOutput.value+='\n見た案内：'+code;});
})();
