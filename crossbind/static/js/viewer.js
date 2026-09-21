/* CrossBind 3Dmol viewer + residue browser */
(function () {
  const vp = document.getElementById("viewport");
  if (!vp) return;

  function fail(msg) {
    vp.innerHTML = "<p class='viewer-fail' style='padding:1.25rem;color:#d9776c;font-family:ui-monospace,monospace'>" + msg + "</p>";
  }

  if (typeof $3Dmol === "undefined") {
    fail("3Dmol.js failed to load (CDN blocked?). Check network or open DevTools console.");
    return;
  }

  const jobId = vp.dataset.job;
  const box = {
    cx: parseFloat(vp.dataset.cx) || 0,
    cy: parseFloat(vp.dataset.cy) || 0,
    cz: parseFloat(vp.dataset.cz) || 0,
    sx: parseFloat(vp.dataset.sx) || 20,
    sy: parseFloat(vp.dataset.sy) || 20,
    sz: parseFloat(vp.dataset.sz) || 20,
  };

  // Ensure the container has size before WebGL init
  if (vp.clientHeight < 40) vp.style.minHeight = "560px";

  let viewer;
  try {
    viewer = $3Dmol.createViewer(vp, { backgroundColor: "#080706" });
  } catch (e) {
    fail("Could not create WebGL viewer: " + e.message);
    return;
  }

  let receptorData = null;
  let receptorFormat = "pdb";
  let posesData = null;
  let highlight = null;

  async function fetchStructure(kind) {
    const r = await fetch(
      "/api/job/" + encodeURIComponent(jobId) + "/structure?kind=" + kind + "&_=" + Date.now(),
      { cache: "no-store" }
    );
    if (!r.ok) return null;
    return r.json();
  }

  function drawBox() {
    const tog = document.getElementById("tog-box");
    if (!tog || !tog.checked) return;
    const hx = box.sx / 2, hy = box.sy / 2, hz = box.sz / 2;
    const c = { x: box.cx, y: box.cy, z: box.cz };
    const corners = [
      [-hx, -hy, -hz], [hx, -hy, -hz], [hx, hy, -hz], [-hx, hy, -hz],
      [-hx, -hy, hz], [hx, -hy, hz], [hx, hy, hz], [-hx, hy, hz],
    ].map(([x, y, z]) => ({ x: c.x + x, y: c.y + y, z: c.z + z }));
    const edges = [
      [0, 1], [1, 2], [2, 3], [3, 0],
      [4, 5], [5, 6], [6, 7], [7, 4],
      [0, 4], [1, 5], [2, 6], [3, 7],
    ];
    edges.forEach(([a, b]) => {
      viewer.addLine({
        start: corners[a],
        end: corners[b],
        color: "0xe6a23c",
        dashed: true,
      });
    });
  }

  function styleReceptor() {
    const cartoon = document.getElementById("tog-cartoon");
    const sides = document.getElementById("tog-sidechains");
    const wantCartoon = !cartoon || cartoon.checked;
    const wantSides = sides && sides.checked;

    if (wantCartoon) {
      viewer.setStyle({ hetflag: false }, { cartoon: { color: "spectrum", opacity: 0.95 } });
    } else {
      viewer.setStyle({ hetflag: false }, { line: { colorscheme: "amino" } });
    }
    if (wantSides) {
      // Side chains as sticks (full residue sticks are readable and robust)
      viewer.addStyle({ hetflag: false }, { stick: { radius: 0.12, colorscheme: "default" } });
    }
    if (highlight) {
      viewer.addStyle(
        { chain: highlight.chain, resi: parseInt(highlight.resi, 10) },
        { stick: { radius: 0.28, color: "0xe6a23c" }, sphere: { scale: 0.35, color: "0xe6a23c" } }
      );
    }
  }

  function stylePoses() {
    const tog = document.getElementById("tog-poses");
    if (!posesData || !tog || !tog.checked) return;
    const mode = parseInt((document.getElementById("pose-select") || {}).value || "1", 10);
    try {
      if (viewer.getModel(1)) {
        viewer.setFrame(Math.max(0, mode - 1));
        viewer.setStyle({ model: 1 }, { stick: { colorscheme: "greenCarbon", radius: 0.2 } });
      }
    } catch (e) {
      /* ignore pose frame issues */
    }
  }

  function rebuild() {
    viewer.clear();
    if (!receptorData) {
      fail("No receptor structure for this job yet (dock may have failed before receptor prep). Re-run after the ligand fix, or check that a .pdb/.pdbqt was uploaded.");
      return;
    }
    try {
      const fmt = receptorFormat === "pdb" ? "pdb" : "pdbqt";
      viewer.addModel(receptorData, fmt);
      if (posesData && document.getElementById("tog-poses") && document.getElementById("tog-poses").checked) {
        viewer.addModelsAsFrames(posesData, "pdbqt");
      }
      styleReceptor();
      stylePoses();
      drawBox();
      viewer.zoomTo();
      viewer.resize();
      viewer.render();
    } catch (e) {
      fail("Viewer render error: " + e.message);
    }
  }

  async function init() {
    try {
      const rec = await fetchStructure("receptor");
      if (rec && rec.data) {
        receptorData = rec.data;
        receptorFormat = rec.format === "pdb" ? "pdb" : "pdbqt";
      } else {
        fail("Receptor fetch failed (404). Job may not have saved receptor.pdb / receptor.pdbqt.");
        return;
      }
      const poses = await fetchStructure("poses");
      if (poses && poses.data) posesData = poses.data;
      rebuild();
    } catch (e) {
      fail("Init failed: " + e.message);
    }
  }

  ["tog-cartoon", "tog-sidechains", "tog-box", "tog-poses", "pose-select"].forEach((id) => {
    const el = document.getElementById(id);
    if (el) el.addEventListener("change", rebuild);
  });

  const search = document.getElementById("res-search");
  const list = document.getElementById("res-list");
  if (search && list) {
    search.addEventListener("input", () => {
      const q = search.value.trim().toLowerCase();
      list.querySelectorAll(".res-item").forEach((btn) => {
        const hay = (btn.dataset.label + " " + btn.dataset.chain + " " + btn.dataset.resn + " " + btn.dataset.resi).toLowerCase();
        btn.style.display = !q || hay.includes(q) ? "" : "none";
      });
    });
    list.addEventListener("click", (ev) => {
      const btn = ev.target.closest(".res-item");
      if (!btn) return;
      list.querySelectorAll(".res-item.active").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      highlight = { chain: btn.dataset.chain, resi: btn.dataset.resi };
      rebuild();
      try {
        viewer.zoomTo({ chain: highlight.chain, resi: parseInt(highlight.resi, 10) }, 400);
        viewer.render();
      } catch (e) { /* ignore */ }
    });
  }

  init();
  window.addEventListener("resize", () => {
    try { viewer.resize(); viewer.render(); } catch (e) {}
  });
})();
