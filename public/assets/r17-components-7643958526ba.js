/* Search/memo run only in this browser; no requests, cookies or storage. */
(() => {
  'use strict';
  const normalize = (s) => String(s || '').normalize('NFKC').toLocaleLowerCase('ja').trim();
  const finder = document.querySelector('[data-r17-finder]');
  if (finder) {
    const input = finder.querySelector('[data-r17-query]');
    const group = finder.querySelector('[data-r17-category]');
    const cards = Array.from(document.querySelectorAll('[data-r17-card]'));
    const status = finder.querySelector('[data-r17-status]');
    const empty = document.querySelector('[data-r17-empty]');
    const update = () => {
      const terms = normalize(input.value).split(/\s+/).filter(Boolean);
      let count = 0;
      for (const card of cards) {
        const text = normalize(card.textContent);
        const shown = (!group.value || card.dataset.category === group.value) && terms.every((t) => text.includes(t));
        card.hidden = !shown;
        if (shown) count++;
      }
      status.textContent = `${cards.length}件中${count}件を表示しています。`;
      if (empty) empty.hidden = count !== 0;
    };
    input.addEventListener('input', update);
    group.addEventListener('change', update);
    finder.querySelector('[data-r17-reset]').addEventListener('click', () => {
      input.value = ''; group.value = ''; update(); input.focus();
    });
    update();
  }
  for (const memo of document.querySelectorAll('[data-r17-memo]')) {
    const issue = memo.querySelector('[data-r17-issue]');
    const materials = memo.querySelector('[data-r17-materials]');
    const output = memo.querySelector('[data-r17-output]');
    const status = memo.querySelector('[data-r17-copy-status]');
    const title = document.querySelector('h1')?.textContent?.trim() || '学習ガイド';
    const canonical = document.querySelector('link[rel="canonical"]')?.href || location.origin + location.pathname;
    const update = () => {
      output.value = `黒田塾の無料相談について\n読んだページ：${title}\n${canonical}\n\n困っていること：${issue.value.trim() || '（ここに記入）'}\n現在の教材・授業：${materials.value.trim() || '（分かる範囲で記入）'}\n\n次に取り組む課題を相談したいです。`;
      status.textContent = '';
    };
    issue.addEventListener('input', update); materials.addEventListener('input', update); update();
    memo.querySelector('[data-r17-copy]').addEventListener('click', async () => {
      try {
        if (!navigator.clipboard?.writeText) throw new Error('clipboard unavailable');
        await navigator.clipboard.writeText(output.value);
        status.textContent = 'コピーしました。内容を確認し、LINEにご自身で貼り付けて送信してください。';
      } catch (_) {
        output.focus(); output.select();
        status.textContent = '文章を選択しました。端末の「コピー」を使ってください。';
      }
    });
  }
})();
