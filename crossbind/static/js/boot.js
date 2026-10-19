/* ddOS — one-shot boot overlay: instrument start-up log backed by /api/health */
(function () {
  "use strict";

  var STORAGE_KEY = "ddos_booted";
  var STEP_MS = 380;
  var HOLD_MS = 700;
  var MIN_MS = 3000;
  var MAX_MS = 5000;
  var HEALTH_TIMEOUT_MS = 2500;
  var REDUCED_MS = 400;
  var TITLE = "ddOS";
  var CAPTION = "Drug Discovery Operating System";
  var CREDIT = "Alexander Cecena & Grok Bot";
  var LOGO_URL = "/static/img/boot-logo.png";

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

  function buildOverlay() {
    var root = el("div");
    root.id = "cb-boot";
    root.setAttribute("role", "status");
    root.setAttribute("aria-live", "polite");
    root.setAttribute("aria-label", "ddOS starting");

    var panel = el("div", "cb-boot__panel");
    var head = el("div", "cb-boot__head");
    var mark = el("img", "cb-boot__mark");
    mark.src = LOGO_URL;
    mark.alt = "";
    mark.width = 56;
    mark.height = 56;
    var ident = el("div", "cb-boot__ident");
    ident.appendChild(el("h1", "cb-boot__title", TITLE));
    ident.appendChild(el("p", "cb-boot__caption", CAPTION));
    head.appendChild(mark);
    head.appendChild(ident);

    var log = el("ul", "cb-boot__log");
    var bar = el("div", "cb-boot__bar");
    bar.setAttribute("aria-hidden", "true");
    var track = el("div", "cb-boot__track");
    var fill = el("div", "cb-boot__fill");
    var pct = el("span", "cb-boot__pct", "0%");
    track.appendChild(fill);
    bar.appendChild(track);
    bar.appendChild(pct);

    panel.appendChild(head);
    panel.appendChild(log);
    panel.appendChild(bar);

    var foot = el("div", "cb-boot__foot");
    foot.appendChild(el("span", null, CREDIT));
    foot.appendChild(el("span", null, "local · " + (window.location.host || "127.0.0.1")));

    root.appendChild(panel);
    root.appendChild(foot);
    return { root: root, log: log, fill: fill, pct: pct };
  }

  function addLine(log, key) {
    var li = el("li", "cb-boot__line");
    li.appendChild(el("span", "cb-boot__tag", TAGS.pending));
    li.appendChild(el("span", "cb-boot__key", key));
    li.appendChild(el("span", "cb-boot__val", ""));
    log.appendChild(li);
    // Force a style flush so the opacity transition runs.
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

  function probeHealth() {
    var ctrl = typeof AbortController === "function" ? new AbortController() : null;
    var timer = setTimeout(function () {
      if (ctrl) ctrl.abort();
    }, HEALTH_TIMEOUT_MS);
    return fetch("/api/health", { cache: "no-store", signal: ctrl ? ctrl.signal : undefined })
      .then(function (r) {
        if (!r.ok) throw new Error("HTTP " + r.status);
        return r.json();
      })
      .then(
        function (data) {
          clearTimeout(timer);
          return data;
        },
        function () {
          clearTimeout(timer);
          return null;
        }
      );
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
    document.documentElement.classList.add("cb-booting");
    var ui = buildOverlay();
    document.body.appendChild(ui.root);

    var reduced = prefersReducedMotion();
    var start = performance.now();
    var finished = false;
    var queue = [];
    var pumping = false;
    var expected = reduced ? 1 : 6;
    var done = 0;

    function progress() {
      var u = Math.min(1, done / expected);
      ui.fill.style.width = (u * 100).toFixed(1) + "%";
      ui.pct.textContent = Math.round(u * 100) + "%";
    }

    function cleanup() {
      if (finished) return;
      finished = true;
      markBooted();
      ui.root.classList.add("cb-boot--out");
      setTimeout(function () {
        if (ui.root.parentNode) ui.root.parentNode.removeChild(ui.root);
        document.documentElement.classList.remove("cb-booting");
      }, reduced ? 120 : 340);
    }

    function finishAfterHold() {
      var elapsed = performance.now() - start;
      setTimeout(cleanup, Math.max(HOLD_MS, MIN_MS - elapsed));
    }

    function enqueue(fn) {
      queue.push(fn);
      if (!pumping) pump();
    }

    function pump() {
      if (finished || !queue.length) {
        pumping = false;
        return;
      }
      pumping = true;
      queue.shift()();
      setTimeout(pump, STEP_MS);
    }

    ui.root.classList.add("is-live");

    if (reduced) {
      var only = addLine(ui.log, "shell");
      setLine(only, "ok", TAGS.ok, "interface loaded · engine probe skipped");
      done = 1;
      progress();
      setTimeout(cleanup, REDUCED_MS);
      return;
    }

    setTimeout(cleanup, MAX_MS);

    var healthLine = null;
    var health = probeHealth();

    enqueue(function () {
      setLine(addLine(ui.log, "shell"), "ok", TAGS.ok, "interface loaded");
      done += 1;
      progress();
    });

    enqueue(function () {
      healthLine = addLine(ui.log, "health");
      setLine(healthLine, "", TAGS.pending, "GET /api/health");
    });

    health.then(function (h) {
      enqueue(function () {
        if (!h) {
          setLine(healthLine, "warn", TAGS.fail, "no response — engine status unknown");
          expected = 3;
        } else {
          setLine(healthLine, "ok", TAGS.ok, "200 · ddOS v" + (h.version || "?"));
        }
        done += 1;
        progress();
      });

      var degraded = !h || !h.vina_ok || !h.p2rank_ok;
      if (h) {
        engineLines(h).forEach(function (row) {
          enqueue(function () {
            setLine(addLine(ui.log, row.key), row.state, row.tag, row.val);
            done += 1;
            progress();
          });
        });
      }

      enqueue(function () {
        var sys = addLine(ui.log, "system");
        if (!h) setLine(sys, "warn", TAGS.warn, "started · see /api/health");
        else if (degraded) setLine(sys, "warn", TAGS.warn, "ready with warnings");
        else setLine(sys, "ok", TAGS.ok, "ready");
        done = expected;
        progress();
        finishAfterHold();
      });
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
