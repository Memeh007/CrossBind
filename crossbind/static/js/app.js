/* CrossBind front-end helpers */
window.CrossBind = window.CrossBind || {};

CrossBind.pollJob = function (jobId) {
  const logEl = document.getElementById("job-log");
  const vinaEl = document.getElementById("m-vina");
  const cnnEl = document.getElementById("m-cnn");
  const rmsdEl = document.getElementById("m-rmsd");
  let timer = null;

  async function tick() {
    try {
      const r = await fetch("/api/job/" + encodeURIComponent(jobId));
      if (!r.ok) return;
      const data = await r.json();
      const statusSpan = document.querySelector("#job-status .status");
      if (statusSpan) {
        statusSpan.textContent = data.status;
        statusSpan.className = "status " + (data.status || "");
      }
      if (logEl && data.log != null) logEl.textContent = data.log;
      if (vinaEl && data.vina_affinity != null)
        vinaEl.textContent = Number(data.vina_affinity).toFixed(3) + " kcal/mol";
      if (cnnEl && data.gnina_cnn_score != null)
        cnnEl.textContent = Number(data.gnina_cnn_score).toFixed(3);
      if (rmsdEl && data.rmsd_to_reference != null)
        rmsdEl.textContent = Number(data.rmsd_to_reference).toFixed(3) + " Å";
      if (data.status === "completed" || data.status === "failed") {
        clearInterval(timer);
        if (data.poses && data.poses.length) location.reload();
      }
    } catch (e) {
      /* ignore transient */
    }
  }
  timer = setInterval(tick, 1500);
  tick();
};

document.addEventListener("DOMContentLoaded", () => {
  const btn = document.getElementById("btn-pubchem");
  if (!btn) return;
  btn.addEventListener("click", async () => {
    const name = document.querySelector('[name="pubchem_name"]').value.trim();
    const status = document.getElementById("pubchem-status");
    if (!name) {
      status.textContent = "Enter a PubChem name first.";
      return;
    }
    status.textContent = "Resolving…";
    const fd = new FormData();
    fd.append("name", name);
    try {
      const r = await fetch("/api/pubchem", { method: "POST", body: fd });
      const data = await r.json();
      if (!r.ok) throw new Error(data.detail || "lookup failed");
      document.querySelector('[name="smiles"]').value = data.smiles;
      status.textContent = "Resolved: " + data.smiles;
    } catch (err) {
      status.textContent = "Failed: " + err.message;
    }
  });
});
