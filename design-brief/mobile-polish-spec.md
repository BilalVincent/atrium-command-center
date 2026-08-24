# Atrium OS — Mobile Polish Pass (v6.1)

**Author:** Solari1 (Chief of Staff) · **Date:** 2026-08-21
**File:** `~/atrium-command-center/index.html` (single-file frontend; commit as `v6.1: mobile-friendly OS chrome`)
**Server:** keep `CC_NO_AUTH=1 python cc_server.py 8800` running for verification.

## Context (what was just shipped)

v6 (`b90bdb04`) delivered glass-morphic chrome, the top-right corner fix (pills row horizontal), filter relocation into the corner cluster, and the left rail reorder (Agent Profiles → Directives TOP 3 → Documents → Calendar bottom-left). Desktop at 1600px is verified good. **Mobile is NOT adapted** — the app still uses the desktop grid at small viewports.

## Verified defects (from headless Edge screenshots — trust these, they are real)

### Phone 390×844 — BROKEN
1. `.app` grid (`grid-template-columns:272px 1fr 322px`) stays fixed → left rail eats ~65% of the viewport, main canvas is a thin strip.
2. Top-right corner cluster (DASHBOARD/TASK pills, filter pills, clock) is clipped/partially off-screen and not tappable.
3. Orbit is clipped to a vertical sliver on the right.
4. Document/agent labels truncate to `Ag…`, `Ch…`, `Me…`; touch targets are sub-40px.

### Tablet 768×1024 — CRAMPED
1. Top filter row overflows: CHATS/EMAIL/FILES/MEMORY pills squeeze against the clock + ALL cluster (clipping/overlap at the right edge).
2. Left rail labels truncate (`Ag…`, `Ch…`, `Me…`).
3. **AGENT PROFILES section renders collapsed/empty at 768px** even though desktop shows it — investigate: likely the `.left-scroll` flex container height or a media-query conflict. It must show the 7 head-shot rows at tablet width.
4. Right panel correctly hidden <1000px (existing rule) — keep that.

## Required changes

### A. Breakpoints — add THREE media query blocks (keep existing 1000px and 900px rules)

**A1. `@media (max-width: 820px)` — tablet:**
- `.app` → `grid-template-columns: 216px 1fr; grid-template-areas: "topbar topbar" "left center"` (right rail already hidden; make left rail 216px).
- `.topbar .right` → allow wrap with `gap:6px; padding:0 6px`, reduce pill padding (`padding:6px 10px`), font 10px, so the filter row fits one line at 768px. Ensure the clock + ALL cluster never overlaps: add `margin-left:auto` on the clock group and `flex-wrap:wrap` on the cluster.
- `.left-scroll` → set `min-height:0` + explicit `max-height: calc(100dvh - 200px)` so AGENT PROFILES, DIRECTIVES, DOCUMENTS render and scroll; never collapse to zero.
- Rail labels: allow full labels by reducing font to 10.5px and removing `max-width` truncation where it fits; ellipsis only as last resort.

**A2. `@media (max-width: 600px)` — large phone:**
- `.app` → single column: `grid-template-columns: 1fr; grid-template-areas: "topbar" "center"`.
- Left rail becomes an **overlay drawer**: `position:fixed; left:0; top:56px; bottom:0; width:280px; transform:translateX(-105%); transition:transform .28s ease; z-index:60;` + class `.left.open{transform:translateX(0)}`.
- Add a hamburger/logo button in the topbar left (44px target) that toggles `.left.open` (small JS: `document.querySelector('.menu-btn').onclick = () => document.querySelector('.left').classList.toggle('open')`; close on backdrop tap/overlay click and on selecting a profile).
- Center: full width, orbit visible; `padding:0`.
- Top-right cluster: compact icon-first pills (hide text labels < 480px if needed, keep icons ◉ 💬 ⏱ 📁 🧠 + DASHBOARD/TASK icons), `gap:4px`, `padding:5px 8px`, clock smaller (10px). Must NOT overflow — if the row still overflows, let it wrap to a second line with `flex-wrap:wrap`.
- Modals (glass panels, Memory Brief, search results, file viewer, ghost modal): **full-screen on phones** — `position:fixed; inset:0; width:100vw; height:100dvh; max-width:none; border-radius:0; top:0; right:0; left:0; transform:none;` with a visible close (✕) button ≥ 40px, content scrollable internally.
- Chat input + bottom bar: full width, input font ≥ 16px (prevents iOS zoom), send button ≥ 44px.

**A3. `@media (max-width: 420px)` — small phone:**
- Hide pill text labels in the top-right cluster entirely (icons only, `aria-label` retained), keep clock HH:MM.
- Reduce rail drawer width to 260px.
- Ensure ALL interactive targets ≥ 40×40px.

### B. General mobile rules (apply at all three breakpoints)
- `body { overflow-x:hidden; }` and `html,body { -webkit-text-size-adjust:100%; }`.
- `input, select, textarea { font-size:16px; }` on touch to prevent auto-zoom.
- Add `touch-action: manipulation;` to interactive elements; `-webkit-tap-highlight-color: transparent;`.
- Keep glass recipe (blur 22px, gold hairlines) — do NOT remove glass styling; only geometry changes.
- Orbit engine: **do NOT touch orbit JS or 3D geometry** — only CSS viewport sizing around it.
- Agent head-shots: at ≤600px, the profiles inside the drawer must still show all 7 rows with head-shots; tap = select profile (existing behavior), tap again = deselect. When a profile is selected the section focuses on that profile's KPIs — keep that behavior; ensure a back/close affordance in the drawer.

### C. Verification (REQUIRED before commit)
1. `python -c "import re; open('_check.js','w').write(chr(10).join(re.findall(r'<script>(.*?)</script>', open('index.html').read(), re.S)))"` — confirm no JS syntax errors.
2. Reload dev server (it serves from disk; just re-curl). `curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8800/` → 200.
3. Headless Edge screenshots at **1600×950**, **768×1024**, **390×844** — save to `$LOCALAPPDATA/Temp/cc-mobile-qa/` and verify with vision: (a) 390px — top-right cluster visible & tappable, drawer opens, orbit fills center, modals full-screen; (b) 768px — filter row fits, AGENT PROFILES shows all rows, no overflow; (c) 1600px — desktop unchanged from v6 (regression check).
4. Commit as `v6.1: mobile-friendly OS chrome` and push.

## Do NOT
- Do not change the Atrium brand palette (ink/gold/cream) or introduce Quro navy/coral.
- Do not alter orbit v5.1 geometry/JS.
- Do not touch `design-brief/` outputs or the concept PNGs.
- Do not rework desktop layout that is already verified good — mobile pass only.

## Success criteria (checklist for your summary)
- [ ] 390px: no horizontal overflow; corner cluster tappable; left drawer opens/closes; orbit center visible; modals full-screen with close button.
- [ ] 768px: filter row fits one line (or wraps cleanly); AGENT PROFILES shows all 7 rows; labels readable.
- [ ] 1600px: pixel-identical to v6 behavior (no regression).
- [ ] Committed `v6.1: mobile-friendly OS chrome` and pushed.
- [ ] Screenshots at all three widths saved under `$LOCALAPPDATA/Temp/cc-mobile-qa/`.
