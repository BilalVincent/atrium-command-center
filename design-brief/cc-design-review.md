# Atrium Command Center — Design Review & Scale Plan

*Read against: `index.html` (2,472 lines, v6.5) + `design-brief/v65-qa-desktop.png` (live capture, 1,321 nodes · 1,139 links). No files were modified.*

---

## A. DESIGN REVIEW

### What's genuinely working

- **Palette discipline is excellent.** The ink/gold/cream system holds almost everywhere; status colors (`--ok/--warn/--danger`, line 15) are quarantined to tiny status dots. The VAULT override block (`index.html:272-277`) re-points tokens rather than scattering hex — the right instinct.
- **The layout skeleton is sound.** `grid-template-columns:272px 1fr 322px` with a 56px topbar (`index.html:26`) gives a stable triptych; the calendar lives *outside* `.left-scroll` (`index.html:708`), so "docked bottom, never scrolls" is structurally guaranteed, not hoped for.
- **v6.5 shows the right lessons learned** — slim single-row top-right cluster, chat capped at `min(40dvh,360px)` (`index.html:125`), pills back in the rail.
- **Accessibility touches are real**: 44px touch targets, `aria-label`s, tap-highlight suppression, 16px inputs on mobile.

### What fights the "calm OS" goal

1. **Nothing is ever still.** Five always-on motion systems run simultaneously: `livePulse` (2s), `dotPulse` (1s per busy agent), `ghostHalo` (3s, a 56px pulsing button permanently in the scene), 220 twinkling particles (`index.html:1111`), auto-rotation at 0.00025 rad/frame, plus an activity pulse spawned every 0.34s. Individually each is tasteful; together the screen never rests, so real activity (gold pulses) has nothing to stand out against. Calm requires a baseline of stillness.

2. **Emoji are the one brand-language break.** 📊⚡💬⏱📁🧠📄📂🔗🕘🗺🧩🔊➤ sit inside a refined gold/ink palette as multicolor platform glyphs. In the QA capture the pills and topbar read as two different design systems colliding. This is the single cheapest "ultra-sleek" upgrade available (see B5).

3. **Micro-type has no scale.** The rail alone uses 8, 8.5, 9, 9.5, 10, 10.5, 11, 11.5, 12, 12.5px (`.dow` 8px at `index.html:81`, `.pf-kpi .pk` 8px at `index.html:474`, `.vital .vk` 8.5px at `index.html:348`…). Sub-9px type isn't sleek, it's strained, and the 0.5px steps destroy rhythm. Letter-spacing ranges .02–.16em with no system.

4. **Cascade archaeology is now a correctness risk.** Five override strata (base → VAULT → AI-OS additions → v6 glass → v6.x patches) with "do not edit above" comments. Concrete debris: `renderAgents/renderChats/renderCron/renderAssets/renderVitals/renderMemoryTab` all query DOM that no longer exists (`#agentList`, `#chatList`, `#cronList`, `#assetList`, `#vitalGrid`, `#zoneFilters`, `#memoryList`) and bail via null guards every 8s poll (`index.html:890`, `2468`); `.hud-filters` class selectors (`index.html:401,497`) target a wrapper the rail markup doesn't use (it's `class="zone-filters"`, `index.html:692`); media rules still style `.topbar .right .hud-filter` (`index.html:521,558,595,602`) from before the v6.5 move; `.zf.on` (`index.html:368`) and `.panel[hidden]`/`.tab` wiring (`index.html:2364-2371`) are orphans. Also `.right` names both the topbar cluster and the inspector — the brute-force fix at `index.html:413` is a symptom patch; rename the inspector `.inspector`.

### Concern 1 — Filter pills: verdict

**Yes, there is a direct cascade conflict, and it has two causes:**

- **Cause 1 — the v6.5 glass override clobbers the recipe.** The v5.1 recipe lives at `index.html:402`: `font-size:10px; letter-spacing:.14em; uppercase; weight 700; background:rgba(12,11,8,.6); border:rgba(176,141,87,.35); padding:5px 12px` — all intact. But `index.html:498` re-declares `.hud-filter` with `background:rgba(250,247,240,.055); backdrop-filter:blur(22px) saturate(150%); border:1px solid rgba(217,185,120,.22)`. Same specificity (0,1,0), later in source order → the crisp dark fill and gold border lose. That override was written when pills floated over the orbit canvas in the topbar HUD; in the rail they sit on opaque `--paper:#15130F`, so the glass treatment adds nothing but milkiness (and five 22px blurs of perf cost). **Hover and active states survive** — `.hud-filter:hover` and `.hud-filter.active` (`index.html:403-404`) have specificity (0,2,0), so the gold-tint hover and solid-gold/#14110D active still win regardless of order.

- **Cause 2 — the text token silently drifted.** The recipe's `color:var(--gold-pale)` was authored when `--gold-pale:#E7DAC2` (solid cream, line 11). The VAULT block redefined it to `rgba(176,141,87,.16)` (`index.html:275`). The pill labels are therefore rendered at **16% alpha gold on a near-transparent fill** — a contrast ratio around 1.5:1. The QA capture confirms it: AGENTS (active, solid gold) is crisp; the four inactive pills are ghosts. Restoring the background alone will *not* fix the wash-out; the color must be pinned too.

**Restoration recipe (exact, no character change):** delete the `index.html:498` override entirely, and in the line-402 rule pin `color:#E7DAC2` as a literal (or re-point only the pill rule at a solid token) so the drifted variable can't wash it out again. Icons are inline spans inheriting `currentColor`, so ◉💬⏱📁🧠 carry over automatically.

**Refinements worth making without changing character:**
- `display:inline-flex;align-items:center;gap:6px` — emoji glyph advance widths are inconsistent, so icon/label spacing is ragged today.
- Drop `backdrop-filter` from the pill entirely in rail context (pointless over opaque paper).
- `:focus-visible{outline:1px solid var(--gold-bright);outline-offset:2px}` + `aria-pressed` on the active pill.
- The emoji icons don't inherit color; to complete the monochrome look cheaply: `.hud-filter .fic{filter:grayscale(1) sepia(1) saturate(2.4) hue-rotate(-12deg) brightness(1.2)}` tints them into the gold family without replacing them. (Note ◉ is a text glyph and already inherits; the other four are color emoji.)
- At the 272px rail the five pills **wrap 3+2** (confirmed in the capture) — that's fine, but give the wrap intent: keep `gap:5px` and consider `flex:1 1 auto; justify-content:center` so both rows read as a deliberate grid.

### Concern 2 — Left rail vertical budget

**Current measured heights** (derived from the CSS; calendar worst case = 6-week month + 3 events, per `index.html:1764`):

| Section | Height now | Derivation |
|---|---|---|
| Topbar | 56px | grid row, `index.html:26` |
| Profiles card (7 `.prof` rows) | **~348px** | margins 10+2, padding 12+6, `rail-sec` ~20, rows: 4+4 padding + 30 avatar + 2 border = 40px × 7 + 6×3 gaps = 298 |
| Filter row (wraps 3+2 at 272px) | **~59px** | 2×22px pills + 5 gap + 8+2 margins |
| Calendar (worst) | **~285px** | margins 20 + padding 26 + head 28 + grid ~138 + events 73 |
| **Total** | **~748px** | vs **644px available** at a 700px viewport → **~48px over** → `.left-scroll` scrolls internally. Owner's report confirmed, with numbers. |

Note the real cliff is worse than 700px: a 1366×768 Windows laptop yields **dvh ≈ 640** after browser chrome. Design to 640.

**Key finding about focus mode:** the KPI card *replaces* the 7-row list and is *shorter* — `pf-head` 68 + `pf-kpis` ~100 + skills 18–64 + chrome ~50 ≈ **259–282px** vs the list's 348px. Expansion is not the risk; the full list + event-bearing months is. Only risk in focus mode: 8 skill chips wrapping to 3 rows (`index.html:2088` slices to 8) — clamp to 2 rows.

**Tightened budget (target ≤ 640, no character change):**

| Rule change | Saves |
|---|---|
| `.prof` padding `4px 6px` → `3px 6px`; `.p-av` 30 → 27px; `.profile-list` gap 3 → 2 | rows 40 → 35px → **−46** (profiles card ≈ 302) |
| `.zone-filters` margin-top 8 → 6 | **−2** (57) |
| `.calendar` padding `12px 14px 14px` → `10px 12px 12px`; `.cal-head` mb 8 → 6; `.day` padding 3 → 2; `.dow` padding 2 → 1; grid gap 2 → 1 | **−27** |
| Events: keep 3 but `.ev` padding 2 → 1 and `.cal-events` margin/padding 8/7 → 6/5 — *or* `slice(0,3)` → `slice(0,2)` (`index.html:1764`) for the full −19 | **−10 to −19** (calendar ≈ 239–258) |
| **New total** | **~598–617px → fits 640 with 23–42px slack** |

Slack absorbs an 8th agent (+37px). Below that, add an explicit compact tier rather than letting scroll sneak in:

```css
@media (max-height:760px){ .p-rl{display:none} .prof{padding:2px 6px} } /* rows → ~24px, card → ~225px */
```

**Guarantee layer (optional but recommended):** since "nothing scrolls" is a hard rule, enforce it mechanically — after `renderProfiles()`/`renderCalendar()`, compare `.left-scroll` `scrollHeight` vs `clientHeight` and toggle a `.rail-dense` class carrying the tightened values. Then the budget degrades gracefully by measurement, not by hope. Also remove the magic `max-height:calc(100dvh - 200px)` on `.left-scroll` at ≤820px (`index.html:525`) — the flex contract (`flex:1 1 auto; min-height:0`, `index.html:435`) already does this correctly. And if the hidden Directives/Documents cards ever return, they carry 160–170px `max-height` scroll containers each — they will break any budget; keep them retired.

### Concern 3 — Orbit visual scale: verified facts

All claims check out in code:

- `drawNode` (`index.html:1441`): `rad = (agent?13 : (readable||file?9 : 6)) * s` — **files sit in the same "readable" tier (9) as memory/skill/profile nodes**, and `bright` (`index.html:1440`) includes `file`, so files get the full-brightness path.
- **Every node draws a glow halo**, including files: `gs = rad*(2.6 + activity*1.5)` (`index.html:1445-1447`). A resting file therefore paints a ~94px-wide soft gold blob (r=9 → halo radius ≈ 23px at s=1, ×2 across) at 0.65 alpha. With ~1,000+ file nodes the halos merge into the cotton-ball fog visible in the QA capture — *this, not node radius, is why files dominate*.
- Seven per-owner file clusters at `base:220` (`index.html:958`), memory zones also 220, skills/conversations/cron at 380, agents 70, profiles 95.
- Radius growth `base + 12*sqrt(members)` (`index.html:974`) and placement-sphere growth `(clusters/24)^0.4` (`index.html:981`) — confirmed.
- Totals 1,321 nodes / 1,139 links confirmed on-screen (`hudLive`, `index.html:891`).

**Assessment of the two growth formulas:** for *spatial density* under uniform growth they're roughly adequate — cluster volume grows ~r³ and r ~ √m while the sphere grows ~(clusters)^0.4, so local crowding stays approximately constant. But they fail three ways:

1. **They scale space, not salience.** Every added file arrives with a readable-tier radius *and* a 2.6× glow halo. Salience per node never decays, so 10× the nodes = 10× the fog. The dominance problem is render-weight, not layout.
2. **√m over-grows single huge clusters in 3D.** One owner reaching 5,000 files gets r = 220+749 = 969 — and since each cluster's center is placed at *its own* radius × growth (`index.html:992`) with no inter-cluster collision resolution, neighboring shells interpenetrate into mush.
3. **The compute path doesn't survive 10×.** The force pass is intra-cluster O(m²) × 120 iterations (`index.html:1018-1041`) — a 5k-member cluster is ~1.5B pair-checks, a multi-second freeze; and `computeLayout()` re-runs on *any* node-count change (`index.html:888`) while the state polls every 8s (`index.html:2468`), so one new file re-freezes everything. Per frame: a full `sort()` of all nodes (`index.html:1405`), an unbatched `stroke()` per edge (1,139 today → 10k+ at scale), and `hitNode` is a linear scan per pointermove (`index.html:1202`).

**What 5k–50k looks like if unchanged:** fill-rate collapse (thousands of overlapping 94px halos → ~20–30fps on integrated GPUs), contrast death (background becomes muddy gold; the filter pills' 0.14-alpha culling still *draws* everything including glow), layout freezes on every poll that adds a file, and a latent **near-plane bug**: `project()` (`index.html:1122`) computes `FOCAL/(FOCAL+z)` with no guard — nodes rotating behind the camera produce huge/negative `s` and get drawn as giant mirrored sprites. Harmless at 1.3k, guaranteed artifacts at 50k.

---

## B. NEW DESIGN IDEAS

Ordered by leverage. All hooks reference actual code; nothing here adds features — it's polish, hierarchy, motion discipline, depth.

**1. Pin the v5.1 pill recipe + sweep the cascade debris — S.**
Delete `index.html:498`; pin `color:#E7DAC2` in the line-402 rule; remove the dead `.topbar .right .hud-filter` media rules (`521, 558, 595, 602`) and `.zf.on` (368). Why: the rail's control layer becomes legible again, and the stylesheet stops fighting itself. This is the owner's stated wish plus the hygiene that keeps it restored.

**2. Attention-gated motion: one "alive" thing at a time — S.**
When a node is focused (`selected.id` set) or the chat is active: pause `ghostHalo` (`.scene-wrap.focused .ghost-btn{animation-play-state:paused}`), halve particle alpha and count (guard in the `frame()` particle loop, `index.html:1326`), and slow auto-rotation 0.00025 → 0.00012 (`index.html:1312`). Why: motion should *signal* state changes (pulses, flashes), not run as wallpaper. This is the single biggest "calm" lever and it's a few lines.

**3. Depth-fade the far hemisphere — S.**
In `drawNode`, multiply alpha by `clamp((pr.s - 0.10)/0.18, 0, 1)`. Far-side nodes sink into the background; the orbit instantly reads as 3D volume instead of a flat tangle, overdraw drops ~40%, and it pre-solves half the fog problem. One line, `index.html:1446`.

**4. Chat docks to a slim bar until spoken to — M.**
`.chat` (`index.html:125`) permanently consumes min(40dvh, 360px); in the QA capture it's ~300px of *empty* dark panel. Add `.chat.docked{height:46px}` with a height transition; the head row toggles it; show an unread badge on `chatThinking`/reply; persist in `localStorage`; default to docked when a session has no messages. Why: returns ~40% of center stage to the orbit — the hero — without losing the team-chat function.

**5. Replace emoji chrome with a 12-icon stroked SVG set — M.**
Hooks: `.fic` spans, `.row .ic`, `.file .fi`, chat `🔊/➤`, right-panel `h4 .ic`. One inline SVG sprite (chart, bolt, chat, clock, folder, brain, file, link, doc, speaker, send, close), 1.5px stroke, `currentColor`. Why: emoji are the only multicolor, platform-inconsistent element in an otherwise disciplined ink/gold system; swapping them is what "ultra-sleek OS" actually looks like. (Idea 1's CSS-filter tint is the zero-effort interim.)

**6. Type & space tokens — M (mechanical).**
`:root` additions: `--fs-2xs:9px; --fs-xs:10px; --fs-sm:11.5px; --fs-md:13px; --fs-lg:15px; --sp-1..4: 4/8/12/16px`; sweep the ~20 hard-coded sizes and the .02–.16em letter-spacing zoo down to three steps (.08/.12/.16em). Why: kills the sub-9px strain (`.pf-kpi .pk` 8px, `.dow` 8px), makes every rail card sit on one rhythm, and makes future edits one-token affairs.

**7. ⌘K command palette on the existing search backend — M.**
Reuse `runOrbitSearch`/`renderSearchResults` (`index.html:2387-2430`) in a centered modal; add verb results: switch filter pill (`setOrbitFilter`), open Dashboard/Task, jump to agent. Why: one entry point to everything is the defining OS interaction, it retires the "two search boxes" feel, and the hard part (fuzzy backend + result rendering) already exists.

**8. Selection → zone echo — S.**
In `drawZoneRings` (`index.html:1973`): when the selected node is a memory, boost its zone's ring alpha 0.10 → 0.35 and pulse the matching legend dot (`.legend .lg`); when an agent is selected, brighten its segment of the team ring (`index.html:1350`). Why: wires the panels to the canvas so selection feels like the *system* acknowledging you, not a tooltip appearing.

---

## C. ORBIT AT SCALE — ENGINEERING PLAN

### C1. Visual weight tiers (fixes "files too dominant" first)

Redefine `drawNode` tiers — meaning keeps its light; bulk becomes texture:

| Tier | Classes | Radius @s=1 | Glow at rest | Rest alpha |
|---|---|---|---|---|
| 0 — beacon | `agent` | 13 (unchanged) | yes, 2.6× | 1.0 |
| 1 — landmark | `memory.index`, `cron` | 11 / 9 | yes | 0.9 |
| 2 — content | `memory`, `conversation`, `skill`, `profile` | 7.5 | only if `activity>0`, `hotFiles`, hover, or in `focusSet` | 0.75 |
| 3 — bulk | `file` | 5 | **never** at rest (only hot/selected/hover) | 0.5 |

Concrete changes in `index.html:1437-1463`: gate the `drawImage(glowSprite,…)` on `tier<=1 || n.activity>0 || hotFiles.has(n.id) || selected/hover/highlight`; drop the file radius from the `readable` branch to its own `5`. Expected effect at today's 1.3k nodes: ~85% of halo overdraw disappears; clusters resolve from cotton balls into swarms of legible points with glowing meaning-nodes — the composition inverts to agents/memory-first without touching layout.

**Population-compensated radius** so a class shrinking per-node as it grows:
`classScale = clamp(Math.pow(500/N_class, 1/6), 0.62, 1)` — at 180 files ≈ 1.0 (today's look preserved), 5,000 → 0.79, 50,000 → 0.62. The 1/6 exponent damps gently: screen area ~r², so salience decays far slower than count grows.

### C2. Cluster shell rebalancing

1. **Calibrated cbrt spread** — keep the approved look today, tighten growth above the crossover. `12·√m` and `28.5·∛m` intersect at m≈180 (both = 161 at today's file-cluster size), so:
   `c.radius = c.base + Math.min(12*Math.sqrt(m), 28.5*Math.cbrt(m))`
   Unchanged below 180 members; at 5k members → 488 vs 749 (√), at 50k → 1,051 vs 2,684 — 60% tighter, and it caps how far any one blob can balloon.
2. **Split rule:** when a cluster exceeds 400 members, bisect into sibling sub-clusters sharing the parent's orbital slot at ±offset angles (recursive). Bounds the O(m²) force pass (400² × 120 ≈ 19M ops — fine) and prevents any single blob outweighing the semantic core.
3. **Center collision resolve:** after Fibonacci placement (`index.html:991-995`), run 8 deterministic iterations pushing apart any center pair closer than `(r_i + r_j) × 0.92` along their separation axis. Today centers are placed at their own radius with no resolution — this is the interpenetration fix.
4. **Semantic ordering (option B, only if tiers alone don't satisfy):** re-tier base shells so glance-value decays outward — agents 70, profiles 95, memory 220, skills/conversations 300–340, **files 380 (outermost frame)**. Bulk becomes the boundary; meaning stays central. More disruptive to the approved composition, so stage it after C1.
5. **Auto-fit camera** so growth never drifts out of frame: on layout change, `zoomTarget = 0.42 × (min(W,H)/2) ÷ (maxClusterCenterDist + maxClusterSpread)`, clamped to `MIN_ZOOM/MAX_ZOOM` (`index.html:1100`). Retires the fixed `cam.zoom = 0.45` default (`index.html:1101`).

### C3. Density management at 10×–50×

Per-frame pipeline, in draw order:

1. **Near-plane + frustum cull** (also fixes the latent bug): in the projection loop (`index.html:1336`), skip if `z >= FOCAL - 40` (behind camera), `s <= 0.02`, or projected xy outside `[-48, W+48] × [-48, H+48]`.
2. **Depth fade** (idea 3, promoted to law): `alpha *= clamp((s - 0.10)/0.18, 0, 1)`. Far hemisphere recedes; zooming out automatically declutters.
3. **Screen-size LOD buckets** (computed from `rad·s`):
   - `≥ 2.5px` → full sprite + entitled glow;
   - `1.2–2.5px` → sprite only, no glow;
   - `0.5–1.2px` → batched 2px rects — one `beginPath` per color, `rect()` calls, single `fill()` (draw calls collapse from N to ~7 colors);
   - `< 0.5px` → skipped.
4. **Edge budget:** hard cap 2,500 strokes/frame with priority `focusSet > hot > refs/mentions > owns`. Beyond 800 visible `owns` edges, aggregate them into one containment circle per cluster (centroid + spread, alpha 0.06) — the radial beam-fans in the QA capture are ~1,000 individual owns-strokes; at 10× they'd be pure fog.
5. **Sort elimination:** keep the per-frame sort (`index.html:1405`) at N ≤ 4,000; above that, counting-sort into 32 preallocated depth buckets by `s` — O(N), no allocation, visually indistinguishable for round sprites.
6. **Picking:** during the existing projection loop, drop `{x, y, id}` into a 32px uniform-grid; `hitNode` (`index.html:1202`) queries one cell + 8 neighbors instead of scanning every clickable node per `pointermove`.
7. **Layout off the main thread:** move the force pass to a Web Worker (positions back as a transferable `Float32Array`); debounce recomputes to ≥1,500ms; incremental mode when only one cluster's membership changed (re-run that cluster's forces, re-apply the global centroid lock). Kills the "one new file → 8s-poll freeze" failure mode at its source (`index.html:888, 2468`).
8. **Label budget:** labels (`flashes`) only for selected/hover/search-highlight plus the top 4 highest-activity nodes — never per-frame labels for bulk classes.
9. **FPS governor with hysteresis:** EMA of frame time — >50fps: full fidelity; 35–50: glow disabled for tiers ≥2; <35: "constellation mode" (points only, focus-set edges only, particles off, floor rings at 50%). Check every 5s, switch with a 400ms alpha ramp so degradation itself is calm.
10. **Aggregation ceiling:** beyond ~60k nodes the server pre-aggregates into super-nodes per (cluster × ext/zone) with counts; the client expands a super-node on focus. The canvas then never holds more than ~15k live nodes, and the plan above never sees 50k.

**Projected outcomes:** at 5k nodes — drawn sprites drop from ~5,000 to ~1,200 + ~3,800 batched points, edges capped at 2,500 → comfortable 60fps on integrated graphics, no layout freeze. At 50k — impossible raw, routine under aggregation; the visual language (glow = meaning, bulk = texture, depth = distance) stays identical at every scale, which is what makes it feel like an OS rather than a demo that breaks.
