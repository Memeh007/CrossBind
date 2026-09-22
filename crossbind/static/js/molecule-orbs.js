/**
 * Cross Affinity — organic molecule "orbs" physics (vanilla JS)
 * Independent node drift + bond stretch + global breathe/glow; core/ligand anchored.
 */
(function (global) {
  "use strict";

  function rand(min, max) {
    return min + Math.random() * (max - min);
  }

  function easeInOutSine(t) {
    return -(Math.cos(Math.PI * t) - 1) / 2;
  }

  /**
   * @param {SVGElement} svgRoot  The #ca-molecule svg (or container holding it)
   * @param {HTMLElement} [wrapper] Outer element for scale + filter pulse
   * @param {object} [opts]
   */
  function animateMolecule(svgRoot, wrapper, opts) {
    opts = opts || {};
    const reduce =
      opts.respectReducedMotion !== false &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reduce) return { stop: function () {} };

    const svg = svgRoot.tagName === "svg" ? svgRoot : svgRoot.querySelector("svg");
    if (!svg) return { stop: function () {} };

    const wrap = wrapper || svg.parentElement || svg;
    wrap.classList.add("ca-orb-wrap");

    const nodes = {};
    svg.querySelectorAll("[data-node]").forEach(function (el) {
      const id = el.getAttribute("data-node");
      const role = el.getAttribute("data-role") || "scaffold";
      const cx = parseFloat(el.getAttribute("cx"));
      const cy = parseFloat(el.getAttribute("cy"));
      let amp, speed;
      if (role === "core") {
        amp = rand(0.15, 0.35);
        speed = rand(0.35, 0.55);
      } else if (role === "ligand") {
        amp = rand(0.4, 0.85);
        speed = rand(0.45, 0.75);
      } else {
        amp = rand(1.4, 2.8);
        speed = rand(0.55, 1.15);
      }
      nodes[id] = {
        el: el,
        role: role,
        ox: cx,
        oy: cy,
        ampX: amp,
        ampY: amp * rand(0.85, 1.15),
        phaseX: rand(0, Math.PI * 2),
        phaseY: rand(0, Math.PI * 2),
        speedX: speed,
        speedY: speed * rand(0.8, 1.2),
        x: cx,
        y: cy,
      };
    });

    const bonds = [];
    svg.querySelectorAll("[data-bond]").forEach(function (el) {
      bonds.push({
        el: el,
        a: el.getAttribute("data-a"),
        b: el.getAttribute("data-b"),
      });
    });

    const breathMs = opts.breathMs || 4500;
    let raf = 0;
    let start = performance.now();
    let running = true;

    function frame(now) {
      if (!running) return;
      const t = (now - start) / 1000;

      Object.keys(nodes).forEach(function (id) {
        const n = nodes[id];
        n.x = n.ox + Math.sin(t * n.speedX + n.phaseX) * n.ampX;
        n.y = n.oy + Math.cos(t * n.speedY + n.phaseY) * n.ampY;
        n.el.setAttribute("cx", n.x.toFixed(3));
        n.el.setAttribute("cy", n.y.toFixed(3));
      });

      bonds.forEach(function (b) {
        const A = nodes[b.a];
        const B = nodes[b.b];
        if (!A || !B) return;
        b.el.setAttribute("x1", A.x.toFixed(3));
        b.el.setAttribute("y1", A.y.toFixed(3));
        b.el.setAttribute("x2", B.x.toFixed(3));
        b.el.setAttribute("y2", B.y.toFixed(3));
      });

      // Global inhale/exhale 1 → 1.04, ease-in-out, 4.5s loop
      const cycle = ((now - start) % breathMs) / breathMs;
      const wave = cycle < 0.5 ? easeInOutSine(cycle * 2) : easeInOutSine((1 - cycle) * 2);
      const scale = 1 + 0.04 * wave;
      const glow = 8 + 14 * wave;
      wrap.style.transform = "scale(" + scale.toFixed(4) + ")";
      wrap.style.filter =
        "drop-shadow(0 0 " +
        glow.toFixed(1) +
        "px rgba(232, 93, 4, " +
        (0.25 + 0.35 * wave).toFixed(3) +
        ")) drop-shadow(0 0 " +
        (glow * 0.45).toFixed(1) +
        "px rgba(126, 184, 201, " +
        (0.15 + 0.2 * wave).toFixed(3) +
        "))";

      raf = requestAnimationFrame(frame);
    }

    raf = requestAnimationFrame(frame);

    return {
      stop: function () {
        running = false;
        if (raf) cancelAnimationFrame(raf);
      },
    };
  }

  /** Fetch logo SVG and mount into a host element, then animate. */
  async function mountLogo(host, svgUrl, opts) {
    opts = opts || {};
    const r = await fetch(svgUrl + (svgUrl.includes("?") ? "&" : "?") + "v=1", {
      cache: "force-cache",
    });
    if (!r.ok) throw new Error("logo fetch failed");
    const text = await r.text();
    host.innerHTML = text;
    const svg = host.querySelector("svg");
    if (svg) {
      svg.removeAttribute("width");
      svg.removeAttribute("height");
      svg.style.width = "100%";
      svg.style.height = "100%";
      svg.style.display = "block";
    }
    return animateMolecule(svg || host, host, opts);
  }

  global.CrossAffinityOrbs = {
    animateMolecule: animateMolecule,
    mountLogo: mountLogo,
  };
})(typeof window !== "undefined" ? window : globalThis);
