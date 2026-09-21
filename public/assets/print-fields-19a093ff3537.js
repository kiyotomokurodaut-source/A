/* Expose complete long answers in print without writing user input as HTML. */
(() => {
  'use strict';
  const temporarilyOpened = new Set();
  const sync = () => {
    document.querySelectorAll('main details:not([open])').forEach(e => { temporarilyOpened.add(e); e.open = true; });
    document.querySelectorAll('.print-value').forEach(e => e.remove());
    document.querySelectorAll('main textarea, main input, main select').forEach((e, i) => {
      if (e.type === 'hidden' || e.type === 'checkbox' || e.type === 'radio') return;
      const copy = document.createElement('div');
      copy.className = 'print-value';
      copy.setAttribute('aria-hidden', 'true');
      copy.dataset.printIndex = String(i);
      copy.textContent = e.tagName === 'SELECT' ? e.options[e.selectedIndex]?.text || '未選択' : e.value || '（未記入）';
      e.classList.add('print-field-original');
      e.insertAdjacentElement('afterend', copy);
    });
  };
  window.addEventListener('beforeprint', sync);
  window.addEventListener('afterprint', () => { temporarilyOpened.forEach(e => { e.open = false; }); temporarilyOpened.clear(); });
  // Kept in the DOM after printing, hidden on screen; subsequent prints rebuild it.
})();
