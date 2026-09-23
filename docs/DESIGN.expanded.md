# DESIGN.md — ddOS visual system (agent-readable)

**Product:** ddOS (Drug Discovery Operating System)  
**Authority:** Read with root `AGENTS.md`. **Do not implement a UI redesign until Alexander says go.**  
**Stack today:** FastAPI + Jinja2 + `crossbind/static/css/crossbind.css` + 3Dmol.js (not Next/React by default).  
**Sources absorbed (patterns + rules, not scraped assets):**

| Source | URL / repo | What we took |
|--------|------------|--------------|
| Taste Skill v2 | https://github.com/Leonxlnx/taste-skill · https://www.tasteskill.dev/docs | Brief inference, three dials, anti-slop bans, locks, pre-flight discipline |
| Soft / Minimalist / Output skills | Taste Skill skill pack | Calm density, finished outputs |
| Originkit | https://uiroot.com/tools/203 | Animated component *patterns*; MCP/Framer/React inspiration only |
| getdesign.md / awesome-design-md | https://getdesign.md/ · VoltAgent/awesome-design-md | Stitch-style DESIGN.md sections; closest cousins: VoltAgent (void+emerald), Cursor dark, Linear minimal |
| Open Design | https://opendesigner.io/ | 9-section DESIGN.md schema (color, type, spacing, layout, components, motion, voice, brand, anti-patterns) |
| TypeUI DESIGN.md anatomy | https://www.typeui.sh/design-md | DESIGN.md as agent constraint set |
| UIRoot catalogs | https://uiroot.com/category/design-md · ui-component · animation-tools | Landscape awareness |

**Honest adaptation note (Taste Skill §13):** Taste Skill’s core skill is written for **landing pages / portfolios**, and explicitly says it is **not** for dashboards, data tables, or multi-step product UI. ddOS **is** a dense scientific instrument. We keep Taste’s **anti-slop bans, locks, and dials**, but set dials for **cockpit density** and borrow **Carbon / Primer / Fluent-style** density thinking for tables and forms—not marketing hero rules.

---

## Design Read (always declare before UI work)

**Reading this as:** local scientific instrument OS for computational chemists and translational biologists, with Soft+Minimalist + high-density cockpit language, leaning toward native CSS tokens already in `crossbind.css` (void ink + bio-luminescent teal), semantic motion only, Carbon/Primer-like data density—not a SaaS marketing site.

**Three dials (locked for ddOS product chrome):**

| Dial | Value | Meaning for ddOS |
|------|-------|------------------|
| `DESIGN_VARIANCE` | **4** | Mostly structured grids; slight asymmetry OK in Discover staging; no artsy chaos |
| `MOTION_INTENSITY` | **4** | CSS transitions + purposeful reveals; no cinematic scroll-hijack by default |
| `VISUAL_DENSITY` | **8** | Cockpit: tight pads, 1px separators, mono for numbers, bento instrument panels |

Override only if Alexander explicitly asks for a calmer gallery mode (drop density toward 5) or a demo-marketing shell (raise variance/motion—but keep science surfaces dense).

---

## 1. Visual Theme and Atmosphere

- **Mood:** Precise, calm, trustworthy, nocturnal lab instrument—not startup hype.
- **Philosophy:** Every pixel either shows biology/physics evidence or gets out of the way.
- **Density:** High on Jobs / Job proof / pocket tables; medium on Discover steps; stage-first on Viewer.
- **Closest public DESIGN.md cousins (inspiration only):** VoltAgent (void-black + emerald), Cursor dark IDE, Linear minimal dark. Do **not** copy Claude terracotta or purple AI chrome.
- **Brand mark:** `boot-logo.png` / favicon art (molecule cross)—text-free. Product wordmark: **ddOS**.

---

## 2. Color Palette and Roles

Ground truth lives in `crossbind/static/css/crossbind.css` `:root`. Agents must not invent a second palette.

| Token | Hex / value | Role |
|-------|-------------|------|
| `--bg` | `#080A0A` | App canvas (Taste: off-black, never pure `#000`) |
| `--bg2` | `#0f1011` | Alternate canvas |
| `--elev1` | `#121414` | Sidebar, sticky chrome, panels |
| `--elev2` | `#171a1a` | Nested elev / hover |
| `--elev3` | `#1c2020` | Deep nested |
| `--line` | `rgba(255,255,255,0.08)` | 1px borders |
| `--line-soft` | `rgba(255,255,255,0.05)` | Hairlines |
| `--text` | `#e8ecec` | Primary text (off-white, never `#fff` full-bleed) |
| `--muted` | `#8a9393` | Secondary labels |
| `--teal` / `--ok` / `--cyan` | `#2ee6c5` | **Sole accent** — CTAs, selected pocket, active nav, ok chips |
| `--teal-dim` | `#1bb89a` | Pressed / secondary teal |
| `--warn` | `#f5a524` | Honesty / AF warnings |
| `--bad` | `#f07178` | Errors / cancel danger |

**Locks (from Taste Skill §4 / docs “locks”):**

1. **Color Consistency Lock** — one accent (`#2ee6c5`) everywhere. No sudden purple/blue CTAs.
2. **Page Theme Lock** — dark instrument theme for the whole app. No mid-route flip to warm paper sections.
3. **LILA rule** — AI purple / mesh blob gradients **banned**.

**Semantic contact colors (must ship with legend):** H-bond, hydrophobic, pi-stack, clash, vdw—distinct but not rainbow noise; never encode meaning by color alone (a11y).

**Provenance chips:** crystal PDB / AlphaFold / upload—three mutually distinct neutrals + optional teal only when selected.

---

## 3. Typography

| Role | Stack | Notes |
|------|-------|-------|
| UI sans | `"Inter", system-ui, Segoe UI, sans-serif` | Already in product. Taste discourages Inter as *marketing default*; for **instrument OS** Inter is acceptable (Linear/devtool override path). Do not switch fonts without Alexander. |
| Mono | `"JetBrains Mono", "Fira Code", ui-monospace` | Scores, coords, PDB, UniProt, SMILES snippets |
| Base size | `14px` / line-height `1.45` | Dense but readable |
| Features | `font-feature-settings: "tnum" 1` | **tabular-nums on all metrics** |

**Rules:**

- No Fraunces / Instrument Serif / decorative serif headlines.
- No em-dash (`—`) or en-dash separators in UI copy (Taste §9.G). Use hyphen `-` or rephrase.
- No section-number eyebrows (`01 · Pockets`). Plain labels: `Pockets`, `Structure`, `Evidence`.
- Metric values: always `.mono` + tabular-nums.
- Headlines on Discover: short (not marketing manifesto).

---

## 4. Spacing, Grid, Layout

- **Radius:** `6px` everywhere (`--radius`) — **Shape Consistency Lock** (all-soft-small). Do not mix pills + sharp randomly.
- **Spacing:** 4/8px grid. Panel padding ~12px. Sidebar width `--sidebar-w: 220px`.
- **Shell:** flex app-shell; sticky sidebar; sticky top chrome with `--line` border.
- **Bento / instrument panels:** CSS grid of unequal cells OK at variance 4; prefer readable sections over artsy masonry.
- **Tables:** Jobs, pockets, contacts—high density; prefer `border-bottom` hairlines sparsely (Taste bans `border-t`+`border-b` on every row).
- **Breakpoints:** collapse sidebar to top nav on small screens (existing mobile nav). Prefer `min-h-[100dvh]` thinking if/when migrating off Jinja; avoid `h-screen` jumpiness.
- **Grid over fragile flex math** when building new layouts.

---

## 5. Depth and Elevation

- Elevation = background step (`elev1` → `elev3`), not heavy drop shadows.
- Prefer 1px `--line` borders over card shadows.
- Soft inset highlight optional on active teal CTAs only.
- Modals/overlays (if added): elev3 + dim backdrop; z-index scale documented (nav < overlay < toast).

---

## 6. Component stylings (ddOS required objects)

Implement against these contracts when UI is authorized. Golden HTML patterns also in `AGENTS.md` §5.

### 6.1 Metric card

```html
<div class="panel metric-card">
  <div class="metric-label">Vina affinity</div>
  <div class="metric-value mono">-5.84</div>
  <div class="metric-hint">kcal/mol rank - not Kd</div>
</div>
```

### 6.2 Provenance chip

Pill/chip: `PDB 6B1U` | `AlphaFold` | `Upload` — warn styling when AF.

### 6.3 Pocket strip / table

Columns: select · method · score · center · residues · ligand-aware rank. Selected row uses teal border/background tint. Honesty line under table.

### 6.4 Proof table

Columns: residue · type · distance_A · detail · method. Rows: `data-contact-id="{id}"`. Click syncs viewer highlight.

### 6.5 Honesty banner

```html
<div class="banner warn">Docking scores are ranking tools, not experimental Kd/IC50.</div>
```

### 6.6 Engine badge

Vina / GNINA / DiffDock-L labeled with correct field names—never “affinity = Kd”.

### 6.7 Job timeline

queued → preparing → docking → scoring → completed|failed|cancelled. Cancel is danger (`--bad`).

### 6.8 Docking stage (Viewer)

3Dmol canvas hero; chrome secondary. Contact pulse on selection. Box overlay visible. Ligand CPK/ball-stick readable.

### 6.9 Buttons / inputs

- Primary CTA: teal fill, dark text or high-contrast pairing (WCAG AA).
- Secondary: elev2 + line border.
- Inputs: label above; helper optional; error below; never placeholder-as-label.
- Full interactive states: loading (skeleton shaped like content), empty, error, `:active` slight press.

### 6.10 Originkit / motion kits

Use as **pattern references** for: staged step reveal, soft emphasize, success pulse. Prefer CSS/`requestAnimationFrame`-free scroll; if Motion/GSAP ever added, isolate leaves and honor `prefers-reduced-motion`. Do not import marketing marquees or sparkle packs into science surfaces.

---

## 7. Motion

| Intensity | Allowed |
|-----------|---------|
| Default (dial 4) | `transition` on hover/active; Discover step fade; contact highlight pulse; job progress bar |
| Higher (only if Alexander asks demo flair) | Pose morph between ranks; pocket proposal emphasize—still **motivated** (Taste: hierarchy/story/feedback/state) |

**Banned:** scroll cues, marquees, falling molecules, ambient particles, `window.addEventListener('scroll')`, infinite loops on every card, cinematic pin stacks as default product chrome.

**Reduced motion:** any animation above dial 3 must degrade under `prefers-reduced-motion`.

---

## 8. Voice and content

- Plain scientific English. Concrete verbs. No “elevate / seamless / unleash / revolutionize”.
- Scores always captioned as ranks / engine outputs.
- Empty states explain the next real action (“Select a target to load Open Targets dossier”).
- No fake-precise stats. No Jane Doe testimonials. No fake product UI divs pretending to be the 3D viewer—use the real viewer.
- Max one intent per primary CTA on a screen.

---

## 9. Brand

- Name: **ddOS** · expand once: Drug Discovery Operating System.
- Logo: text-free molecule mark (`boot-logo.png`).
- Credit line OK on boot only: “Developed by Alexander Cecena & Grok Bot”.
- Do not rebrand to Cross Affinity / CrossBind in UI chrome (repo folder may stay CrossBind).

---

## 10. Anti-patterns (merged Taste Skill bans + ddOS)

### Hard bans

- AI purple / mesh blob / glass everywhere
- Em-dash `—` in UI copy
- Section-number eyebrows (`00 / INDEX`)
- Scroll cues (“Scroll to explore”)
- Decorative status dots (unless real semantic state)
- Div-based fake dashboards / fake terminals as “preview”
- Three equal marketing feature cards as Discover layout
- Falling molecules / particle fields
- Labeling Vina/GNINA/DiffDock confidence as Kd
- Mid-app theme flip to light paper
- Mixing multiple icon families / design systems blindly
- Shipping placeholders / TODO panels in production routes
- Scraping UIRoot / Originkit / Mobbin screenshots into the repo

### Soft bans (avoid unless asked)

- Marquee strips, kinetic type heroes, agency decoration text
- Serif display type
- Heavy GSAP scroll-hijack on job pages
- Sound kits (Cuelume etc.) until intentionally productized

---

## 11. Redesign protocol (when UI go is given)

From Taste Skill §11, adapted:

1. Declare Design Read + dials (this file).
2. **Audit** current Jinja/CSS (tokens already match §2—preserve them).
3. Mode: **Redesign–Preserve** brand tokens/IA routes (`/discover`, `/jobs`, …) unless Alexander asks overhaul.
4. Modernization order: typography/spacing rhythm → component density → semantic motion → viewer stage polish.
5. Never silently change route slugs, primary nav labels, or form field names that analytics/muscle memory depend on.
6. Run **Pre-flight** (§12) before claiming done.

---

## 12. Pre-flight checklist (product UI)

Before shipping any authorized UI change:

- [ ] Design Read stated; dials = 4 / 4 / 8 unless overridden
- [ ] Only `--teal` accent; no purple/mesh
- [ ] Theme locked dark; no mid-page invert
- [ ] Radius system consistent (`6px`)
- [ ] Tabular-nums on scores/coords/MW
- [ ] Zero em-dashes in copy
- [ ] Required objects present if touching those surfaces (provenance, pocket strip, stage, proof sync, honesty, engine badge, timeline)
- [ ] Loading / empty / error states real
- [ ] CTA contrast WCAG AA; no wrapped primary CTA labels at desktop
- [ ] Motion motivated + `prefers-reduced-motion` honored
- [ ] No fake 3D / fake Kd / scraped assets
- [ ] Routes and nav labels preserved
- [ ] Static assets cache-busted if JS/CSS changed
- [ ] Still matches `AGENTS.md` library-first + honesty rules

If any box fails, output is not done.

---

## 13. Stack honesty (ddOS vs Taste defaults)

| Taste Skill default (landings) | ddOS choice |
|--------------------------------|-------------|
| React/Next + Tailwind v4 + Motion | Keep **Jinja + CSS variables** unless Alexander approves a front-end migration |
| Marketing heroes / bento brand grids | Instrument panels + scientific stage |
| Dual light/dark marketing | Dark instrument primary; light mode only if explicitly requested later |
| Phosphor icons etc. | Prefer one icon family if we add icons; keep current UI minimal |
| Landing anti-dashboard | We **are** dashboard-like—use Carbon/Primer density instincts |

---

## 14. External references (do not vendor; read when stuck)

- Taste Skill SKILL.md: https://github.com/Leonxlnx/taste-skill  
- Taste docs: https://www.tasteskill.dev/docs  
- getdesign.md gallery: https://getdesign.md/  
- Open Design systems: https://opendesigner.io/design-systems  
- UIRoot DESIGN.md category: https://uiroot.com/category/design-md  
- UIRoot UI components: https://uiroot.com/category/ui-component  
- Originkit listing: https://uiroot.com/tools/203  

---

*Expanded 2026-09-22 from UIRoot-linked tools’ public docs/code for Hermes/Cursor/Grok. Implementation remains gated until Alexander says go.*
