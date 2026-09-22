/* ほんごうねむり 公式サイト
   JavaScript は補助だけを担当します。これが読み込まれなくても、
   全ページの内容は読めて、リンクはすべて動きます。 */
(function () {
  "use strict";

  document.documentElement.classList.remove("no-js");

  /* --- モバイルのメニュー --- */
  var toggle = document.querySelector(".nav-toggle");
  var nav = document.getElementById("site-nav");

  if (toggle && nav) {
    var setOpen = function (open) {
      toggle.setAttribute("aria-expanded", String(open));
      nav.setAttribute("data-open", String(open));
      document.body.style.overflow = open ? "hidden" : "";
    };

    toggle.addEventListener("click", function () {
      setOpen(toggle.getAttribute("aria-expanded") !== "true");
    });

    // メニュー内のリンクを押したら閉じる
    nav.addEventListener("click", function (event) {
      if (event.target.closest("a")) setOpen(false);
    });

    document.addEventListener("keydown", function (event) {
      if (event.key === "Escape" && toggle.getAttribute("aria-expanded") === "true") {
        setOpen(false);
        toggle.focus();
      }
    });

    // 画面がデスクトップ幅に戻ったら、開いたままにしない
    var wide = window.matchMedia("(min-width: 901px)");
    var onWide = function (event) { if (event.matches) setOpen(false); };
    if (wide.addEventListener) wide.addEventListener("change", onWide);
    else if (wide.addListener) wide.addListener(onWide);
  }

  /* --- スクロールに合わせた表示 --- */
  var targets = document.querySelectorAll("[data-reveal]");
  var reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  if (!targets.length) return;

  if (reduced || !("IntersectionObserver" in window)) {
    Array.prototype.forEach.call(targets, function (el) { el.classList.add("is-visible"); });
    return;
  }

  var observer = new IntersectionObserver(function (entries) {
    entries.forEach(function (entry) {
      if (!entry.isIntersecting) return;
      // 並んだ要素は少しずつ遅らせて出す
      var delay = Number(entry.target.getAttribute("data-reveal-delay") || 0);
      setTimeout(function () { entry.target.classList.add("is-visible"); }, delay);
      observer.unobserve(entry.target);
    });
  }, { rootMargin: "0px 0px -8% 0px", threshold: 0.08 });

  Array.prototype.forEach.call(targets, function (el) { observer.observe(el); });
})();
