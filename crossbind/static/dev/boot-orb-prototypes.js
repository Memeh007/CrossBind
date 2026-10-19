/* ddOS boot orb — THROWAWAY prototypes for the splash bake-off (not loaded by the app).
   A = orbital (electron cloud), B = fold (rippling density mesh), C = dock (ligand into pocket).
   Shared API: DdosOrbProto.create(canvas, concept, {total, reduced}) -> {step(state), complete(), destroy()} */
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

  /* —— stage: canvas sizing + projection —— */
  function Stage(canvas) {
    this.cv = canvas;
    this.ctx = canvas.getContext("2d");
    this.resize();
  }
  Stage.prototype.resize = function () {
    var dpr = Math.min(2, global.devicePixelRatio || 1);
    var w = Math.max(120, Math.round(this.cv.getBoundingClientRect().width || 320));
    this.cv.width = w * dpr;
    this.cv.height = w * dpr;
    this.dpr = dpr;
    this.size = w;
    this.cx = w / 2;
    this.cy = w / 2;
    this.R = w * 0.29;
  };
  Stage.prototype.begin = function () {
    var c = this.ctx;
    c.setTransform(this.dpr, 0, 0, this.dpr, 0, 0);
    c.globalCompositeOperation = "source-over";
    c.globalAlpha = 1;
    c.clearRect(0, 0, this.size, this.size);
    c.globalCompositeOperation = "lighter";
  };
  // yaw about Y, then pitch about X; writes [sx, sy, z, f] into out
  Stage.prototype.project = function (x, y, z, yaw, pitch, out) {
    var cy = Math.cos(yaw), sy = Math.sin(yaw);
    var x1 = x * cy + z * sy, z1 = -x * sy + z * cy;
    var cp = Math.cos(pitch), sp = Math.sin(pitch);
    var y2 = y * cp - z1 * sp, z2 = y * sp + z1 * cp;
    var f = 4 / (4 - z2);
    out[0] = this.cx + x1 * f * this.R;
    out[1] = this.cy - y2 * f * this.R;
    out[2] = z2;
    out[3] = f;
    return out;
  };

  /* —— progress dial shared by all concepts —— */
  function drawDial(st, m) {
    var c = st.ctx, R = st.R * 1.5, n = 96, i, a, r1, lit;
    var flash = m.done >= 0 ? Math.exp(-m.done * 3) : 0;
    c.lineWidth = 1;
    for (var pass = 0; pass < 2; pass++) {
      c.beginPath();
      for (i = 0; i < n; i++) {
        lit = i / n < m.prog;
        if ((pass === 1) !== lit) continue;
        a = -Math.PI / 2 + (i / n) * Math.PI * 2;
        r1 = R + (i % 8 === 0 ? 7 : 3);
        c.moveTo(st.cx + Math.cos(a) * R, st.cy + Math.sin(a) * R);
        c.lineTo(st.cx + Math.cos(a) * r1, st.cy + Math.sin(a) * r1);
      }
      c.strokeStyle = pass ? rgba(TEAL, 1) : rgba(DOT, 1);
      c.globalAlpha = pass ? 0.75 + 0.25 * flash : 0.13;
      c.stroke();
    }
    if (m.prog > 0 && m.prog < 1) {
      a = -Math.PI / 2 + m.prog * Math.PI * 2;
      glow(c, TEAL, st.cx + Math.cos(a) * (R + 3), st.cy + Math.sin(a) * (R + 3), 9, 0.9);
    }
    c.globalAlpha = 0.07;
    c.beginPath();
    c.arc(st.cx, st.cy, R - 5, 0, Math.PI * 2);
    c.stroke();
  }

  /* —— A: orbital / electron cloud —— */
  function Orbital() {
    this.nuc = fib(260);
    this.orbits = [
      { n: norm([0.15, 1, 0.2]), r: 1.0, sp: 1.5 },
      { n: norm([0.9, 0.45, 0.25]), r: 0.9, sp: -1.15 },
      { n: norm([-0.65, 0.7, 0.45]), r: 1.1, sp: 0.95 },
    ];
    this.orbits.forEach(function (o) {
      var ref = Math.abs(o.n[1]) < 0.9 ? [0, 1, 0] : [1, 0, 0];
      o.u = norm(cross(o.n, ref));
      o.v = cross(o.n, o.u);
    });
    this.tmp = [0, 0, 0, 0];
  }
  Orbital.prototype.orbitPoint = function (o, ang, r) {
    var c = Math.cos(ang) * r, s = Math.sin(ang) * r;
    return [o.u[0] * c + o.v[0] * s, o.u[1] * c + o.v[1] * s, o.u[2] * c + o.v[2] * s];
  };
  Orbital.prototype.frame = function (st, m) {
    var c = st.ctx, t = m.t, P = this.tmp, i, j, k;
    var yaw = m.reduced ? 0.5 : t * 0.28, pitch = 0.32;
    var flash = m.done >= 0 ? Math.exp(-m.done * 2.5) : 0;
    var breathe = m.reduced ? 1 : 1 + 0.035 * Math.sin(t * 2.2);
    var nr = 0.27 * breathe * (1 - 0.15 * m.p);
    glow(c, TEAL, st.cx, st.cy, st.R * (0.7 + 0.2 * m.p), 0.16 + 0.18 * m.p + 0.4 * flash);
    c.fillStyle = rgba(DOT, 1);
    for (i = 0; i < this.nuc.length; i++) {
      var q = this.nuc[i];
      st.project(q[0] * nr, q[1] * nr, q[2] * nr, yaw * 1.7, pitch, P);
      var d = (P[2] / nr + 1) / 2;
      c.globalAlpha = 0.1 + 0.8 * d * d;
      c.fillRect(P[0] - 0.7, P[1] - 0.7, 1.4, 1.4);
    }
    var lit = Math.floor((m.steps.length * 6) / m.total);
    for (k = 0; k < this.orbits.length; k++) {
      var o = this.orbits[k];
      var rr = o.r * (1 + 0.05 * flash);
      for (j = 0; j < 180; j++) {
        var pt = this.orbitPoint(o, (j / 180) * Math.PI * 2, rr);
        st.project(pt[0], pt[1], pt[2], yaw, pitch, P);
        c.globalAlpha = (0.05 + 0.22 * ((P[2] + 1) / 2)) * (1 + flash);
        c.fillRect(P[0] - 0.5, P[1] - 0.5, 1, 1);
      }
      for (var e = 0; e < 2; e++) {
        var idx = k * 2 + e;
        var on = idx < lit || m.done >= 0;
        var col = on && m.steps[idx] ? STATE_RGB[m.steps[idx].state] || TEAL : on ? TEAL : DOT;
        var ph = (m.reduced ? 0.6 : t * o.sp) + e * Math.PI + k;
        for (var tr = on && !m.reduced ? 14 : 0; tr >= 0; tr--) {
          var p2 = this.orbitPoint(o, ph - tr * 0.045 * Math.sign(o.sp), rr);
          st.project(p2[0], p2[1], p2[2], yaw, pitch, P);
          var dz = (P[2] + 1) / 2;
          if (tr === 0) {
            glow(c, col, P[0], P[1], on ? 10 : 6, on ? 0.55 + 0.45 * dz : 0.2);
          } else {
            c.fillStyle = rgba(col, 1);
            c.globalAlpha = (1 - tr / 15) * 0.5 * dz;
            c.fillRect(P[0] - 0.8, P[1] - 0.8, 1.6, 1.6);
          }
        }
      }
    }
  };

  /* —— B: fold / rippling density mesh —— */
  function Fold() {
    this.lats = 15;
    this.segs = 80;
    this.grid = [];
    for (var i = 0; i < this.lats; i++) {
      var phi = ((i + 1) / (this.lats + 1)) * Math.PI;
      var row = [];
      for (var j = 0; j <= this.segs; j++) {
        var th = (j / this.segs) * Math.PI * 2;
        row.push([Math.sin(phi) * Math.cos(th), Math.cos(phi), Math.sin(phi) * Math.sin(th)]);
      }
      this.grid.push(row);
    }
    this.nodes = fib(14).map(function (p) { return p; });
    this.tmp = [0, 0, 0, 0];
    this.buf = [];
  }
  Fold.prototype.radius = function (p, t, amp) {
    var d = noise3(p[0] * 2.2 + t * 0.55, p[1] * 2.2 - t * 0.4, p[2] * 2.2 + t * 0.25);
    var rip = Math.sin(p[1] * 7 - t * 3.2) * 0.018 * (amp / 0.24);
    return 1 + amp * d + rip;
  };
  Fold.prototype.frame = function (st, m) {
    var c = st.ctx, t = m.reduced ? 1.2 : m.t, P = this.tmp, i, j;
    var yaw = t * 0.3, pitch = 0.38;
    var flash = m.done >= 0 ? Math.exp(-m.done * 2.5) : 0;
    var amp = 0.25 * (1 - m.p) + 0.02;
    glow(c, TEAL, st.cx, st.cy, st.R * 1.1, 0.05 + 0.08 * m.p + 0.25 * flash);
    var buckets = [[], [], []];
    for (i = 0; i < this.lats; i++) {
      var prev = null;
      for (j = 0; j <= this.segs; j++) {
        var q = this.grid[i][j];
        var r = this.radius(q, t, amp);
        st.project(q[0] * r, q[1] * r, q[2] * r, yaw, pitch, P);
        var cur = [P[0], P[1], P[2]];
        if (prev) {
          var z = (prev[2] + cur[2]) / 2;
          buckets[z < -0.25 ? 0 : z < 0.35 ? 1 : 2].push(prev[0], prev[1], cur[0], cur[1]);
        }
        prev = cur;
      }
    }
    var alphas = [0.06, 0.2, 0.5];
    c.lineWidth = 1;
    c.strokeStyle = rgba(DOT, 1);
    for (var b = 0; b < 3; b++) {
      var L = buckets[b];
      c.beginPath();
      for (var s = 0; s < L.length; s += 4) {
        c.moveTo(L[s], L[s + 1]);
        c.lineTo(L[s + 2], L[s + 3]);
      }
      c.globalAlpha = alphas[b] * (0.75 + 0.5 * m.p) * (1 + flash);
      c.stroke();
    }
    for (i = 0; i < m.steps.length && i < this.nodes.length; i++) {
      var n = this.nodes[(i * 5) % this.nodes.length];
      var rn = this.radius(n, t, amp) * 1.01;
      st.project(n[0] * rn, n[1] * rn, n[2] * rn, yaw, pitch, P);
      var age = (m.now - m.steps[i].at) / 1000;
      var front = (P[2] + 1) / 2;
      glow(c, STATE_RGB[m.steps[i].state] || TEAL, P[0], P[1], 10 + 10 * Math.exp(-age * 3), (0.3 + 0.7 * front) * (0.6 + 0.4 * Math.exp(-age * 3)));
    }
  };

  /* —— C: dock / ligand converges into a surface pocket —— */
  function mulberry(seed) {
    return function () {
      seed |= 0;
      seed = (seed + 0x6d2b79f5) | 0;
      var t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }

  function Dock() {
    var N = 1100, i, rnd = mulberry(7);
    this.pts = fib(N).map(function (p) {
      return norm([p[0] + (rnd() - 0.5) * 0.06, p[1] + (rnd() - 0.5) * 0.06, p[2] + (rnd() - 0.5) * 0.06]);
    });
    this.n = N;
    var P = norm([0.42, 0.22, 0.88]);
    this.P = P;
    this.r = new Float32Array(N);
    this.k = new Float32Array(N);
    this.ang = new Float32Array(N);
    this.sx = new Float32Array(N);
    this.sy = new Float32Array(N);
    var TH = 0.64;
    this.TH = TH;
    for (i = 0; i < N; i++) {
      var p = this.pts[i];
      var a = Math.acos(clamp(dot3(p, P), -1, 1));
      var lump = 1 + 0.07 * noise3(p[0] * 2.6, p[1] * 2.6, p[2] * 2.6) + 0.03 * noise3(p[0] * 6.1 + 2, p[1] * 6.1, p[2] * 6.1 - 1);
      var k = a < TH ? 1 - (a / TH) * (a / TH) : 0;
      var bowl = 0.4 * k * k * (3 - 2 * k);
      var rim = 0.06 * Math.exp(-Math.pow((a - TH) / 0.09, 2));
      this.r[i] = lump - bowl + rim;
      this.k[i] = k;
      this.ang[i] = a;
    }
    var e1 = [-P[0], -P[1], -P[2]];
    var e2 = norm(cross(P, [0, 1, 0]));
    var e3 = cross(e1, e2);
    this.basis = [e1, e2, e3];
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
    // contact targets: rim dots in the direction each seated atom points away from the pocket axis
    var order = [1, 4, 8, 7, 10, 2, 9, 5, 0, 3, 6];
    var used = {};
    this.targets = [];
    for (var s = 0; s < 12; s++) {
      var ai = order[s % order.length];
      var fa = this.worldAtom(ai, this.seat, 0, 0);
      var off = [fa[0] - this.seat[0], fa[1] - this.seat[1], fa[2] - this.seat[2]];
      var along = dot3(off, P);
      var perp = norm([off[0] - P[0] * along, off[1] - P[1] * along, off[2] - P[2] * along]);
      var ra = TH * (0.7 + 0.12 * (s % 3));
      var aim = [P[0] * Math.cos(ra) + perp[0] * Math.sin(ra), P[1] * Math.cos(ra) + perp[1] * Math.sin(ra), P[2] * Math.cos(ra) + perp[2] * Math.sin(ra)];
      var best = -1, bd = -2;
      for (i = 0; i < N; i++) {
        if (used[i]) continue;
        var d = dot3(this.pts[i], aim);
        if (d > bd) { bd = d; best = i; }
      }
      used[best] = 1;
      this.targets.push({ atom: ai, dot: best });
    }
    this.tmp = [0, 0, 0, 0];
    this.ax = new Float32Array(this.atoms.length);
    this.ay = new Float32Array(this.atoms.length);
    this.az = new Float32Array(this.atoms.length);
  }
  Dock.prototype.worldAtom = function (i, pos, a1, a2) {
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
  Dock.prototype.frame = function (st, m) {
    var c = st.ctx, t = m.t, P = this.tmp, i;
    var yaw = m.reduced ? -0.2 : -0.2 + 0.22 * Math.sin(t * 0.37);
    var pitch = m.reduced ? 0.14 : 0.14 + 0.06 * Math.sin(t * 0.29 + 1);
    var wave = m.done >= 0 ? m.done * 2.8 : -9;
    var waveFade = m.done >= 0 ? Math.max(0, 1 - m.done / 1.3) : 0;
    c.fillStyle = rgba(DOT, 1);
    for (i = 0; i < this.n; i++) {
      var q = this.pts[i], r = this.r[i];
      st.project(q[0] * r, q[1] * r, q[2] * r, yaw, pitch, P);
      this.sx[i] = P[0];
      this.sy[i] = P[1];
      var d = clamp((P[2] + 1) / 2, 0, 1);
      var kk = this.k[i];
      var rimGlow = Math.exp(-Math.pow((this.ang[i] - this.TH) / 0.08, 2));
      var a = (0.05 + 0.62 * d * d) * (1 - 0.6 * kk) + rimGlow * (0.15 + 0.35 * m.p) * d;
      if (waveFade > 0) a += 0.9 * waveFade * Math.exp(-Math.pow(this.ang[i] - wave, 2) / 0.025);
      var s = 0.8 + 1.1 * d * P[3];
      c.globalAlpha = clamp(a, 0, 1);
      c.fillRect(P[0] - s / 2, P[1] - s / 2, s, s);
    }
    var ap = m.reduced ? 1 : easeOutCubic(clamp(t / 1.1, 0, 1));
    var u = 1 - ap, S = this.start, C = this.ctrl, M = this.mouth;
    var bz = [
      u * u * S[0] + 2 * u * ap * C[0] + ap * ap * M[0],
      u * u * S[1] + 2 * u * ap * C[1] + ap * ap * M[1],
      u * u * S[2] + 2 * u * ap * C[2] + ap * ap * M[2],
    ];
    var qn = easeInOut(clamp(m.p, 0, 1)) * ap;
    var hov = (1 - qn) * 0.07 * ap * (m.reduced ? 0 : 1);
    var b = this.basis;
    var pos = [0, 1, 2].map(function (k) {
      return bz[k] + (this.seat[k] - bz[k]) * qn + b[1][k] * hov * Math.sin(t * 2.1) + b[2][k] * hov * Math.cos(t * 1.7);
    }, this);
    var a1 = m.reduced ? 0 : (1 - qn) * (t * 2.2 + 0.6);
    var a2 = m.reduced ? 0 : (1 - qn) * 1.2 * Math.sin(t * 1.1);
    for (i = 0; i < this.atoms.length; i++) {
      var w = this.worldAtom(i, pos, a1, a2);
      st.project(w[0], w[1], w[2], yaw, pitch, P);
      this.ax[i] = P[0];
      this.ay[i] = P[1];
      this.az[i] = P[2];
    }
    var flash = m.done >= 0 ? Math.exp(-m.done * 3) : 0;
    c.lineWidth = 1.2;
    c.strokeStyle = rgba(LIG, 1);
    c.globalAlpha = 0.5 + 0.4 * flash;
    c.beginPath();
    for (i = 0; i < this.bonds.length; i++) {
      var bd = this.bonds[i];
      c.moveTo(this.ax[bd[0]], this.ay[bd[0]]);
      c.lineTo(this.ax[bd[1]], this.ay[bd[1]]);
    }
    c.stroke();
    for (i = 0; i < this.atoms.length; i++) {
      glow(c, TEAL, this.ax[i], this.ay[i], 7 + 4 * flash, 0.55 + 0.45 * flash);
      c.fillStyle = rgba(LIG, 1);
      c.globalAlpha = 0.95;
      c.fillRect(this.ax[i] - 1, this.ay[i] - 1, 2, 2);
    }
    c.lineWidth = 1;
    for (i = 0; i < m.steps.length; i++) {
      var tg = this.targets[i % this.targets.length];
      var col = STATE_RGB[m.steps[i].state] || TEAL;
      var age = m.reduced ? 9 : (m.now - m.steps[i].at) / 1000;
      var pulse = Math.exp(-age * 3.2);
      var x1 = this.ax[tg.atom], y1 = this.ay[tg.atom], x2 = this.sx[tg.dot], y2 = this.sy[tg.dot];
      c.setLineDash(m.steps[i].state === "bad" ? [1, 4] : [2, 3]);
      c.lineDashOffset = m.reduced ? 0 : -t * 10;
      c.strokeStyle = rgba(col, 1);
      c.globalAlpha = 0.45 + 0.55 * pulse;
      c.beginPath();
      c.moveTo(x1, y1);
      c.lineTo(x2, y2);
      c.stroke();
      glow(c, col, x2, y2, 5 + 7 * pulse, 0.6 + 0.4 * pulse);
    }
    c.setLineDash([]);
  };

  var CONCEPTS = { orbital: Orbital, fold: Fold, dock: Dock };

  function Orb(canvas, concept, opts) {
    opts = opts || {};
    this.st = new Stage(canvas);
    this.reduced = !!opts.reduced;
    this.concept = new CONCEPTS[concept]();
    this.total = opts.total || 8;
    this.steps = [];
    this.pDisp = 0;
    this.completeAt = null;
    this.t0 = performance.now();
    this.last = this.t0;
    this.raf = 0;
    var self = this;
    this._tick = function (now) { self.tick(now); };
    if (this.reduced) this.render(this.t0);
    else this.raf = requestAnimationFrame(this._tick);
  }
  Orb.prototype.progress = function () { return Math.min(1, this.steps.length / this.total); };
  Orb.prototype.step = function (state) {
    this.steps.push({ state: state || "ok", at: performance.now() });
    if (this.reduced) this.render(performance.now());
  };
  Orb.prototype.complete = function () {
    if (this.completeAt == null) this.completeAt = performance.now();
    if (this.reduced) this.render(performance.now());
  };
  Orb.prototype.tick = function (now) {
    var dt = Math.min(0.05, (now - this.last) / 1000);
    this.last = now;
    var target = this.completeAt != null ? 1 : this.progress();
    this.pDisp += (target - this.pDisp) * Math.min(1, dt * 5);
    this.render(now);
    this.raf = requestAnimationFrame(this._tick);
  };
  Orb.prototype.render = function (now) {
    var st = this.st;
    st.begin();
    var prog = this.completeAt != null ? 1 : this.progress();
    var m = {
      t: (now - this.t0) / 1000,
      now: now,
      p: this.reduced ? 1 : this.pDisp,
      prog: this.reduced ? prog : this.pDisp,
      steps: this.steps,
      total: this.total,
      done: this.completeAt != null && !this.reduced ? (now - this.completeAt) / 1000 : -1,
      reduced: this.reduced,
    };
    this.concept.frame(st, m);
    drawDial(st, m);
  };
  Orb.prototype.destroy = function () {
    cancelAnimationFrame(this.raf);
    this.raf = 0;
  };

  global.DdosOrbProto = {
    create: function (canvas, concept, opts) { return new Orb(canvas, concept, opts); },
  };
})(window);
