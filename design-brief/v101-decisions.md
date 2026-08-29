# v10.1 — click-focus discipline (2026-08-29, commit 61d8d2a on local main, NOT deployed)

Vincent's 5-point review of the glass-ball orbit (screenshots 043742 + 044023, QA ref 013823):

1. **Always-on straight lines (043742)** → were the legacy activity pulses: dots
   shot along straight edge segments across ALL edges even with nothing selected.
   FIXED: pulse emission block deleted entirely. At rest the ball is a pure dot
   cloud + clockwise drift. The ONLY edge animation is the animated dashed
   quadratic filament flow on the selected node's relations (comet heads also
   deleted — "too much animation, keep it simple with dashed lines").
2. **Edges pointing at ghost nodes (044023)** → related nodes now render at
   full alpha regardless of tab-filter and depth-fade (inFocus check in the
   node alpha chain, O(1) via focusEdgeNodes Set).
3. **Center of gravity on click** → selecting a node no longer pans the camera;
   it ROTATES the globe until the node faces front-center, then eases zoom.
   Ball freezes while selected (no auto-spin, no drag momentum); empty-space
   drag is inert until deselect (click again / empty space / Esc).
   Implementation: `v10FaceCamera(x,y,z)` solves ry=atan2(x,z) then rx=atan2(y,z1)
   (Y-then-X rotate order); target kept CONTINUOUS with current rotY/rotX via
   nearest-2π wrapping (raw atan2 flips ±π at the seam and the ease oscillated —
   probe-rot trace proved it); ease `k = 1-exp(-dt/550ms)` frame-rate independent;
   face recomputed LIVE each frame from the node's current layout position.
4. **Edge cap (ref 013823 calmer look)** → `MAX_FOCUS_EDGES = 30`; priority
   order: the picked node's own links first (agent-0 / agent-linked-1 / memory-2 /
   other-3). **Hold-deepdive lifts the cap** and reveals the full 2-hop web
   (edges woven through the 1-hop neighbourhood). Holding an ALREADY-SELECTED
   node deepens instead of toggling off (v10.1.4).
5. **Deploy HOLD** — Vincent: nothing goes to the live Atrium prod until he
   declares the product ~98% finished. NO deploy this cycle.

## QA evidence (all run on the VPS, not the dev box)

- Harness now lives on the VPS: `~/cc-qa/` (playwright + chromium-headless-shell,
  deps installed via sudo apt). QA server = throwaway container `cc-qa-v101`
  (python:3.11-slim, port 127.0.0.1:8899 inside the VPS, serving the staged
  index.html + prod cc_server.py/agents.js mounts). PROD 8800 untouched.
- `node v101-qa.js` gates, all passing:
  rest focusEdges=0 & rotTarget=false; spin drift active at rest;
  after click: SELECTED_ROT_DELTA≈0.0004 (frozen), rotResidual→~0 (converged
  front-center, offCenterPx residual ≈ zoom-lerp), zoom settles ~1.3;
  deselect → rotTarget released, drift resumes; 404s were QA-container
  asset-path artifacts (portraits relative to prod path), not app errors.
- CAP probe (synthetic 101-edge injection): click reveals 30, deep reveals 101.
- Vision QA screenshots: `~/atrium/cc-qa/shots/s1-click.png` (Amara front-center,
  halo, 1 real dashed filament to Thabo's node which is LIT), release shot = clean
  unlinked-globe. FPS low (~2) in headless-shell on 4 vCPU = software raster
  ceiling (~30ms full-canvas raster measured) — real browsers render 60fps;
  the 32-node VPS prod graph isn't the 1300-node local dev case.
- Probe scripts in `~/cc-qa/` (probe-rot2, probe-anim, probe-cap2, probe-vis,
  probe-full) — reusable for the next orbit change.

## Pitfalls hit (for the next session)

- Local headless-Edge on the dev box is DEAD for this app now (Bitdefender
  kills --headless=new spawns, exit 21 silently). All QA must run on the VPS.
- Vincent directive (2026-08-29): the Windows box is a CONDUIT — all files,
  installs, deps for Atrium live on the VPS; full context must survive there.
  Hence QA harness + session notes on the VPS, not local Temp.
- Playwright headless-shell needs libnspr4/libnss3/libgbm1/... (sudo apt-get
  install list in this session; `ldd chrome-headless-shell | grep "not found"`
  to verify).
- Time-based easing mandatory: per-frame ease factors break at low fps.