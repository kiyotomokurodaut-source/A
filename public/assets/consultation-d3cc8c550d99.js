(() => {
'use strict';
const byId=id=>document.getElementById(id);if(!byId('consultation-form'))return;
const fields=[['consult-stage','学年・受験までの時期'],['consult-goal','目標・相談したい方向性'],['consult-current','今の学習環境'],['consult-trouble','一番困っている場面'],['consult-support','検討している支援'],['consult-topic','相談のきっかけ']];
const output=byId('consult-output'),status=byId('consult-status'),say=text=>{status.textContent=text;};
for(const[id]of fields)byId(id).addEventListener('input',()=>{if(output.value.trim())say('入力が変わりました。「相談文を作る」を押すと手編集した文章も上書きされます。');});
byId('consult-build').addEventListener('click',()=>{const parts=fields.map(([id,label])=>[label,byId(id).value.trim()]).filter(([,v])=>v);if(!parts.length){say('まだ入力がありません。困っていることを一つ記入してください。');return;}output.value='黒田塾の無料相談を希望しています。\n\n'+parts.map(([label,value])=>'【'+label+'】\n'+value).join('\n\n')+'\n\n現在の状況に合う支援について相談したいです。';say('相談文を作成しました。確認して編集できます。外部への送信はしていません。');});
byId('consult-copy').addEventListener('click',async()=>{if(!output.value.trim()){say('先に相談文を作るか、相談文の欄に記入してください。');return;}try{if(!navigator.clipboard||!window.isSecureContext)throw Error('clipboard unavailable');await navigator.clipboard.writeText(output.value);say('コピーしました。LINEで送信先と内容を確認して貼り付けてください。');}catch(_){output.focus();output.select();output.setSelectionRange(0,output.value.length);say('自動コピーを利用できません。選択された文章を端末の操作でコピーしてください。');}});
byId('consult-save').addEventListener('click',()=>{if(!output.value.trim()){say('保存する相談文がまだありません。');return;}const url=URL.createObjectURL(new Blob(['\ufeff',output.value],{type:'text/plain;charset=utf-8'}));const a=document.createElement('a');a.href=url;a.download='kurodajuku-consultation.txt';document.body.appendChild(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),2000);say('テキストの保存を開始しました。共有端末では保存先に注意してください。');});
byId('consult-clear').addEventListener('click',()=>{if((output.value||fields.some(([id])=>byId(id).value))&&!window.confirm('入力と相談文をすべて消しますか？'))return;for(const[id]of fields)byId(id).value='';output.value='';say('入力と相談文を消しました。');});
})();
