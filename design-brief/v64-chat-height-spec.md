# Atrium OS — v6.4: Increase Chat Height

**Author:** Solari1 · **Date:** 2026-08-21
**File:** `~/atrium-command-center/index.html`
**Commit message:** `v6.4: increase chat height`

## Context
Vincent clarified: the chat panel in the right rail is too **short** — only ~2 chat bubbles are visible at once. The issue is **vertical height**, not width. The chat body feels cramped because the header/profile area and fixed elements eat too much vertical space.

## Required changes

### A. Chat body must fill available height
- Locate the right-rail chat layout (likely inside `.right` or `#rightBody` when a chat is active).
- Ensure the chat body element (`#chatBody` or equivalent) uses `flex:1 1 auto; min-height:0; overflow-y:auto` so it expands to fill all leftover vertical space in the right rail.
- Ensure `.right` container uses `display:flex; flex-direction:column; height:100%` (or grid row `1fr`) so the body can grow.

### B. Reduce vertical footprint of the chat header
- When the right rail is in chat mode, the agent profile hero card should collapse to a compact header:
  - Keep only avatar + name + role on one line.
  - Hide or collapse the rate pill, skill tags, and KPI grid when the chat panel is active.
  - Compact header height target: ~60-70px instead of the current tall hero card.
- Add a smooth transition/animation if desired, but keep it simple.

### C. Reduce padding/gaps in chat body and input
- Decrease message bubble vertical margins to fit more bubbles:
  - `.cmsg{margin:3px 0}` (or current equivalent) tighten to `2px 0`.
- Reduce chat body internal padding:
  - Chat body padding from e.g. `14px` to `10px`.
- Keep input area at the bottom fixed height, not growing.

### D. Ensure chat history is scrollable
- The body must remain `overflow-y:auto` so longer conversations scroll.
- Autoscroll to bottom on new message if already near the bottom.

### E. Desktop right-rail height
- The right rail already spans full app height (`height:100dvh - topbar`). Do not change overall width.
- If the chat body still feels short because the right rail itself is shorter than the viewport, check for any `max-height` or `height:auto` on `.right` and override with `height:100%`.

### F. Mobile unchanged
- Mobile chat already uses a full-screen modal (v6.1). No changes needed there.

## Do NOT
- Do not change the right-rail width (Vincent clarified width is fine).
- Do not remove the right rail or chat input.
- Do not touch orbit engine, v6.1/v6.2/v6.3 responsive breakpoints, brand palette.
- Do not touch design-brief outputs.

## Verification (before commit)
1. `python -c "import re; open('_check.js','w').write(chr(10).join(re.findall(r'<script>(.*?)</script>', open('index.html').read(), re.S)))"`
2. `curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8800/` → 200
3. Headless Edge screenshot at 1600×950 with the right-rail chat open (select an agent or click the chat path) saved under `$LOCALAPPDATA/Temp/cc-v64-qa/`. Vision-check: at least 5-6 chat bubbles should be visible vertically, header is compact, input at bottom, no overlap.
4. Commit `v6.4: increase chat height` and push.
