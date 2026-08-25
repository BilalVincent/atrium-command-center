# The floating Memory Brief panel and Zoom-out pill are removed, not broken

Vincent flagged the floating "Memory Brief" card (top-right popup on node
focus) and the "⌕ Zoom out" pill as clutter (2026-08-25). Both were removed
entirely in v9.3 rather than hidden or reduced.

- **Memory Brief**: node preview, links, Open, and Listen all still exist in
  the right panel (`renderRightStable`) — the floating card was a duplicate
  surface that covered the scene. Do not re-add a floating node card.
- **Zoom out**: clicking empty canvas or pressing **Escape** deselects and
  re-fits the camera (`deselectNode()`); the pill was a redundant third
  affordance. Guide copy now points at Esc.

If a future design wants a node popup again, build it as part of the right
panel or the drawer — not as an absolutely-positioned overlay over the scene.
