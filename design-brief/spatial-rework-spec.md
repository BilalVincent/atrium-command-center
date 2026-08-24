# Atrium OS — Spatial Rework Spec (v6.2)

**Author:** Solari1 · **Date:** 2026-08-21
**File:** `~/atrium-command-center/index.html` (single-file frontend; commit as `v6.2: spatial declutter`)
**Server:** `CC_NO_AUTH=1 python cc_server.py 8800` on 127.0.0.1:8800.

## Context

v6.1 (mobile-friendly) is landing in parallel — do this work on top of v6.1's committed state, not before it. This pass is about **spatial declutter** per Vincent's review of three screenshots. Do NOT redo v6.1's mobile breakpoints; do NOT touch the orbit engine; keep the glass recipe and brand palette (ink/gold/cream).

## Vincent's verified feedback (three screenshots)

1. **FOCUS bar clipped on the left** — "FOCUS: LIAM VAN" reads as "OCUS: LIAM VAN"; the left edge of the focus tag is cut off. Also shows a right-side pill "R 7,000/10K" (rate/target). Fix the clipping + give it breathing room.
2. **Left rail is cluttered with redundant cards** — DIRECTIVES TOP 3 card and DOCUMENTS list card stack full-width in the rail. Vincent: "do we really need the directives and documents modals. i have access to the content on node click right?" → CONFIRMED: `selectNode(id)` → `populateBrief(n)` + `#briefPanel.show` + `renderRight(n)` gives full content on node click. **Remove the always-on Directives and Documents cards from the left rail.** The content stays reachable via: node click (brief panel + right rail), the corner FILES/zone filter pills, and the DASHBOARD view.
3. **Top-right corner cluster is cluttered** — currently: 3 status chips (CORE·OK / LINK·OK / RUNNER·OK), LIVE·7 AGENTS, DASHBOARD/TASK pills, zone filter pills (AGENTS/OPATS/$CRON/FILES/MEMORY), and the clock — all jammed in one wrap row. Needs spatial grouping, not just smaller fonts.

## Required changes

### A. FOCUS tag / profile focus bar (fix clipping + space)
- Locate `#hudFocus` (`.hud-tag`) — it's inside `.scene-hud` (`position:absolute;top:14px;left:16px;right:16px`). The left edge gets clipped because `.scene-hud` has `left:16px` but the tag's own padding/overflow or a parent overflow hides the first glyph — give `.scene-hud` a safe `padding-left` (or `left:20px`) and ensure no `overflow:hidden` ancestor clips the tag. Verify the "F" of "FOCUS:" is fully visible.
- When a profile is selected, the focus tag shows the agent name; the "R 7,000/10K"-style rate/target pill should sit beside it with a clean gap (min 8px) — not touching the tag border.
- Keep the tag's glass/hud styling (gold hairline, uppercase, letter-spacing) — only fix geometry.

### B. Left rail — remove redundant cards (declutter)
- Remove the **DIRECTIVES TOP 3** card and the **DOCUMENTS** list card from the left rail entirely (HTML + their CSS rules if now unused; keep the section-render JS functions intact so node click and the DASHBOARD view still work — just don't render the rail cards, or guard their container with `display:none` if removing the HTML risks breaking JS that queries those nodes).
- The left rail becomes: **Agent Profiles (head-shots)** → **Calendar (docked bottom-left)**. This is what Vincent likes — keep those two.
- The rail should now feel light: one compact scroll region (`.left-scroll` stays) with the profiles list, then the calendar pinned at the bottom. No stacked full-width cards.
- If any JS references `#directives`, `#documents`, `directivesList`, `docsList` etc. during render and would throw on missing nodes, keep the container elements but hide them (`style="display:none"` on the section wrapper) — do not break the render loop.

### C. Top-right corner cluster — spatial grouping
Current order (from HTML): status chips → LIVE count → DASHBOARD/TASK → zone filters → clock. Rework into a **two-group glass cluster with clear separation**:

1. **Group 1 — System status (compact):** collapse CORE·OK / LINK·OK / RUNNER·OK into ONE status pill: `● SYSTEM · <b>OK</b>` (dot color = worst status, tooltip lists CORE/LINK/RUNNER individually). Keep the LIVE·7 AGENTS pill next to it. Both compact (≤ 10px font, tighter padding).
2. **Group 2 — Nav + filters:** DASHBOARD / TASK pills, then the zone filter pills (AGENTS ◉ / CHATS 💬 / CRON ⏱ / FILES 📁 / MEMORY 🧠) with their icons, then the clock at the far right.
3. Separate the two groups with a **hairline vertical divider** `rgba(217,185,120,.18)` (2px wide, ~20px tall) and a gap ≥ 10px, so the cluster reads as "status | controls | time", not one wall of pills.
4. Keep `flex-wrap:wrap` for narrow widths (v6.1 behavior) but tighten gaps to 5-6px inside groups and 10px between groups.

### D. General spatial polish
- Audit the three screenshots' cluttered spots: reduce pill padding noise (consistent `padding:5px 10px`), consistent 1px gold hairline borders, consistent 10px font for all cluster text, no double borders between adjacent pills.
- Glass panels keep blur(22px), radius 22px (small chips 14px) — no geometry regression.

## Do NOT
- Do not remove node-click content access (brief panel, right rail, DASHBOARD view must keep working).
- Do not touch orbit engine JS/geometry or v6.1 mobile breakpoints.
- Do not change palette (ink/gold/cream; no Quro navy/coral).
- Do not touch `design-brief/` outputs.

## Verification (REQUIRED before commit)
1. JS syntax check: `python -c "import re; open('_check.js','w').write(chr(10).join(re.findall(r'<script>(.*?)</script>', open('index.html').read(), re.S)))"`.
2. `curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8800/` → 200.
3. Headless Edge screenshots at 1600×950 and 390×844 → save under `$LOCALAPPDATA/Temp/cc-spatial-qa/`. Vision-check: (a) 1600 — "FOCUS:" fully visible when a profile is selected (click a head-shot first), left rail has NO directives/documents cards, corner cluster has 2 groups + divider + clock; (b) 390 — corner cluster still fits, rail drawer shows profiles + calendar only, focus tag not clipped.
4. Commit `v6.2: spatial declutter` and push to origin main.

## Success criteria
- [ ] FOCUS tag left edge fully visible (no clipped "F").
- [ ] Left rail = profiles + calendar only; no directives/documents cards.
- [ ] Node click still opens brief panel + right rail content (test via JS or screenshot).
- [ ] Corner cluster = status group | divider | nav+filters+clock group.
- [ ] 1600 + 390 screenshots verified, committed `v6.2: spatial declutter`, pushed.
