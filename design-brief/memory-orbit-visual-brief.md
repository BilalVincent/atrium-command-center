# Atrium Command Center — Memory Orbit Visual Design Brief
## Theme: "Planet seen from a passing spaceship"

**Date:** 2026-08-18  
**Brand:** Atrium (AI head-hunt agency)  
**Hero feature:** 3D memory orbit on custom canvas  
**Primary palette:** Ink `#2A2620` · Gold `#B08B57` · Cream `#F6EBD0`

---

## 1. Visual thesis

The default Command Center view should feel like a luxury spaceship window looking out at a living planet. The planet is the **AI OS hub**. The concentric zone rings are the **memory layers** (raw, wiki, outputs, runs, ops, index). The glowing spheres traveling those rings are **memory nodes**. Everything is slow, vast, and expensive-looking — motion comes from camera drift and pulse traffic, not frantic spinning.

---

## 2. Five concrete design approaches

### A. The Saturn flyby (recommended default framing)
- **Framing:** Planet sits in the lower-right third of the canvas, occupying ~40 % of viewport height. Rings sweep diagonally from upper-left to lower-right.
- **Why it works:** Creates immediate cinematic scale; negative space in upper-left can hold UI panels without fighting the hero.
- **Implementation cue:** Camera angle ≈ 35° above the ring plane, looking across it. Perspective foreshortens the outer rings.

### B. Atmospheric rim glow
- **Lighting:** A soft light source (off-canvas upper-right) catches the planet limb with a warm cream-gold arc.
- **Atmosphere:** Add a thin Fresnel/limb glow shader around the planet sphere — brighter where the surface faces the light, fading to ink-black in shadow.
- **Implementation cue:** Use a radial gradient or simple dot-product falloff on the planet disc. Layer a blurred cream ellipse behind the planet for the atmospheric halo.

### C. Holographic data rings
- **Rings as UI, not geology:** Keep the rings thin, semi-transparent, and luminous rather than solid. Subtle dashed glyph texture or very faint scanlines can suggest data lanes.
- **Why it works:** Reinforces that this is a knowledge graph, not a screensaver.
- **Implementation cue:** Each ring drawn as two concentric strokes: a dim base (`rgba(176,139,87,0.15)`) and a brighter core (`rgba(246,235,208,0.45)`). Add a 1 px animated dash texture that drifts slowly along each ring.

### D. Gold-dust node halos
- **Nodes as living data:** Memory nodes rendered as small golden spheres with soft bloom/halos. Hot/recent nodes pulse brighter.
- **Why it works:** Provides focal points and reads as "activity" without noisy HUDs.
- **Implementation cue:** Draw each node as a radial gradient (cream center → gold mid → transparent outer) plus a screened glow using `globalCompositeOperation = 'screen'`. Size 2–5 px at default zoom; 1.5× scale for hot nodes.

### E. Passing-spaceship camera drift
- **Motion:** Ultra-slow camera parallax. The orbit gently rotates ~0.5–1°/sec, and the whole scene drifts ±10 px on a 20–30 s sine wave.
- **Why it works:** Sells the "view from a ship" fantasy. Slow enough that text and UI remain readable.
- **Implementation cue:** Apply a tiny continuous rotation to the projection matrix and an overlay transform for the drift. Keep mouse-drag override available.

---

## 3. Mood concepts

Two generated concept images are included in this folder for reference. They are mood pieces, not final UI.

| File | What it shows | Use |
|---|---|---|
| `memory-orbit-concept-wide.png` | Wide cinematic ringed planet, warm cream/gold rings, deep ink space, strong rim lighting. | Default framing and atmosphere reference. |
| `memory-orbit-concept-rings.png` | Closer view of glowing concentric rings around a dark sphere, small bright orbital nodes, passing-ship perspective. | Ring style, node halos, and node-on-ring placement reference. |

---

## 4. Frontend implementation spec

### Color swatches

| Token | Hex | RGBA | Usage |
|---|---|---|---|
| `--ink` | `#2A2620` | `rgba(42,38,32,1)` | Space background, planet shadow side, UI dark panels |
| `--gold` | `#B08B57` | `rgba(176,139,87,1)` | Ring cores, node mid-tones, accent lines, active pulses |
| `--cream` | `#F6EBD0` | `rgba(246,235,208,1)` | Ring highlights, node centers, rim glow, labels |
| `--gold-dim` | — | `rgba(176,139,87,0.18)` | Ring base strokes, faint particles |
| `--cream-dim` | — | `rgba(246,235,208,0.35)` | Atmospheric halo, hot-node bloom |
| `--star` | — | `rgba(246,235,208,0.6)` | Starfield points |

### Rings

- **Count:** 6 zone rings (raw, wiki, outputs, runs, ops, index) + optional 7th faint outer "index" halo.
- **Thickness:** 1.5–3 px at default zoom. Rings are hairlines, not bands.
- **Style:** Each ring = base stroke (`gold-dim`) + core stroke (`cream-dim` to `--cream` depending on ring) + soft outer glow (`screen` composite, 6–10 px blur, `rgba(176,139,87,0.15)`).
- **Spacing:** Radii roughly `120, 160, 210, 270, 340, 420` px for a 1920×1080 viewport. Scale with `min(W,H)`.
- **Zone tints:** Keep existing zone colors (`raw #C98A5E`, `wiki #CDA526`, etc.) as a 15 % tint on top of the gold/cream base so the planet stays cohesive but zones remain distinguishable on hover/focus.
- **Dash texture:** A very faint 4 px dash / 12 px gap pattern drifting along each ring at ~2 px/sec. Optional; disable on low-perf devices.

### Planet (AI OS hub)

- **Size:** ~80 px radius at default zoom (scales with viewport).
- **Body:** Solid `--ink` disc with a subtle radial gradient: slightly lighter (`#3A3530`) near the light source, darker (`#1A1815`) on the shadow side.
- **Atmosphere:** 1) Fresnel rim glow: cream ellipse clipped to planet edge, opacity 0.3–0.6. 2) Outer halo: blurred gold/cream ellipse behind the planet, 1.6× planet radius, opacity 0.12.
- **Label:** "A.I.O.S." or hub glyph sits on or near the planet, small (10 px), cream, letter-spacing 0.2 em, no glow (readability).

### Memory nodes

- **Count:** Proportional to real file count but capped visually at ~60–80 visible spheres at default zoom. Fade distant/smaller ones.
- **Default size:** 2–3 px radius (files), 4–5 px (agents/index nodes), 1.5× for "hot" recently-modified files.
- **Shape:** Soft radial gradient: center `#F6EBD0` (opacity 0.9), mid `#B08B57` (0.5), outer transparent (0). Add a `screen` bloom layer of 6–10 px radius at low opacity (0.15).
- **Hot nodes:** Gentle pulse: scale 1.0 → 1.25 → 1.0 over 3 s; bloom opacity +50 %.
- **Halos:** Only on hover/focus and on the 6–10 most active nodes by default, to avoid sparkle noise.

### Starfield / particles

- **Stars:** 150–250 tiny points across the background. Vary size 0.5–1.5 px, opacity 0.2–0.7, cream color. Static or very slow twinkle.
- **Dust:** 40–60 faint gold specks drifting at 0.2–0.5 px/sec, random directions, near the ring plane. Opacity 0.08–0.18.
- **Performance:** Render on a separate offscreen canvas if needed; only redraw when the camera moves.

### Camera & default view

- **Default camera:** Oblique 3/4 view, planet in lower-right third, rings tilting away to upper-left.
- **Field of view:** Mild perspective projection. Use a vanishing point slightly above center (`cy = H*0.45` initially) so rings recede naturally.
- **Zoom:** Default zoom level 1.0. Clicking a node eases to zoom 2.5–3.0 over 600 ms. Empty click / Esc eases back.
- **Drift:** Continuous scene rotation 0.3°/sec around the hub axis + 10 px horizontal/vertical drift on a 24 s loop. Mouse drag overrides drift and keeps the new angle.

### Animation speeds

| Element | Speed | Note |
|---|---|---|
| Scene rotation | 0.3°/sec | Almost imperceptible; prevents staleness |
| Ring dash drift | 2 px/sec | Suggests data flow without distraction |
| Node pulse (hot) | 3 s cycle | Scale + bloom breathe |
| Traffic pulses | 60–120 px/sec along edges | Fast energy against slow scene |
| Camera drift | 10 px / 24 s | Very slow parallax |
| Zoom transitions | 600 ms | Ease-out-cubic |

### Premium touches

1. **Vignette:** A soft radial vignette (ink-black, opacity 0.25 at edges) draws the eye to the planet and hides canvas edges.
2. **Lens reflections:** One or two subtle cream-gold flare streaks in the upper-left dark space (opposite the planet light). Keep opacity ≤ 0.08.
3. **Ring occlusions:** Rings behind the planet dim to 50 % opacity and desaturate; rings in front stay bright. This depth cue is critical for the "planet" read.
4. **Edge traffic:** Gold pulses travel between connected memory nodes along ring-plane paths. Use existing pulse system but tint with `--gold` and `--cream`.
5. **Hover focus:** On hover, the hovered ring/node brightens 30 %, non-hovered rings dim 25 %, and a faint cream spotlight sweeps the ring plane.
6. **No harsh UI chrome on the canvas:** Keep HUD panels outside the hero view; let the planet be the only "interface" in the 3D space.

### Accessibility / fallback

- Respect `prefers-reduced-motion`: disable drift, dash texture, and hot-node pulse; keep slow rotation only.
- Low-power mode: hide dust, reduce star count by 60 %, disable bloom.

---

## 5. What not to do

- Do not fill the rings with solid opaque color — they should read as luminous energy, not Saturn's ice rings.
- Do not place a literal spaceship model in the scene. The "passing spaceship" is the camera mood, not an asset.
- Do not use Vincent's Quro navy/coral palette here; this is Atrium-branded (ink/gold/cream).
- Avoid heavy bloom that makes text unreadable. Bloom lives on the rings and nodes, not across UI panels.

---

## 6. Deliverables in this folder

- `memory-orbit-visual-brief.md` — this document
- `memory-orbit-concept-wide.png` — wide cinematic mood concept
- `memory-orbit-concept-rings.png` — ring/node detail mood concept
