/* Kuroda Juku r15. No network requests; explicit local storage only. */
(() => {
  'use strict';
  const fieldNames = ['problem','cause','trigger','action','criterion','reviewDate'];
  const labels = ['問題・教材','止まった場所','気づく条件','次の練習','終了条件','再確認日'];
  document.querySelectorAll('[data-review-worksheet]').forEach((root) => {
    const status = root.querySelector('[data-review-status]');
    const key = `kurodajuku.review.v1:${location.pathname}`;
    const fields = fieldNames.map(name => root.querySelector(`[name="${name}"]`));
    if (fields.some(el => !el) || !status) return;
    const read = () => Object.fromEntries(fieldNames.map((name,i) => [name,fields[i].value.slice(0,600)]));
    const say = text => { status.textContent = text; };
    root.querySelectorAll('[data-review-action]').forEach(button => {
      button.addEventListener('click', () => {
        const action = button.dataset.reviewAction;
        if (action === 'save') {
          try { localStorage.setItem(key, JSON.stringify({version:1,fields:read()})); say('このブラウザーに保存しました。サーバーには送信していません。'); }
          catch (_) { say('このブラウザーでは保存できません。テキストで保存するか、書き写してください。'); }
        } else if (action === 'load') {
          try {
            const raw = localStorage.getItem(key);
            if (!raw) { say('このページで保存した内容はありません。'); return; }
            const data = JSON.parse(raw);
            if (data.version !== 1 || typeof data.fields !== 'object' || !data.fields) throw new Error('Invalid data');
            fields.forEach((field,i) => { field.value = typeof data.fields[fieldNames[i]] === 'string' ? data.fields[fieldNames[i]].slice(0,600) : ''; });
            say('このページで保存した内容を読み込みました。');
          } catch (_) { say('保存した内容を読み込めませんでした。入力欄の内容は手元で確認してください。'); }
        } else if (action === 'clear') {
          try { localStorage.removeItem(key); say('このページの端末内保存を削除しました。現在の入力欄は残しています。'); }
          catch (_) { say('端末内保存を削除できませんでした。ブラウザーの設定を確認してください。'); }
        } else if (action === 'download') {
          try {
            const data = read();
            const text = `黒田塾 復習記録\n参照ページ：${location.origin}${location.pathname}\n\n` + fieldNames.map((name,i) => `${labels[i]}\n${data[name]}\n`).join('\n');
            const url = URL.createObjectURL(new Blob(['\uFEFF',text], {type:'text/plain;charset=utf-8'}));
            const a = document.createElement('a'); a.href = url; a.download = 'kurodajuku-review.txt';
            document.body.append(a); a.click(); a.remove(); setTimeout(() => URL.revokeObjectURL(url),1000);
            say('テキスト保存を開始しました。保存先はブラウザーで確認してください。');
          } catch (_) { say('テキスト保存を開始できませんでした。入力内容を書き写してください。'); }
        } else if (action === 'print') {
          window.print();
        }
      });
    });
  });
  const display = document.getElementById('timer-display');
  const start = document.getElementById('timer-start');
  const stop = document.getElementById('timer-stop');
  const reset = document.getElementById('timer-reset');
  if (display && start && stop && reset) {
    let elapsed = 0, began = 0, interval = null;
    const update = () => {
      const seconds = Math.floor((elapsed + (interval === null ? 0 : performance.now()-began))/1000);
      display.textContent = `${Math.floor(seconds/60).toString().padStart(2,'0')}:${(seconds%60).toString().padStart(2,'0')}`;
    };
    stop.disabled = true;
    start.addEventListener('click', () => { if(interval !== null)return; began=performance.now(); interval=setInterval(update,200); start.disabled=true; stop.disabled=false; });
    stop.addEventListener('click', () => { if(interval===null)return; elapsed+=performance.now()-began; clearInterval(interval);interval=null;update();start.disabled=false;start.textContent='計測を再開する';stop.disabled=true; });
    reset.addEventListener('click', () => { if(interval!==null)clearInterval(interval); interval=null;elapsed=0;began=0;update();start.disabled=false;start.textContent='時間計測を始める';stop.disabled=true; });
  }
  const drill = document.querySelector('[data-reading-drill]');
  const grade = document.getElementById('grade-drill');
  if (drill && grade) {
    grade.addEventListener('click', () => {
      const correct = {q1:'a',q2:'b',q3:'b'};
      const notes = {q1:'集合時刻と出発時刻を分ける',q2:'総額と追加の差額を分ける',q3:'大雨の場合の変更条件をたどる'};
      let score=0;const missing=[];const feedback=[];
      Object.entries(correct).forEach(([name,answer],i) => {
        const chosen=drill.querySelector(`input[name="${name}"]:checked`);
        if(!chosen)missing.push(`Q${i+1}`);
        else if(chosen.value===answer)score++;
        else feedback.push(`Q${i+1}：${notes[name]}`);
      });
      const result=document.getElementById('drill-result');
      if(missing.length) { result.textContent=`未回答：${missing.join('・')}。3問すべてに答えてから採点してください。`; return; }
      result.textContent=`3問中${score}問正解。`+(feedback.length?`復習：${feedback.join('／')}。`:'次は正解の根拠と、誤った選択肢の違いを説明してください。')+'この3問は本番の得点や合格可能性を判定するものではありません。';
      const explanation=document.getElementById('drill-explanations');if(explanation)explanation.open=true;
    });
  }
})();
/* Print values without depending on textarea clipping. */
addEventListener('beforeprint', () => {
  document.querySelectorAll('[data-review-worksheet] input,[data-review-worksheet] textarea,[data-review-worksheet] select').forEach(field => {
    let span=field.nextElementSibling;
    if(!span || !span.classList.contains('r15-print-field')){span=document.createElement('span');span.className='r15-print-field';field.after(span);}
    span.textContent=field.value||'（未記入）';
  });
});
