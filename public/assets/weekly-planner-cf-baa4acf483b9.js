/* Weekly study planner. User data never leave this document automatically. */
(function(root){
'use strict';
const DAYS=['mon','tue','wed','thu','fri','sat','sun'];
const DAY_NAMES=['月','火','水','木','金','土','日'];
const STATES={planned:'未着手',working:'途中',checked:'自力で再確認済み',review:'再確認が必要'};
const MAX_TASKS=14, FORMAT='kuroda-weekly-plan', VERSION=1;
function minutes(v,label,max=1440){
 if(v===''||v===null||v===undefined)return null;
 const s=String(v);if(!/^\d+$/.test(s)||Number(s)>max)throw Error(label+'は0〜'+max+'の整数で入力してください。');
 return Number(s);
}
function string(v,max,label){if(typeof v!=='string'||v.length>max)throw Error(label+'の形式・文字数を確認してください。');return v;}
function normalize(data){
 if(!data||typeof data!=='object'||Array.isArray(data)||data.format!==FORMAT||data.version!==VERSION)throw Error('このプランナーの保存ファイル（version 1）ではありません。');
 const c=data.capacity;if(!c||!Array.isArray(c.overrides)||c.overrides.length!==7)throw Error('曜日別時間の形式が正しくありません。');
 const weekday=minutes(c.weekday,'平日の時間'),weekend=minutes(c.weekend,'休日の時間'),reserve=minutes(c.reserve,'予備割合',100);
 if([weekday,weekend,reserve].some(x=>x===null))throw Error('平日・休日・予備割合をすべて入力してください。');
 const overrides=c.overrides.map((x,i)=>minutes(x,DAY_NAMES[i]+'曜の時間'));
 if(!Array.isArray(data.tasks)||data.tasks.length>MAX_TASKS)throw Error('課題は14件以内にしてください。');
 const tasks=data.tasks.map((t,i)=>{
  if(!t||typeof t!=='object'||Array.isArray(t))throw Error('課題の形式が正しくありません。');
  const name=string(t.name,140,'課題名'),goal=string(t.goal,250,'終了条件');
  if(!['unassigned',...DAYS].includes(t.day)||!Object.hasOwn(STATES,t.status))throw Error('曜日・確認状態の形式が正しくありません。');
  return {name,goal,day:t.day,planned:minutes(t.planned,'課題'+(i+1)+'の予定時間'),actual:minutes(t.actual,'課題'+(i+1)+'の実績時間'),status:t.status};
 });
 return {format:FORMAT,version:VERSION,label:string(data.label,60,'週のメモ'),note:string(data.note,2000,'振り返り'),capacity:{weekday,weekend,reserve,overrides},tasks};
}
function active(t){return !!(t.name.trim()||t.goal.trim()||t.day!=='unassigned'||t.planned!==null||t.actual!==null||t.status!=='planned');}
function calculate(raw){
 const s=normalize(raw),tasks=s.tasks.filter(active),available=DAYS.map((_,i)=>s.capacity.overrides[i]===null?(i<5?s.capacity.weekday:s.capacity.weekend):s.capacity.overrides[i]);
 const total=available.reduce((a,b)=>a+b,0),reserve=Math.round(total*s.capacity.reserve/100),budget=total-reserve;
 let planned=0,actual=0,actualCount=0,unknownPlan=0,unknownDay=0,comparablePlan=0,comparableActual=0,comparableCount=0;
 const daily=available.map((v,i)=>({day:DAYS[i],available:v,planned:0,unknown:0}));
 tasks.forEach(t=>{if(t.planned===null)unknownPlan++;else planned+=t.planned;
  if(t.actual!==null){actual+=t.actual;actualCount++;}
  if(t.day==='unassigned')unknownDay++;
  else{const d=daily[DAYS.indexOf(t.day)];if(t.planned===null)d.unknown++;else d.planned+=t.planned;}
  if(t.planned!==null&&t.actual!==null){comparablePlan+=t.planned;comparableActual+=t.actual;comparableCount++;}
 });
 return {state:s,tasks,total,reserve,budget,planned,actual,actualCount,unknownPlan,unknownDay,remaining:budget-planned,daily,overDays:daily.filter(d=>d.planned>d.available),comparableCount,comparablePlan,comparableActual};
}
function fmt(n){return Math.floor(n/60)+'時間'+(n%60)+'分';}
function summary(r){
 if(!r.tasks.length)return '課題はまだ未入力です。自習枠'+fmt(r.total)+'のうち、予備'+fmt(r.reserve)+'を残し、課題に使える時間は'+fmt(r.budget)+'です。';
 const p=['自習枠 '+fmt(r.total)+'／予備 '+fmt(r.reserve)+'／課題の上限 '+fmt(r.budget),'記入済みの予定 '+fmt(r.planned)+'（'+r.tasks.length+'課題）'];
 if(r.remaining<0)p.push('週の上限を'+fmt(-r.remaining)+'超えています。課題を分ける・別の週へ回す・優先順位を相談する必要があります。');
 else if(r.unknownPlan)p.push('所要時間が未入力の課題が'+r.unknownPlan+'件あります。「収まる」とはまだ判断できません。');
 else p.push('週の上限との差は'+fmt(r.remaining)+'です。これとは別に、曜日ごとの偏りも確認してください。');
 if(r.overDays.length)p.push('曜日別の超過：'+r.overDays.map(d=>DAY_NAMES[DAYS.indexOf(d.day)]+'曜 '+(d.planned-d.available)+'分').join('、')+'。');
 if(r.unknownDay)p.push('曜日が未定の課題：'+r.unknownDay+'件。週合計には含め、曜日別には配分していません。');
 p.push(r.actualCount?'実績は記録した'+r.actualCount+'件で'+fmt(r.actual)+'。未入力の実績は0分扱いにしません。':'実績の記録はありません。0分として判定していません。');
 if(r.comparableCount)p.push('予定と実績が両方ある'+r.comparableCount+'件だけの差：'+(r.comparableActual-r.comparablePlan>=0?'+':'')+(r.comparableActual-r.comparablePlan)+'分。');
 return p.join('\n');
}
function report(r){
 const lines=['黒田塾｜週間学習プラン',r.state.label||'週のメモ：未入力',summary(r),'','曜日ごとの計画（予備は週全体で確保）'];
 r.daily.forEach((d,i)=>lines.push(DAY_NAMES[i]+'曜：自習枠'+d.available+'分／記入済み予定'+d.planned+'分'+(d.unknown?'／時間未入力'+d.unknown+'件':'')));
 lines.push('','課題・終了条件・確認状態');
 r.tasks.forEach((t,i)=>{lines.push((i+1)+'. '+(t.name||'課題名未入力')+' ['+(t.day==='unassigned'?'曜日未定':DAY_NAMES[DAYS.indexOf(t.day)]+'曜')+']');lines.push('終了条件：'+(t.goal||'未入力'));lines.push('予定：'+(t.planned===null?'未入力':t.planned+'分')+'／実績：'+(t.actual===null?'未記録':t.actual+'分')+'／状態：'+STATES[t.status]);});
 lines.push('','週末の振り返り',r.state.note||'未入力','','時間と自己記録を整理する道具です。理解度・努力・合格可能性を判定しません。','https://kurodaschool.jp/study-guides/weekly-study-plan/');
 return lines.join('\n');
}
const core={normalize,calculate,summary,report,fmt,DAYS,DAY_NAMES,STATES};
if(typeof module==='object'&&module.exports){module.exports=core;return;}
root.KurodaWeeklyPlanner=core;
const app=document.getElementById('weekly-planner');if(!app)return;
const $=id=>document.getElementById(id),cards=$('planner-tasks'),message=$('planner-message');
const cap=[$('weekday-minutes'),$('weekend-minutes'),$('reserve-percent')];let id=0;
function taskCard(t={name:'',goal:'',day:'unassigned',planned:null,actual:null,status:'planned'}){
 const frag=$('planner-task-template').content.cloneNode(true),card=frag.querySelector('fieldset');id++;
 card.dataset.card=String(id);card.querySelector('legend').textContent='課題 '+id;
 for(const key of ['name','goal','day','planned','actual','status']){
  const field=card.querySelector('[data-field="'+key+'"]');field.value=t[key]===null?'':t[key];field.id='planner-task-'+id+'-'+key;field.closest('label').htmlFor=field.id;
 }
 card.querySelector('[data-remove]').addEventListener('click',()=>{const t=taskValue(card);if(active(t)&&!confirm('この課題を削除しますか？'))return;card.remove();refresh();$('planner-add').focus();});
 cards.append(frag);
}
function taskValue(card){const get=k=>card.querySelector('[data-field="'+k+'"]').value;return {name:get('name'),goal:get('goal'),day:get('day'),planned:get('planned')===''?null:get('planned'),actual:get('actual')===''?null:get('actual'),status:get('status')};}
function raw(){return {format:FORMAT,version:VERSION,label:$('planner-label').value,note:$('planner-note').value,capacity:{weekday:cap[0].value,weekend:cap[1].value,reserve:cap[2].value,overrides:DAYS.map(d=>$('planner-cap-'+d).value||null)},tasks:[...cards.querySelectorAll('fieldset')].map(taskValue)};}
function el(tag,text){const e=document.createElement(tag);if(text!==undefined)e.textContent=text;return e;}
function hasData(){const s=raw();return !!(s.label||s.note||s.tasks.some(active)||s.capacity.overrides.some(x=>x!==null)||String(s.capacity.weekday)!=='90'||String(s.capacity.weekend)!=='180'||String(s.capacity.reserve)!=='20');}
function renderPrint(r){const node=$('planner-print-sheet');node.replaceChildren();node.append(el('h2','週間学習プラン'),el('p',r.state.label||'週のメモ：未入力'),el('p',summary(r)));
 const table=el('table'),thead=el('thead'),h=el('tr');['曜日','自習枠','記入済み予定'].forEach(v=>h.append(el('th',v)));thead.append(h);table.append(thead);const body=el('tbody');r.daily.forEach((d,i)=>{const tr=el('tr');[DAY_NAMES[i],d.available+'分',d.planned+'分'+(d.unknown?'＋未入力'+d.unknown+'件':'')].forEach(v=>tr.append(el('td',v)));body.append(tr);});table.append(body);node.append(table);
 r.tasks.forEach((t,i)=>{const sec=el('section');sec.append(el('h2',(i+1)+'. '+(t.name||'課題名未入力')),el('p','終了条件：'+(t.goal||'未入力')),el('p',(t.day==='unassigned'?'曜日未定':DAY_NAMES[DAYS.indexOf(t.day)]+'曜')+'／予定 '+(t.planned===null?'未入力':t.planned+'分')+'／実績 '+(t.actual===null?'未記録':t.actual+'分')+'／'+STATES[t.status]));node.append(sec);});
 node.append(el('h2','振り返りと次の課題'),el('p',r.state.note||'未入力'),el('p','時間・自己記録を整理する道具です。理解度・努力・合格可能性を判定しません。'),el('p','https://kurodaschool.jp/study-guides/weekly-study-plan/'));
}
function refresh(){
 message.textContent='';$('planner-output').value='';$('planner-output-box').hidden=true;$('planner-add').disabled=cards.querySelectorAll('fieldset').length>=MAX_TASKS;
 try{const r=calculate(raw());$('planner-summary').textContent=summary(r);$('planner-summary').dataset.over=String(r.remaining<0||r.overDays.length>0);const tbody=$('planner-daily');tbody.replaceChildren();
  r.daily.forEach((d,i)=>{const tr=el('tr'),th=el('th',DAY_NAMES[i]+'曜');th.scope='row';tr.append(th,el('td',d.available+'分'),el('td',d.planned+'分'+(d.unknown?'＋未入力'+d.unknown+'件':'')),el('td',d.planned>d.available?(d.planned-d.available)+'分超過':d.unknown?'所要時間を確認':'—'));tbody.append(tr);});
  const missing=r.tasks.filter(t=>!t.name.trim()||!t.goal.trim()).length;$('planner-completion').textContent=missing?'課題名または終了条件が空欄の課題：'+missing+'件。時間内に何ができれば終わりかを具体化してください。':'時間内に終わったことと、自力で再現できたことは別です。各課題の確認状態を記録してください。';
  renderPrint(r);return r;
 }catch(e){$('planner-summary').textContent=e.message;$('planner-daily').replaceChildren();$('planner-completion').textContent='入力を直すまで、時間内に収まるか判定しません。';$('planner-print-sheet').replaceChildren();return null;}
}
function load(s){s=normalize(s);cap[0].value=s.capacity.weekday;cap[1].value=s.capacity.weekend;cap[2].value=s.capacity.reserve;DAYS.forEach((d,i)=>{$('planner-cap-'+d).value=s.capacity.overrides[i]===null?'':s.capacity.overrides[i];});$('planner-label').value=s.label;$('planner-note').value=s.note;cards.replaceChildren();id=0;(s.tasks.length?s.tasks:[{name:'',goal:'',day:'unassigned',planned:null,actual:null,status:'planned'}]).forEach(taskCard);cap[0].dispatchEvent(new Event('input',{bubbles:true}));refresh();}
function download(blob,name){const a=document.createElement('a'),url=URL.createObjectURL(blob);a.href=url;a.download=name;document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),1500);}
function need(){const r=refresh();if(!r){message.textContent='入力を直してから保存・印刷してください。';return null;}return r;}
app.addEventListener('input',e=>{if(e.target.id!=='planner-import')refresh();});app.addEventListener('change',e=>{if(e.target.id!=='planner-import')refresh();});cap.forEach(e=>e.addEventListener('input',refresh));
$('planner-add').addEventListener('click',()=>{if(cards.querySelectorAll('fieldset').length<MAX_TASKS){taskCard();refresh();cards.lastElementChild.querySelector('input').focus();}});
$('planner-example').addEventListener('click',()=>{if(hasData()&&!confirm('入力中の課題を、架空の記入例で置き換えますか？必要な内容は先に保存してください。'))return;load({format:FORMAT,version:VERSION,label:'架空の記入例（時間配分を確かめるための例）',note:'水曜日の数学を10分以上ほかの日に分ける。終了条件は時間ではなく、自力で説明できる内容で確認する。',capacity:{weekday:90,weekend:180,reserve:20,overrides:[null,null,null,null,null,null,null]},tasks:[{name:'英語：長文1題',goal:'指示語が表す内容と、誤答の根拠を説明する',day:'mon',planned:60,actual:70,status:'review'},{name:'数学：解き直し3問',goal:'方針を選ぶ理由を言葉で説明して解く',day:'wed',planned:100,actual:null,status:'planned'},{name:'国語：記述2問',goal:'本文の根拠を残して字数に収める',day:'fri',planned:80,actual:null,status:'planned'},{name:'数学：条件変更問題',goal:'条件が変わるとどの式を変えるか説明する',day:'sat',planned:180,actual:null,status:'planned'},{name:'英語：解き直しと音読',goal:'文の構造を確かめ、和訳を参照せず内容を説明する',day:'sun',planned:180,actual:null,status:'planned'}]});message.textContent='架空の記入例を読み込みました。週合計600分は上限648分内ですが、水曜日は10分超過しています。';});
$('planner-reset').addEventListener('click',()=>{if(hasData()&&!confirm('課題・振り返り・曜日別の時間をすべて消しますか？保存ファイルは削除しません。'))return;load({format:FORMAT,version:VERSION,label:'',note:'',capacity:{weekday:90,weekend:180,reserve:20,overrides:[null,null,null,null,null,null,null]},tasks:[]});message.textContent='この画面の計画を初期値に戻しました。';});
$('planner-export-json').addEventListener('click',()=>{const r=need();if(!r)return;download(new Blob([JSON.stringify(r.state,null,2)+'\n'],{type:'application/json;charset=utf-8'}),'kuroda-weekly-plan.json');message.textContent='計画ファイルの保存を開始しました。保存先はお使いのブラウザーで確認してください。';});
$('planner-export-text').addEventListener('click',()=>{const r=need();if(!r)return;download(new Blob([report(r)+'\n'],{type:'text/plain;charset=utf-8'}),'kuroda-weekly-plan.txt');message.textContent='メモの保存を開始しました。';});
$('planner-copy').addEventListener('click',async()=>{const r=need();if(!r)return;const text=report(r);$('planner-output').value=text;$('planner-output-box').hidden=false;try{if(!navigator.clipboard)throw Error();await navigator.clipboard.writeText(text);message.textContent='計画メモをコピーしました。';}catch(_){$('planner-output').focus();$('planner-output').select();message.textContent='下の計画メモを選択してコピーしてください。';}});
$('planner-import').addEventListener('change',async ev=>{const input=ev.target,file=input.files&&input.files[0];if(!file)return;try{if(file.size>65536)throw Error('読み込めるファイルは64KBまでです。');const parsed=normalize(JSON.parse(await file.text()));if(hasData()&&!confirm('現在の計画を保存ファイルの内容で置き換えますか？'))return;load(parsed);message.textContent='保存した計画を読み込みました。この操作で外部送信はしていません。';}catch(e){message.textContent='読込みできませんでした：'+e.message+' 現在の入力は保持しています。';}finally{input.value='';}});
$('planner-print').addEventListener('click',()=>{const r=need();if(!r)return;document.body.classList.add('planner-print-only');window.print();});
window.addEventListener('afterprint',()=>document.body.classList.remove('planner-print-only'));
const oldPrint=$('print-sheet');if(oldPrint)oldPrint.addEventListener('click',()=>document.body.classList.remove('planner-print-only'),{capture:true});
$('planner-controls').hidden=false;for(let i=0;i<3;i++)taskCard();refresh();
})(typeof globalThis!=='undefined'?globalThis:this);
