# Atrium OS — Glass-Morphic Design Brief (Coder-Ready)
**Date:** 2026-08-21 · **Brand:** Atrium (AI head-hunt agency) · **Never** Quro navy/coral
**Palette:** Ink `#2A2620` · Gold `#B08D57` · Cream `#F6EBD0` · OS bg near-black `#0C0B08`

---

## 1. The glass recipe (copy-paste CSS)

```css
:root {
  --glass:          rgba(250,247,240,.055);
  --glass-strong:   rgba(250,247,240,.09);
  --glass-border:   rgba(217,185,120,.22);
  --glass-border-strong: rgba(217,185,120,.38);
  --gold:           #B08D57; --gold-bright: #D9B978; --gold-pale: #E7DAC2;
  --cream:          #F6F3ED; --ink: #2A2620; --ink-2: #1E1B16;
}
.glass {
  background: var(--glass);
  backdrop-filter: blur(22px) saturate(150%);
  -webkit-backdrop-filter: blur(22px) saturate(150%);
  border: 1px solid var(--glass-border);
  border-radius: 22px;                 /* pills: 999px, small chips: 14px */
  box-shadow: 0 18px 50px rgba(0,0,0,.42), inset 0 1px 0 rgba(255,255,255,.07);
  color: var(--cream);
  transition: opacity .35s ease, transform .35s ease, box-shadow .3s ease;
}
.glass:hover { border-color: var(--glass-border-strong);
  box-shadow: 0 22px 60px rgba(0,0,0,.5), inset 0 1px 0 rgba(255,255,255,.1); }
```
- **Header style:** 10.5px, weight 700, letter-spacing `.16em`, uppercase, color `--gold-bright`.
- **Body text:** 11–12px cream at ~.5–.6 opacity; hairline dividers `rgba(217,185,120,.10)`.
- **OS background:** `radial-gradient(120% 90% at 50% 42%, #1B1824 0%, #131019 55%, #0B0A10 100%)` (or flat `#0C0B08`); nebula washes `rgba(176,141,87,.075)` / `rgba(217,185,120,.04)` at low opacity. Orbit in center: 6 gold/cream concentric rings, 1.5–3px, base stroke `rgba(176,139,87,.15)` + core `rgba(246,235,208,.45)`, golden node halos.
- **Apply glass to:** ALL side widgets (calendar, filters, directives, documents, profiles) AND all center popups (Memory Brief, search, ghost modal, file viewer). Float with `position:fixed` + z-index ≥ 20; modal over orbit = z 30, `top:50%;left:50%;translate(-50%,-50%)`.

## 2. Layout positions (1920×1080 reference)

| Region | Content | Position |
|---|---|---|
| **Top-right corner cluster** | Pill row (Agents ◉ · Chats 💬 · Cron ⏱ · Files 📁 · Memory 🧠) + filter chips + clock | `top:26px; right:30px` — pills in a row (radius 999px), filters + clock in a compact glass group below/inline |
| **Left rail (vertical stack, top→bottom)** | 1. Agent profiles (circular headshots in glass avatar frames, vertical list) → 2. Directives (small cards) → 3. Documents (thumbnail stack) → 4. Calendar (mini month grid) | `top:88px; left:30px; width:290px`, sections separated by hairline `rgba(217,185,120,.10)` dividers |
| **Right rail** | Pulse/activity feed, filter controls | `top:88px; right:30px; width:250px` |
| **Center (above orbit)** | Glass modal: Memory Brief / search / ghost modal / file viewer; slim search pill inside top-left of modal | centered, `width:~560px`, radius 22px |
| **Bottom** | Task pill (left), vault dock pill (center, radius 999px), voice orb (right, 52px circle, `--glass-strong`) | `bottom:30px` |

## 3. Filter-pill icon mapping (top-right cluster)

| Pill | Icon | Active state |
|---|---|---|
| Agents | ◉ | border `--glass-border-strong`, label `--gold-bright` |
| Chats | 💬 | same |
| Cron | ⏱ | same |
| Files | 📁 | same |
| Memory | 🧠 | same |

Inactive: dimmed (opacity .45). Active pill keeps glass bg + bright gold border + cream label. Clicking a pill filters the orbit nodes; multiple pills may be active.

## 4. Concept images (mood references, not final UI)

| File | What it shows | Use |
|---|---|---|
| `glass-os-side-widgets.png` | Full OS: dark command center, gold 3D orbit center, frosted glass side panels, top-right glass cluster with pills + clock (4.5/5 match) | Overall composition, corner cluster, side widgets |
| `glass-left-rail-profiles.png` | Vertical frosted glass rail: 4 circular executive headshots, stacked cards w/ gold connector lines (5/5) | Left-rail avatar list + card stacking |
| `glass-center-modal-orbit.png` | Large frosted glass modal floating over glowing gold orbit, search pill, doc cards (5/5) | Center modal over 3D orbit, search pill |

*Note: AI mood pieces — treat text as placeholder; use real type per section 1. All three are 2048×1152 PNG, generated 2026-08-21 via Higgsfield z_image (free plan, 0.45 credits).*

## 5. Do / don't

- DO use gold `#B08D57`/`#D9B978` for borders, rim light, active states · cream `#F6EBD0` for text.
- DON'T introduce navy/coral (Quro palette) anywhere · DON'T make panels opaque — the orbit must read through the blur.
- DO keep modal text readable: blur lives on panels, not on labels (11px+ cream at ≥.6 opacity).
