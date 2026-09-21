/* CrossBind boot — instrument console, once per browser session */
(function () {
  const FORCE = /[?&]boot=1\b/.test(location.search);
  const KEY = "crossbind_booted";
  if (!FORCE && sessionStorage.getItem(KEY)) return;

  const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const stages = [
    { t: 0.12, label: "warming geometry kernel…" },
    { t: 0.28, label: "loading residue atlas…" },
    { t: 0.48, label: "checking Vina / GNINA…" },
    { t: 0.72, label: "calibrating pocket grid…" },
    { t: 0.92, label: "locking local bind…" },
    { t: 1.0, label: "ready." },
  ];

  document.documentElement.classList.add("cb-booting");

  const overlay = document.createElement("div");
  overlay.id = "cb-boot";
  overlay.setAttribute("role", "status");
  overlay.setAttribute("aria-live", "polite");
  overlay.innerHTML = `
    <div class="cb-boot__grain" aria-hidden="true"></div>
    <div class="cb-boot__scan" aria-hidden="true"></div>
    <div class="cb-boot__inner">
      <div class="cb-boot__mark" aria-hidden="true">
        <svg class="cb-boot__x" viewBox="0 0 100 100" width="112" height="112">
          <rect class="cb-boot__bar a" x="42" y="8" width="16" height="84" rx="2"/>
          <rect class="cb-boot__bar b" x="8" y="42" width="84" height="16" rx="2"/>
        </svg>
      </div>
      <div class="cb-boot__word">CROSSBIND</div>
      <div class="cb-boot__tag">biology × compute</div>
      <div class="cb-boot__serial">CB · LOCAL INSTRUMENT · Memeh007</div>
      <div class="cb-boot__track"><div class="cb-boot__fill" id="cb-boot-fill"></div></div>
      <div class="cb-boot__status" id="cb-boot-status">power on…</div>
    </div>
  `;
  document.body.prepend(overlay);

  const fill = document.getElementById("cb-boot-fill");
  const status = document.getElementById("cb-boot-status");
  let healthDone = false;

  fetch("/api/health").then(() => { healthDone = true; }).catch(() => { healthDone = true; });

  const duration = reduce ? 400 : 3200;
  const t0 = performance.now();

  function frame(now) {
    let p = Math.min(1, (now - t0) / duration);
    // slight mechanical jitter
    if (!reduce && p < 1) p = Math.min(1, p + (Math.random() - 0.5) * 0.008);
    // hold near end until health returns or timeout
    if (p > 0.85 && !healthDone && now - t0 < duration + 1500) {
      p = 0.85;
    }
    fill.style.width = (p * 100).toFixed(1) + "%";
    let label = stages[0].label;
    for (const s of stages) if (p >= s.t) label = s.label;
    status.textContent = label;
    if (p < 1) {
      requestAnimationFrame(frame);
    } else {
      finish();
    }
  }

  function finish() {
    sessionStorage.setItem(KEY, "1");
    overlay.classList.add("cb-boot--out");
    document.documentElement.classList.remove("cb-booting");
    setTimeout(() => overlay.remove(), reduce ? 120 : 700);
  }

  requestAnimationFrame(frame);
})();
