/* ddOS — one-shot boot overlay (teal ink, ~5s) */
(function () {
  "use strict";

  var STORAGE_KEY = "cross_affinity_booted";
  var DURATION_MS = 5000;
  var REDUCED_MS = 400;
  var TITLE = "ddOS";
  var CAPTION = "Drug Discovery Operating System";
  var CREDIT = "Developed by Alexander Cecena & Grok Bot";
  var LOGO_URL = "/static/img/logo-molecule.svg";

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

  /* —— Falling 2D molecules (rings, sticks, hexagons) —— */
  function createFallingMolecules(canvas) {
    var ctx = canvas.getContext("2d");
    var w = 0;
    var h = 0;
    var mols = [];
    var raf = 0;
    var stopped = false;
    var COLORS = [
      "rgba(46,230,197,0.55)",
      "rgba(34,211,238,0.5)",
      "rgba(167,139,250,0.45)",
      "rgba(125,211,252,0.4)",
      "rgba(20,184,166,0.45)",
    ];

    function resize() {
      var dpr = Math.min(window.devicePixelRatio || 1, 2);
      w = window.innerWidth;
      h = window.innerHeight;
      canvas.width = Math.floor(w * dpr);
      canvas.height = Math.floor(h * dpr);
      canvas.style.width = w + "px";
      canvas.style.height = h + "px";
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    }

    function makeMol() {
      var kind = Math.floor(Math.random() * 4); // 0 hex, 1 stick, 2 ring+stick, 3 dual ring
      return {
        x: Math.random() * w,
        y: -20 - Math.random() * h * 0.4,
        vy: 3.2 + Math.random() * 5.5, // fall quickly
        vx: (Math.random() - 0.5) * 0.8,
        rot: Math.random() * Math.PI * 2,
        vr: (Math.random() - 0.5) * 0.08,
        scale: 0.45 + Math.random() * 0.85,
        color: COLORS[Math.floor(Math.random() * COLORS.length)],
        kind: kind,
      };
    }

    function seed() {
      var count = Math.min(48, Math.max(28, Math.floor((w * h) / 28000)));
      mols = [];
      for (var i = 0; i < count; i++) {
        var m = makeMol();
        m.y = Math.random() * h;
        mols.push(m);
      }
    }

    function drawHex(m) {
      var r = 7 * m.scale;
      ctx.beginPath();
      for (var i = 0; i < 6; i++) {
        var a = m.rot + (i * Math.PI) / 3;
        var px = m.x + Math.cos(a) * r;
        var py = m.y + Math.sin(a) * r;
        if (i === 0) ctx.moveTo(px, py);
        else ctx.lineTo(px, py);
      }
      ctx.closePath();
      ctx.stroke();
      // center atom
      ctx.beginPath();
      ctx.arc(m.x, m.y, 1.4 * m.scale, 0, Math.PI * 2);
      ctx.fill();
    }

    function drawStick(m) {
      var len = 14 * m.scale;
      var c = Math.cos(m.rot);
      var s = Math.sin(m.rot);
      ctx.beginPath();
      ctx.moveTo(m.x - c * len, m.y - s * len);
      ctx.lineTo(m.x + c * len, m.y + s * len);
      ctx.stroke();
      ctx.beginPath();
      ctx.arc(m.x - c * len, m.y - s * len, 2.2 * m.scale, 0, Math.PI * 2);
      ctx.arc(m.x + c * len, m.y + s * len, 2.2 * m.scale, 0, Math.PI * 2);
      ctx.fill();
    }

    function drawRingStick(m) {
      drawHex(m);
      var len = 12 * m.scale;
      var a = m.rot + Math.PI / 6;
      ctx.beginPath();
      ctx.moveTo(m.x + Math.cos(a) * 7 * m.scale, m.y + Math.sin(a) * 7 * m.scale);
      ctx.lineTo(m.x + Math.cos(a) * (7 * m.scale + len), m.y + Math.sin(a) * (7 * m.scale + len));
      ctx.stroke();
      ctx.beginPath();
      ctx.arc(
        m.x + Math.cos(a) * (7 * m.scale + len),
        m.y + Math.sin(a) * (7 * m.scale + len),
        2 * m.scale,
        0,
        Math.PI * 2
      );
      ctx.fill();
    }

    function drawDual(m) {
      var ox = 9 * m.scale;
      var c = Math.cos(m.rot);
      var s = Math.sin(m.rot);
      var saved = { x: m.x, y: m.y };
      m.x = saved.x - c * ox;
      m.y = saved.y - s * ox;
      drawHex(m);
      m.x = saved.x + c * ox;
      m.y = saved.y + s * ox;
      drawHex(m);
      m.x = saved.x;
      m.y = saved.y;
      ctx.beginPath();
      ctx.moveTo(saved.x - c * ox, saved.y - s * ox);
      ctx.lineTo(saved.x + c * ox, saved.y + s * ox);
      ctx.stroke();
    }

    function tick() {
      if (stopped) return;
      ctx.clearRect(0, 0, w, h);
      for (var i = 0; i < mols.length; i++) {
        var m = mols[i];
        m.y += m.vy;
        m.x += m.vx;
        m.rot += m.vr;
        if (m.y > h + 40) {
          mols[i] = makeMol();
          continue;
        }
        ctx.strokeStyle = m.color;
        ctx.fillStyle = m.color;
        ctx.lineWidth = 1.25;
        if (m.kind === 0) drawHex(m);
        else if (m.kind === 1) drawStick(m);
        else if (m.kind === 2) drawRingStick(m);
        else drawDual(m);
      }
      raf = requestAnimationFrame(tick);
    }

    resize();
    seed();
    tick();
    window.addEventListener("resize", onResize);

    function onResize() {
      resize();
      seed();
    }

    return {
      stop: function () {
        stopped = true;
        if (raf) cancelAnimationFrame(raf);
        raf = 0;
        window.removeEventListener("resize", onResize);
      },
    };
  }

  function buildOverlay() {
    var el = document.createElement("div");
    el.id = "cb-boot";
    el.setAttribute("role", "dialog");
    el.setAttribute("aria-label", "ddOS loading");
    el.innerHTML =
      '<canvas class="cb-boot__fall" aria-hidden="true"></canvas>' +
      '<div class="cb-boot__grain" aria-hidden="true"></div>' +
      '<div class="cb-boot__center">' +
      '  <div class="cb-boot__logo" id="cb-boot-logo"></div>' +
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

    var canvas = overlay.querySelector(".cb-boot__fall");
    var fall = createFallingMolecules(canvas);
    var logoHost = overlay.querySelector("#cb-boot-logo");
    var titleEl = overlay.querySelector("#cb-boot-title");
    var fillEl = overlay.querySelector("#cb-boot-fill");
    var statusEl = overlay.querySelector("#cb-boot-status");

    var reduced = prefersReducedMotion();
    var duration = reduced ? REDUCED_MS : DURATION_MS;
    var orbCtrl = null;

    spellTitle(titleEl, TITLE, duration, reduced);

    function mountOrbs() {
      if (!window.CrossAffinityOrbs || !window.CrossAffinityOrbs.mountLogo) {
        // fallback: inject img
        logoHost.innerHTML =
          '<div class="ca-orb-wrap"><img src="' +
          LOGO_URL +
          '" alt="" width="140" height="140"/></div>';
        return Promise.resolve(null);
      }
      return window.CrossAffinityOrbs.mountLogo(logoHost, LOGO_URL, {
        duration: 4500,
        intensity: 1,
      }).then(function (ctrl) {
        orbCtrl = ctrl;
        return ctrl;
      }).catch(function () {
        logoHost.innerHTML =
          '<div class="ca-orb-wrap"><img src="' +
          LOGO_URL +
          '" alt="" width="140" height="140"/></div>';
        return null;
      });
    }

    var start = performance.now();
    var raf = 0;
    var finished = false;

    function cleanup() {
      if (finished) return;
      finished = true;
      if (raf) cancelAnimationFrame(raf);
      fall.stop();
      if (orbCtrl && orbCtrl.stop) orbCtrl.stop();
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

    mountOrbs().then(function () {
      raf = requestAnimationFrame(tick);
    });

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
