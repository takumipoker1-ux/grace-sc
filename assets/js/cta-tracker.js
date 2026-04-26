(function () {
  'use strict';

  if (typeof window.gtag !== 'function') return;

  function send(name, params) {
    try { window.gtag('event', name, params || {}); } catch (e) {}
  }

  function findAnchor(target) {
    while (target && target !== document) {
      if (target.tagName === 'A') return target;
      target = target.parentNode;
    }
    return null;
  }

  function classify(href) {
    if (!href) return null;
    if (href.indexOf('instagram.com') !== -1) return 'instagram_outbound';
    if (href.indexOf('mond.how') !== -1) return 'mond_outbound';
    if (href.indexOf('lin.ee') !== -1 || href.indexOf('line.me') !== -1) return 'line_outbound';
    return null;
  }

  document.addEventListener('click', function (e) {
    var a = findAnchor(e.target);
    if (!a) return;
    var href = a.getAttribute('href') || '';
    var text = (a.textContent || '').trim().slice(0, 40);

    if (text.indexOf('Instagram相談') !== -1) {
      send('cta_click', {
        cta_label: 'instagram_soudan',
        cta_position: a.closest('header') ? 'header' : 'page',
        page_path: location.pathname
      });
    }

    var outboundType = classify(href);
    if (outboundType) {
      send(outboundType, {
        link_url: href,
        link_text: text,
        page_path: location.pathname
      });
    }
  }, { capture: true });
})();
