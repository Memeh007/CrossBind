/* Cross Affinity 3Dmol viewer + residue browser (realistic ligands) */
(function () {
  const vp = document.getElementById("viewport");
  if (!vp || typeof $3Dmol === "undefined") {
    if (vp) vp.innerHTML = "<p style='padding:1rem;color:#f87171'>3Dmol.js failed to load (CDN).</p>";
    return;
  }

  const jobId = vp.dataset.job;
  const box = {
    cx: parseFloat(vp.dataset.cx),
    cy: parseFloat(vp.dataset.cy),
    cz: parseFloat(vp.dataset.cz),
    sx: parseFloat(vp.dataset.sx),
    sy: parseFloat(vp.dataset.sy),
    sz: parseFloat(vp.dataset.sz),
  };

  const statusEl = document.getElementById("viewer-status");
  function setStatus(text, cls) {
    if (!statusEl) return;
    statusEl.textContent = text;
    statusEl.className = "viewer-status" + (cls ? " " + cls : "");
  }

  // Force container into a sane size before WebGL allocates textures
  function clampViewport() {
    if (vp.clientHeight > 900 || vp.clientHeight < 80) {
      vp.style.height = "100%";
      vp.style.maxHeight = "100%";
    }
    if (vp.clientWidth < 80) {
      vp.style.width = "100%";
    }
  }
  clampViewport();

  let viewer = $3Dmol.createViewer(vp, {
    backgroundColor: "0x05080f",
    antialias: true,
    ambientOcclusion: true,
  });
  clampViewport();
  if (typeof viewer.resize === "function") viewer.resize();

  let receptorData = null;
  let receptorFormat = "pdb";
  let posesData = null;
  let highlight = null;
  let poseModelIndex = null; // 3Dmol model index for ligand frames

  // Jmol / CPK-ish element colors (hex strings for 3Dmol)
  const ELEM_COLORS = {
    C: "0x909090",
    N: "0x3050F8",
    O: "0xFF0D0D",
    S: "0xFFFF30",
    P: "0xFF8000",
    F: "0x90E050",
    CL: "0x1FF01F",
    Cl: "0x1FF01F",
    BR: "0xA62929",
    Br: "0xA62929",
    I: "0x940094",
    H: "0xE6E6E6",
    B: "0xFFB5B5",
    SE: "0xFFA100",
  };

  function fetchStructure(kind, prefer) {
    let url = "/api/job/" + encodeURIComponent(jobId) + "/structure?kind=" + kind;
    if (prefer) url += "&prefer=" + encodeURIComponent(prefer);
    return fetch(url).then(function (r) {
      if (!r.ok) return null;
      return r.json();
    });
  }

  function drawBox() {
    const tog = document.getElementById("tog-box");
    if (!tog || !tog.checked) return;
    if (![box.cx, box.cy, box.cz, box.sx, box.sy, box.sz].every(function (n) {
      return typeof n === "number" && !isNaN(n);
    })) return;
    const hx = box.sx / 2, hy = box.sy / 2, hz = box.sz / 2;
    const c = { x: box.cx, y: box.cy, z: box.cz };
    const corners = [
      [-hx, -hy, -hz], [hx, -hy, -hz], [hx, hy, -hz], [-hx, hy, -hz],
      [-hx, -hy, hz], [hx, -hy, hz], [hx, hy, hz], [-hx, hy, hz],
    ].map(function (p) {
      return { x: c.x + p[0], y: c.y + p[1], z: c.z + p[2] };
    });
    const edges = [
      [0, 1], [1, 2], [2, 3], [3, 0],
      [4, 5], [5, 6], [6, 7], [7, 4],
      [0, 4], [1, 5], [2, 6], [3, 7],
    ];
    edges.forEach(function (pair) {
      viewer.addLine({
        start: corners[pair[0]],
        end: corners[pair[1]],
        color: "0x2ee6c5",
        linewidth: 1,
        opacity: 0.35,
        dashed: true,
      });
    });
  }

  function styleReceptor() {
    const cartoonEl = document.getElementById("tog-cartoon");
    const sidesEl = document.getElementById("tog-sidechains");
    const cartoon = cartoonEl ? cartoonEl.checked : true;
    const sides = sidesEl ? sidesEl.checked : false;

    // Clear protein styles only on model 0 when possible
    if (receptorData) {
      viewer.setStyle({ model: 0 }, {});
      if (cartoon) {
        viewer.setStyle(
          { model: 0, hetflag: false },
          {
            cartoon: {
              color: "spectrum",
              opacity: 0.88,
              thickness: 0.3,
            },
          }
        );
      } else {
        viewer.setStyle(
          { model: 0, hetflag: false },
          { line: { colorscheme: "amino", linewidth: 1.2 } }
        );
      }
      if (sides) {
        // Thin sidechain sticks — keep backbone quieter so ligand pops
        viewer.addStyle(
          { model: 0, hetflag: false, byres: true, sidechain: true },
          { stick: { radius: 0.12, colorscheme: "default", opacity: 0.85 } }
        );
        // Fallback if sidechain selector unsupported: all non-backbone heavy
        viewer.addStyle(
          {
            model: 0,
            hetflag: false,
            not: { atom: ["C", "N", "O", "CA", "H", "HA"] },
          },
          { stick: { radius: 0.11, colorscheme: "default", opacity: 0.8 } }
        );
      }
      if (highlight) {
        viewer.addStyle(
          { model: 0, chain: highlight.chain, resi: highlight.resi },
          {
            stick: { radius: 0.22, color: "0x22d3ee" },
            sphere: { scale: 0.28, color: "0x22d3ee" },
          }
        );
      }
    }
  }

  function applyElementColors(sel, stickRadius, sphereScale, opacity) {
    opacity = opacity == null ? 1 : opacity;
    // Base stick with Jmol scheme, then reinforce common elements
    viewer.setStyle(
      sel,
      {
        stick: {
          radius: stickRadius,
          colorscheme: "Jmol",
          opacity: opacity,
        },
        sphere: {
          scale: sphereScale,
          colorscheme: "Jmol",
          opacity: opacity,
        },
      }
    );
    // Hide hydrogens for clarity (faint if somehow present)
    viewer.addStyle(
      Object.assign({}, sel, { elem: "H" }),
      {
        stick: { hidden: true },
        sphere: { hidden: true },
      }
    );
  }

  function stylePoses() {
    const tog = document.getElementById("tog-poses");
    if (!posesData || !tog || !tog.checked) return;
    if (poseModelIndex == null) return;

    const mode = parseInt(
      (document.getElementById("pose-select") || {}).value || "1",
      10
    );
    const frame = Math.max(0, mode - 1);
    try {
      viewer.setFrame(frame);
    } catch (e) {
      /* ignore */
    }

    const sel = { model: poseModelIndex };
    // Active pose: licorice + sphere (ball-and-stick), thicker than protein
    applyElementColors(sel, 0.22, 0.28, 1.0);

    // Soft teal rim on carbons so ligand reads against cartoon
    viewer.addStyle(
      Object.assign({}, sel, { elem: "C" }),
      {
        stick: { radius: 0.22, color: "0xb8c4c0", opacity: 1 },
        sphere: { scale: 0.26, color: "0xb8c4c0", opacity: 1 },
      }
    );
    Object.keys(ELEM_COLORS).forEach(function (el) {
      if (el === "C" || el === "H") return;
      viewer.addStyle(
        Object.assign({}, sel, { elem: el }),
        {
          stick: { radius: 0.22, color: ELEM_COLORS[el], opacity: 1 },
          sphere: { scale: 0.28, color: ELEM_COLORS[el], opacity: 1 },
        }
      );
    });
  }

  function zoomToLigand() {
    if (poseModelIndex == null) {
      viewer.zoomTo();
      return;
    }
    try {
      viewer.zoomTo({ model: poseModelIndex }, 400);
    } catch (e) {
      viewer.zoomTo();
    }
  }

  function afterRender() {
    requestAnimationFrame(function () {
      clampViewport();
      if (typeof viewer.resize === "function") viewer.resize();
      viewer.render();
    });
  }

  function rebuild() {
    clampViewport();
    viewer.clear();
    poseModelIndex = null;

    if (receptorData) {
      const fmt = receptorFormat === "pdb" ? "pdb" : "pdbqt";
      viewer.addModel(receptorData, fmt);
    }
    if (posesData && document.getElementById("tog-poses").checked) {
      // addModelsAsFrames returns void; ligand is the next model index
      const before = viewer.getNumModels ? viewer.getNumModels() : (receptorData ? 1 : 0);
      viewer.addModelsAsFrames(posesData, "pdbqt");
      poseModelIndex = before; // first new model
      // If getNumModels unavailable, assume model 1 when receptor present
      if (poseModelIndex == null || isNaN(poseModelIndex)) {
        poseModelIndex = receptorData ? 1 : 0;
      }
    }

    styleReceptor();
    stylePoses();
    drawBox();
    zoomToLigand();
    viewer.render();
    afterRender();
  }

  async function init() {
    setStatus("loading…", "loading");
    try {
      let rec = await fetchStructure("receptor", "pdbqt");
      if (!rec) rec = await fetchStructure("receptor", "pdb");
      if (rec) {
        receptorData = rec.data;
        receptorFormat = rec.format === "pdb" ? "pdb" : "pdbqt";
      }
      const poses = await fetchStructure("poses");
      if (poses) posesData = poses.data;
      rebuild();
      setStatus(receptorData ? "ready" : "no receptor", receptorData ? "ok" : "err");
    } catch (err) {
      setStatus("error", "err");
      console.error(err);
    }
  }

  ["tog-cartoon", "tog-sidechains", "tog-box", "tog-poses", "pose-select"].forEach(function (id) {
    const el = document.getElementById(id);
    if (el) el.addEventListener("change", rebuild);
  });

  const search = document.getElementById("res-search");
  const list = document.getElementById("res-list");
  if (search && list) {
    search.addEventListener("input", function () {
      const q = search.value.trim().toLowerCase();
      list.querySelectorAll(".res-item").forEach(function (btn) {
        const hay = (
          btn.dataset.label +
          " " +
          btn.dataset.chain +
          " " +
          btn.dataset.resn +
          " " +
          btn.dataset.resi
        ).toLowerCase();
        btn.style.display = !q || hay.indexOf(q) !== -1 ? "" : "none";
      });
    });
    list.addEventListener("click", function (ev) {
      const btn = ev.target.closest(".res-item");
      if (!btn) return;
      list.querySelectorAll(".res-item.active").forEach(function (b) {
        b.classList.remove("active");
      });
      btn.classList.add("active");
      highlight = { chain: btn.dataset.chain, resi: btn.dataset.resi };
      styleReceptor();
      stylePoses();
      viewer.zoomTo({ chain: highlight.chain, resi: highlight.resi }, 500);
      viewer.center(
        {
          x: parseFloat(btn.dataset.x),
          y: parseFloat(btn.dataset.y),
          z: parseFloat(btn.dataset.z),
        },
        500
      );
      viewer.render();
      afterRender();
    });
  }

  init();
  window.addEventListener("resize", function () {
    clampViewport();
    if (typeof viewer.resize === "function") viewer.resize();
    viewer.render();
  });
})();
