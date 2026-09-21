/* Navigation only. No cookies, click-id collection, automatic form posts or external analytics. */
(() => {
  'use strict';
  const lineUrl = 'https://lin.ee/YXdwMqY';
  function localEvent(cta) {
    document.dispatchEvent(new CustomEvent('kurodajuku:line-click', {detail:{path:location.pathname,cta:String(cta||'line').slice(0,80)}}));
  }
  window.KurodaLineTrack = localEvent;
  if (!document.body.classList.contains('line-lp') && !location.pathname.startsWith('/publish-check')) {
    const floating=document.createElement('a');
    floating.className='line-float';floating.href=lineUrl;floating.target='_blank';floating.rel='noopener';floating.dataset.lineCta='floating-line';
    const bubble=document.createElement('span');bubble.className='bubble';bubble.textContent='LINE';floating.append(bubble,document.createTextNode('LINEで相談する'));
    const sticky=document.createElement('div');sticky.className='line-mobile-sticky';sticky.setAttribute('aria-label','無料相談の案内');
    const line=document.createElement('a');line.className='primary';line.href=lineUrl;line.target='_blank';line.rel='noopener';line.dataset.lineCta='mobile-sticky-line';line.textContent='LINEで相談';
    const contact=document.createElement('a');contact.className='secondary';contact.href='/contact/?source=sticky';contact.textContent='無料相談の内容';
    sticky.append(line,contact);document.body.append(floating,sticky);document.body.classList.add('r15-has-sticky');
    const show=()=>floating.classList.toggle('is-visible',window.scrollY>500);show();addEventListener('scroll',show,{passive:true});
  }
  document.addEventListener('click',event => {
    const a=event.target instanceof Element?event.target.closest('a'):null;
    if(a && (a.href.startsWith(lineUrl) || a.hasAttribute('data-line-cta'))) localEvent(a.dataset.lineCta||'line-link');
  });
})();
