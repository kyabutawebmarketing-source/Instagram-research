/* ============================================================
   hakutakagami 接触冷感ドッグウェア LP 専用スクリプト
   - 固定CTA（スマホ）の表示制御のみ
   - スムーズスクロールはCSS（scroll-behavior）で実装
   - jQuery等の外部ライブラリには依存しない
   ============================================================ */
(function () {
  'use strict';

  // 同一ページに複数回読み込まれても二重初期化しない
  if (window.__hklpStickyInit) return;
  window.__hklpStickyInit = true;

  function init() {
    var bar = document.querySelector('[data-hklp-sticky]');
    if (!bar) return;

    var showAfter = parseInt(bar.getAttribute('data-show-after') || '600', 10);
    var scrolledEnough = false;
    var nearFooter = false;

    function update() {
      var visible = scrolledEnough && !nearFooter;
      bar.classList.toggle('is-visible', visible);
      bar.setAttribute('aria-hidden', visible ? 'false' : 'true');
      document.documentElement.classList.toggle('hklp-sticky-visible', visible);
    }

    function onScroll() {
      var next = window.scrollY > showAfter;
      if (next !== scrolledEnough) {
        scrolledEnough = next;
        update();
      }
    }

    window.addEventListener('scroll', onScroll, { passive: true });
    onScroll();

    // フッター付近では非表示にする
    var footer =
      document.querySelector('.shopify-section-group-footer-group') ||
      document.querySelector('footer');

    if (footer && 'IntersectionObserver' in window) {
      var observer = new IntersectionObserver(
        function (entries) {
          nearFooter = entries[0].isIntersecting;
          update();
        },
        { rootMargin: '0px 0px 0px 0px', threshold: 0 }
      );
      observer.observe(footer);
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
