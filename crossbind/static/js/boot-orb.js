/* ddOS boot orb — a dot-surface receptor with a carved pocket; a ball-and-stick ligand flies in,
   tumbles, and seats as boot checks land. Each check forms one contact (coloured by its result),
   the outer dial fills per check, and "ready" sends a wave across the surface.
   Canvas 2D, no dependencies. Decorative only: nothing here is a docking result.
   API: DdosBootOrb.create(canvas, {total, reduced}) -> {step(state), setTotal(n), complete(), destroy()} */
(function (global) {
  "use strict";

  var TEAL = [46, 230, 197];
  var DOT = [140, 232, 212];
  var LIG = [214, 255, 244];
  var STATE_RGB = { ok: TEAL, warn: [245, 165, 36], bad: [240, 113, 120], off: [104, 116, 116] };

  function rgba(c, a) { return "rgba(" + c[0] + "," + c[1] + "," + c[2] + "," + a + ")"; }
  function clamp(x, a, b) { return x < a ? a : x > b ? b : x; }
  function easeOutCubic(t) { return 1 - Math.pow(1 - t, 3); }
  function easeInOut(t) { return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2; }
  function norm(v) { var l = Math.hypot(v[0], v[1], v[2]) || 1; return [v[0] / l, v[1] / l, v[2] / l]; }
  function dot3(a, b) { return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]; }
  function cross(a, b) { return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]]; }
  function noise3(x, y, z) {
    return Math.sin(x * 1.7 + Math.sin(y * 1.3)) * Math.sin(y * 1.9 + Math.sin(z * 1.1)) * Math.sin(z * 1.5 + Math.sin(x * 1.2));
  }
  function mulberry(seed) {
    return function () {
      seed = (seed + 0x6d2b79f5) | 0;
      var t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }
  function fib(n) {
    var out = [], g = Math.PI * (3 - Math.sqrt(5));
    for (var i = 0; i < n; i++) {
      var y = 1 - ((i + 0.5) * 2) / n, r = Math.sqrt(1 - y * y), th = g * i;
      out.push([Math.cos(th) * r, y, Math.sin(th) * r]);
    }
    return out;
  }

  var sprites = {};
  function sprite(c) {
    var k = c.join(",");
    if (sprites[k]) return sprites[k];
    var s = document.createElement("canvas");
    s.width = s.height = 64;
    var g = s.getContext("2d");
    var gr = g.createRadialGradient(32, 32, 0, 32, 32, 32);
    gr.addColorStop(0, rgba(c, 1));
    gr.addColorStop(0.16, rgba(c, 0.5));
    gr.addColorStop(0.45, rgba(c, 0.1));
    gr.addColorStop(1, rgba(c, 0));
    g.fillStyle = gr;
    g.fillRect(0, 0, 64, 64);
    return (sprites[k] = s);
  }
  function glow(ctx, c, x, y, r, a) {
    ctx.globalAlpha = clamp(a, 0, 1);
    ctx.drawImage(sprite(c), x - r, y - r, 2 * r, 2 * r);
  }

  /* —— scene geometry (receptor frame) —— */
  var N_DOTS = 1100;
  var POCKET_HALF_ANGLE = 0.64;

  function Scene() {
    var i, rnd = mulberry(7), TH = POCKET_HALF_ANGLE;
    var P = norm([0.42, 0.22, 0.88]);
    this.P = P;
    this.pts = fib(N_DOTS).map(function (p) {
      return norm([p[0] + (rnd() - 0.5) * 0.06, p[1] + (rnd() - 0.5) * 0.06, p[2] + (rnd() - 0.5) * 0.06]);
    });
    this.r = new Float32Array(N_DOTS);
    this.k = new Float32Array(N_DOTS);
    this.rim = new Float32Array(N_DOTS);
    this.ang = new Float32Array(N_DOTS);
    this.sx = new Float32Array(N_DOTS);
    this.sy = new Float32Array(N_DOTS);
    for (i = 0; i < N_DOTS; i++) {
      var p = this.pts[i];
      var a = Math.acos(clamp(dot3(p, P), -1, 1));
      var lump = 1 + 0.07 * noise3(p[0] * 2.6, p[1] * 2.6, p[2] * 2.6) + 0.03 * noise3(p[0] * 6.1 + 2, p[1] * 6.1, p[2] * 6.1 - 1);
      var k = a < TH ? 1 - (a / TH) * (a / TH) : 0;
      this.r[i] = lump - 0.4 * k * k * (3 - 2 * k) + 0.06 * Math.exp(-Math.pow((a - TH) / 0.09, 2));
      this.k[i] = k;
      this.rim[i] = Math.exp(-Math.pow((a - TH) / 0.08, 2));
      this.ang[i] = a;
    }

    var e1 = [-P[0], -P[1], -P[2]];
    var e2 = norm(cross(P, [0, 1, 0]));
    this.basis = [e1, e2, cross(e1, e2)];
    var ring = [], L = 0.15;
    for (i = 0; i < 6; i++) ring.push([0.025 * (i % 2 ? 1 : -1), Math.cos((i * Math.PI) / 3) * L, Math.sin((i * Math.PI) / 3) * L]);
    this.atoms = ring.concat([
      [-0.04, 0.3, 0.0], [-0.1, 0.38, 0.1], [0.02, -0.29, 0.04], [0.05, 0.37, -0.1], [-0.06, -0.12, -0.27],
    ]);
    this.bonds = [[0, 1], [1, 2], [2, 3], [3, 4], [4, 5], [5, 0], [0, 6], [6, 7], [3, 8], [6, 9], [4, 10]];
    this.seat = [P[0] * 0.86, P[1] * 0.86, P[2] * 0.86];
    this.mouth = [P[0] * 1.6, P[1] * 1.6, P[2] * 1.6];
    this.start = [-2.0, 1.4, 1.6];
    this.ctrl = [-0.5, 2.0, 2.0];
    this.ax = new Float32Array(this.atoms.length);
    this.ay = new Float32Array(this.atoms.length);

    // Contact slots: each pairs a ligand atom with the rim dot it points toward once seated,
    // so successive contacts fan out around the pocket instead of piling up.
    var order = [1, 4, 8, 7, 10, 2, 9, 5, 0, 3, 6];
    var used = {};
    this.targets = [];
    for (var s = 0; s < 16; s++) {
      var ai = order[s % order.length];
      var fa = this.atomAt(ai, this.seat, 0, 0);
      var off = [fa[0] - this.seat[0], fa[1] - this.seat[1], fa[2] - this.seat[2]];
      var along = dot3(off, P);
      var perp = norm([off[0] - P[0] * along, off[1] - P[1] * along, off[2] - P[2] * along]);
      var ra = TH * (0.7 + 0.12 * (s % 3)), ca = Math.cos(ra), sa = Math.sin(ra);
      var aim = [P[0] * ca + perp[0] * sa, P[1] * ca + perp[1] * sa, P[2] * ca + perp[2] * sa];
      var best = 0, bd = -2;
      for (i = 0; i < N_DOTS; i++) {
        if (used[i]) continue;
        var d = dot3(this.pts[i], aim);
        if (d > bd) { bd = d; best = i; }
      }
      used[best] = 1;
      this.targets.push({ atom: ai, dot: best });
    }
  }

  // Ligand atom i in receptor frame at centre `pos`, tumbled by a1 (about e1) then a2 (about e2).
  Scene.prototype.atomAt = function (i, pos, a1, a2) {
    var l = this.atoms[i], x = l[0], y = l[1], z = l[2];
    var c1 = Math.cos(a1), s1 = Math.sin(a1);
    var y1 = y * c1 - z * s1, z1 = y * s1 + z * c1;
    var c2 = Math.cos(a2), s2 = Math.sin(a2);
    var x2 = x * c2 + z1 * s2, z2 = -x * s2 + z1 * c2;
    var b = this.basis;
    return [
      pos[0] + b[0][0] * x2 + b[1][0] * y1 + b[2][0] * z2,
      pos[1] + b[0][1] * x2 + b[1][1] * y1 + b[2][1] * z2,
      pos[2] + b[0][2] * x2 + b[1][2] * y1 + b[2][2] * z2,
    ];
  };

  /* —— orb controller —— */
  function Orb(canvas, opts) {
    opts = opts || {};
    this.cv = canvas;
    this.ctx = canvas.getContext("2d");
    this.scene = new Scene();
    this.reduced = !!opts.reduced;
    this.total = Math.max(1, opts.total || 8);
    this.steps = [];
    this.pDisp = 0;
    this.completeAt = null;
    this.t0 = performance.now();
    this.last = this.t0;
    this.raf = 0;
    this.out = [0, 0, 0, 0];
    var self = this;
    this._tick = function (now) { self.tick(now); };
    this._resize = function () { self.resize(); if (self.reduced) self.render(performance.now()); };
    this.resize();
    global.addEventListener("resize", this._resize);
    if (this.reduced) this.render(this.t0);
    else this.raf = requestAnimationFrame(this._tick);
  }

  Orb.prototype.resize = function () {
    var dpr = Math.min(2, global.devicePixelRatio || 1);
    var w = Math.max(120, Math.round(this.cv.getBoundingClientRect().width || 300));
    this.cv.width = w * dpr;
    this.cv.height = w * dpr;
    this.dpr = dpr;
    this.size = w;
    this.cx = w / 2;
    this.cy = w / 2;
    this.R = w * 0.29;
  };

  Orb.prototype.project = function (x, y, z, yaw, pitch) {
    var o = this.out;
    var cy = Math.cos(yaw), sy = Math.sin(yaw);
    var x1 = x * cy + z * sy, z1 = -x * sy + z * cy;
    var cp = Math.cos(pitch), sp = Math.sin(pitch);
    var y2 = y * cp - z1 * sp, z2 = y * sp + z1 * cp;
    var f = 4 / (4 - z2);
    o[0] = this.cx + x1 * f * this.R;
    o[1] = this.cy - y2 * f * this.R;
    o[2] = z2;
    o[3] = f;
    return o;
  };

  Orb.prototype.step = function (state) {
    this.steps.push({ state: STATE_RGB[state] ? state : "ok", at: performance.now() });
    if (this.steps.length > this.total) this.total = this.steps.length;
    if (this.reduced) this.render(performance.now());
  };
  Orb.prototype.setTotal = function (n) {
    this.total = Math.max(1, n, this.steps.length);
    if (this.reduced) this.render(performance.now());
  };
  Orb.prototype.complete = function () {
    if (this.completeAt == null) this.completeAt = performance.now();
    if (this.reduced) this.render(performance.now());
  };
  Orb.prototype.destroy = function () {
    cancelAnimationFrame(this.raf);
    this.raf = 0;
    global.removeEventListener("resize", this._resize);
  };

  Orb.prototype.tick = function (now) {
    var dt = Math.min(0.05, (now - this.last) / 1000);
    this.last = now;
    var target = this.completeAt != null ? 1 : Math.min(1, this.steps.length / this.total);
    this.pDisp += (target - this.pDisp) * Math.min(1, dt * 5);
    this.render(now);
    this.raf = requestAnimationFrame(this._tick);
  };

  Orb.prototype.render = function (now) {
    var c = this.ctx;
    c.setTransform(this.dpr, 0, 0, this.dpr, 0, 0);
    c.globalCompositeOperation = "source-over";
    c.globalAlpha = 1;
    c.clearRect(0, 0, this.size, this.size);
    c.globalCompositeOperation = "lighter";
    var exact = this.completeAt != null ? 1 : Math.min(1, this.steps.length / this.total);
    var m = {
      t: (now - this.t0) / 1000,
      now: now,
      // reduced motion: ligand is drawn already seated; only discrete state (contacts, dial) changes
      p: this.reduced ? 1 : this.pDisp,
      prog: this.reduced ? exact : this.pDisp,
      done: this.completeAt != null && !this.reduced ? (now - this.completeAt) / 1000 : -1,
    };
    this.drawSurface(m);
    this.drawLigand(m);
    this.drawContacts(m);
    this.drawDial(m);
  };

  Orb.prototype.view = function (t) {
    if (this.reduced) return [-0.2, 0.14];
    return [-0.2 + 0.22 * Math.sin(t * 0.37), 0.14 + 0.06 * Math.sin(t * 0.29 + 1)];
  };

  Orb.prototype.drawSurface = function (m) {
    var c = this.ctx, S = this.scene, v = this.view(m.t), i;
    var wave = m.done >= 0 ? m.done * 2.8 : -9;
    var waveFade = m.done >= 0 ? Math.max(0, 1 - m.done / 1.3) : 0;
    c.fillStyle = rgba(DOT, 1);
    for (i = 0; i < N_DOTS; i++) {
      var q = S.pts[i], r = S.r[i];
      var o = this.project(q[0] * r, q[1] * r, q[2] * r, v[0], v[1]);
      S.sx[i] = o[0];
      S.sy[i] = o[1];
      var d = clamp((o[2] + 1) / 2, 0, 1);
      // pocket interior darkens (reads as a cavity); the rim brightens as boot progresses
      var a = (0.05 + 0.62 * d * d) * (1 - 0.6 * S.k[i]) + S.rim[i] * (0.15 + 0.35 * m.p) * d;
      if (waveFade > 0) a += 0.9 * waveFade * Math.exp(-Math.pow(S.ang[i] - wave, 2) / 0.025);
      var s = 0.8 + 1.1 * d * o[3];
      c.globalAlpha = clamp(a, 0, 1);
      c.fillRect(o[0] - s / 2, o[1] - s / 2, s, s);
    }
  };

  Orb.prototype.drawLigand = function (m) {
    var c = this.ctx, S = this.scene, v = this.view(m.t), t = m.t, i, k;
    var ap = this.reduced ? 1 : easeOutCubic(clamp(t / 1.1, 0, 1));
    var u = 1 - ap, A = S.start, C = S.ctrl, M = S.mouth, b = S.basis;
    var qn = easeInOut(clamp(m.p, 0, 1)) * ap;
    var hov = this.reduced ? 0 : (1 - qn) * 0.07 * ap;
    var pos = [0, 0, 0];
    for (k = 0; k < 3; k++) {
      var bz = u * u * A[k] + 2 * u * ap * C[k] + ap * ap * M[k];
      pos[k] = bz + (S.seat[k] - bz) * qn + b[1][k] * hov * Math.sin(t * 2.1) + b[2][k] * hov * Math.cos(t * 1.7);
    }
    var a1 = this.reduced ? 0 : (1 - qn) * (t * 2.2 + 0.6);
    var a2 = this.reduced ? 0 : (1 - qn) * 1.2 * Math.sin(t * 1.1);
    for (i = 0; i < S.atoms.length; i++) {
      var w = S.atomAt(i, pos, a1, a2);
      var o = this.project(w[0], w[1], w[2], v[0], v[1]);
      S.ax[i] = o[0];
      S.ay[i] = o[1];
    }
    var flash = m.done >= 0 ? Math.exp(-m.done * 3) : 0;
    c.lineWidth = 1.2;
    c.strokeStyle = rgba(LIG, 1);
    c.globalAlpha = 0.5 + 0.4 * flash;
    c.beginPath();
    for (i = 0; i < S.bonds.length; i++) {
      var bd = S.bonds[i];
      c.moveTo(S.ax[bd[0]], S.ay[bd[0]]);
      c.lineTo(S.ax[bd[1]], S.ay[bd[1]]);
    }
    c.stroke();
    c.fillStyle = rgba(LIG, 1);
    for (i = 0; i < S.atoms.length; i++) {
      glow(c, TEAL, S.ax[i], S.ay[i], 7 + 4 * flash, 0.55 + 0.45 * flash);
      c.globalAlpha = 0.95;
      c.fillRect(S.ax[i] - 1, S.ay[i] - 1, 2, 2);
    }
  };

  Orb.prototype.drawContacts = function (m) {
    var c = this.ctx, S = this.scene, i;
    c.lineWidth = 1;
    for (i = 0; i < this.steps.length; i++) {
      var stp = this.steps[i];
      var tg = S.targets[i % S.targets.length];
      var col = STATE_RGB[stp.state];
      var pulse = this.reduced ? 0 : Math.exp(-((m.now - stp.at) / 1000) * 3.2);
      var x2 = S.sx[tg.dot], y2 = S.sy[tg.dot];
      c.setLineDash(stp.state === "bad" ? [1, 4] : [2, 3]);
      c.lineDashOffset = this.reduced ? 0 : -m.t * 10;
      c.strokeStyle = rgba(col, 1);
      c.globalAlpha = 0.45 + 0.55 * pulse;
      c.beginPath();
      c.moveTo(S.ax[tg.atom], S.ay[tg.atom]);
      c.lineTo(x2, y2);
      c.stroke();
      glow(c, col, x2, y2, 5 + 7 * pulse, 0.6 + 0.4 * pulse);
    }
    c.setLineDash([]);
  };

  // Outer dial: one arc segment per boot check, lit in that check's colour as progress passes it.
  Orb.prototype.drawDial = function (m) {
    var c = this.ctx, R = this.R * 1.5, n = 96, i, a, r1, seg, col, key;
    var flash = m.done >= 0 ? Math.exp(-m.done * 3) : 0;
    var paths = {};
    for (i = 0; i < n; i++) {
      var f = i / n;
      if (f < m.prog) {
        seg = Math.min(this.steps.length - 1, Math.floor(f * this.total));
        key = seg >= 0 ? this.steps[seg].state : "ok";
      } else key = "dim";
      a = -Math.PI / 2 + f * Math.PI * 2;
      r1 = R + (i % 8 === 0 ? 7 : 3);
      (paths[key] = paths[key] || []).push(Math.cos(a), Math.sin(a), r1);
    }
    c.lineWidth = 1;
    for (key in paths) {
      var L = paths[key];
      c.beginPath();
      for (i = 0; i < L.length; i += 3) {
        c.moveTo(this.cx + L[i] * R, this.cy + L[i + 1] * R);
        c.lineTo(this.cx + L[i] * L[i + 2], this.cy + L[i + 1] * L[i + 2]);
      }
      col = key === "dim" ? DOT : STATE_RGB[key];
      c.strokeStyle = rgba(col, 1);
      c.globalAlpha = key === "dim" ? 0.13 : 0.75 + 0.25 * flash;
      c.stroke();
    }
    if (m.prog > 0.002 && m.prog < 0.998) {
      a = -Math.PI / 2 + m.prog * Math.PI * 2;
      glow(c, TEAL, this.cx + Math.cos(a) * (R + 3), this.cy + Math.sin(a) * (R + 3), 9, 0.9);
    }
    c.strokeStyle = rgba(DOT, 1);
    c.globalAlpha = 0.07;
    c.beginPath();
    c.arc(this.cx, this.cy, R - 5, 0, Math.PI * 2);
    c.stroke();
  };

  global.DdosBootOrb = {
    create: function (canvas, opts) {
      if (!canvas || !canvas.getContext) return null;
      return new Orb(canvas, opts);
    },
  };
})(window);
