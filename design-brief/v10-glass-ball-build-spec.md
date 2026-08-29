# v10.0 "Glass Ball" build spec — Command Center orbit rework (BUILD CHILD BRIEF)

You are completing a HALF-FINISHED build in `~/atrium-command-center/index.html`
(single-file app, ~3168 lines). The chairman already applied these edits (TRUSTED,
do not re-verify by reading whole file — only the surgical greps listed):

DONE (anchors verified on-disk):
- CSS block for v10.0 (legend roundel `.legend.lg-collapsed`, `.app.v10-rail-hidden`,
  `.scene-wrap{cursor:grab}`, `.v10-hold-flash`) inserted before `</style>` (was line 829).
- `computeLayout()` replaced with a Fibonacci-sphere globe (v10.0 comment block,
  line ~1290; sphere R = 170*pow(N/120,0.30); agents/files/memories/profiles on
  the sphere, skills/conversations/cron on an outer belt at R+90).
- Rotation state: `let rotY = 0, rotX = 0;` + `const AUTO_ROT = 0.00045;` +
  `let v10SpinVel = 0;` (v10.0 comment, ~line 1515).
- Pointer handlers rewritten: pointerdown captures `drag.hit` + 550ms hold timer
  (`v10HoldTimer` → `v10HoldFired`, calls `selectNodeDeep(hit)`); pointermove
  spins ball on empty-space drag (`rotY += dx*0.0042; rotX clamp ±1.1;
  v10SpinVel = dx*0.0042`), node-drag moves node on sphere (`v10NodeDrag`);
  pointerup clears hold, suppresses click if `v10HoldFired`.

YOUR JOB — the remaining edits, in WRITE-FIRST order. Budget ~12 tool calls.

## 1. frame() loop (function at ~line 1935 — grep "function frame")
a) After `const t = now/1000;` add:
   `rotY += AUTO_ROT + v10SpinVel; v10SpinVel *= 0.94;   // v10.0 clockwise auto-spin + drag momentum`
   (AUTO_ROT is positive; rotY increase = clockwise on screen with existing rotate3.)
b) EDGES: replace the entire edge-drawing block (from `// edges — v8.0 flat atlas`
   comment through `ctx.setLineDash([]);` after the edge for-loop) so that:
   - When NO node selected: edges are NOT drawn at all (skip loop entirely).
   - When selected: draw ONLY edges in focusSet (source or target === selected.id
     — but rendered between the two ENDPOINTS). Use a QUADRATIC CURVE:
     midpoint pushed perpendicular to the chord (bow ~12% of chord length,
     perpendicular in SCREEN space):
       `const mx=(pa.x+pb.x)/2 + (pb.y-pa.y)*0.12, my=(pa.y+pb.y)/2 - (pb.x-pa.x)*0.12;`
       `ctx.beginPath(); ctx.moveTo(pa.x,pa.y); ctx.quadraticCurveTo(mx,my,pb.x,pb.y); ctx.stroke();`
   - Keep the animated "blood flow": `ctx.setLineDash([7,5]); ctx.lineDashOffset = -((t*46)%24);`
     toward the selected node, + comet head gliding from far node into the
     selected one (keep the existing comet code shape, adapting hx/hy/ctrl to the
     curve: point at param u on quad Bezier = (1-u)^2*P0 + 2(1-u)u*Ctrl + u^2*P1).
   - Dashed gold, alpha ~0.7, width ~1.6; non-focus edges invisible (alpha 0.05
     at most — effectively skip).
c) NODE DEPTH SORT: replace the current `const order = nodes.slice().sort(...)`
   with sort by projected z DESCENDING (far first): use projMap[n.id].s or worldPos
   z — far nodes drawn first, near nodes last. Fade far-side nodes:
   `const behind = pr (s) is smaller` — multiply alpha by
   `depthMul = Math.max(0.25, Math.min(1, (pr.s - 0.55) / 0.45 + 1))` ONLY for
   non-agent nodes; agents keep full alpha. (Goal: back of the glass ball reads
   dimmer/blurred.)
d) TEAM RING: the dashed agent-ring polygon (lines with `team ring (agents form the center)`)
   — delete it (agents are on the sphere now; a flat ring through them looks wrong).

## 2. selectNodeDeep(id) — new function (place right after selectNode/deselectNode)
```js
/* v10.0 hold-to-deepdive: selection + expand focusSet to the full 2-hop
   relation neighbourhood so hold reveals MORE of the graph web. */
function selectNodeDeep(id){
  selectNode(id);
  if(selected.id !== id) return;
  const oneHop = new Set();
  G.edges.forEach(e=>{ if(e.source===id) oneHop.add(e.target); if(e.target===id) oneHop.add(e.source); });
  oneHop.add(id);
  G.edges.forEach(e=>{ if(oneHop.has(e.source) && oneHop.has(e.target)){ focusSet.add(e.source); focusSet.add(e.target); } });
}
```

## 3. selectNode() tweaks (function ~line 1730)
- KEEP existing zoom glide. But inside it, guard: it currently references
  `const s0 = 1;` — harmless, leave.
- Edge count `deg` line stays.

## 4. Legend collapse JS — in `renderLegend()` (grep "function renderLegend", ~line 2800)
- The zone divider already renders as inline style div; add class `lg-divider` to it
  (so `.lg-collapsed` hides it): replace
  `'<div style="height:1px;background:rgba(232,207,160,.18);margin:6px 0"></div>'`
  with `'<div class="lg-divider"></div>'` and add CSS rule in the v10 block:
  `.legend .lg-divider{height:1px;background:rgba(232,207,160,.18);margin:6px 0}` (already there).
- At END of renderLegend body add:
```js
  // v10.0: default collapsed to the "L" roundel; hover or click expands
  const lgEl = el;
  lgEl.classList.add('lg-collapsed');
  if(!lgEl.__v10bound){
    lgEl.__v10bound = true;
    lgEl.addEventListener('click', ()=> lgEl.classList.toggle('lg-collapsed'));
    lgEl.addEventListener('mouseenter', ()=> lgEl.classList.remove('lg-collapsed'));
    lgEl.addEventListener('mouseleave', (ev)=>{ if(!lgEl.contains(ev.relatedTarget)) lgEl.classList.add('lg-collapsed'); });
  }
```

## 5. Left rail collapse — brand mark toggle
- Markup (~line 873): `<span class="mark">Q</span>` →
  `<button class="mark" id="railToggle" aria-label="Toggle menu" title="Toggle menu">Q</button>`
  (button needs the existing .mark styles; add `border:2px solid var(--gold);background:var(--cream);font-family:inherit` is already covered by .mark rule — but button default styling: append to the v10 CSS block:
  `.brand button.mark{font-family:inherit}`)
- JS: near boot (grep `resize();` line ~1516 area or the `window.addEventListener('keydown'` line):
```js
/* v10.0: brand mark toggles the left rail (expand/collapse everything) */
(function(){
  const btn = document.getElementById('railToggle'); const app = document.querySelector('.app');
  if(!btn || !app) return;
  btn.addEventListener('click', ()=> app.classList.toggle('v10-rail-hidden'));
})();
```

## 6. Node size bump (~1.4x) in drawNode() (function ~line 2130, grep "function drawNode")
- agent rad 13 → 18; readable/file 9 → 13 base; memory 9.5/11 → 13/15; cron 9 → 13;
  file `rad = (readable?7:4.5)*s*fileClsScale()` → `(readable?10:6.5)*s*fileClsScale()`.

## 7. VERIFY (same call budget — combine commands with &&)
a) `cd ~/atrium-command-center && python -c "
import re
html=open('index.html',encoding='utf-8').read()
blocks=re.findall(r'<script>(.*?)</script>', html, re.S)
open('_check.js','w',encoding='utf-8').write('\n;\n'.join(blocks))
print('blocks', len(blocks))"
   then `node --check _check.js` (expect clean).
b) Start dev server on a FRESH port: kill stale listeners first
   `netstat -ano | grep ":8800.*LISTEN"` (use taskkill //F //PID <pid> in git-bash
   — note DOUBLE slashes in git-bash), then
   `CC_NO_AUTH=1 CC_TOKEN=test1234 python cc_server.py 8801` background.
c) Headless Edge screenshot with isolated profile:
   `"/c/Program Files (x86)/Microsoft/Edge/Application/msedge.exe" --headless=new --user-data-dir="$LOCALAPPDATA/Temp/edge-cc-v10" --no-first-run --window-size=1600,950 --timeout=15000 --screenshot="C:/Users/VincentMamashela/AppData/Local/Temp/cc-v10-qa.png" http://127.0.0.1:8801/`
   (msedge may also live at /c/Program Files/Microsoft/Edge/ — pick whichever exists).
d) Report: syntax-check result, screenshot path, any console errors you can see,
   and whether the globe (scattered spherical dot cloud, no edges) is plausible.
DO NOT commit, DO NOT push, DO NOT deploy — chairman handles git.

## Constraints (Vincent's standing rules)
- Atrium palette only: ink #2A2620 / gold #B08D57 / cream. NO Quro navy/coral.
- Additive CSS at END of style block; do not rewrite existing rules.
- Do NOT touch cc_server.py, do NOT touch other agents' dirty files.
  Working tree: `index.html` is THE file being modified; *.bak*/ files exist — ignore them.
- If an anchor doesn't grep exactly, adapt minimally and NOTE the adaptation in your report.