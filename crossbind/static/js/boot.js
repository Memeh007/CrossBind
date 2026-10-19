/* ddOS — one-shot boot splash: docking orb + phosphor wordmark + start-up log backed by /api/boot */
(function () {
  "use strict";

  var STORAGE_KEY = "ddos_booted";
  var STEP_MS = 170;
  var HOLD_MS = 650;
  var MIN_MS = 2200;
  var MAX_MS = 4000;
  var PROBE_TIMEOUT_MS = 1800;
  var FONT_TIMEOUT_MS = 900;
  var REDUCED_HOLD_MS = 900;
  var OUT_MS = 420;
  var OUT_FAST_MS = 160;
  var TITLE = "ddOS";
  var CAPTION = "Drug Discovery Operating System";
  var CREDIT = "Alexander Cecena & Grok Bot";
  // one orb contact per check below; "system" completes the boot instead of adding a contact
  var CHECKS = ["shell", "type", "modules", "probe", "cache", "orthologs", "vina", "p2rank", "gnina"];

  var TAGS = {
    pending: "[ .. ]",
    ok: "[ OK ]",
    miss: "[MISS]",
    off: "[ -- ]",
    warn: "[WARN]",
    fail: "[FAIL]",
  };

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

  function el(tag, cls, text) {
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text != null) n.textContent = text;
    return n;
  }

  function pad2(n) {
    return n < 10 ? "0" + n : String(n);
  }

  function wait(ms) {
    return new Promise(function (r) {
      setTimeout(r, ms);
    });
  }

  function buildOverlay() {
    var root = el("div");
    root.id = "cb-boot";
    root.setAttribute("role", "status");
    root.setAttribute("aria-live", "polite");
    root.setAttribute("aria-label", "ddOS starting");

    var stage = el("div", "cb-boot__stage");

    var orb = el("div", "cb-boot__orb");
    orb.setAttribute("aria-hidden", "true");
    var canvas = el("canvas", "cb-boot__canvas");
    orb.appendChild(canvas);
    ["tl", "tr", "bl", "br"].forEach(function (k) {
      orb.appendChild(el("span", "cb-boot__corner cb-boot__corner--" + k));
    });

    var brand = el("div", "cb-boot__brand");
    var word = el("h1", "cb-boot__word", TITLE);
    word.setAttribute("data-text", TITLE);
    var sub = el("p", "cb-boot__sub", CAPTION);
    sub.setAttribute("data-text", CAPTION);
    brand.appendChild(word);
    brand.appendChild(sub);

    var log = el("ul", "cb-boot__log");

    var meta = el("div", "cb-boot__meta");
    var count = el("span", "cb-boot__count", "boot 00/" + pad2(CHECKS.length));
    var clock = el("span", "cb-boot__clock", "t+0.00 s");
    meta.appendChild(count);
    meta.appendChild(clock);

    stage.appendChild(orb);
    stage.appendChild(brand);
    stage.appendChild(log);
    stage.appendChild(meta);

    var foot = el("div", "cb-boot__foot");
    foot.appendChild(el("span", null, CREDIT));
    foot.appendChild(el("span", "cb-boot__skip", "click or press any key to skip"));
    foot.appendChild(el("span", null, "local · " + (window.location.host || "127.0.0.1")));

    root.appendChild(stage);
    root.appendChild(foot);
    return { root: root, canvas: canvas, log: log, count: count, clock: clock };
  }

  function addLine(log, key) {
    var li = el("li", "cb-boot__line");
    li.appendChild(el("span", "cb-boot__tag", TAGS.pending));
    li.appendChild(el("span", "cb-boot__key", key));
    li.appendChild(el("span", "cb-boot__val", ""));
    log.appendChild(li);
    // Force a style flush so the reveal transition runs.
    void li.offsetWidth;
    li.classList.add("is-on");
    return li;
  }

  function setLine(li, state, tag, val) {
    li.classList.remove("ok", "bad", "warn");
    if (state) li.classList.add(state);
    li.children[0].textContent = tag;
    li.children[2].textContent = val;
  }

  function probeBoot() {
    var ctrl = typeof AbortController === "function" ? new AbortController() : null;
    var t0 = performance.now();
    var timer = setTimeout(function () {
      if (ctrl) ctrl.abort();
    }, PROBE_TIMEOUT_MS);
    return fetch("/api/boot", { cache: "no-store", signal: ctrl ? ctrl.signal : undefined })
      .then(function (r) {
        if (!r.ok) throw new Error("HTTP " + r.status);
        return r.json();
      })
      .then(
        function (data) {
          clearTimeout(timer);
          data._ms = Math.round(performance.now() - t0);
          return data;
        },
        function () {
          clearTimeout(timer);
          return null;
        }
      );
  }

  function fontsReady() {
    var f = document.fonts;
    if (!f || !f.ready) return Promise.resolve(null);
    return Promise.race([f.ready, wait(FONT_TIMEOUT_MS)]).then(function () {
      try {
        return { sans: f.check('600 16px "IBM Plex Sans"'), mono: f.check('400 12px "IBM Plex Mono"') };
      } catch (_) {
        return null;
      }
    });
  }

  function pageModules() {
    var names = [];
    Array.prototype.forEach.call(document.scripts, function (s) {
      if (!s.src) return;
      var name = s.src.split("?")[0].split("/").pop();
      if (/^boot(-orb)?\.js$/.test(name) || names.indexOf(name) !== -1) return;
      names.push(name);
    });
    return names;
  }

  function cacheLine(d) {
    if (!d || !d.present) return { state: "", tag: TAGS.off, val: "discovery cache empty · fills on first query" };
    if (d.error) return { state: "warn", tag: TAGS.warn, val: "discovery.sqlite unreadable" };
    return { state: "ok", tag: TAGS.ok, val: "discovery.sqlite · " + d.entries + (d.entries === 1 ? " entry" : " entries") };
  }

  function orthologLine(o) {
    if (!o || !o.present) {
      return o && o.seed_available
        ? { state: "", tag: TAGS.off, val: "PlanMine RBH not built · seed loads on first query" }
        : { state: "warn", tag: TAGS.miss, val: "PlanMine RBH cache and seed missing" };
    }
    if (o.error) return { state: "warn", tag: TAGS.warn, val: "PlanMine RBH cache unreadable" };
    var scope = o.mode === "complete" ? "full index" : o.mode === "seed" ? "seed slice" : "partial";
    return { state: "ok", tag: TAGS.ok, val: "PlanMine RBH · " + o.symbols + " symbols · " + scope };
  }

  function engineLines(h) {
    return [
      h.vina_ok
        ? { key: "vina", state: "ok", tag: TAGS.ok, val: "ready" }
        : { key: "vina", state: "bad", tag: TAGS.miss, val: "not found — docking unavailable" },
      h.p2rank_ok
        ? { key: "p2rank", state: "ok", tag: TAGS.ok, val: "ready" }
        : { key: "p2rank", state: "warn", tag: TAGS.miss, val: "not found — holo / centroid pockets only" },
      h.gnina_ok
        ? { key: "gnina", state: "ok", tag: TAGS.ok, val: "ready" }
        : { key: "gnina", state: "", tag: TAGS.off, val: "optional · not configured" },
    ];
  }

  function runBoot() {
    var html = document.documentElement;
    html.classList.add("cb-booting");
    var ui = buildOverlay();
    document.body.appendChild(ui.root);

    var reduced = prefersReducedMotion();
    var start = performance.now();
    var finished = false;
    var total = CHECKS.length;
    var done = 0;
    var flagged = [];
    var orb = window.DdosBootOrb ? window.DdosBootOrb.create(ui.canvas, { total: total, reduced: reduced }) : null;
    var clockTimer = reduced ? 0 : setInterval(tickClock, 50);

    function tickClock() {
      ui.clock.textContent = "t+" + ((performance.now() - start) / 1000).toFixed(2) + " s";
    }

    function counter() {
      ui.count.textContent = "boot " + pad2(done) + "/" + pad2(total);
      tickClock();
    }

    function settle(li, key, row) {
      setLine(li, row.state, row.tag, row.val);
      if (row.state === "warn" || row.state === "bad") flagged.push(key);
      done += 1;
      if (orb) orb.step(row.state || "off");
      counter();
    }

    function line(key, row) {
      settle(addLine(ui.log, key), key, row);
    }

    function finish(skipped) {
      if (finished) return;
      finished = true;
      markBooted();
      clearInterval(clockTimer);
      document.removeEventListener("keydown", onSkip, true);
      ui.root.removeEventListener("click", onSkip);
      ui.root.classList.add(skipped ? "cb-boot--skip" : "cb-boot--out");
      setTimeout(function () {
        if (orb) orb.destroy();
        if (ui.root.parentNode) ui.root.parentNode.removeChild(ui.root);
        html.classList.remove("cb-booting");
      }, skipped || reduced ? OUT_FAST_MS : OUT_MS);
    }

    function onSkip() {
      finish(true);
    }

    document.addEventListener("keydown", onSkip, true);
    ui.root.addEventListener("click", onSkip);
    setTimeout(function () {
      finish(false);
    }, MAX_MS);

    var probe = probeBoot();
    var fonts = fontsReady();
    var chain = Promise.resolve();

    function next(fn) {
      chain = chain
        .then(function () {
          if (!finished) return fn();
        })
        .then(function () {
          if (!finished && !reduced) return wait(STEP_MS);
        });
    }

    ui.root.classList.add("is-live");

    next(function () {
      var dom = Math.round(performance.now());
      line("shell", { state: "ok", tag: TAGS.ok, val: "interface loaded · DOM ready in " + dom + " ms" });
    });

    next(function () {
      return fonts.then(function (f) {
        if (f && f.sans && f.mono) line("type", { state: "ok", tag: TAGS.ok, val: "IBM Plex Sans · IBM Plex Mono" });
        else line("type", { state: "warn", tag: TAGS.warn, val: "IBM Plex unavailable · system fallback" });
      });
    });

    next(function () {
      var mods = pageModules();
      line("modules", { state: "ok", tag: TAGS.ok, val: mods.length ? mods.join(" · ") : "shell only" });
    });

    var probeLi = null;
    var boot = null;
    next(function () {
      probeLi = addLine(ui.log, "probe");
      setLine(probeLi, "", TAGS.pending, "GET /api/boot");
      return probe.then(function (h) {
        boot = h;
        if (!h) {
          total = done + 1;
          if (orb) orb.setTotal(total);
          settle(probeLi, "probe", { state: "warn", tag: TAGS.fail, val: "no response — cache / engine status unknown" });
        } else {
          settle(probeLi, "probe", { state: "ok", tag: TAGS.ok, val: "200 · ddOS v" + (h.version || "?") + " · " + h._ms + " ms" });
        }
      });
    });

    next(function () {
      if (boot) line("cache", cacheLine(boot.caches && boot.caches.discovery));
    });
    next(function () {
      if (boot) line("orthologs", orthologLine(boot.caches && boot.caches.orthologs));
    });
    [0, 1, 2].forEach(function (i) {
      next(function () {
        if (!boot) return;
        var row = engineLines(boot)[i];
        line(row.key, row);
      });
    });

    next(function () {
      var sys = addLine(ui.log, "system");
      if (!boot) setLine(sys, "warn", TAGS.warn, "started · see /api/health");
      else if (flagged.length) setLine(sys, "warn", TAGS.warn, "ready · check " + flagged.join(", "));
      else setLine(sys, "ok", TAGS.ok, "ready");
      if (orb) orb.complete();
      counter();
      var elapsed = performance.now() - start;
      setTimeout(function () {
        finish(false);
      }, reduced ? REDUCED_HOLD_MS : Math.max(HOLD_MS, MIN_MS - elapsed));
    });
  }

  function maybeBoot() {
    // sessionStorage gates once per tab so job-page polls never replay; ?boot=1 forces a replay.
    if (!qsForceBoot() && alreadyBooted()) return;
    runBoot();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", maybeBoot);
  } else {
    maybeBoot();
  }
})();
