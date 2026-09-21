/* Local-only worksheet: no network, analytics, cookies or browser storage. */
(() => {
  'use strict';
  const root = document.getElementById('review-workspace');
  if (!root) return;
  const summary = document.getElementById('review-summary');
  const status = document.getElementById('review-action-status');
  const rows = [...root.querySelectorAll('.review-row')];
  const causeNames = {
    knowledge: '知識を取り出せない', strategy: '方針を選べない',
    processing: '計算・処理で崩れる', reading: '読み取り・記述を外す',
    timing: '時間配分で未完になる', unknown: '原因はまだ不明'
  };
  const get = (row, field) => row.querySelector(`[data-field="${field}"]`);
  const numberText = n => String(Math.round(n * 2) / 2);
  const collect = () => rows.map((row, i) => {
    const data = { row: i + 1 };
    ['question', 'max', 'score', 'cause', 'evidence', 'next'].forEach(field => {
      data[field] = get(row, field).value.trim();
    });
    return data;
  });
  function calculate(focusErrors = false) {
    root.querySelectorAll('[aria-invalid]').forEach(e => e.removeAttribute('aria-invalid'));
    const data = collect().filter(row => ['question', 'max', 'score', 'cause', 'evidence', 'next'].some(k => row[k] !== ''));
    const errors = [];
    let first = null;
    const invalid = (d, field, message) => {
      const e = get(rows[d.row - 1], field);
      e.setAttribute('aria-invalid', 'true');
      if (!first) first = e;
      errors.push(`記録${d.row}：${message}`);
    };
    const isMark = s => s !== '' && Number.isFinite(Number(s)) && Number(s) >= 0 && Number(s) <= 1000 && Number.isInteger(Number(s) * 2);
    for (const d of data) {
      if (!d.question) invalid(d, 'question', '設問名を記入してください。');
      if (!isMark(d.max)) invalid(d, 'max', '配点を0〜1000の0.5刻みで入力してください。');
      if (!isMark(d.score)) invalid(d, 'score', '得点を0〜1000の0.5刻みで入力してください。未採点の設問はこの記録から外して集計してください。');
      if (isMark(d.max) && isMark(d.score) && Number(d.score) > Number(d.max)) invalid(d, 'score', '得点が配点を超えています。');
      if (!Object.hasOwn(causeNames, d.cause)) invalid(d, 'cause', '主な原因を選んでください。決められない場合は「原因はまだ不明」を選べます。');
    }
    if (errors.length) {
      summary.textContent = `集計できません。\n${errors.join('\n')}`;
      if (focusErrors && first) first.focus();
      return false;
    }
    if (!data.length) {
      summary.textContent = 'まだ記録がありません。設問名・配点・得点・主な原因を記入してください。';
      return false;
    }
    let max = 0, score = 0;
    const byCause = {};
    data.forEach(d => {
      max += Number(d.max); score += Number(d.score);
      byCause[d.cause] = (byCause[d.cause] || 0) + Number(d.max) - Number(d.score);
    });
    const lines = [`記録した${data.length}問：配点${numberText(max)}点／得点${numberText(score)}点／失点${numberText(max - score)}点。`];
    Object.keys(causeNames).forEach(c => {
      if (Object.hasOwn(byCause, c)) lines.push(`${causeNames[c]}：${numberText(byCause[c])}点`);
    });
    lines.push('入力した設問だけの集計です。原因は仮の分類です。模試全体の弱点割合や、回復できる点数を表すものではありません。');
    summary.textContent = lines.join('\n');
    return true;
  }
  document.getElementById('review-calculate').addEventListener('click', () => calculate(true));
  // Invalidate a stale total as soon as its inputs change.
  rows.forEach(row => row.addEventListener('input', () => { summary.textContent = '記録を変更しました。再度「記録した設問の失点を集計する」を押してください。'; }));
  document.getElementById('review-export').addEventListener('click', () => {
    calculate(false);
    const lines = ['黒田塾｜模試の復習・失点原因整理シート', document.getElementById('review-label').value, ''];
    collect().filter(d => ['question', 'max', 'score', 'cause', 'evidence', 'next'].some(k => d[k] !== '')).forEach(d => {
      lines.push(`【記録${d.row}】${d.question || '（設問名なし）'}`, `配点：${d.max || '未入力'}／得点：${d.score || '未入力'}`,
        `主な原因：${causeNames[d.cause] || '未選択'}`, `根拠・別の原因：${d.evidence}`, `次にすること：${d.next}`, '');
    });
    lines.push('【集計】', summary.textContent, '', '【今週優先する課題】', document.getElementById('review-week').value,
      '', 'このファイルは端末上で生成されました。サイトへの入力内容の送信は行っていません。');
    const blob = new Blob(['\uFEFF' + lines.join('\n')], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = 'kurodajuku-mock-review.txt';
    document.body.append(a); a.click(); a.remove();
    window.setTimeout(() => URL.revokeObjectURL(url), 30000);
    status.textContent = 'テキストファイルの保存を開始しました。保存先はブラウザーの設定で確認してください。';
  });
  document.getElementById('review-print').addEventListener('click', () => { calculate(false); window.print(); });
})();
