/* Cross Affinity Discover UI */
(function () {
  let lastPayload = null;

  function show(id) {
    const el = document.getElementById(id);
    if (el) el.hidden = false;
  }

  function setKV(id, pairs) {
    const el = document.getElementById(id);
    if (!el) return;
    el.innerHTML = pairs
      .map(([k, v]) => `<dt>${k}</dt><dd><code>${v == null || v === "" ? "—" : v}</code></dd>`)
      .join("");
  }

  document.getElementById("discover-form").addEventListener("submit", async (ev) => {
    ev.preventDefault();
    const status = document.getElementById("discover-status");
    status.textContent = "Resolving (PubChem / ChEMBL / structures)…";
    const name = document.getElementById("drug-name").value.trim();
    const uniprot = document.getElementById("uniprot-override").value.trim();
    const body = new URLSearchParams();
    body.set("name", name);
    if (uniprot) body.set("uniprot", uniprot);
    try {
      const r = await fetch("/api/discover", {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body,
      });
      const data = await r.json();
      if (!r.ok) throw new Error(data.detail || JSON.stringify(data));
      lastPayload = data;
      render(data);
      status.textContent = "Done.";
    } catch (err) {
      status.textContent = "Failed: " + err.message;
    }
  });

  function render(data) {
    const drug = data.drug || {};
    show("panel-drug");
    setKV("drug-kv", [
      ["Input", drug.input],
      ["CID", drug.cid],
      ["SMILES", drug.smiles],
      ["InChIKey", drug.inchikey],
      ["ChEMBL", drug.chembl_id],
      ["Formula", drug.molecular_formula],
      ["Ambiguous name?", drug.ambiguous ? "yes — check candidates" : "no"],
    ]);

    show("panel-mech");
    document.getElementById("mech-disclaimer").textContent =
      (data.pharmacology && data.pharmacology.disclaimer) || "";
    const mechList = document.getElementById("mech-list");
    mechList.innerHTML = ((data.pharmacology && data.pharmacology.mechanisms) || [])
      .map((m) => `<li><strong>${m.text}</strong> <span class="muted">(${m.source || ""})</span></li>`)
      .join("") || "<li class='muted'>No mechanisms returned (ChEMBL may be down; try again).</li>";
    const tb = document.querySelector("#targets-table tbody");
    tb.innerHTML = (data.targets || [])
      .slice(0, 40)
      .map(
        (t) =>
          `<tr><td>${t.gene || "—"}</td><td>${t.uniprot || "—"}</td><td>${t.mechanism || "—"}</td><td>${t.source || ""}</td></tr>`
      )
      .join("");

    const st = data.structure || {};
    show("panel-structure");
    setKV("structure-kv", [
      ["Provenance", st.label || st.provenance],
      ["PDB / AF id", st.pdb_id],
      ["UniProt", st.uniprot],
      ["Path", st.path],
      ["pLDDT mean", st.plddt_mean],
      ["OK", st.ok],
    ]);
    document.getElementById("structure-warn").textContent = st.warning || st.error || "";

    const pk = data.pocket || {};
    show("panel-pocket");
    setKV("pocket-kv", [
      ["Method", pk.method],
      ["Center", pk.center ? pk.center.join(", ") : "—"],
      ["Size", pk.size ? pk.size.join(", ") : "—"],
      ["Ligand", pk.ligand_resn || "—"],
      ["Non-zero", pk.nonzero],
    ]);
    document.getElementById("pocket-warn").textContent = pk.warning || "";

    const ortho = data.orthologs || {};
    show("panel-ortho");
    document.getElementById("ortho-disclaimer").textContent = ortho.disclaimer || "";
    const otb = document.querySelector("#ortho-table tbody");
    otb.innerHTML = (ortho.species || [])
      .map(
        (s) =>
          `<tr><td>${s.label}</td><td><span class="status ${s.status}">${s.status}</span></td><td>${s.id || s.symbol || "—"}</td><td>${s.identity != null ? Number(s.identity).toFixed(1) : "—"}</td><td class="muted">${s.note || ""}</td></tr>`
      )
      .join("");

    if (st.ok && drug.smiles && pk.center) show("panel-dock");
  }

  document.getElementById("prepare-dock-form").addEventListener("submit", async (ev) => {
    ev.preventDefault();
    if (!lastPayload) return;
    const status = document.getElementById("dock-status");
    status.textContent = "Queuing docking job…";
    const fd = new FormData(ev.target);
    fd.set("discovery_json", JSON.stringify(lastPayload));
    try {
      const r = await fetch("/api/discover/dock", { method: "POST", body: fd });
      const data = await r.json();
      if (!r.ok) throw new Error(data.detail || "dock failed");
      if (data.job_id) location.href = "/job/" + encodeURIComponent(data.job_id);
      else status.textContent = JSON.stringify(data);
    } catch (err) {
      status.textContent = "Failed: " + err.message;
    }
  });
})();
