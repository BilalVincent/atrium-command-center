# B-02 COMMAND PALETTE (Cmd/Ctrl+K) — COUNCIL INPUT BRIEF

> You are one reviewer seat of the Atrium council (atrium-council skill). This file is your complete
> context — you know nothing else. Read it fully before answering. SENSITIVITY: INTERNAL.

## Task (roadmap item B-02, Vincent-approved)
Add a **command palette** (Cmd/Ctrl+K) to the Atrium Command Center on the EXISTING `/search`
backend: fuzzy vault/file/skill/conversation jump. No new backend endpoints unless strictly needed
(preference: none). Desktop shortcut; decide graceful behavior on touch/mobile.

## Product context
- Single-file frontend `index.html` (2868 lines) + dependency-free stdlib server `cc_server.py`.
  Repo PUBLIC. Deployed prod: https://cc.theatrium.tech behind PIN gate.
- Buyer persona: non-technical CEO / solo doctor. The CC renders a live knowledge graph (agents,
  memory vault nodes, conversations, skills, files) on canvas with glass-morphic chrome.
- The app ALREADY has an orbit search box in the topbar header (`#orbitSearchInput`, placeholder
  "Search memory…") with a dropdown (`#searchDropdown`) of results; clicking a result selects the
  node in the orbit (`selectNode(n.id)`), glides camera, opens its brief panel.

## TRUSTED ANCHORS (chairman pre-verified 2026-08-23 dawn — do NOT spend reads re-verifying)
- `<style>` block ends line 765 (`</style>`). Convention: version-labeled override blocks appended
  at END of style win ties by source order.
- Script blocks: L781-803 (auth gate, pre-body), L905-1027 (shrunk-bar), L1107-2866 (main script).
- Orbit search markup ~L814-819 inside `.topbar`: `#orbitSearch > input#orbitSearchInput +
  div.search-dropdown#searchDropdown`.
- Search JS (main block, ~L2781-2834):
  - `runOrbitSearch(q)` → fetch(`/search?q=…`) → `renderSearchResults(d.results)`; abort flag
    `searchAbort`; debounce timer `searchTimer` (250ms).
  - Result object fields: `{name, type(memory|conversation|skill|file|…), zone, score(0-1),
    snippet, node_id, path}`. Click handler resolves `nodeMap[r.node_id]` → `selectNode(id)`,
    closes dropdown, clears input; toast('Result is not on the current graph.') when unmapped.
  - Listeners: `input`(debounce), `keydown`(Escape closes), `blur`(closes after 200ms).
- Global Escape handler L1547: `window.addEventListener('keydown', e=>{ if(e.key==='Escape')
  deselectNode(); })` — palette Esc handling MUST compose with this (close palette first,
  deselect only if palette already closed — or equivalent decided behavior).
- Shrunk chat bar keydown handlers L1013/L1020 (Enter sends, stopPropagation already used there).
- Chat input keydown L2109. Poll loop: `fetchState()` every 8000ms — any shared-DOM renderer you
  add must be poll-safe (no auto-renderer may clobber user-owned UI; precedent v6.6.2/v6.6.4 fixes).
- Auth: fetches get 401 when session expires → pattern `if(r.status===401){ window.showGate &&
  window.showGate(); throw new Error('auth'); }`.

## Vincent's standing rules (HARD constraints)
- Real data only (reuse live /search). Never mock.
- Palette ink #2A2620 / gold #B08D57 / cream #F6EBD0 — pin LITERAL hex values, never shared theme
  tokens (token-drift incident v6.5.1). NEVER Quro navy/coral.
- No CDN, no external libs, single-file self-contained. Vanilla JS/CSS only.
- Mobile friendly mandatory (QA 390px). Touch has no Cmd key — define behavior (a visible affordance?
  nothing? reuse existing search box?) — ship the SMALLER delta.
- Spatial restraint: improve placement, don't invent structures. Settled placements are load-bearing;
  do NOT relocate the orbit search box, pills, corner cluster, or chat bar.
- Glow/glass reserved per approved recipes; glass recipe proven: bg rgba(250,247,240,.055),
  backdrop-filter blur(22px) saturate(150%), border 1px solid rgba(217,185,120,.22), radius 22px,
  shadow 0 18px 50px rgba(0,0,0,.42) + inset highlight.
- Honest phase text under spinners (no bare spinners). Buyer-language error copy; tech detail to console.
- Guard EVERY `$()` lookup you introduce near removed/optional DOM (`if(el)`), listener guards
  (v6.3.1 null-listener crash class).
- `node --check` catches syntax only, NOT undefined identifiers — grep-audit new identifiers.
- Commit convention `vN: ...`. Never commit secrets.

## Deliverable shape (answer ALL five, concise, concrete)
1. RECOMMENDED APPROACH — concrete DOM structure, CSS placement strategy (which block, what rules),
   JS wiring (event capture phase, focus management, selection model, how it reuses runOrbitSearch /
   renderSearchResults vs new render path), keyboard map.
2. WHY — reasoning tied to the standing rules + buyer persona.
3. RISKS — ranked top 5 with mitigations (think: focus traps, Esc composition with deselectNode,
   IME/input edge cases, z-index over briefPanel/dashboard modals, poll interference, mobile).
4. EFFORT — S/M/L with a call count estimate for a builder agent.
5. VERIFY PLAN — exact checks you'd run (syntax, serve, CDP interactions, screenshots at 1600x950
   AND 390x844, security battery if endpoints touched).

Length target: <=120 lines total answer. Be decisive; this becomes a build spec.
