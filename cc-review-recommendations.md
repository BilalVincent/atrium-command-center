# Atrium Command Center — Review & Recommendations
**Date:** 2026-08-18 · **Reviewer:** senior product/engineering consultant · **Scope:** `atrium-command-center` (live = cc.theatrium.tech) vs `design-brief/memory-orbit-visual-brief.md` + Abacus.AI toolset leverage.

Read-only review. All line numbers refer to the current files: `index.html` (1,892 lines), `cc_server.py` (942 lines), `dispatch.py` (161 lines).

---

## 1. Current-state assessment

### What exists today

**Frontend (`index.html`, single file)**
- Three-rail V.A.U.L.T. dark dashboard: left rail (vitals + sparklines, directives TOP 3, documents, 5 tabs, calendar), center canvas scene + chat dock, right inspector panel. Dark theme is an additive override block (`index.html:276-422`) — already ink/gold/cream.
- Custom 2D-canvas 3D projection engine: `rotate3()` / `project()` with `FOCAL = 560` (`index.html:782-791`), drag-rotate (`rotY += dx*0.005`, line 858), wheel zoom toward cursor (921-936), pinch zoom (939-973), hit-testing on clickable nodes only (`hitNode`, 870-881).
- Knowledge graph from real data: agents (ring radius 66), files (radius 150 + jitter), memory nodes on zone rings (`RADII = {index:225, wiki:265, raw:310, outputs:355, runs:400, ops:445}`, line 739).
- Orbit V2 (already deployed, per board): `/search` with dropdown + hover highlight + camera fly-to (`renderSearchResults`, 1844-1874), readable-node gating (`isReadableNode`, 793-801), Memory Brief panel (`populateBrief`, 1717-1746), robotic click SFX (`playClick`, 804-818), cinematic default zoom 0.45 (line 771), non-readable nodes dimmed to 0.22-0.35 alpha (line 1122-1124).
- Live-feel systems: edge pulses every 0.34 s traveling edges at `pu.t += 0.05`/frame (1048-1070), hot-file detection (`markHot`, 710-714), activity decay glow (`n.activity`, 1111), name flashes on select (1097-1108), 220-particle starfield (780, 994-1000), auto-rotate `rotY += 0.00025`/frame (980).
- Full app chrome: agent chat via relay proxy + TTS with browser fallback (1299-1351), task delegation modal with async polling (1467-1518), metrics dashboard with sparkline (1403-1465), ghost guide modal, auth gate.

**Backend (`cc_server.py`, stdlib-only)**
- Real data only: `scan_files()` (163-198) with secret-filename filtering (178), `parse_agents()` from `agents.js` (111-161), vault memory layer `build_memory()` with 60 s cache (416-496), wikilink edge extraction from `index.md`/wiki files (464-480), directives from `ops/directives.md` (498-513), relay probes (531-550).
- Vector search: `search_vault()` (338-387) — Ollama `qwen3-embedding:0.6b`, disk cache keyed by path+mtime at `~/.atrium/embeddings.json` (249-264), Python cosine, top-5, keyword fallback (323-336). Solid, honest engineering.
- Auth: `CC_TOKEN` PIN → HMAC session cookie (64-91); random token generated if unset — never open by default. Good.
- `dispatch.py`: persona→worker routing with per-worker craft bars and serialized Hermes spawns. Clean.

### What's genuinely strong
1. **The data is real.** No mock anything — nodes, edges, vitals, pulses all derive from disk/relay state. This is the hardest part and it's done.
2. **The projection/camera engine is already 80 % of the brief's needs.** `project()` already samples circles into perspective ellipses (see `drawFloor`, 1528-1560) — the exact technique the brief's rings need.
3. **Search → camera fly-to → brief panel** is a complete, demo-able loop that most "AI OS" mockups never reach.
4. **Performance discipline**: sprite caches (`nodeSprite`/`glowSprite`, 822-837), 60 s server caches, DPR cap of 2 (761).

### What's weak (thesis-level)
The scene currently reads as **"TRON floor with a network graph floating above it"**, not **"planet seen from a passing spaceship"**. Three structural reasons:
- The hub is a faint 46 px glow dot with a label under it (`index.html:1011-1015`) — there is **no planet**. The brief's entire emotional payload (approaches A + B) is absent.
- `drawFloor()` (1528-1560) draws a perspective grid floor with 18 spokes and 10 concentric rings at `fy = 165`. A floor plane says "I'm standing in a room", which directly contradicts the flyby fantasy and visually competes with the zone rings.
- Zone rings are **node-connecting dashed polygons** (`drawZoneRings`, 1561-1576), not concentric orbital rings — with fewer than 3 nodes in a zone the ring vanishes entirely (line 1565), so the "Saturn" read collapses exactly when the vault is young (i.e., in early demos).

---

## 2. Brief gap analysis (A–E vs current code)

### A. Saturn flyby framing — ❌ NOT IMPLEMENTED
| Brief | Current code | Gap |
|---|---|---|
| Planet lower-right third, ~40 % of viewport height | Hub centered: `cx = W/2; cy = H*0.52` (`index.html:766`) | No off-center composition |
| Camera ≈ 35° above ring plane | `rotX = 0.55` rad ≈ 31.5° (line 769) | ✅ Close — keep |
| Perspective foreshortens outer rings | `FOCAL = 560` does foreshorten | ✅ Works |
| Planet ~80 px radius at default zoom | 46 px corona glow, no disc | No planet body |

### B. Atmospheric rim glow — ❌ NOT IMPLEMENTED
- No planet disc, so no limb/terminator. The `cor` gradient (991-993) and hub gradient (1011-1013) are centered glows, not a lit sphere: no light direction (brief wants off-canvas upper-right), no Fresnel rim, no 1.6× atmospheric halo ellipse behind the planet.

### C. Holographic data rings — ⚠️ PARTIAL
| Brief | Current code | Gap |
|---|---|---|
| Fixed radii `120,160,210,270,340,420` px @1080p | `RADII` 225-445 world units (line 739) | Radii exist but in world space; no `min(W,H)` scaling |
| Base `rgba(176,139,87,0.15)` + core `rgba(246,235,208,0.45)` double stroke | Single dashed stroke, full zone color, alpha 0.18, `setLineDash([6,6])` (1567) | Wrong color model (zone color at full saturation instead of 15 % tint over gold), wrong dash pattern (brief: 4 px dash / 12 px gap drifting 2 px/s) |
| Rings always visible as data lanes | Rings only drawn if zone has ≥ 3 nodes (1565); ring is a polygon through node positions | Ring disappears on sparse zones; polygon wobbles with node placement instead of being a clean circle |
| 1 px animated dash drift | Static dash | No drift animation |

### D. Gold-dust node halos — ⚠️ PARTIAL
- Sprite gradient is cream → zone color → **`#5A4A2E` opaque** (`nodeSprite`, 827). Brief wants transparent outer falloff (cream 0.9 → gold 0.5 → transparent 0) — current nodes read as solid billiard balls, not dust.
- Bloom exists (`glowSprite`, 831-837, drawn at 2.6×+activity) but with default `source-over` composite; brief specifies `globalCompositeOperation = 'screen'`.
- Hot nodes: only get a label + brighter edges (1034-1035, 1084). **No 1.5× scale, no 3 s breathing pulse** (brief: scale 1.0→1.25→1.0 over 3 s, bloom +50 %). `hotFiles` set already exists (710-714) — the data is there, the animation isn't.
- Sizes: memory nodes 9.5-11 px radius at zoom 1 (line 1119) vs brief 2-5 px. At the deployed 0.45 default zoom they render ~4-5 px — acceptable, but agent nodes at 13 px are chunky relative to the brief's "small golden spheres".

### E. Passing-spaceship camera drift — ⚠️ PARTIAL
- Rotation exists but is **~2.9× too fast**: `rotY += 0.00025`/frame (line 980) = 0.015 rad/s ≈ **0.86°/s** at 60 fps. Brief: 0.3°/s → should be `0.000087`/frame.
- **No ±10 px sine drift at all.** No 24 s loop. The scene rotates but never *drifts* — the "passing ship" parallax is missing.
- Drag override exists and is correct (`autoRot=false` on pointerdown, resume after 2.5 s, 844/867). Keep.

### Premium touches (brief §4) — scorecard
| Touch | Status | Note |
|---|---|---|
| 1. Vignette | ⚠️ Weak | CSS radial bg on `.scene-wrap` (line 340) + canvas bg glow (987-989) give a soft center-weighting, but no true edge vignette at 0.25 opacity |
| 2. Lens flares | ❌ | None |
| 3. Ring occlusion by planet | ❌ | No planet → no occlusion. Nodes are z-sorted (1073) but rings draw as full polygons |
| 4. Edge traffic pulses | ✅ | Exists (1048-1070), already gold/cream tinted |
| 5. Hover focus (brighten 30 % / dim 25 %) | ⚠️ | Dim/brighten exists for **selected** node neighborhoods (`focusSet`, 911-916); **hover** only changes halo stroke (1128-1133) — no ring-plane spotlight, no non-hover dimming |
| 6. No harsh UI chrome on canvas | ⚠️ | Legend (414-416), primary directive strip (406-412), HUD tags, search box, zoom-out, brief panel — 6 chrome elements sit on the canvas. The brief wants the planet to be the only interface. The primary strip (bottom-center) and legend (bottom-left) are the worst offenders against the "window" illusion |

### Accessibility / fallback — ❌ NOT IMPLEMENTED
No `prefers-reduced-motion` handling anywhere in the file; no low-power mode; starfield redraws every frame on the main canvas instead of an offscreen layer (brief §4).

### Palette drift — ⚠️ MINOR
- CSS `--gold:#B08D57` (line 10) vs brief `#B08B57`; CSS `--cream:#F6F3ED` (line 13) vs brief `#F6EBD0`. The canvas node sprite already uses the brief's `#F6EBD0` (827), so UI panels and canvas are subtly two different creams.
- Zone colors (`ZONE_COLORS`, 1523) match `cc_server.py:233-239` — good — but rings use them at full saturation instead of the brief's 15 % tint over the gold base.

---

## 3. Top 10 prioritized recommendations (demo impact ranked)

> Impact = how much it closes the "luxury spaceship window" gap in a live demo. Effort estimates assume the current single-file architecture.

### 1. Build the planet (approach B) — the single biggest gap
Replace the hub block (`index.html:1011-1015`) with a real planet disc, drawn **after** back-side rings and **before** front-side rings:
- Body: radial gradient disc, light offset toward upper-right: `createRadialGradient(cx+R*0.35, cy-R*0.4, R*0.1, cx, cy, R)` with stops `#3A3530` → `#2A2620` → `#1A1815`, `R ≈ 80 * cam.zoom`-aware px (brief §Planet).
- Fresnel rim: stroke an arc on the lit limb (roughly the upper-right 200° of the circumference) with `rgba(246,235,208,0.45)`, lineWidth 2-3, plus a second pass at 6 px / 0.15 alpha for softness.
- Atmosphere halo: blurred ellipse behind the disc at 1.6× radius, `rgba(217,185,120,0.12)` — reuse `glowSprite` drawn at 3.2× planet radius, alpha 0.35, `globalCompositeOperation='screen'`.
- Label: keep `A.I.O.S.` but place it **on** the planet's dark side (e.g. `cx, cy + R*0.15`), 10 px, cream, `letter-spacing` simulated by spacing the string `A . I . O . S .` — brief explicitly wants no glow on the label.
**Effort:** ~2 h · **Impact:** ★★★★★ — this IS the brief.

### 2. Saturn framing: move the hub to the lower-right third
In `resize()` (759-766): `cx = W * 0.63; cy = H * 0.64;` and scale the world to viewport: add `const SC = Math.min(W,H)/1000;` and multiply `RADII` (739) and `FOCAL` (789) by `SC` so the ops ring (445) doesn't clip at smaller sizes. Brief: planet ≈ 40 % of viewport height → planet radius `R = H * 0.20 / cam.zoom` world-side, or simply `R = min(W,H) * 0.075` screen-side. The upper-left negative space then naturally holds the search box + HUD tags without fighting the hero.
**Effort:** ~1 h (mostly testing clip/edge cases at 0.22-3.0 zoom) · **Impact:** ★★★★★ — instant cinematic composition.

### 3. True concentric zone rings (approach C)
Rewrite `drawZoneRings` (1561-1576) to draw **fixed circles through the projector** (the exact sampling loop `drawFloor` already uses at 1546-1552):
- For each of the 6 radii in `RADII`: 64-segment sampled circle at `y=0` (not `fy=165` — kill the floor plane association), two strokes: base `rgba(176,139,87,0.15)` lineWidth 2.5, core `rgba(246,235,208,0.35)` lineWidth 1, then zone color at **15 % alpha** as a third hairline for identity.
- Remove the `arr.length < 3` early-return (1565) — rings are chrome of the *system*, not of the data; a young vault must still look like Saturn.
- Dash drift: `ctx.setLineDash([4,12]); ctx.lineDashOffset = -(t*2) % 16;` on the base stroke (brief: 4 px dash / 12 px gap @ 2 px/s). Gate behind the perf flag (rec 10).
**Effort:** ~1.5 h · **Impact:** ★★★★☆

### 4. Ring occlusion depth cue (premium touch #3)
Once the planet exists (rec 1), split each ring's 64-point polyline at the planet's screen-space angular span: draw the far arc first at 50 % alpha + desaturated (brief: dim to 50 %), then the planet, then the near arc at full brightness. Implementation: compute each sample point's `z` from `worldPos`-equivalent rotation; points with `z > planetZ` and inside the planet's screen disc radius go in the "back" list. This is the cue that makes the brain read "sphere", not "circle with dots".
**Effort:** ~2 h · **Impact:** ★★★★☆ — small code, huge perceptual payoff.

### 5. Slow the rotation to spec + add the 24 s sine drift (approach E)
- Line 980: `rotY += 0.00025` → `rotY += 0.000087` (0.3°/s at 60 fps).
- Add in `frame()` after camera easing (line 983): `const drift = Math.sin(t * (Math.PI*2/24)) * 10; const driftY = Math.cos(t * (Math.PI*2/24)) * 6;` then offset all projections by `(drift, driftY)` — cheapest correct way: add to `cam.tx/cam.ty` *targets only when `autoRot` is true and nothing is selected*, so drag/select still override cleanly (drag already sets `autoRot=false`, 844).
**Effort:** ~30 min · **Impact:** ★★★★☆ — motion is what sells "ship" in a 5-second demo glance.

### 6. Gold-dust nodes + hot-node breathing (approach D)
- `nodeSprite` (822-830): change outer stop from opaque `#5A4A2E` to transparent: stops `(0, rgba(246,235,208,0.9))`, `(0.5, color@0.5)`, `(1, color@0)`.
- Draw the sprite pass with `ctx.globalCompositeOperation='screen'` for readable/agent nodes only (reset after — brief warns against bloom washing UI).
- Hot nodes: in `drawNode` (1115), if `hotFiles.has(n.id)` or memory `mtime < 24 h`: `rad *= 1.5 * (1 + 0.125*Math.sin(t*(Math.PI*2/3)))` (3 s cycle, 1.0→1.25→1.0) and glow alpha +50 %. `t` is already available in `frame()` — pass it into `drawNode`.
**Effort:** ~1 h · **Impact:** ★★★★☆ — turns "dots" into "living data".

### 7. Retire (or demote) the perspective floor grid
`drawFloor` (1528-1560) fights the thesis: a floor says "room", not "space". Options in order of preference: **(a)** delete the call at line 1007 and keep the function for a future "tactical view" toggle; **(b)** drop spoke alpha 0.16→0.04 and ring alpha 0.10→0.03 so it reads as faint space-dust lanes. Replace its compositional job with 40-60 gold dust specks drifting at 0.2-0.5 px/s near the ring plane (brief §Starfield/Dust) — a second `dustParticles` array seeded like line 780 but constrained to |y| < 40 world units.
**Effort:** 15-30 min · **Impact:** ★★★★☆ — removes the single biggest thesis conflict.

### 8. Vignette + lens flare (premium touches #1-2)
- Vignette: draw last in `frame()`, before `requestAnimationFrame` (line 1113): `createRadialGradient(cx, cy, min(W,H)*0.45, cx, cy, max(W,H)*0.75)` from transparent to `rgba(10,8,6,0.25)`, fillRect full canvas. (Pure CSS alternative: `box-shadow: inset 0 0 180px rgba(10,8,6,.55)` on `.scene-wrap` — zero JS cost, but it also dims the HUD chips, which is actually fine/premium.)
- Lens flare: two static streaks upper-left — a 120×3 px rotated cream gradient bar at alpha 0.06 + a 24 px radial bloom at alpha 0.08, drawn right after the starfield (after line 1000). Keep ≤ 0.08 per the brief.
**Effort:** 30 min · **Impact:** ★★★☆☆ — cheap luxury.

### 9. Pull UI chrome off the canvas + palette token alignment
- Move the **legend** (line 529) into the left rail under Documents (it duplicates `zone-filters` there anyway, 507), and let the **primary directive strip** (534-544) collapse to a 36 px minibar that expands on hover. Keep only: search (top-center), HUD tags (top corners), zoom-out. The brief is explicit: the planet is the only interface in 3D space.
- Align tokens: `--gold:#B08B57`, `--cream:#F6EBD0` in both `:root` blocks (lines 10-13 and 280-283), so panels and canvas share one cream.
**Effort:** ~1 h · **Impact:** ★★★☆☆ — un-clutters the "window".

### 10. `prefers-reduced-motion` + perf/low-power mode + node cap
- `const REDUCED = matchMedia('(prefers-reduced-motion: reduce)').matches;` → skip drift (rec 5), dash drift (rec 3), hot pulse (rec 6); keep slow rotation only (brief §Accessibility).
- Low-power (`navigator.hardwareConcurrency <= 4` or saveData): star count 220→90, skip bloom sprite pass, skip dust.
- Cap visible node glow passes at ~80 at default zoom: nodes are already z-sorted (1073) — skip the `glowSprite` draw for nodes beyond the 80 nearest when `cam.zoom < 0.7`, keeping the flat sprite. This protects the demo on a weak laptop.
**Effort:** ~1 h · **Impact:** ★★★☆☆ — demo insurance + accessibility compliance the brief explicitly requests.

**Bug/hygiene items found en route (fix opportunistically):**
- `hitNode` (870-881) only tests clickable nodes — hovering a dimmed code/json node gives zero feedback, which reads as "broken". Add a non-interactive hover tooltip (name only) for non-clickable nodes.
- `cc_server.py:212-225` — `calendar_events()` hardcodes 2026-08-17/18 events; already stale today. Same for `CRON_JOBS` (201-209, "snapshot from 2026-08-16"). Both should read from a vault file (e.g. `ops/calendar.md`) like directives do — one stale date in a demo undermines the "live" claim.
- `cc_server.py:832-865` — `_open_file` on Linux serves **any** file under allowed dirs with no secret-name filter (the filter exists only in `scan_files`, line 178). `/open?path=.../.env` passes the prefix check. Add the same `(".env","payfast","auth","secret","token","credential","password")` blocklist before serving. Auth is a single shared PIN — this hole matters.

---

## 4. Abacus.AI integration roadmap (recommendation-only)

Grounded in: account snapshot (chatllm-teams project, 8 active deployments, 0 datasets/connectors), `route_llm_models.json` (verified model list below), and the prior report's verdicts (DB → Postgres/pgvector, payments → Stripe/PayFast, video → Higgsfield until RouteLLM video is documented).

**What RouteLLM actually exposes (from `route_llm_models.json`):**
- **Text:** claude-sonnet-5, claude-opus-5, claude-haiku-4-5-20251001, gpt-5.6-terra/sol/luna, gemini-3.6/3.5-flash (+lite), grok-4.6/4.5, Kimi-K3, DeepSeek-V4, Qwen3.8-max… OpenAI-compatible `/v1/chat/completions`.
- **Image (`model_type: image_generation`, 35 models):** gpt_image15, gpt_image2(+edit), flux2, flux2_pro, flux_kontext, nano_banana/pro/2/lite, ideogram, **ideogram_character** (consistent-character generation), recraft / **recraft_svg** (vector output), seedream 4.5/5, dalle, midjourney, hunyuan_image, magnific (upscaler).
- **Audio (`audio_generation`):** **elevenlabs**, hume, openai_tts, minimax_tts (Speech 2.8 HD), gemini-2.5-flash/pro TTS, vibevoice, seed_speech.
- **Video (`video_generation`, 32 models):** sora (Sora 2), veo31/lite, runway, luma_labs, kling_ai v1.6→v3 + motion control, minimax (Hailuo 2), seedance family, grok_imagine_video, wan 2.2/2.5/2.7, hunyuan, topaz (upscaler). **Docs still sparse per prior report.**
- **Embeddings:** ❌ none in the list — the Ollama `qwen3-embedding:0.6b` stack (`cc_server.py:245-284`) stays. Do not plan an Abacus migration for search.

### Phase 0 — Verify (this week, $0)
1. Confirm Basic vs Pro tier on the billing page (prior report: Pro = $20/user/mo, 30K credits; Basic = 20K, Studio limited to 3 conversations). Everything below that touches media assumes Pro-level credit headroom.
2. Move the API key out of `abacus-ai-eval/.env` into a server-side env var (`ABACUS_API_KEY`) on the VPS before anything calls it from `cc_server.py` — never ship it to the browser; all calls must be proxied exactly like `/chat` and `/tts` are today (`cc_server.py:711-736`).

### Phase 1 — Quick wins (1-2 days, low credit burn)
3. **Agent voices via RouteLLM TTS.** The `/tts` chain (`cc_server.py:726-736`) currently falls back to browser `speechSynthesis` (`index.html:1315-1321`). Insert Abacus `elevenlabs` (or `minimax_tts` for cost) as a fallback rung when the relay TTS is down — or as the primary if the relay's Google TTS voices are the weak link in agent demos. Each agent keeps a fixed voice ID for continuity. **Impact: high in live demos (voice = product); Effort: small (one more proxy function); Cost: per-character market rate, trivial at demo volume.**
4. **One-time generated scene assets.** Generate, once, with `flux2_pro` or `seedream5_pro`: (a) a subtle ink/gold nebula starfield backdrop (used as `.scene-wrap` CSS background under the canvas), (b) the auth-gate backdrop (currently flat `#17130d`, `index.html:427-437`), (c) an og:image/social card for cc.theatrium.tech. Static files in `assets/` — zero runtime cost, immediate premium lift. Optionally run hero assets through `magnific` for 2× crispness.
5. **Brief auto-summaries.** `populateBrief` (1717-1746) shows raw markdown previews. Add a server-side "TL;DR" generated by `gemini-3.5-flash-lite` ($0.0000003/token in per the rate card — essentially free) or `claude-haiku-4-5-20251001`, cached by path+mtime exactly like the embedding cache pattern (`cc_server.py:249-264`). The Memory Brief becomes an executive one-liner + preview. **Impact: high (the brief panel becomes demo-narratable); Effort: small; Cost: negligible.**

### Phase 2 — Product features (1-2 weeks)
6. **Memory-brief thumbnails ("postcards").** New `/thumb?path=` endpoint: on first request for a wiki/outputs node, generate a 512×512 ink/gold illustration from the doc's title+preview via `nano_banana` or `gemini-2.5-flash-image` (cheapest image-output models in the list), cache to disk keyed by path+mtime, serve in `#briefPanel` above the preview text. Nodes with thumbnails could render on the canvas as tiny image sprites at high zoom. **Impact: very high visual differentiation; Effort: medium (new endpoint + cache + panel UI); Cost: image models carry null token rates = market-rate per image — budget ~1-2 credits/image equivalent, cache aggressively.**
7. **Chat fallback brain.** When the relay 502s (`cc_server.py:897-898` returns 502 today), fall back to RouteLLM `claude-sonnet-5` with the agent's bio/personality as system prompt so the dashboard never says "relay unreachable" in front of a prospect. Keep the relay primary (souls live there).
8. **Avatar pipeline for new agents.** `ideogram_character` is purpose-built for consistent characters from a reference — when Vincent adds agent #8, generate the portrait in the existing style (reference: `assets/portraits/reception_avatar_512.png`) instead of commissioning/bespoke prompting each time. Also usable for customer-facing "cloned agent" avatars — a genuinely monetizable Atrium feature, aligned with the agency's core offer.

### Phase 3 — Marketing & optional infra (only if needed)
9. **Cinematic demo loops.** One 5-8 s `veo31_lite` or `kling_ai_v25` clip of the orbit concept (animate `design-brief/memory-orbit-concept-wide.png` image-to-video) for the landing page / sales deck. Validate the undocumented video endpoint with one tiny paid test first (prior report's explicit caution). Keep Higgsfield as the production video pipeline.
10. **Hosted read-only demo instance.** Abacus app hosting (`*.abacusai.app`, free tier 25K credits/mo) could serve a **sanitized, static-data** snapshot of the dashboard for prospects — no auth gate sharing, no live VPS exposure. Verdict from prior report stands: production stays on the VPS; this is purely a demo mirror.
11. **Explicit non-goals (do not revisit):** no Abacus DB/vector store (0 connectors/datasets, no pgvector — keep vault+Ollama, or Postgres/pgvector when scale demands); no Abacus billing (none exists — Stripe/PayFast/Multica); no embedding migration (none offered).

### Abacus risks
- **Credit burn:** image/video models are market-rate with `null` token rates in the model list — a runaway thumbnail loop could eat the monthly 20-30K credit pool. Mitigate with disk caches keyed by content hash and per-day caps in the proxy.
- **Undocumented video API:** model IDs exist in the list; the endpoint shape doesn't (per prior report). One cheap validation call before any commitment.
- **Tier gating:** SuperComputer/unrestricted Studio need Pro — confirm before promising any of Phase 1+.
- **Latency:** RouteLLM TTS in the live chat path adds a network hop vs the local relay; keep it as fallback, not primary, if latency shows in demos.
- **Key hygiene:** the key currently sits in a local `.env`; production use must go through the VPS env + server-side proxy with the existing `CC_TOKEN` auth gate in front (`cc_server.py:798` already guards `/search`, `/read`, `/chat` — new endpoints must join that list).

---

## 5. Risks & quick wins

### Quick wins (one focused afternoon, ~3 h total, no Abacus, no backend changes)
Do these first — they deliver ~70 % of the visual gap:
1. **Rec 7** — kill/demote `drawFloor` (15 min). Thesis conflict gone.
2. **Rec 5** — rotation to 0.3°/s + 24 s sine drift (30 min). Scene comes alive.
3. **Rec 8** — vignette + lens flare (30 min). Instant luxury.
4. **Rec 9** — legend into the rail, palette tokens aligned (45 min). Clean window.
5. **Rec 3** — fixed concentric rings with base+core strokes (1 h). Saturn appears.

### Demo-day checklist risks
- **Stale hardcoded data:** `CRON_JOBS` (cc_server.py:201) and `calendar_events` (212) are snapshots from 2026-08-16/17 — a prospect asking "is this live?" and seeing yesterday's meeting is a credibility hit. Move to vault files this week.
- **Secret-serving hole:** `/open` on Linux lacks the secret-name filter (see §3 bug list). Fix before any external demo login is shared.
- **Sparse-vault collapse:** with < 3 nodes in a zone, that zone's ring disappears (index.html:1565). Rec 3 fixes it; until then, a fresh client vault looks broken rather than young.
- **Perf on weak hardware:** 220 starfield rects + full-screen gradients + ~700 edge strokes every frame on the main canvas. Rec 10's caps are the insurance policy; test once on integrated graphics before demoing on an unknown laptop.
- **Single-file frontend:** at 117 KB and growing, every visual change above touches the same 400-line render section. Consider splitting the scene engine into `scene.js` served from `assets/` after this round — not urgent, but the fifth person-hour of merge conflicts will cost more than the split.

### Strategic note
The brief and the codebase are closer than they look: the projection engine, the zone radii, the pulse system, and the palette are all already in place. What separates the current build from the brief is **one rendered sphere, three compositing tricks (occlusion, screen-bloom, vignette), and two motion curves (0.3°/s + 24 s drift)**. That is roughly two focused days of canvas work — after which the Command Center genuinely matches the "planet seen from a passing spaceship" promise, and every Abacus media investment (Phase 1+) lands on a surface that deserves it.
