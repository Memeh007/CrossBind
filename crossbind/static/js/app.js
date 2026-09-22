/* Cross Affinity front-end helpers */
window.CrossAffinity = window.CrossAffinity || {};
/* Compat alias for older markup */
window.CrossBind = window.CrossAffinity;

CrossAffinity._TERMINAL = { completed: 1, failed: 1, cancelled: 1 };

CrossAffinity.pollJob = function (jobId) {
  if (!jobId) return;
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
      const st = data.status || "";
      if (CrossAffinity._TERMINAL[st]) {
        clearInterval(timer);
        const btn = document.getElementById("btn-cancel-job");
        if (btn) btn.remove();
        if (st === "completed" && data.poses && data.poses.length) location.reload();
        if (st === "cancelled" || st === "failed") {
          /* soft refresh so error banner / badge update */
          if (!document.querySelector(".banner.bad") || st === "cancelled") {
            setTimeout(function () { location.reload(); }, 400);
          }
        }
      }
    } catch (e) {
      /* ignore transient */
    }
  }
  timer = setInterval(tick, 1500);
  tick();
};

CrossAffinity.cancelJob = async function (jobId, btn) {
  if (!jobId) return;
  if (btn) {
    btn.disabled = true;
    btn.textContent = "Cancelling…";
  }
  try {
    const r = await fetch("/api/job/" + encodeURIComponent(jobId) + "/cancel", {
      method: "POST",
    });
    const data = await r.json().catch(function () { return {}; });
    if (!r.ok) throw new Error(data.detail || "cancel failed");
    if (btn) btn.textContent = "Cancelled";
    /* Prefer navigate to job page so badge updates */
    if (location.pathname.indexOf("/job/") === 0) {
      location.reload();
    } else {
      location.href = "/job/" + encodeURIComponent(jobId);
    }
  } catch (err) {
    if (btn) {
      btn.disabled = false;
      btn.textContent = "Cancel";
    }
    alert("Cancel failed: " + (err && err.message ? err.message : err));
  }
};

CrossAffinity.wireCancelButton = function (btn) {
  if (!btn) return;
  btn.addEventListener("click", function () {
    CrossAffinity.cancelJob(btn.getAttribute("data-job"), btn);
  });
};

CrossAffinity.wireCancelButtons = function (nodes) {
  if (!nodes) return;
  nodes.forEach(function (btn) {
    CrossAffinity.wireCancelButton(btn);
  });
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
