# BUILD SPEC v6.9 — B-02 COMMAND PALETTE (council synthesis, chairman-approved)

You are the BUILD agent. Everything below is TRUSTED — anchors were verified by the chairman
2026-08-23 dawn. Do NOT spend reads re-verifying them. Budget: ~12 tool calls, WRITE-FIRST order:
CSS edit -> DOM edit -> JS edit -> syntax check -> COMMIT EARLY -> then verify/QA -> report.
Do NOT push, do NOT deploy — shipping stays with the chairman.

## Repo
`~/atrium-command-center` (= C:/Users/VincentMamashela/atrium-command-center), branch main,
HEAD 0d50059 (v6.8). Edit ONLY index.html. Commit message exactly:
`v6.9: B-02 command palette (Cmd/Ctrl+K) - keyboard jump over live /search`

## Trusted anchors (index.html, 2868 lines)
- `<style>` ends at line 765 (`</style>`). Append your labeled CSS block JUST BEFORE that line.
- Main script block runs L1107-2866 (`</script>` at 2866). Append your JS IIFE at its tail
  (after the `fetchState(); setInterval(fetchState, 8000); requestAnimationFrame(frame);` lines).
- DOM overlay: insert just before `</body>` (last line 2868).
- Existing globals you may close over: `$`, `esc`, `toast`, `selectNode`, `nodeMap`, `nodes`,
  `highlightId`, `window.showGate`. Existing Esc bubble handler at L1547 deselects nodes — your
  capture handler must shield it while the palette is open (see below).
- Do NOT modify `runOrbitSearch`, `renderSearchResults`, `#searchDropdown`, chat-bar handlers
  (L1013/L1020/L2109), or ANY settled markup/CSS. Purely additive.

## 1. CSS — one labeled block `/* v6.9: B-02 COMMAND PALETTE */` before `</style>`
- Overlay `#cmdkOverlay{position:fixed;inset:0;display:none;z-index:<LITERAL>` — FIRST run ONE grep
  for existing z-index values in index.html and set the literal ABOVE the observed max (do not guess).
- `.open` class shows it (`display:flex`) with a subtle fade/scale on the panel (transform .12s ease).
- Scrim: `background:rgba(42,38,32,.45)`; click on overlay (not panel) closes.
- Panel: glass recipe VERBATIM — `background:rgba(250,247,240,.055); backdrop-filter:blur(22px)
  saturate(150%); border:1px solid rgba(217,185,120,.22); border-radius:22px;
  box-shadow:0 18px 50px rgba(0,0,0,.42), inset 0 1px 0 rgba(255,255,255,.07)`.
- Palette literals pinned HEX ONLY (no var(--…) tokens): ink text `#2A2620` on light field is WRONG
  here — panel sits on dark scene: use cream/gold text scheme like other glass panels: text
  `#E9E4D8`, gold accents/borders `#B08D57`, active row background `rgba(176,141,87,.18)` with left
  border `3px solid #B08D57`, dim meta `rgba(233,228,216,.55)`.
- Panel geometry: `width:min(600px, calc(100vw - 32px)); margin:12vh auto auto; max-height:70vh;
  display:flex; flex-direction:column`.
- Results list: `overflow:auto`; rows padded 10px 14px; type badge uppercase 9px letterspaced gold;
  snippet 11px dim, single-line ellipsis. Active row styled per above.
- Input row: transparent input, `color:#E9E4D8`, font 15px, padding 14px 16px, bottom hairline
  `border-bottom:1px solid rgba(217,185,120,.18)`.
- Footer hints: 10px uppercase letterspaced dim gold: `↑↓ NAVIGATE · ↵ JUMP · ESC CLOSE`.

## 2. DOM — insert before `</body>`
```html
<div id="cmdkOverlay">
  <div id="cmdkPanel" role="dialog" aria-modal="true" aria-label="Search memory">
    <input id="cmdkInput" autocomplete="off" spellcheck="false" placeholder="Type to search memory…">
    <div id="cmdkStatus"></div>
    <div id="cmdkResults" role="listbox" aria-label="Results"></div>
    <div id="cmdkHints">↑↓ navigate · ↵ jump · esc close</div>
  </div>
</div>
```
(`#cmdkStatus` doubles as phase/error line; hidden when empty.)

## 3. JS — single IIFE at tail of main script block
Sentinel first line: `if(window.__cmdkBound) return; window.__cmdkBound=1;`

Keyboard: ONE `window.addEventListener('keydown', h, true)` CAPTURE handler.
- Ctrl OR Meta + 'k' (case-insensitive) → `e.preventDefault(); toggleCmdk();`
- Escape while open → `e.preventDefault(); e.stopPropagation(); closeCmdk();` (capture-phase
  stopPropagation prevents the L1547 bubble handler from firing → selection preserved).
  While closed → return untouched (L1547 behavior byte-identical).
- ArrowDown/ArrowUp while open → move active index with wrap; `e.preventDefault()`.
- Enter while open → activate active row; `e.preventDefault()`.
- Tab while open → `e.preventDefault()` (single-input model).
- Guard EVERY branch with `if(e.isComposing || e.keyCode===229) return;` before acting.

Open/close: save `document.activeElement` → overlay.classList.add('open') → focus input (and
`input.select()` if it has text). Close: remove class, clear input/results/status/index, restore
saved focus guarded `if(prev && prev.focus) prev.focus()`.

Search: own `cmdkTimer` (250ms debounce) + own `AbortController` (`cmdkAbort`) + MONOTONIC
`cmdkReqSeq` counter — discard any response whose seq < current (stale-response race).
- Empty query → results cleared, status cleared, fire nothing.
- Pending → status text `Searching memory…` (honest phase text, no bare spinner).
- Fetch `/search?q=` + encodeURIComponent, headers none; 401 → `window.showGate && window.showGate(); throw`
  same pattern as runOrbitSearch; non-auth failure → status `Couldn't reach memory right now.` +
  `console.warn(detail)`.
- Zero results → status `Nothing found for "<q>"` (esc()d).

Render rows (same contract as renderSearchResults): dot color = zoneColor(n.zone) for memory else
`#B08D57`; title esc(r.name); badge `(r.type||'memory').toUpperCase()`; zone uppercase; score
`Math.round((r.score||0)*100)%`; snippet slice 140 esc'd. Resolve `nodeMap[r.node_id] || nodes.find(x=>x.path===r.path)`
for interactivity. Hover syncs active index. Click = activate.

Activate: resolve node → mapped: `closeCmdk(); selectNode(n.id);` (close FIRST so camera glide is
visible); unmapped: keep palette open, `toast('Result is not on the current graph.')` + console.warn fields.

Poll-safety: all state in IIFE-closure locals; nothing re-renders palette except user actions;
no `#cmdk*` id may collide with any existing id (grep-audit uniqueness).

## 4. Hard rules
- NO discoverability chip / NO changes to orbit search box / NO mobile affordance (keyboard-only by
  design; chair decision this cycle). CSS width clamp must simply not break at 390px.
- Every `$()` you add targets ids you created in step 2 (statically present) — still use guards where
  natural. No `clamp(...)` helper exists in this file — inline Math.max/Math.min only.
- Literal hexes only; NEVER Quro navy #1A3561/coral #FF595A; no CDN/libs; no secrets.

## 5. Verify (after COMMIT)
1. Extract `<script>` blocks → temp .js → `node --check` all pass.
2. Grep-audit: `__cmdkBound|cmdk[A-Z]` identifiers defined once each; no duplicate ids `id="cmdk`.
3. Kill stale :880x listeners (netstat → taskkill), start FRESH port server
   `CC_NO_AUTH=1 CC_TOKEN=test1234 python cc_server.py 8812` (LOCAL PREVIEW ONLY), curl `/` → 200.
4. CDP headless Edge (isolated profile): open page, dispatch Ctrl+K keydown → overlay.open true +
   input focused; type `vault` → wait results>0; ArrowDown×2 → active row moves; Enter → palette
   closed AND a node selected (#hudFocus/#rightBody populated); reopen → Esc → closed AND selection
   unchanged; dispatch Escape again (closed) → deselectNode fires (selection cleared). Focus restore:
   focus #chatInput, open palette, close → document.activeElement === #chatInput.
5. Screenshots 1600×950 (palette open with results over scene) + 390×844 (opened state fits viewport,
   no horizontal scroll) → save under %LOCALAPPDATA%/Temp/cc-v69-qa/.
6. Leave palette open ≥25s across ≥3 poll ticks → results list unchanged (poll soak).
7. Report: what shipped, verification evidence (command outputs, screenshot paths), any deviations.

## 6. Out of scope (chairman handles)
git push, VPS scp + docker compose recreate, prod battery (Lane E), STATE/BACKLOG/runs updates,
Multica updates.
