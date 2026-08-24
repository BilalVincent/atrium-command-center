# Atrium OS — v6.3: Remove Redundant Rail Tabs + Enlarge Corner Panel

**Author:** Solari1 · **Date:** 2026-08-21
**File:** `~/atrium-command-center/index.html`
**Commit message:** `v6.3: remove redundant rail tabs + enlarge corner panel`

## Context
Vincent reviewed v6.2 and identified two remaining spatial issues:
1. The list above the calendar (`nav.tabs` + 5 `panel-*` divs showing Agents/Chats/Cron/Files/Memory) is redundant — the filters already live in the top-right corner cluster and the content is reachable via node click.
2. The top-right corner cluster is cramped inside a single-row glass strip. Decision: **enlarge it** into a clean two-row glass panel.

## Required changes

### A. Remove redundant left-rail tab system
- Remove the entire `<nav class="tabs" id="tabs">` block (lines ~715-721) from inside `.left-scroll`.
- Remove the five `<div class="panel" id="panel-...">` blocks (lines ~722-732) from inside `.left-scroll`.
- Keep `.profiles` and `.calendar` in the rail — those are the only two Vincent wants.
- Clean up now-dead JS: the functions `renderAgents`, `renderChats`, `renderCron`, `renderAssets`, `renderMemoryTab`, `renderMemoryList`, and `renderMemoryRight` can be deleted IF they are only used by the left rail panels. **BUT** verify first:
  - `renderCron()` is also called in the refresh loop (line ~935) and may still be needed for something else — check.
  - `renderAssets()` populates `#assetCount` (which may now be gone) and may also be used by the right rail or file modal — check.
  - `renderChats()` may be called from `renderRight` or chat flow — check.
  - `renderMemoryTab()`/`renderMemoryList()` may feed the corner Memory filter or brief panel — check.
  - **Safer approach:** keep the render functions but guard `const el = $('#agentList')` etc. with `if(!el) return;` so they don't throw when the panels are gone. Also remove any tab-switching event listeners (`tabs.querySelectorAll('[data-tab]')` etc.) if they exist.
- Remove dead CSS rules for `.tab`, `.tabs`, `.panel` if no longer used elsewhere. Keep `.panel-list` if still used by the right rail? (Right rail uses `.right-body`/`#rightBody`, not `.panel-list` — check.)
- Remove the count update lines that write to `#agentCount`, `#chatCount`, `#cronCount`, `#assetCount`, `#memCount` if those elements are gone. Also remove those element IDs from any render code.

### B. Enlarge top-right corner cluster into a two-row glass panel
Current structure (simplified): `.topbar .right` contains status chips + controls + clock all in one flex row.

Rework:
- Wrap the corner cluster in a glass card/panel `.topbar .right .corner-panel` with:
  - `display:flex; flex-direction:column; gap:6px; padding:8px 10px; border-radius:16px; background:rgba(250,247,240,.055); backdrop-filter:blur(22px) saturate(150%); border:1px solid rgba(217,185,120,.22); box-shadow:...` (same glass recipe).
- **Row 1 (status + clock):** status group (SYSTEM pill + LIVE pill) on left, clock on right.
  - Use `justify-content:space-between; align-items:center`.
  - Keep the existing status chip styling but reduce font to 10px and padding to `4px 8px`.
- **Row 2 (nav + filters):** DASHBOARD/TASK/AGENTS nav pills + filter pills (AGENTS ◉ / CHATS 💬 / CRON ⏱ / FILES 📁 / MEMORY 🧠) in a single wrap row.
  - Use `flex-wrap:wrap; gap:5px; justify-content:flex-end`.
  - Keep compact pill sizing from v6.1/v6.2 but give them more room because they're now in a 2-row panel.
- Add a thin horizontal divider between row 1 and row 2: `width:100%; height:1px; background:rgba(217,185,120,.15); margin:2px 0;`.
- At ≤600px (mobile): the panel should still fit but may need the same icon-only behavior below 480px. Ensure the panel doesn't overflow the viewport at 390px — if row 2 still overflows, allow it to wrap to a 3rd row gracefully (it already has `flex-wrap`).

### C. General cleanup
- Verify the FOCUS tag and rate pill still don't overlap with the search bar/zoom-out (regression check).
- Verify Directives/Documents still hidden.
- Verify mobile drawer still opens/closes and shows profiles + calendar only.

## Verification (before commit)
1. `python -c "import re; open('_check.js','w').write(chr(10).join(re.findall(r'<script>(.*?)</script>', open('index.html').read(), re.S)))"`
2. `curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8800/` → 200
3. Headless Edge screenshots at 1600×950 and 390×844 saved under `$LOCALAPPDATA/Temp/cc-v63-qa/`. Vision-check:
   - 1600: left rail has profiles + calendar only; no tab/panel list; corner cluster is a 2-row glass panel with status row + nav/filter row; FOCUS tag visible.
   - 390: corner cluster fits (may wrap); drawer opens with profiles + calendar; no tabs in rail.
4. Commit `v6.3: remove redundant rail tabs + enlarge corner panel` and push.

## Do NOT
- Do not remove the filters from the corner cluster — they move back above the calendar if removed.
- Do not touch orbit engine, brand palette, or v6.1/v6.2 responsive breakpoints.
- Do not touch `design-brief/` outputs.
