/* CrossBind front-end helpers */
window.CrossBind = window.CrossBind || {};

CrossBind.pollJob = function (jobId) {
  const logEl = document.getElementById("job-log");
  const vinaEl = document.getElementById("m-vina");
  const cnnEl = document.getElementById("m-cnn");
  const rmsdEl = document.getElementById("m-rmsd");
  const statusRoot = document.getElementById("job-status");
  let timer = null;
  let terminalReloaded = false;

  function ensureErrorBanner(msg) {
    let banner = document.getElementById("job-error");
    if (!msg) {
      if (banner) banner.remove();
      return;
    }
    if (!banner) {
      banner = document.createElement("div");
      banner.id = "job-error";
      banner.className = "banner bad";
      const metrics = statusRoot && statusRoot.querySelector(".metrics");
      if (metrics && metrics.parentNode) {
        metrics.insertAdjacentElement("afterend", banner);
      } else if (statusRoot) {
        statusRoot.prepend(banner);
      }
    }
    banner.innerHTML = "<strong>Error:</strong> " + String(msg);
  }

  function refreshPoses(poses) {
    const box = document.getElementById("poses-table");
    if (!box || !poses || !poses.length) return;
    let html = '<table class="jobs"><thead><tr><th>Mode</th><th>Affinity / scores</th></tr></thead><tbody>';
    poses.forEach((p) => {
      let score = "";
      if (p.affinity != null) score = Number(p.affinity).toFixed(3) + " kcal/mol";
      else if (p.vina_affinity != null)
        score = "vina " + Number(p.vina_affinity).toFixed(3) + " · CNN " + Number(p.cnn_score || 0).toFixed(3);
      else score = JSON.stringify(p);
      html += "<tr><td>" + (p.mode != null ? p.mode : "?") + "</td><td>" + score + "</td></tr>";
    });
    html += "</tbody></table>";
    box.innerHTML = html;
  }

  async function tick() {
    try {
      const r = await fetch("/api/job/" + encodeURIComponent(jobId) + "?_=" + Date.now(), {
        cache: "no-store",
      });
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
      if (data.error) ensureErrorBanner(data.error);
      if (data.poses && data.poses.length) refreshPoses(data.poses);

      if (data.status === "completed" || data.status === "failed") {
        clearInterval(timer);
        // One reload so server-rendered banners/downloads match — but only once
        if (!terminalReloaded) {
          terminalReloaded = true;
          const key = "cb_reloaded_" + jobId + "_" + data.status;
          if (!sessionStorage.getItem(key)) {
            sessionStorage.setItem(key, "1");
            location.reload();
          }
        }
      }
    } catch (e) {
      /* ignore transient */
    }
  }
  timer = setInterval(tick, 1200);
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
      status.textContent = "Resolved: " + data.smiles + " (salts stripped at dock time if needed)";
    } catch (err) {
      status.textContent = "Failed: " + err.message;
    }
  });
});
