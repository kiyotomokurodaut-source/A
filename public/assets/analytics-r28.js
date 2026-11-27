/* r28（2026-11-27）GA4: LINEクリック計測。
   送るのはページのパス・CTAの識別子・文言の種類だけ。入力内容や氏名は送らない。
   gtag が読めない環境（広告ブロッカー等）では何もしない。 */
(function () {
  'use strict';

  function send(name, params) {
    try {
      if (typeof window.gtag === 'function') window.gtag('event', name, params);
    } catch (e) {
      /* 計測できないだけで、ページの動作は妨げない */
    }
  }

  function isLineLink(a) {
    var href = a.getAttribute('href') || '';
    return href.indexOf('lin.ee/') > -1 || href.indexOf('line.me/') > -1;
  }

  function ctaLocation(a) {
    var explicit = a.getAttribute('data-line-cta');
    if (explicit) return explicit;
    if (a.closest('.r27-sticky')) return 'sticky-fallback';
    if (a.closest('header')) return 'header-fallback';
    if (a.closest('footer')) return 'footer-fallback';
    if (a.closest('.r27-cta,.r28-anx,.r28-diag,.r28-table-cta,.cta-box')) return 'inline-fallback';
    return 'other-fallback';
  }

  document.addEventListener('click', function (event) {
    var node = event.target;
    while (node && node.nodeType === 1 && node.tagName !== 'A') node = node.parentElement;
    if (!node || node.tagName !== 'A' || !isLineLink(node)) return;
    var href = node.getAttribute('href') || '';
    send('line_click', {
      cta_location: ctaLocation(node),
      cta_variant: node.getAttribute('data-cta-variant') || 'none',
      page_path: location.pathname,
      link_type: href.indexOf('oaMessage') > -1 ? 'oa_message' : 'friend_add',
      transport_type: 'beacon'
    });
  }, true);
})();
