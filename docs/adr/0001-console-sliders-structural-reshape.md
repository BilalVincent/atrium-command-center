# Graph Console sliders reshape the atlas structurally, not via per-node physics

The Graph Console's Repel / Link length sliders originally drove a per-node
physics sim (bounded repulsion + springs) layered on top of the deterministic
flat-atlas layout. That never worked in practice for three stacked reasons:
the link-length spring loop was dead code (`const ia = -1; return;`), the
physics displacement was capped at ~42px (≈15 screen px at fit-zoom —
imperceptible), and worst of all `refreshState()` re-ran `computeLayout()`
on every `/state` poll where the node count changed — which **wiped all
physics displacement within seconds**, silently resetting the graph. A live
vault gains nodes constantly, so any slider effect erased itself.

Decision (v9.3, Vincent chose "fix it"): the sliders reshape the atlas
**inside `computeLayout()` itself** — Repel scales satellite ring spacing
and the outer belt width (`SPREAD = 0.55 + 0.45*repel`), Link length scales
the hub→satellite spoke radius (`R0*LINK`) and belt offset. Slider input
triggers an immediate `computeLayout()`. Because the effect is structural,
it survives every re-layout **by construction** — no offset bookkeeping to
lose. Hubs never move (agents stay on their ring); only satellites and the
belt respond. The per-node physics sim (`physicsStep`) remains as a gentle
settling layer, but the sliders no longer depend on it.

Consequence: slider changes are deterministic and instant, but they are a
re-layout, not an animation — nodes jump to their new positions (the camera
eases, nodes don't). If animated morphing is ever wanted, it must be built
as interpolation between two computed layouts, not by resurrecting the
per-node offset approach.
