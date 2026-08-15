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

  // CTAがページのどこに置かれていたか
  function position(a) {
    if (!a.closest) return 'body';
    if (a.closest('#mobile-menu')) return 'mobile_menu';
    if (a.closest('header')) return 'header';
    if (a.closest('footer')) return 'footer';
    return 'body';
  }

  function isLine(href) {
    return href.indexOf('line.me') !== -1 || href.indexOf('lin.ee') !== -1;
  }

  // トップページのCTA欄（#cta）へのアンカー移動かどうか
  function isCtaAnchor(href) {
    return href === '#cta' || href === '/#cta' || href.indexOf('grace-sc.com/#cta') !== -1;
  }

  document.addEventListener('click', function (e) {
    var a = findAnchor(e.target);
    if (!a) return;
    var href = a.getAttribute('href') || '';
    if (!href) return;

    var params = {
      link_text: (a.textContent || '').trim().slice(0, 40),
      cta_position: position(a),
      page_path: location.pathname
    };

    // 主要CV：LINEを実際に開いた
    if (isLine(href)) {
      params.link_url = href;
      send('line_outbound', params);
      return;
    }

    // マイクロCV：トップのCTA欄へ移動しただけ。CVとして数えない
    if (isCtaAnchor(href)) {
      send('cta_anchor_click', params);
      return;
    }

    if (href.indexOf('instagram.com') !== -1) {
      params.link_url = href;
      send('instagram_outbound', params);
      return;
    }

    if (href.indexOf('tiktok.com') !== -1) {
      params.link_url = href;
      send('tiktok_outbound', params);
      return;
    }

    if (href.indexOf('mond.how') !== -1) {
      params.link_url = href;
      send('mond_outbound', params);
    }
  }, { capture: true });
})();
