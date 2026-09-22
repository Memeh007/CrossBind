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
  const statusSpan0 = document.querySelector("#job-status .status");
  const initial = ((statusSpan0 && statusSpan0.textContent) || "").trim().toLowerCase();
  /* Already terminal on first paint — do not poll (avoids reload storms). */
  if (CrossAffinity._TERMINAL[initial]) return;

  const reloadKey = "ca_job_hydrated_" + jobId;
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
        rmsdEl.textContent = Number(data.rmsd_to_reference).toFixed(3) + " A.";
      const st = (data.status || "").toLowerCase();
      if (!CrossAffinity._TERMINAL[st]) return;

      clearInterval(timer);
      timer = null;
      const btn = document.getElementById("btn-cancel-job");
      if (btn) btn.remove();

      /* One-shot reload so ADMET / IFP / evidence panels hydrate from the server.
         Never reload again for this job in this tab (was infinite GET /job + /api/job). */
      if (!sessionStorage.getItem(reloadKey)) {
        sessionStorage.setItem(reloadKey, "1");
        location.reload();
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

CrossAffinity._parseResLabel = function (label) {
  const s = String(label || "").trim();
  let m = s.match(/^([A-Za-z]{1,4})\s*(-?\d+)(?:\.([A-Za-z0-9]))?$/);
  if (m) return { resn: m[1].toUpperCase(), resi: m[2], chain: (m[3] || "").toUpperCase(), label: s };
  m = s.match(/^([A-Za-z0-9])[.:]([A-Za-z]{1,4})\s*(-?\d+)$/);
  if (m) return { chain: m[1].toUpperCase(), resn: m[2].toUpperCase(), resi: m[3], label: s };
  return { resn: s, resi: "", chain: "", label: s };
};

CrossAffinity._renderIxRows = function (rows, jobId, method) {
  const tbody = document.getElementById("ix-tbody");
  const table = document.getElementById("ix-table");
  if (!tbody) return;
  const meth = method || "geometry";
  if (!rows || !rows.length) {
    tbody.innerHTML = "";
    return;
  }
  tbody.innerHTML = rows
    .map(function (row) {
      const parsed = CrossAffinity._parseResLabel(row.residue);
      const resn = row.resn || parsed.resn || row.residue || "—";
      const chain = row.chain || parsed.chain || "";
      const resi = row.resi != null && row.resi !== "" ? String(row.resi) : parsed.resi;
      const dist =
        row.distance_A != null && row.distance_A !== ""
          ? Number(row.distance_A).toFixed(2)
          : "—";
      const link =
        chain || resi
          ? '<a href="/viewer/' +
            encodeURIComponent(jobId) +
            "?resi=" +
            encodeURIComponent(resi) +
            "&chain=" +
            encodeURIComponent(chain) +
            '&highlight=contacts">' +
            (chain || "—") +
            " / " +
            (resi || "—") +
            "</a>"
          : "<code>" + (row.residue || "") + "</code>";
      return (
        "<tr>" +
        "<td><code>" +
        resn +
        "</code></td>" +
        '<td class="num">' +
        link +
        "</td>" +
        "<td>" +
        (row.type || "") +
        "</td>" +
        '<td class="num">' +
        dist +
        "</td>" +
        '<td class="muted">' +
        (row.detail || "") +
        "</td>" +
        '<td class="muted">' +
        (row.method || meth) +
        "</td>" +
        "</tr>"
      );
    })
    .join("");
  if (table) table.style.display = "";
};

CrossAffinity.wireInteractionsPoseSelect = function () {
  const sel = document.getElementById("ix-pose-select");
  const wrap = document.getElementById("interactions-table");
  const jsonEl = document.getElementById("ix-by-pose-json");
  if (!sel || !wrap || !jsonEl) return;
  let byPose = {};
  try {
    byPose = JSON.parse(jsonEl.textContent || "{}");
  } catch (e) {
    byPose = {};
  }
  const jobId = wrap.dataset.job;
  const method = wrap.dataset.method || "geometry";
  sel.addEventListener("change", function () {
    const mode = String(sel.value || "1");
    CrossAffinity._renderIxRows(byPose[mode] || [], jobId, method);
  });
};

CrossAffinity.wireExplainPanel = function (jobId) {
  if (!jobId) return;
  const statusEl = document.getElementById("explain-status");
  const summaryEl = document.getElementById("evidence-summary");
  const llmEl = document.getElementById("llm-narration");
  const btnExplain = document.getElementById("btn-rebuild-explain");
  const btnNarrate = document.getElementById("btn-narrate-llm");

  function setStatus(msg, spinning) {
    if (!statusEl) return;
    if (spinning) {
      statusEl.innerHTML = '<span class="spinner"></span>' + (msg || "");
    } else {
      statusEl.textContent = msg || "";
    }
  }

  if (btnExplain) {
    btnExplain.addEventListener("click", async function () {
      btnExplain.disabled = true;
      setStatus("Rebuilding summary…", true);
      try {
        const r = await fetch("/api/job/" + encodeURIComponent(jobId) + "/explain", {
          method: "POST",
        });
        const data = await r.json().catch(function () {
          return {};
        });
        if (!r.ok) throw new Error(data.detail || "explain failed");
        if (summaryEl) summaryEl.value = data.explanation || "";
        setStatus("Summary rebuilt from result.json");
      } catch (err) {
        setStatus("Failed: " + (err && err.message ? err.message : err));
      } finally {
        btnExplain.disabled = false;
      }
    });
  }

  if (btnNarrate) {
    btnNarrate.addEventListener("click", async function () {
      btnNarrate.disabled = true;
      setStatus("Calling local Ollama…", true);
      try {
        const r = await fetch("/api/job/" + encodeURIComponent(jobId) + "/narrate", {
          method: "POST",
        });
        const data = await r.json().catch(function () {
          return {};
        });
        if (!r.ok) throw new Error(data.detail || "narrate failed");
        if (summaryEl && data.explanation) summaryEl.value = data.explanation;
        if (llmEl) llmEl.value = data.narration || data.message || "";
        if (data.ok) {
          setStatus("Narration from " + (data.model || "ollama") + " (evidence-bound)");
        } else {
          setStatus(data.message || "Local LLM not available — showing evidence summary only.");
        }
      } catch (err) {
        setStatus("Failed: " + (err && err.message ? err.message : err));
      } finally {
        btnNarrate.disabled = false;
      }
    });
  }
};
