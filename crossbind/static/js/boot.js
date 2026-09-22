/* ddOS — one-shot boot overlay (dark monochrome/teal, ~5s) */
(function () {
  "use strict";

  var STORAGE_KEY = "cross_affinity_booted";
  var DURATION_MS = 5000;
  var REDUCED_MS = 400;
  var TITLE = "ddOS";
  var CAPTION = "Drug Discovery Operating System";
  var CREDIT = "Developed by Alexander Cecena & Grok Bot";
  /* Prefer large PNG favicon as the centered brand mark */
  var LOGO_URL = "/static/img/favicon-512.png";

  var STAGES = [
    { at: 0.0, text: "Initializing affinity engine…" },
    { at: 0.22, text: "Warming ligand prep…" },
    { at: 0.48, text: "Seeding structure cache…" },
    { at: 0.72, text: "Calibrating docking grid…" },
    { at: 0.9, text: "Ready." },
  ];

  function qsForceBoot() {
    try {
      return new URLSearchParams(window.location.search).get("boot") === "1";
    } catch (_) {
      return false;
    }
  }

  function alreadyBooted() {
    try {
      return sessionStorage.getItem(STORAGE_KEY) === "1";
    } catch (_) {
      return false;
    }
  }

  function markBooted() {
    try {
      sessionStorage.setItem(STORAGE_KEY, "1");
    } catch (_) {}
  }

  function prefersReducedMotion() {
    try {
      return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    } catch (_) {
      return false;
    }
  }

  function buildOverlay() {
    var el = document.createElement("div");
    el.id = "cb-boot";
    el.setAttribute("role", "dialog");
    el.setAttribute("aria-label", "ddOS loading");
    el.innerHTML =
      '<div class="cb-boot__glow" aria-hidden="true"></div>' +
      '<div class="cb-boot__grain" aria-hidden="true"></div>' +
      '<div class="cb-boot__center">' +
      '  <div class="cb-boot__logo" id="cb-boot-logo">' +
      '    <img class="cb-boot__mark" src="' +
      LOGO_URL +
      '" alt="ddOS" width="160" height="160" />' +
      "  </div>" +
      '  <h1 class="cb-boot__title" id="cb-boot-title" aria-label="' +
      TITLE +
      '"></h1>' +
      '  <p class="cb-boot__caption">' +
      CAPTION +
      "</p>" +
      '  <div class="cb-boot__bar" aria-hidden="true">' +
      '    <div class="cb-boot__track"><div class="cb-boot__fill" id="cb-boot-fill"></div></div>' +
      '    <div class="cb-boot__status" id="cb-boot-status"></div>' +
      "  </div>" +
      "</div>" +
      '<div class="cb-boot__credit">' +
      CREDIT +
      "</div>";
    return el;
  }

  function spellTitle(host, text, duration, reduced) {
    host.textContent = "";
    var letters = text.split("");
    var spans = letters.map(function (ch) {
      var s = document.createElement("span");
      s.className = "cb-boot__letter" + (ch === " " ? " cb-boot__letter--space" : "");
      s.textContent = ch === " " ? "\u00a0" : ch;
      host.appendChild(s);
      return s;
    });
    if (reduced) {
      spans.forEach(function (s) {
        s.classList.add("is-on");
      });
      return;
    }
    var step = Math.max(40, Math.floor((duration * 0.55) / Math.max(1, spans.length)));
    spans.forEach(function (s, i) {
      setTimeout(function () {
        s.classList.add("is-on");
      }, 180 + i * step);
    });
  }

  function setStage(statusEl, fillEl, u) {
    var text = STAGES[0].text;
    for (var i = 0; i < STAGES.length; i++) {
      if (u >= STAGES[i].at) text = STAGES[i].text;
    }
    if (statusEl && statusEl.textContent !== text) statusEl.textContent = text;
    if (fillEl) fillEl.style.width = Math.min(100, Math.max(0, u * 100)).toFixed(2) + "%";
  }

  function runBoot() {
    document.documentElement.classList.add("cb-booting");
    var overlay = buildOverlay();
    document.body.appendChild(overlay);

    var titleEl = overlay.querySelector("#cb-boot-title");
    var fillEl = overlay.querySelector("#cb-boot-fill");
    var statusEl = overlay.querySelector("#cb-boot-status");

    var reduced = prefersReducedMotion();
    var duration = reduced ? REDUCED_MS : DURATION_MS;

    spellTitle(titleEl, TITLE, duration, reduced);

    var start = performance.now();
    var raf = 0;
    var finished = false;

    function cleanup() {
      if (finished) return;
      finished = true;
      if (raf) cancelAnimationFrame(raf);
      markBooted();
      overlay.classList.add("cb-boot--out");
      setTimeout(function () {
        if (overlay.parentNode) overlay.parentNode.removeChild(overlay);
        document.documentElement.classList.remove("cb-booting");
      }, reduced ? 120 : 480);
    }

    function tick(now) {
      var u = Math.min(1, (now - start) / duration);
      setStage(statusEl, fillEl, u);
      if (u >= 1) {
        cleanup();
        return;
      }
      raf = requestAnimationFrame(tick);
    }

    raf = requestAnimationFrame(tick);

    // Safety timeout
    setTimeout(cleanup, duration + 800);
  }

  function maybeBoot() {
    // Never infinite-replay on job page polls — sessionStorage gates once per tab.
    // Only ?boot=1 forces a replay.
    if (!qsForceBoot() && alreadyBooted()) return;
    runBoot();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", maybeBoot);
  } else {
    maybeBoot();
  }
})();
