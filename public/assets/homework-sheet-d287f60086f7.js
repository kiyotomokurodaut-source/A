(()=>{
 const sheet=document.getElementById('homework-sheet');
 const rows=[...sheet.querySelectorAll('.homework-task')];
 const out=document.getElementById('homework-total');
 function update(){
  const times=[...sheet.querySelectorAll('input[type=number]')];
  if(times.some(x=>x.validity.badInput||(x.value!==''&&!x.validity.valid))){out.textContent='時間は0〜10080の整数で入力してください。';return;}
  const pairs=rows.filter(r=>r.querySelector('.planned').value!==''&&r.querySelector('.actual').value!=='');
  const planned=times.filter(x=>x.classList.contains('planned')&&x.value!=='').reduce((s,x)=>s+Number(x.value),0);
  const actual=times.filter(x=>x.classList.contains('actual')&&x.value!=='').reduce((s,x)=>s+Number(x.value),0);
  if(times.every(x=>x.value==='')){out.textContent='予定時間と実際の時間を入力すると、記録した課題の合計と差を表示します。';return;}
  const difference=pairs.reduce((s,r)=>s+Number(r.querySelector('.actual').value)-Number(r.querySelector('.planned').value),0);
  const comparison=pairs.length===0?'予定と実際の両方を記録した課題はまだありません。':`両方を記録した${pairs.length}課題の合計は、${difference===0?'予定と同じです':`実際の時間が予定より${Math.abs(difference)}分${difference>0?'長く':'短く'}なっています`}。`;
  out.textContent=`入力済みの予定：${planned}分。入力済みの実際：${actual}分。${comparison}`;
 }
 sheet.addEventListener('input',e=>{if(e.target.tagName==='TEXTAREA'){e.target.style.height='auto';e.target.style.height=e.target.scrollHeight+'px';}update();});
 document.getElementById('print-homework').addEventListener('click',()=>window.print());
 update();
})();
