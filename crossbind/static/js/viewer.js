/* CrossBind 3Dmol viewer + residue browser */
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

  let viewer = $3Dmol.createViewer(vp, { backgroundColor: "0x060b14" });
  let receptorData = null;
  let receptorFormat = "pdb";
  let posesData = null;
  let highlight = null;

  async function fetchStructure(kind) {
    const r = await fetch("/api/job/" + encodeURIComponent(jobId) + "/structure?kind=" + kind);
    if (!r.ok) return null;
    return r.json();
  }

  function drawBox() {
    if (!document.getElementById("tog-box").checked) return;
    const hx = box.sx / 2, hy = box.sy / 2, hz = box.sz / 2;
    const c = { x: box.cx, y: box.cy, z: box.cz };
    // wireframe box via corners
    const corners = [
      [-hx, -hy, -hz], [hx, -hy, -hz], [hx, hy, -hz], [-hx, hy, -hz],
      [-hx, -hy, hz], [hx, -hy, hz], [hx, hy, hz], [-hx, hy, hz],
    ].map(([x, y, z]) => ({ x: c.x + x, y: c.y + y, z: c.z + z }));
    const edges = [
      [0,1],[1,2],[2,3],[3,0],
      [4,5],[5,6],[6,7],[7,4],
      [0,4],[1,5],[2,6],[3,7],
    ];
    edges.forEach(([a, b]) => {
      viewer.addLine({
        start: corners[a],
        end: corners[b],
        color: "0x2dd4bf",
        dashed: true,
      });
    });
  }

  function styleReceptor() {
    const cartoon = document.getElementById("tog-cartoon").checked;
    const sides = document.getElementById("tog-sidechains").checked;
    viewer.setStyle({}, {}); // clear
    if (cartoon) {
      viewer.setStyle({ hetflag: false }, { cartoon: { color: "spectrum", opacity: 0.95 } });
    } else {
      viewer.setStyle({ hetflag: false }, { line: { colorscheme: "amino" } });
    }
    if (sides) {
      // all amino-acid sidechains as sticks (exclude backbone-only look by full residue sticks)
      viewer.addStyle(
        { hetflag: false, not: { atom: ["C", "N", "O", "CA"] } },
        { stick: { radius: 0.15, colorscheme: "default" } }
      );
      // also show CA-CB connection context
      viewer.addStyle({ hetflag: false }, { stick: { radius: 0.08, hidden: false, color: "white", opacity: 0.35 } });
    }
    if (highlight) {
      viewer.addStyle(
        { chain: highlight.chain, resi: highlight.resi },
        { stick: { radius: 0.25, color: "0xfbbf24" }, sphere: { scale: 0.3, color: "0xfbbf24" } }
      );
    }
  }

  function stylePoses() {
    if (!posesData || !document.getElementById("tog-poses").checked) return;
    const mode = parseInt(document.getElementById("pose-select").value || "1", 10);
    // 3Dmol models: receptor = 0, poses = 1+
    const models = viewer.getModel(1);
    if (!models) return;
    // Hide all then show selected frame if multi-model
    viewer.setStyle({ model: 1 }, { stick: { hidden: true } });
    viewer.setFrame(mode - 1);
    viewer.setStyle({ model: 1 }, { stick: { colorscheme: "greenCarbon", radius: 0.2 } });
  }

  function rebuild() {
    viewer.clear();
    if (receptorData) {
      const fmt = receptorFormat === "pdb" ? "pdb" : "pdbqt";
      viewer.addModel(receptorData, fmt);
    }
    if (posesData && document.getElementById("tog-poses").checked) {
      viewer.addModelsAsFrames(posesData, "pdbqt");
    }
    styleReceptor();
    stylePoses();
    drawBox();
    viewer.zoomTo();
    viewer.render();
  }

  async function init() {
    const rec = await fetchStructure("receptor");
    if (rec) {
      receptorData = rec.data;
      receptorFormat = rec.format === "pdb" ? "pdb" : "pdbqt";
    }
    const poses = await fetchStructure("poses");
    if (poses) posesData = poses.data;
    rebuild();
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
      styleReceptor();
      viewer.zoomTo({ chain: highlight.chain, resi: highlight.resi }, 500);
      viewer.center({ x: parseFloat(btn.dataset.x), y: parseFloat(btn.dataset.y), z: parseFloat(btn.dataset.z) }, 500);
      viewer.render();
    });
  }

  init();
  window.addEventListener("resize", () => { viewer.resize(); viewer.render(); });
})();
