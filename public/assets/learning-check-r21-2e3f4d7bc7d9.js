/* A local, deterministic learning check. No requests, cookies, persistence or automatic LINE sends. */
(() => {
 'use strict';
 const plans = {
  english: {
   label:'英語', keyword:'英語相談', link:'/english-support/', guide:'/study-guides/english-reading-diagnosis/',
   difficulties:{
    structure:['単語は分かるが一文の意味が取れない','一文の骨格を先に確認する','長文全体を訳し直す前に、止まった一文を選びます。主語と動詞を示し、修飾する部分を括弧に入れてみてください。','短い英文3文について、主語・動詞・修飾先を解答なしで示せるか確認する。','主語・動詞は示せるか。どの部分がどの語を説明するか。'],
    reference:['一文は読めるが指示語・段落で迷う','文どうしの関係を確認する','this・theyなどが何を指すか、前の文のどの内容に戻るかを書きます。段落ごとに一言で要点を残し、本文の根拠と照らしてください。','短い段落1つを選び、指示語の対象と段落の要点を自分の言葉で書く。','語句の意味、一文の構造、段落の関係のどこで止まっているか。'],
    time:['長文を最後まで解く時間が足りない','読む時間と解く時間を分けて記録する','1つの大問で、本文を読む・根拠を探す・選択肢を比べる時間を分けます。全部を速くしようとする前に、最も時間がかかる段階を確認します。','大問1つで、読む・根拠を探す・選択肢を選ぶ時間と迷った箇所を記録する。','読むこと自体と、解答の根拠探し・選択肢比較のどちらが遅いか。'],
    review:['解説を読んでも次の長文で同じ誤りが出る','読み直しを再テストに変える','和訳を見た直後の理解と、解説なしで読めることは分けて確認します。誤読した一文を翌日もう一度読み、どの知識や読み方が必要だったか説明します。','誤読した一文を解説を閉じて読み直し、翌日にも同じ構造を説明する。','知らない語句、構造の取り違え、設問の根拠のどれか。']
   }
  },
  math: {
   label:'数学', keyword:'数学相談', link:'/math-support/', guide:'/study-guides/math-self-solve/',
   difficulties:{
    start:['解説は分かるが最初の一手が出ない','条件と求めるものから方針を選ぶ','解説を閉じ、使える条件・求めるもの・最初の一手と理由の3行を書きます。公式名だけでなく、この条件だから使えるという理由を残します。','例題2問で、使える条件・求めるもの・最初の一手と理由を、解説なしで書く。','条件を読めているか、候補となる方針を知っているか、選ぶ理由が言えるか。'],
    calculation:['方針は出るが計算・場合分けで止まる','最初に崩れた行を見つける','正解との違いを最後の答えだけで比べず、最初に誤った式や抜けた条件を特定します。計算、定義域、場合分けを分けて確認します。','誤答1問について最初に崩れた行を示し、その一段階から計算をやり直す。','計算の誤りか、条件の見落としか、場合分けの不足か。'],
    repeat:['同じ問題は解けるが少し変わると解けない','覚えた答えと使える方針を分ける','数値や条件が変わったとき、元の方法が使える理由を説明します。解法名だけでなく、使える条件と使えない条件を書き比べます。','例題1問と条件を変えた1問で、方針が同じか変わるか、その理由を書く。','どの条件が方針を決めたか、変えた条件の影響を確認できるか。'],
    answer:['途中までは解けるが答案・時間配分で失点する','解いた過程を採点できる形にする','答案で必要な条件、論拠、結論が読み手に伝わるか確認します。時間不足なら、考える・計算する・書く時間も分けて記録します。','誤答1問の答案を、条件・論拠・結論が分かる順番で書き直す。','方針は正しいか、必要な理由が書かれているか、時間はどこに使ったか。']
   }
  },
  junior: {
   label:'中学受験の算数・宿題', keyword:'算数相談', link:'/junior-homework-support/', guide:'/study-guides/homework-priorities/',
   difficulties:{
    homework:['塾の宿題が多く、毎週残る','予定と実際を比べて課題量を調整する','宿題1つの予定時間、実際の時間、止まった問題を残します。必須範囲を勝手に削る前に、記録をもとに塾の先生へ優先順位を相談します。','算数の宿題1回分で予定・実際の時間と止まった問題を記録し、優先範囲を先生に確認する。','量が多いのか、理解不足で時間が延びるのか、解き直しが後回しか。'],
    ratio:['割合・比の文章題で式が立たない','何を基準に比べるかを図で示す','割合を掛ける前に、もとにする量・比べる量・割合を言葉や図で分けます。答えの数値だけでなく、どの量を1とするか説明します。','文章題2問で、もとにする量・比べる量・割合を図か言葉で示す。','量の関係が読めているか、何を1とするか、式の意味を説明できるか。'],
    repeat:['解き直しても次のテストで同じ問題を落とす','答えを写す復習から自分で解く復習へ','解説で確認した一段階を、解説を閉じて再現します。翌日など別の機会にも、問題の条件から式まで説明できるか確かめます。','前に間違えた基本問題2問を、解説なしで式の理由まで説明して解き直す。','答えを覚えただけか、考え方を説明できるか、期間を空けてもできるか。'],
    parent:['保護者が毎日教えないと勉強が進まない','本人・保護者・先生の役割を分ける','まず本人が止まった問題を残し、保護者は期限と時間を確認します。解き方の判断や課題量の調整は、塾の先生・指導者との相談に使います。','本人が分からない問題に印をつけ、保護者と先生に相談する項目を1つ決める。','本人だけでできる範囲、保護者が支える範囲、指導者に確認する範囲。']
   }
  },
  planning: {
   label:'学習計画', keyword:'計画相談', link:'/study-coaching/', guide:'/study-guides/weekly-study-plan/',
   difficulties:{
    priority:['教材が多く、何から始めるか迷う','今週の優先課題を1つに絞る','提出期限、志望校で必要な範囲、今の理解を確認して、今週最優先の課題を決めます。教材を増やす前に、今ある課題を終えられるか確認します。','今週の優先課題を1つ選び、教材・範囲・終わりの条件を書く。','必要な課題か、今の理解に合うか、使える時間で終えられるか。'],
    unfinished:['計画を立てても毎週終わらない','使える時間と課題量を照合する','先週使えた時間を確認し、予定と実際の差を見ます。残った課題を全部翌週へ上乗せせず、理解不足と量の問題を分けて調整します。','先週終わらなかった課題1つの予定・実際・止まった箇所を書き、今週の量を見直す。','使える時間の見積もり、課題量、理解不足による停滞。'],
    retention:['勉強時間は確保しているが、復習が定着しない','時間に加えて終わりの条件を決める','「1時間勉強した」だけでなく、解説なしで何ができるようになったかを残します。次の日にも同じ知識や方針を使えるか確認します。','課題1つについて、時間と「解説なしでできること」の両方を記録する。','読んだ・写したと、自分で説明できる・解けるの違い。'],
    schedule:['学校・部活・他の塾との両立が難しい','固定予定を引いてから勉強を配置する','睡眠、学校、移動、部活などの固定予定を先に入れ、残る時間へ課題を配置します。予定どおりにいかない日を想定して、調整用の時間を残します。','固定予定を先に書き、使える時間に最優先の課題1つを配置する。','毎週使える時間と、提出期限、変更が多い曜日。']
   }
  }
 };
 const form=document.getElementById('learning-check-form');
 const q=new URLSearchParams(location.search);
 if(form){
  const theme=document.getElementById('check-theme'), difficulty=document.getElementById('check-difficulty');
  const result=document.getElementById('check-result'), error=document.getElementById('check-error');
  const sync=()=>{
   difficulty.replaceChildren(new Option('選んでください',''));
   const p=plans[theme.value];
   if(p) Object.entries(p.difficulties).forEach(([key,value])=>difficulty.add(new Option(value[0],key)));
   difficulty.disabled=!p;
   result.hidden=true; error.textContent='';
  };
  theme.addEventListener('change',sync);
  ['check-grade','check-difficulty'].forEach(id=>document.getElementById(id).addEventListener('change',()=>{result.hidden=true;error.textContent='';}));
  if(Object.hasOwn(plans,q.get('theme')||'')) theme.value=q.get('theme');
  sync();
  form.addEventListener('submit',event=>{
   event.preventDefault();
   const grade=document.getElementById('check-grade');
   const p=plans[theme.value], d=p&&p.difficulties[difficulty.value];
   if(!grade.value||!p||!d){error.textContent='学年・相談テーマ・困っている場面を選んでください。';(!grade.value?grade:!p?theme:difficulty).focus();return;}
   error.textContent='';
   document.getElementById('check-result-title').textContent=d[1];
   document.getElementById('check-result-advice').textContent=d[2];
   document.getElementById('check-result-task').textContent=d[3];
   document.getElementById('check-result-confirm').textContent=d[4];
   const msg='学習チェックの結果を相談したいです。\n学年・立場：'+grade.options[grade.selectedIndex].text+'\nテーマ：'+p.label+'\n困っている場面：'+d[0]+'\nまず試すこと：'+d[3];
   document.getElementById('check-result-copy').value=msg;
   const line=document.getElementById('check-result-line');
   line.href='https://line.me/R/oaMessage/%40670gzfpd/?'+encodeURIComponent(p.keyword);
   line.textContent='LINEで「'+p.keyword+'」を送る';
   document.getElementById('check-result-guide').href=p.guide;
   document.getElementById('check-result-service').href=p.link;
   document.getElementById('check-result-keyword').textContent=p.keyword;
   document.getElementById('check-copy-status').textContent='';
   result.hidden=false;
   const title=document.getElementById('check-result-title');title.focus({preventScroll:true});
   result.scrollIntoView({behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'auto':'smooth',block:'start'});
  });
  form.addEventListener('reset',()=>{setTimeout(()=>{sync();document.getElementById('check-copy-status').textContent='';},0);});
 }
 document.querySelectorAll('[data-r21-copy]').forEach(button=>button.addEventListener('click',async()=>{
  const field=document.getElementById(button.dataset.r21Copy),status=document.getElementById(button.dataset.r21Status);
  status.textContent='コピーしています…';
  try{
   await Promise.race([navigator.clipboard.writeText(field.value),new Promise((_,reject)=>setTimeout(()=>reject(Error('timeout')),1500))]);
   status.textContent='コピーしました。内容を確認して、ご自身で貼り付け・送信してください。';
  }catch(_){field.focus();field.select();status.textContent='自動コピーできませんでした。選択された文章を手動でコピーしてください。';}
 }));
 const printButton=document.getElementById('check-print');
 if(printButton)printButton.addEventListener('click',()=>window.print());
 const share=document.getElementById('parent-share');
 if(share)share.addEventListener('click',async()=>{
  const status=document.getElementById('parent-share-status');
  if(!navigator.share){status.textContent='このブラウザでは共有画面を開けません。下の文章をコピーして転送できます。';return;}
  try{await navigator.share({title:'黒田塾｜保護者の方へ',text:'英語・数学・中学受験の宿題で困っている方へ。指導例・料金・30分の無料相談を確認できます。',url:'https://kurodaschool.jp/for-parents/'});status.textContent='共有画面を閉じました。送信先や送信結果は、このページでは確認しません。';}
  catch(e){status.textContent=e.name==='AbortError'?'共有を中止しました。':'共有画面を開けませんでした。下の文章をコピーして転送できます。';}
 });
})();
