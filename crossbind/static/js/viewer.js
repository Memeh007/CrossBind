/* Cross Affinity 3Dmol viewer — file fetch (not JSON), cartoon-first for large PDBs */
(function () {
  const vp = document.getElementById("viewport");
  if (!vp) return;

  function fail(msg) {
    vp.innerHTML =
      "<p class='viewer-fail' style='padding:1.25rem;color:#d9776c;font-family:ui-monospace,monospace;line-height:1.5'>" +
      msg +
      "</p>";
  }
  function status(msg) {
    let el = document.getElementById("viewer-status");
    if (!el) {
      el = document.createElement("div");
      el.id = "viewer-status";
      el.style.cssText =
        "position:absolute;left:12px;top:12px;z-index:5;background:rgba(14,12,10,0.85);border:1px solid #3a3228;padding:6px 10px;font:12px ui-monospace,monospace;color:#e6a23c";
      vp.style.position = "relative";
      vp.appendChild(el);
    }
    el.textContent = msg;
    el.style.display = msg ? "block" : "none";
  }

  if (typeof $3Dmol === "undefined") {
    fail("3Dmol.js failed to load. Expected /static/vendor/3Dmol-min.js — restart Cross Affinity after update.");
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

  if (vp.clientHeight < 40) vp.style.minHeight = "560px";

  let viewer;
  try {
    viewer = $3Dmol.createViewer(vp, { backgroundColor: "#080706" });
  } catch (e) {
    fail("WebGL viewer failed: " + e.message + ". Try Chrome/Edge with hardware acceleration on.");
    return;
  }

  let receptorData = null;
  let receptorFormat = "pdb";
  let posesData = null;
  let highlight = null;
  let largeStructure = false;

  async function fetchText(url) {
    const r = await fetch(url + (url.includes("?") ? "&" : "?") + "_=" + Date.now(), {
      cache: "no-store",
    });
    if (!r.ok) return null;
    return r.text();
  }

  async function loadReceptor() {
    // Prefer raw file endpoints (streaming text) over JSON-wrapped 2MB+ payloads
    const candidates = [
      { url: "/api/job/" + encodeURIComponent(jobId) + "/file/receptor.pdb", fmt: "pdb" },
      { url: "/api/job/" + encodeURIComponent(jobId) + "/file/upload_receptor.pdb", fmt: "pdb" },
      { url: "/api/job/" + encodeURIComponent(jobId) + "/file/receptor.pdbqt", fmt: "pdbqt" },
      { url: "/api/job/" + encodeURIComponent(jobId) + "/file/upload_receptor.pdbqt", fmt: "pdbqt" },
    ];
    for (const c of candidates) {
      status("Loading " + c.fmt.toUpperCase() + "…");
      const text = await fetchText(c.url);
      if (text && text.length > 80) {
        receptorData = text;
        receptorFormat = c.fmt;
        return true;
      }
    }
    return false;
  }

  async function loadPoses() {
    const text = await fetchText(
      "/api/job/" + encodeURIComponent(jobId) + "/file/poses.pdbqt"
    );
    if (text && text.length > 40) posesData = text;
  }

  function drawBox() {
    const tog = document.getElementById("tog-box");
    if (!tog || !tog.checked) return;
    const hx = box.sx / 2,
      hy = box.sy / 2,
      hz = box.sz / 2;
    const c = { x: box.cx, y: box.cy, z: box.cz };
    const corners = [
      [-hx, -hy, -hz],
      [hx, -hy, -hz],
      [hx, hy, -hz],
      [-hx, hy, -hz],
      [-hx, -hy, hz],
      [hx, -hy, hz],
      [hx, hy, hz],
      [-hx, hy, hz],
    ].map(([x, y, z]) => ({ x: c.x + x, y: c.y + y, z: c.z + z }));
    [
      [0, 1],
      [1, 2],
      [2, 3],
      [3, 0],
      [4, 5],
      [5, 6],
      [6, 7],
      [7, 4],
      [0, 4],
      [1, 5],
      [2, 6],
      [3, 7],
    ].forEach(([a, b]) => {
      viewer.addLine({
        start: corners[a],
        end: corners[b],
        color: "0xe6a23c",
        dashed: true,
      });
    });
  }

  function styleReceptor() {
    const cartoonEl = document.getElementById("tog-cartoon");
    const sidesEl = document.getElementById("tog-sidechains");
    const wantCartoon = !cartoonEl || cartoonEl.checked;
    const wantSides = sidesEl && sidesEl.checked && !largeStructure;

    if (wantCartoon) {
      viewer.setStyle({ hetflag: false }, { cartoon: { color: "spectrum", opacity: 0.95 } });
    } else {
      viewer.setStyle({ hetflag: false }, { line: { colorscheme: "amino" } });
    }
    // Ligands / hetero already in receptor
    viewer.addStyle({ hetflag: true }, { stick: { colorscheme: "magentaCarbon", radius: 0.15 } });

    if (wantSides) {
      viewer.addStyle({ hetflag: false }, { stick: { radius: 0.1, colorscheme: "default" } });
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
        viewer.setStyle({ model: 1 }, { stick: { colorscheme: "greenCarbon", radius: 0.22 } });
      }
    } catch (e) {}
  }

  function rebuild() {
    viewer.clear();
    if (!receptorData) {
      fail("No receptor file found for this job.");
      return;
    }
    try {
      status("Rendering…");
      viewer.addModel(receptorData, receptorFormat, { keepH: false });

      // Heuristic: huge structures (full AMPK etc.) — skip all-sidechain draw
      let natoms = 0;
      try {
        natoms = viewer.getModel(0).selectedAtoms({}).length;
      } catch (e) {
        natoms = (receptorData.match(/\nATOM /g) || []).length;
      }
      largeStructure = natoms > 12000;
      const sidesEl = document.getElementById("tog-sidechains");
      const hint = document.getElementById("viewer-large-hint");
      if (largeStructure && sidesEl) {
        sidesEl.checked = false;
        sidesEl.disabled = true;
        if (hint) hint.style.display = "block";
      } else if (sidesEl) {
        sidesEl.disabled = false;
        if (hint) hint.style.display = "none";
      }

      if (posesData && document.getElementById("tog-poses") && document.getElementById("tog-poses").checked) {
        viewer.addModelsAsFrames(posesData, "pdbqt");
      }
      styleReceptor();
      stylePoses();
      drawBox();
      // Prefer zoom to docking box center if not 0,0,0 — else whole protein
      const boxOrigin = Math.abs(box.cx) + Math.abs(box.cy) + Math.abs(box.cz) > 0.01;
      if (boxOrigin) {
        viewer.center({ x: box.cx, y: box.cy, z: box.cz });
        viewer.zoom(0.8);
      } else {
        viewer.zoomTo();
      }
      viewer.resize();
      viewer.render();
      status("");
    } catch (e) {
      fail("Render error: " + e.message);
    }
  }

  async function init() {
    try {
      status("Fetching receptor…");
      const ok = await loadReceptor();
      if (!ok) {
        fail(
          "Could not load receptor.pdb / receptor.pdbqt for this job. Open Job details → confirm downloads work, then retry."
        );
        return;
      }
      status("Fetching poses…");
      await loadPoses();
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
        const hay = (
          btn.dataset.label +
          " " +
          btn.dataset.chain +
          " " +
          btn.dataset.resn +
          " " +
          btn.dataset.resi
        ).toLowerCase();
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
      } catch (e) {}
    });
  }

  init();
  window.addEventListener("resize", () => {
    try {
      viewer.resize();
      viewer.render();
    } catch (e) {}
  });
})();
