/* Cross Affinity Discover UI — drug + selectable protein */
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
      .map(([k, v]) => `<dt>${k}</dt><dd><code>${v == null || v === "" ? "—" : escapeHtml(String(v))}</code></dd>`)
      .join("");
  }

  function escapeHtml(s) {
    return s
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function provenanceLabel(st) {
    const lab = (st.label || st.provenance || "").toString();
    if (lab === "experimental" || lab === "experimental_pdb") return "experimental (PDB)";
    if (lab === "predicted" || lab === "alphafold_db") return "predicted (AlphaFold)";
    return lab || "—";
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

  document.getElementById("protein-search-form").addEventListener("submit", async (ev) => {
    ev.preventDefault();
    const status = document.getElementById("protein-search-status");
    const q = document.getElementById("protein-query").value.trim();
    const species = document.getElementById("protein-species").value.trim() || "human";
    if (!q) return;
    status.textContent = "Resolving protein…";
    const body = new URLSearchParams();
    body.set("query", q);
    body.set("species", species);
    try {
      const r = await fetch("/api/discover/protein", {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body,
      });
      const data = await r.json();
      if (!r.ok) throw new Error(data.detail || JSON.stringify(data));
      renderProteinSearch(data);
      status.textContent = "Resolved.";
    } catch (err) {
      status.textContent = "Failed: " + err.message;
      document.getElementById("protein-result").hidden = true;
    }
  });

  let lastProteinHit = null;

  function renderProteinSearch(data) {
    lastProteinHit = data;
    const box = document.getElementById("protein-result");
    box.hidden = false;
    setKV("protein-kv", [
      ["Gene", data.gene],
      ["UniProt", data.uniprot],
      ["Organism", data.organism],
      ["Protein", data.protein_name],
      ["Query kind", data.kind],
    ]);
    document.getElementById("protein-function").textContent = data.function
      ? "Function: " + data.function
      : "";
    const sel = document.getElementById("protein-pdb-select");
    const cands = data.candidates || [];
    sel.innerHTML = cands
      .map((c) => {
        const id = c.pdb_id || "";
        const lab = c.label || c.provenance || "";
        const note = c.note ? ` — ${c.note}` : "";
        const text = id
          ? `${id} (${lab})${note}`
          : `AlphaFold fallback (${lab})${note}`;
        return `<option value="${escapeHtml(id)}" ${id === data.selected_pdb ? "selected" : ""}>${escapeHtml(text)}</option>`;
      })
      .join("");
    if (!cands.length) {
      sel.innerHTML = `<option value="">(no candidates)</option>`;
    }
  }

  document.getElementById("btn-select-protein").addEventListener("click", async () => {
    if (!lastProteinHit) return;
    const status = document.getElementById("protein-select-status");
    const pdbSel = document.getElementById("protein-pdb-select").value.trim();
    const uniprot = lastProteinHit.uniprot || "";
    status.textContent = "Fetching structure / pocket / orthologs…";
    try {
      // Ensure we have a discovery payload shell (drug optional — protein-only study)
      if (!lastPayload) {
        lastPayload = {
          drug: { input: document.getElementById("drug-name").value.trim() || "ligand", smiles: null },
          targets: [],
        };
      }
      const updated = await selectTarget({ uniprot, pdb_id: pdbSel || undefined });
      // Merge protein card fields from search hit
      if (updated.selected_protein && lastProteinHit) {
        updated.selected_protein.protein_name =
          updated.selected_protein.protein_name || lastProteinHit.protein_name;
        updated.selected_protein.organism =
          updated.selected_protein.organism || lastProteinHit.organism;
        updated.selected_protein.function =
          updated.selected_protein.function || lastProteinHit.function;
        updated.selected_protein.gene =
          updated.selected_protein.gene || lastProteinHit.gene;
      }
      lastPayload = updated;
      render(updated);
      status.textContent = "Selected for docking.";
    } catch (err) {
      status.textContent = "Failed: " + err.message;
    }
  });

  async function selectTarget({ uniprot, pdb_id }) {
    if (!lastPayload) throw new Error("Run discovery first (or search a protein)");
    const body = new URLSearchParams();
    body.set("discovery_json", JSON.stringify(lastPayload));
    if (uniprot) body.set("uniprot", uniprot);
    if (pdb_id) body.set("pdb_id", pdb_id);
    const r = await fetch("/api/discover/select-target", {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body,
    });
    const data = await r.json();
    if (!r.ok) throw new Error(data.detail || JSON.stringify(data));
    return data;
  }

  function renderSelected(data) {
    const sp = data.selected_protein || {};
    const st = data.structure || {};
    show("panel-selected");
    document.getElementById("job-title-preview").textContent =
      data.job_title_preview || "";
    setKV("selected-kv", [
      ["Gene", sp.gene],
      ["UniProt", sp.uniprot || data.selected_uniprot],
      ["Protein name", sp.protein_name],
      ["Organism", sp.organism],
      ["Mechanism", sp.mechanism],
      ["Structure", provenanceLabel(st)],
      ["PDB / AF", st.pdb_id],
      ["Method", st.method || sp.method],
      ["Resolution (Å)", st.resolution_A != null ? st.resolution_A : "—"],
      ["pLDDT mean", st.plddt_mean],
    ]);
    document.getElementById("selected-function").textContent = sp.function
      ? "Function: " + sp.function
      : "";
  }

  function renderTargets(data) {
    const selected = (data.selected_uniprot || "").toUpperCase();
    const tb = document.querySelector("#targets-table tbody");
    tb.innerHTML = (data.targets || [])
      .slice(0, 40)
      .map((t) => {
        const up = (t.uniprot || "").toUpperCase();
        const checked = up && up === selected ? "checked" : "";
        const disabled = up ? "" : "disabled";
        return `<tr class="${up && up === selected ? "row-selected" : ""}">
          <td><input type="radio" name="dock-target" value="${escapeHtml(up)}" ${checked} ${disabled} data-uniprot="${escapeHtml(up)}" /></td>
          <td>${escapeHtml(t.gene || "—")}</td>
          <td>${escapeHtml(t.uniprot || "—")}</td>
          <td>${escapeHtml(t.mechanism || "—")}</td>
          <td>${escapeHtml(t.source || "")}</td>
        </tr>`;
      })
      .join("");

    tb.querySelectorAll('input[name="dock-target"]').forEach((radio) => {
      radio.addEventListener("change", async () => {
        const up = radio.value;
        if (!up) return;
        const status = document.getElementById("discover-status");
        status.textContent = "Switching target " + up + "…";
        try {
          const updated = await selectTarget({ uniprot: up });
          lastPayload = updated;
          render(updated);
          status.textContent = "Target updated.";
        } catch (err) {
          status.textContent = "Failed: " + err.message;
        }
      });
    });
  }

  function render(data) {
    const drug = data.drug || {};
    if (drug.smiles || drug.cid) {
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
    }

    if (data.targets && data.targets.length) {
      show("panel-mech");
      document.getElementById("mech-disclaimer").textContent =
        (data.pharmacology && data.pharmacology.disclaimer) || "";
      const mechList = document.getElementById("mech-list");
      mechList.innerHTML = ((data.pharmacology && data.pharmacology.mechanisms) || [])
        .map((m) => `<li><strong>${escapeHtml(m.text)}</strong> <span class="muted">(${escapeHtml(m.source || "")})</span></li>`)
        .join("") || "<li class='muted'>No mechanisms returned (ChEMBL may be down; try again).</li>";
      renderTargets(data);
    }

    renderSelected(data);

    const st = data.structure || {};
    show("panel-structure");
    setKV("structure-kv", [
      ["Provenance", provenanceLabel(st)],
      ["PDB / AF id", st.pdb_id],
      ["UniProt", st.uniprot],
      ["Method", st.method],
      ["Resolution (Å)", st.resolution_A],
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
          `<tr><td>${escapeHtml(s.label)}</td><td><span class="status ${escapeHtml(s.status)}">${escapeHtml(s.status)}</span></td><td>${escapeHtml(s.id || s.symbol || "—")}</td><td>${s.identity != null ? Number(s.identity).toFixed(1) : "—"}</td><td class="muted">${escapeHtml(s.note || "")}</td></tr>`
      )
      .join("");

    if (st.ok && drug.smiles && pk.center) show("panel-dock");
    else if (st.ok && pk.center && !drug.smiles) {
      // protein-only: hide dock until drug resolved
      const dock = document.getElementById("panel-dock");
      if (dock) dock.hidden = true;
    }
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
