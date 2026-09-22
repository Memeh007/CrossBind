/* Cross Affinity — subtle phosphor glow orbs (no orange) */
(function () {
  const host = document.getElementById("orb-canvas");
  if (!host) return;
  const c = document.createElement("canvas");
  host.appendChild(c);
  const ctx = c.getContext("2d");
  const COLORS = ["rgba(46,230,197,0.14)", "rgba(34,211,238,0.10)", "rgba(167,139,250,0.08)"];
  let w, h, orbs, raf;

  function resize() {
    w = c.width = host.clientWidth || 600;
    h = c.height = host.clientHeight || 200;
  }
  function seed() {
    orbs = COLORS.map((color, i) => ({
      x: (0.2 + 0.3 * i) * w,
      y: (0.35 + 0.15 * (i % 2)) * h,
      r: 40 + i * 18,
      vx: 0.15 + i * 0.05,
      vy: 0.08 + i * 0.03,
      color,
    }));
  }
  function tick() {
    ctx.clearRect(0, 0, w, h);
    orbs.forEach((o) => {
      o.x += o.vx; o.y += o.vy;
      if (o.x < -o.r || o.x > w + o.r) o.vx *= -1;
      if (o.y < -o.r || o.y > h + o.r) o.vy *= -1;
      const g = ctx.createRadialGradient(o.x, o.y, 0, o.x, o.y, o.r);
      g.addColorStop(0, o.color);
      g.addColorStop(1, "rgba(0,0,0,0)");
      ctx.fillStyle = g;
      ctx.beginPath();
      ctx.arc(o.x, o.y, o.r, 0, Math.PI * 2);
      ctx.fill();
    });
    raf = requestAnimationFrame(tick);
  }
  resize(); seed(); tick();
  window.addEventListener("resize", () => { resize(); seed(); });
  document.addEventListener("visibilitychange", () => {
    if (document.hidden) cancelAnimationFrame(raf);
    else tick();
  });
})();
