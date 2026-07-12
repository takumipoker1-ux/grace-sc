/* サイト共通：スクロールでセクションがジワッと現れる演出
   - JS無効・reduced-motion・旧ブラウザでは何もしない（全文即表示）
   - トップページの .rv-group セクションは独自制御なので対象外 */
(function () {
  if (window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches) return;
  if (!('IntersectionObserver' in window)) return;

  var sections = [].slice.call(document.querySelectorAll('section'));
  if (!sections.length) return;

  sections.forEach(function (section) {
    if (section.classList.contains('rv-group')) return;

    // セクション直下が単一ラッパーならその子要素を時間差で、そうでなければ直下の子を対象に
    var wrap = section.children.length === 1 ? section.children[0] : section;
    var kids = [].slice.call(wrap.children);
    var els = (kids.length > 1 && kids.length <= 30) ? kids : [wrap];

    els.forEach(function (el, i) {
      el.classList.add('rv-a');
      el.style.setProperty('--d', Math.min(i * 0.12, 0.8) + 's');
    });
    section.__rvEls = els;
  });

  var io = new IntersectionObserver(function (entries) {
    entries.forEach(function (e) {
      if (e.isIntersecting) {
        (e.target.__rvEls || []).forEach(function (el) { el.classList.add('rv-on'); });
        io.unobserve(e.target);
      }
    });
  }, { threshold: 0.1 });

  sections.forEach(function (s) {
    if (s.__rvEls) io.observe(s);
  });
})();
