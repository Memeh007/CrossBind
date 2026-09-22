/* Cross Affinity boot — instrument console + living molecule */
(function () {
  const FORCE = /[?&]boot=1\b/.test(location.search);
  const KEY = "cross_affinity_booted";
  if (!FORCE && sessionStorage.getItem(KEY)) return;

  const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const stages = [
    { t: 0.12, label: "warming geometry kernel…" },
    { t: 0.28, label: "loading residue atlas…" },
    { t: 0.48, label: "checking Vina / GNINA…" },
    { t: 0.72, label: "calibrating pocket grid…" },
    { t: 0.9, label: "binding affinity…" },
    { t: 1.0, label: "ready." },
  ];

  document.documentElement.classList.add("cb-booting");

  const overlay = document.createElement("div");
  overlay.id = "cb-boot";
  overlay.setAttribute("role", "status");
  overlay.setAttribute("aria-live", "polite");
  overlay.innerHTML =
    '<div class="cb-boot__grain" aria-hidden="true"></div>' +
    '<div class="cb-boot__scan" aria-hidden="true"></div>' +
    '<div class="cb-boot__inner">' +
    '  <div class="cb-boot__logo ca-orb-wrap" id="cb-boot-logo" aria-hidden="true"></div>' +
    '  <div class="cb-boot__word">CROSS AFFINITY</div>' +
    '  <div class="cb-boot__tag">biology × compute</div>' +
    '  <div class="cb-boot__serial">CA · LOCAL INSTRUMENT · Memeh007</div>' +
    '  <div class="cb-boot__track"><div class="cb-boot__fill" id="cb-boot-fill"></div></div>' +
    '  <div class="cb-boot__status" id="cb-boot-status">power on…</div>' +
    "</div>";
  document.body.prepend(overlay);

  let orbCtl = null;
  const logoHost = document.getElementById("cb-boot-logo");

  function startOrbs() {
    if (!window.CrossAffinityOrbs || !logoHost) return;
    window.CrossAffinityOrbs.mountLogo(logoHost, "/static/img/logo-molecule.svg", {
      breathMs: 4500,
    })
      .then(function (ctl) {
        orbCtl = ctl;
      })
      .catch(function () {
        logoHost.innerHTML = '<span class="cb-boot__x-fallback">×</span>';
      });
  }

  if (window.CrossAffinityOrbs) startOrbs();
  else {
    const s = document.createElement("script");
    s.src = "/static/js/molecule-orbs.js";
    s.onload = startOrbs;
    document.head.appendChild(s);
  }

  const fill = document.getElementById("cb-boot-fill");
  const status = document.getElementById("cb-boot-status");
  let healthDone = false;
  fetch("/api/health")
    .then(function () {
      healthDone = true;
    })
    .catch(function () {
      healthDone = true;
    });

  const duration = reduce ? 400 : 3400;
  const t0 = performance.now();

  function frame(now) {
    let p = Math.min(1, (now - t0) / duration);
    if (!reduce && p < 1) p = Math.min(1, p + (Math.random() - 0.5) * 0.008);
    if (p > 0.85 && !healthDone && now - t0 < duration + 1500) p = 0.85;
    fill.style.width = (p * 100).toFixed(1) + "%";
    let label = stages[0].label;
    for (let i = 0; i < stages.length; i++) if (p >= stages[i].t) label = stages[i].label;
    status.textContent = label;
    if (p < 1) requestAnimationFrame(frame);
    else finish();
  }

  function finish() {
    sessionStorage.setItem(KEY, "1");
    overlay.classList.add("cb-boot--out");
    document.documentElement.classList.remove("cb-booting");
    setTimeout(function () {
      if (orbCtl && orbCtl.stop) orbCtl.stop();
      overlay.remove();
    }, reduce ? 120 : 700);
  }

  requestAnimationFrame(frame);
})();
