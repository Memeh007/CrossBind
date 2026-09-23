# DESIGN.md — ddOS visual & interaction contract

**Product:** ddOS (Drug Discovery Operating System)  
**Status:** Locked taste direction from [UIRoot](https://uiroot.com/) research (Taste Skill, Originkit, UI Component + DESIGN.md catalogs).  
**Authority:** Follow with `AGENTS.md` §7. **Do not implement a UI redesign until Alexander explicitly authorizes UI work.**

This file exists so agents do not invent generic “AI SaaS” chrome. When UI is authorized, implement **this** contract.

---

## 1. Product feel

ddOS should feel like a **scientific instrument / operating system for discovery**, not a marketing site and not a purple-gradient AI demo.

- Dense where data is dense (jobs, contacts, pocket tables)
- Calm where attention should rest (3D stage, evidence proof)
- Every motion and highlight should make a **biological or physical process legible**

North-star interaction: *structure → pocket hypotheses → ligand-aware rank → pose → residue contacts you can see and verify.*

---

## 2. Anti-slop (from UIRoot Taste Skill)

**Forbidden defaults**
- Generic Inter + purple/violet glow + blurry glass cards
- Decorative particles / falling molecules / sparkle loops with no meaning
- Placeholder copy, empty “coming soon” panels left in production paths
- Fake MD / fake physics presented as simulation truth
- Stock shadcn demos left visually unmodified and called “the OS”

**Required discipline**
- Finished outputs (Taste “Output Skill” spirit)
- Restrained palette, strong hierarchy (Soft + Minimalist bias)
- Motion with semantic purpose only
- Typography and spacing that survive long docking sessions

---

## 3. Layout & density

| Surface | Density | Notes |
|---------|---------|-------|
| Discover | Medium | Staged process; one primary CTA per step |
| Dock | Medium-high | Forms as instrument controls |
| Jobs | High | Scannable table; status chips |
| Job / proof | High + calm stage | Table + evidence beside or below 3D |
| Viewer | Stage-first | 3D is the hero; chrome is secondary |

Use consistent panel radii, quiet borders, and monospace for IDs/scores/PDB codes.

---

## 4. Color (direction — refine when UI starts)

- Base: near-black / ink surfaces (already in product)
- Accent: one scientific accent (teal/cyan family OK; avoid purple-AI cliché as primary)
- Provenance: distinct chips for **crystal PDB** vs **AlphaFold** vs **upload**
- Contacts: typed colors (H-bond / hydrophobic / π-stack / clash) — legend required
- Danger: cancel / destructive only

No rainbow decoration. Accessibility: do not encode meaning by color alone.

---

## 5. Motion (Originkit-class patterns, ddOS semantics)

Allowed when UI is authorized:
- Staged reveals for Discover steps
- Pocket proposal emphasis (gentle)
- Pose appear / morph between ranked poses
- Contact pulse on residue select (synced to proof table)
- Progress for long jobs (honest, cancellable)

Disallowed:
- Endless ambient particle fields
- Motion that blocks reading tables
- Animating scores as if they were live experimental Kd

Prefer CSS / small JS / optional Framer-like primitives; keep FastAPI+Jinja stack unless a deliberate front-end migration is approved.

---

## 6. Component sourcing policy (UIRoot UI Component catalog)

Treat catalog entries (Originkit, Magic UI, Aceternity, SmoothUI, Base UI, Radix-inspired kits, ThreeUI, BoardUI, …) as:

1. **Pattern references** — interaction & motion ideas  
2. **Optional dependencies** — only if license-fit and bundle-cost OK  
3. **Never** — scraped assets, copied proprietary demos, or drive-by dependency sprawl  

Molecular viz stays on **3Dmol.js** (or an explicit NGL migration later), not a random Three.js marketing component.

---

## 7. DESIGN.md agent workflow (UIRoot DESIGN.md category)

When Alexander provides screenshots or says “match this feel”:
1. Analyze with a DESIGN.md-style pass (structure, type, spacing, motion, anti-patterns)
2. Write findings into **this file** (tokens + do/don’t)
3. Implement from the updated contract
4. Visual QA against anti-slop list in §2

Related ecosystem to know (do not vendor blindly): Taste Skill, getdesign.md, DesignMD, Open Design, TypeUI, Impeccable, Motionsites-class generators — use as **taste injectors**, not product identity.

---

## 8. ddOS-specific UI objects (must exist in any redesign)

1. **Provenance chip** — PDB / AF / upload  
2. **Pocket strip** — method, score, ligand-aware rank, select  
3. **Docking stage** — protein + ligand + box + contact highlights  
4. **Proof table** — residue, type, distance, atoms, method — click syncs to 3D  
5. **Honesty banners** — scores ≠ Kd; AF pose caution  
6. **Engine badge** — Vina / GNINA / DiffDock-L confidence (labeled correctly)  
7. **Job process timeline** — queued → preparing → docking → scoring → done/failed/cancelled  

If a redesign omits these, it is incomplete.

---

## 9. Gate

Updating this file is allowed anytime.  
**Implementing it in CSS/templates/JS requires Alexander’s explicit UI go-ahead** (`AGENTS.md` §3 / §7.5).

---

*Seeded 2026-09-22 from UIRoot.com (Taste Skill, Originkit, UI Component + DESIGN.md categories) for ddOS.*
