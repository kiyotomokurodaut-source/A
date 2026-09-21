/* Learning reflection, not an automated ability assessment. No network or storage. */
(() => {
  'use strict';
  const root = document.getElementById('reading-check');
  if (!root) return;
  const byId = id => document.getElementById(id);
  const fields = [1,2,3,4,5,6].map(i => byId('reading-status-' + i));
  const labels = {'': '未確認', explained: '根拠まで説明できた', answer: '答えは合ったが根拠が曖昧', missed: '読み違えた'};
  const groups = [
    {name:'一文の構造', ids:[0,3], next:'名詞への説明を括弧に入れ、文全体の主語と動詞を結んでください。誰が何を予想・実行したかを、別の短文でも説明します。'},
    {name:'指示語・省略', ids:[1,4], next:'this・theyが受ける内容と、didが表す動作を具体的に補ってください。主語と肯定・否定を保ったまま前後につながるか確認します。'},
    {name:'段落の論理', ids:[2,5], next:'各文を目的・結果・問題・対応に分けてください。改善した点と残った問題、対策の導入と実施後の成果を混同していないか確認します。'}
  ];
  const out = byId('reading-memo'), message = byId('reading-status'), result = byId('reading-result');
  let dirty = true;
  const say = s => {message.textContent = s;};
  const stale = () => {dirty = true; if (out.value) say('記録を変更しました。「復習の候補を整理する」で結果とメモを更新してください。');};
  fields.forEach(f => f.addEventListener('change', stale));
  byId('reading-note').addEventListener('input', stale);
  byId('reading-build').addEventListener('click', () => {
    const statuses = fields.map(f => Object.hasOwn(labels, f.value) ? f.value : '');
    const completed = statuses.filter(Boolean).length;
    result.replaceChildren();
    if (!completed) {out.value='';dirty=true;say('まだ確認の記録がありません。1問以上、解説と照合して状態を選んでください。');return;}
    const heading = document.createElement('p');
    heading.textContent = `確認の記録：${completed}/6問。未確認は${6-completed}問です。未確認の問題を誤答には数えていません。`;
    result.append(heading);
    const rows = [];
    for (const g of groups) {
      const recorded = g.ids.filter(i => statuses[i]);
      if (!recorded.length) continue;
      const weak = recorded.filter(i => statuses[i] !== 'explained');
      let text;
      if (weak.length) {
        text = `${g.name}（例題${weak.map(i=>i+1).join('・')}）：${g.next}`;
        if (g.ids.some(i => !statuses[i])) text += ' この分野でもう一方の問題は未確認です。';
      } else if (recorded.length < 2) {
        text = `${g.name}：記録した問題では根拠を説明できています。もう一方の問題でも、同じ読み方を使えるか確かめてください。`;
      } else {
        text = `${g.name}：2問とも根拠を説明できたという自己記録です。次は普段の長文で、同じ読み方を使えるか確かめてください。`;
      }
      rows.push(text); const p = document.createElement('p'); p.textContent = text; result.append(p);
    }
    const caution = document.createElement('p');
    caution.textContent = 'この結果は選んだ自己記録の整理です。記述答案の自動採点、偏差値・英語力・合格可能性の判定ではありません。';
    result.append(caution);
    const notes = byId('reading-note').value.trim();
    out.value = '黒田塾｜英語の読み方チェック6問\nhttps://kiyotomokuroda.pages.dev/study-guides/english-reading-diagnosis/\n\n' + statuses.map((s,i)=>`例題${i+1}：${labels[s]}`).join('\n') + '\n\n【次の復習の候補】\n' + rows.join('\n\n') + (notes ? '\n\n【自分のメモ】\n'+notes : '') + '\n\n※自己記録の整理であり、学力判定・自動採点ではありません。';
    dirty=false;say('復習の候補を整理しました。メモは編集して保存できます。入力内容は外部へ送信していません。');
  });
  const ready = () => {
    if (dirty || !out.value.trim()) {say('先に「復習の候補を整理する」を押し、最新の記録をメモに反映してください。');return false;}
    return true;
  };
  byId('reading-copy').addEventListener('click', async () => {
    if (!ready()) return;
    try {if (!navigator.clipboard || !window.isSecureContext) throw Error(); await navigator.clipboard.writeText(out.value);say('メモをコピーしました。共有する相手と内容を確認してください。');}
    catch (_) {out.focus();out.select();out.setSelectionRange(0,out.value.length);say('自動コピーを利用できません。選択された文章を端末の操作でコピーしてください。');}
  });
  byId('reading-save').addEventListener('click', () => {
    if (!ready()) return;
    const url=URL.createObjectURL(new Blob(['\ufeff',out.value], {type:'text/plain;charset=utf-8'}));
    const a=document.createElement('a'); a.href=url;a.download='kurodajuku-english-reading-memo.txt';document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),2000);
    say('テキストの保存を開始しました。共有端末では保存先に注意してください。');
  });
  byId('reading-clear').addEventListener('click', () => {
    if ((fields.some(f=>f.value)||out.value||byId('reading-note').value) && !window.confirm('このページの自己記録とメモを消しますか？')) return;
    fields.forEach(f=>f.value='');byId('reading-note').value='';out.value='';result.replaceChildren();dirty=true;say('自己記録とメモを消しました。');
  });
  root.hidden=false;
})();
