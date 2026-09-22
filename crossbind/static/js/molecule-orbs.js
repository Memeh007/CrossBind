/**
 * Cross Affinity — living molecule orbs (teal/cyan/violet; no orange/amber)
 * Node drift + bond stretch + breathe/glow (~4.5s). Export: window.CrossAffinityOrbs
 */
(function (global) {
  "use strict";

  function rand(min, max) {
    return min + Math.random() * (max - min);
  }

  function easeInOutSine(t) {
    return -(Math.cos(Math.PI * t) - 1) / 2;
  }

  function prefersReducedMotion() {
    try {
      return global.matchMedia && global.matchMedia("(prefers-reduced-motion: reduce)").matches;
    } catch (_) {
      return false;
    }
  }

  /**
   * @param {SVGElement|Element} svgRoot
   * @param {HTMLElement} [wrapper]
   * @param {{breathMs?:number, duration?:number, intensity?:number, respectReducedMotion?:boolean}} [opts]
   */
  function animateMolecule(svgRoot, wrapper, opts) {
    opts = opts || {};
    var reduce =
      opts.respectReducedMotion !== false && prefersReducedMotion();
    if (reduce) return { stop: function () {}, promise: Promise.resolve() };

    var svg = svgRoot && svgRoot.tagName === "svg" ? svgRoot : (svgRoot && svgRoot.querySelector("svg"));
    if (!svg) return { stop: function () {}, promise: Promise.resolve() };

    var wrap = wrapper || svg.parentElement || svg;
    wrap.classList.add("ca-orb-wrap");

    var intensity = opts.intensity != null ? opts.intensity : 1;
    var breathMs = opts.breathMs || opts.duration || 4500;

    var nodes = {};
    svg.querySelectorAll("[data-node]").forEach(function (el) {
      var id = el.getAttribute("data-node");
      var role = el.getAttribute("data-role") || "scaffold";
      var cx = parseFloat(el.getAttribute("cx"));
      var cy = parseFloat(el.getAttribute("cy"));
      var amp, speed;
      if (role === "core") {
        amp = rand(0.15, 0.35) * intensity;
        speed = rand(0.35, 0.55);
      } else if (role === "ligand") {
        amp = rand(0.4, 0.85) * intensity;
        speed = rand(0.45, 0.75);
      } else {
        amp = rand(1.4, 2.8) * intensity;
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

    var bonds = [];
    svg.querySelectorAll("[data-bond]").forEach(function (el) {
      bonds.push({
        el: el,
        a: el.getAttribute("data-a"),
        b: el.getAttribute("data-b"),
      });
    });

    var raf = 0;
    var start = performance.now();
    var running = true;
    var resolvePromise;
    var promise = new Promise(function (res) {
      resolvePromise = res;
    });

    function frame(now) {
      if (!running) return;
      var t = (now - start) / 1000;

      Object.keys(nodes).forEach(function (id) {
        var n = nodes[id];
        n.x = n.ox + Math.sin(t * n.speedX + n.phaseX) * n.ampX;
        n.y = n.oy + Math.cos(t * n.speedY + n.phaseY) * n.ampY;
        n.el.setAttribute("cx", n.x.toFixed(3));
        n.el.setAttribute("cy", n.y.toFixed(3));
      });

      bonds.forEach(function (b) {
        var A = nodes[b.a];
        var B = nodes[b.b];
        if (!A || !B) return;
        b.el.setAttribute("x1", A.x.toFixed(3));
        b.el.setAttribute("y1", A.y.toFixed(3));
        b.el.setAttribute("x2", B.x.toFixed(3));
        b.el.setAttribute("y2", B.y.toFixed(3));
      });

      var cycle = ((now - start) % breathMs) / breathMs;
      var wave = cycle < 0.5 ? easeInOutSine(cycle * 2) : easeInOutSine((1 - cycle) * 2);
      var scale = 1 + 0.04 * wave * intensity;
      var glow = 8 + 14 * wave;
      wrap.style.transform = "scale(" + scale.toFixed(4) + ")";
      // Teal / cyan glow — never orange/amber
      wrap.style.filter =
        "drop-shadow(0 0 " +
        glow.toFixed(1) +
        "px rgba(46, 230, 197, " +
        (0.28 + 0.38 * wave).toFixed(3) +
        ")) drop-shadow(0 0 " +
        (glow * 0.55).toFixed(1) +
        "px rgba(34, 211, 238, " +
        (0.18 + 0.28 * wave).toFixed(3) +
        "))";

      raf = requestAnimationFrame(frame);
    }

    raf = requestAnimationFrame(frame);
    setTimeout(function () {
      resolvePromise();
    }, breathMs);

    return {
      stop: function () {
        running = false;
        if (raf) cancelAnimationFrame(raf);
        raf = 0;
        resolvePromise();
      },
      promise: promise,
    };
  }

  /** Fetch logo SVG and mount into a host element, then animate. */
  function mountLogo(host, svgUrl, opts) {
    opts = opts || {};
    if (!host) return Promise.reject(new Error("mountLogo: host required"));
    var url = svgUrl + (svgUrl.indexOf("?") >= 0 ? "&" : "?") + "v=ca2";
    return fetch(url, { cache: "force-cache" }).then(function (r) {
      if (!r.ok) throw new Error("logo fetch failed");
      return r.text();
    }).then(function (text) {
      host.innerHTML = text;
      var svg = host.querySelector("svg");
      if (svg) {
        svg.setAttribute("id", "ca-molecule");
        svg.removeAttribute("width");
        svg.removeAttribute("height");
        svg.style.width = "100%";
        svg.style.height = "100%";
        svg.style.display = "block";
      }
      var ctl = animateMolecule(svg || host, host, opts);
      return {
        stop: ctl.stop,
        promise: ctl.promise,
        svg: svg,
        wrap: host,
      };
    });
  }

  /** Optional subtle canvas glow if #orb-canvas exists (backward compat). */
  function mountCanvasGlow() {
    var host = document.getElementById("orb-canvas");
    if (!host || host.querySelector("canvas")) return null;
    var c = document.createElement("canvas");
    host.appendChild(c);
    var ctx = c.getContext("2d");
    var COLORS = [
      "rgba(46,230,197,0.14)",
      "rgba(34,211,238,0.10)",
      "rgba(167,139,250,0.08)",
    ];
    var w, h, orbs, raf;
    var stopped = false;
    function resize() {
      w = c.width = host.clientWidth || 600;
      h = c.height = host.clientHeight || 200;
    }
    function seed() {
      orbs = COLORS.map(function (color, i) {
        return {
          x: (0.2 + 0.3 * i) * w,
          y: (0.35 + 0.15 * (i % 2)) * h,
          r: 40 + i * 18,
          vx: 0.15 + i * 0.05,
          vy: 0.08 + i * 0.03,
          color: color,
        };
      });
    }
    function tick() {
      if (stopped) return;
      ctx.clearRect(0, 0, w, h);
      orbs.forEach(function (o) {
        o.x += o.vx;
        o.y += o.vy;
        if (o.x < -o.r || o.x > w + o.r) o.vx *= -1;
        if (o.y < -o.r || o.y > h + o.r) o.vy *= -1;
        var g = ctx.createRadialGradient(o.x, o.y, 0, o.x, o.y, o.r);
        g.addColorStop(0, o.color);
        g.addColorStop(1, "rgba(0,0,0,0)");
        ctx.fillStyle = g;
        ctx.beginPath();
        ctx.arc(o.x, o.y, o.r, 0, Math.PI * 2);
        ctx.fill();
      });
      raf = requestAnimationFrame(tick);
    }
    resize();
    seed();
    tick();
    global.addEventListener("resize", function () {
      resize();
      seed();
    });
    return {
      stop: function () {
        stopped = true;
        if (raf) cancelAnimationFrame(raf);
      },
    };
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", function () {
      mountCanvasGlow();
    });
  } else {
    mountCanvasGlow();
  }

  global.CrossAffinityOrbs = {
    animateMolecule: animateMolecule,
    mountLogo: mountLogo,
    mountCanvasGlow: mountCanvasGlow,
  };
})(typeof window !== "undefined" ? window : globalThis);
