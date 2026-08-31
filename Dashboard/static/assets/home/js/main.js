(function () {
  "use strict";

  // Activate WOW.js - it was loaded on every page already, but never
  // started, so every existing "wow fadeInUp" class across the site was
  // doing nothing. This single call turns all of those on.
  if (typeof WOW !== "undefined") {
    new WOW({ boxClass: "wow", animateClass: "animated", offset: 40, mobile: true, live: true }).init();
  }

  // Back-to-top button show/hide + smooth scroll
  var backToTop = document.querySelector(".back-to-top");
  if (backToTop) {
    window.addEventListener("scroll", function () {
      backToTop.style.display = window.scrollY > 300 ? "block" : "none";
    });
    backToTop.addEventListener("click", function (e) {
      e.preventDefault();
      window.scrollTo({ top: 0, behavior: "smooth" });
    });
  }

  // Animated number counters. Usage: <span class="hz-counter" data-target="42">0</span>
  var counters = document.querySelectorAll(".hz-counter");
  if (counters.length) {
    var animateCounter = function (el) {
      var target = parseInt(el.getAttribute("data-target"), 10) || 0;
      var duration = 900;
      var start = null;
      var startVal = 0;
      function step(ts) {
        if (!start) start = ts;
        var progress = Math.min((ts - start) / duration, 1);
        var eased = 1 - Math.pow(1 - progress, 3); // ease-out-cubic
        el.textContent = Math.floor(startVal + (target - startVal) * eased);
        if (progress < 1) {
          requestAnimationFrame(step);
        } else {
          el.textContent = target;
        }
      }
      requestAnimationFrame(step);
    };

    if ("IntersectionObserver" in window) {
      var observer = new IntersectionObserver(function (entries) {
        entries.forEach(function (entry) {
          if (entry.isIntersecting) {
            animateCounter(entry.target);
            observer.unobserve(entry.target);
          }
        });
      }, { threshold: 0.4 });
      counters.forEach(function (el) { observer.observe(el); });
    } else {
      counters.forEach(animateCounter);
    }
  }
})();
