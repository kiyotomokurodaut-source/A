(function () {
  'use strict';

  const calculator = document.querySelector('[data-price-calculator]');
  if (!calculator) return;

  const prices = Object.freeze({1: 20000, 3: 57000, 5: 92500, 10: 180000, 19: 297000});
  const countInput = document.getElementById('set-count');
  const friendInput = document.getElementById('friend-discount');
  const label = document.getElementById('quote-label');
  const totalOutput = document.getElementById('quote-total');
  const averageOutput = document.getElementById('quote-average');
  const discountOutput = document.getElementById('quote-discount');
  const message = document.getElementById('consultation-text');
  const copyButton = document.getElementById('copy-consultation');
  const copyStatus = document.getElementById('copy-status');
  const format = new Intl.NumberFormat('ja-JP');

  function updateQuote() {
    const count = Number(countInput.value);
    if (!Object.prototype.hasOwnProperty.call(prices, count)) return;
    const base = prices[count];
    const friend = friendInput.checked;
    const total = friend ? Math.round(base * 0.9) : base;
    const average = total / count;
    label.textContent = count + '科目セット' + (friend ? '・友だち割' : '') + '・税込';
    const yen = document.createElement('span');
    yen.textContent = '円';
    totalOutput.replaceChildren(document.createTextNode(format.format(total)), yen);
    averageOutput.textContent = '1科目あたり' + (Number.isInteger(average) ? '' : '約') + format.format(Math.round(average)) + '円';
    discountOutput.hidden = !friend;
    discountOutput.textContent = friend ? 'セット価格' + format.format(base) + '円から' + format.format(base - total) + '円引き' : '';
    if (message) {
      message.value = [
        '購入相談',
        '希望セット：' + count + '個セット',
        count === 19 ? '希望科目：全19科目（使う予定の科目：）' : '希望科目：',
        '学年／受験予定年度：',
        '志望大学・学部：',
        '現在使っている教材：',
        '友だち割：' + (friend ? '希望あり' : '希望なし')
      ].join('\n');
    }
    if (copyStatus) copyStatus.textContent = '';
  }

  countInput.addEventListener('change', updateQuote);
  friendInput.addEventListener('change', updateQuote);
  updateQuote();

  if (copyButton && message && copyStatus) {
    copyButton.addEventListener('click', async function () {
      try {
        if (!navigator.clipboard || !navigator.clipboard.writeText) throw new Error('Clipboard unavailable');
        await navigator.clipboard.writeText(message.value);
        copyStatus.textContent = '相談文をコピーしました。LINEに貼り付け、希望科目などを書き足してください。';
      } catch (_) {
        message.focus();
        message.select();
        message.setSelectionRange(0, message.value.length);
        copyStatus.textContent = '相談文を選択しました。お使いの端末のコピー操作でコピーし、LINEに貼り付けてください。';
      }
    });
  }
}());
