You are assisting with a design review of the Atrium Command Center — a real product, not a demo.

## MAIN BRIEF
An ultra-sleek, modern AI Operating System UI for agentic work. Center stage: an interactive 3D knowledge-graph orbit of the user's files, memory, conversations and AI agents. Around it: agent profiles rail (left), calendar (bottom-left), team chat (bottom-center), node inspector (right), command header (top). Design language: dark "VAULT" theme, ink/gold/cream palette (#2A2620 / #B08D57 / #F6F3ED), glass-morphic panels, Montserrat. The #1 goal is USER EXPERIENCE: calm, clear hierarchy, nothing obstructive, everything scannable at a glance.

## CURRENT IMPLEMENTATION
Single file: index.html (~2,400 lines — CSS first, then HTML, then the canvas orbit engine JS). Served locally at 127.0.0.1:8800. Read the whole file before answering.

Recent history (context for why things look as they do):
- v6.3 added a large two-row glass corner panel in the top-right → owner rejected it as obstructive; v6.5 reverted to a slim single-row cluster.
- v6.4 made the chat panel flex-fill the center column height → far too tall; v6.5 capped it at min(40dvh, 360px).
- v6.5 moved the zone-filter pills back into the LEFT RAIL between Agent Profiles and the Calendar (that is where they belong per the owner).

## OWNER'S OPEN CONCERNS (review + ideate — do NOT edit any files)
1. FILTER PILLS: the pills currently in the left rail feel washed out (translucent glass background). The owner wants the ORIGINAL v5.1 pill style restored — crisp, high contrast: font-size 10px, letter-spacing .14em uppercase, weight 700, background rgba(12,11,8,.6), border rgba(176,141,87,.35), padding 5px 12px, hover gold tint, active solid gold #B08D57 with dark text — KEEPING the icons each pill carries today (◉ 💬 ⏱ 📁 🧠). Confirm whether anything in the current cascade conflicts with restoring that exact recipe inside the rail context, and note any refinement worth making without changing its character.
2. LEFT RAIL FIT: the rail must hold Agent Profiles (7 rows today), the filter row, and the Calendar (month grid + event list) within 100dvh with NOTHING scrolling (calendar docked bottom, never scrolls — hard rule). Today the profiles list scrolls internally and can push the calendar down on shorter screens. Produce a concrete vertical space budget (px per section, with typography/padding tightening suggestions) that keeps no-scroll fit from ~700px viewport height upward, including when a focused-profile KPI card expands.
3. ORBIT VISUAL SCALE: file nodes feel too dominant and the owner worries about behavior at scale. Facts you should verify in code: drawNode() gives file nodes radius 9 * projection scale (same 'readable' tier as memory/skill nodes) plus full glowSprite halo; seven per-owner file clusters sit at shell base 220; total graph is ~1,322 nodes / 1,139 links today. The engine already grows cluster radius by 12*sqrt(members) and the placement sphere by (clusters/24)^0.4 — assess whether that is enough, and what happens visually at 5k–50k nodes.

## DELIVERABLES (return markdown only)
A. DESIGN REVIEW — honest assessment of the existing screen against the brief: hierarchy, typography, color discipline, spacing rhythm, information architecture, and specifically the three concerns above. Reference actual selectors/values from index.html. Call out anything that fights the 'calm OS' goal.
B. NEW DESIGN IDEAS — 5–8 concrete, specific proposals to push this toward an ultra-sleek modern agentic OS. Each: what changes (with the actual CSS/JS hook in this file), why it serves UX, rough effort (S/M/L). Favor restraint over feature creep — polish, hierarchy, motion discipline, depth.
C. ORBIT AT SCALE — a specific engineering plan for visual weight tiers (which node classes deserve glow/large radius), cluster shell rebalancing so files don't outweigh meaning, and density management as nodes grow 10x+ (level-of-detail, culling behind camera, opacity falloff, label budget). Include concrete formulas/thresholds where possible.
