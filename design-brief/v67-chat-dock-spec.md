# v6.7 SPEC — Shrink/Expand chat bar (B-01) — COUNCIL-SYNTHESIZED

> Autopilot cycle 1. Chairman synthesis of 3 Stage-1 reviews (architecture, UX, implementation).
> Source roadmap: cc-design-review.md item 1 (Vincent-approved: expanded default + dock toggle).

## Goal
A DOCKED mode for chat: slim bottom bar, orbit gains height. Default = today's layout
EXACTLY. Nothing changes until the user clicks the toggle.

## Design decisions (council verdict)
1. **In-flow collapse, NOT position:fixed** (arch seat, verified in code):
   `.center` is flex-column with `.scene-wrap{flex:1 1 auto}` (L92-93) -> collapsing `.chat`
   to a fixed height (~52px) makes the orbit grow AUTOMATICALLY at every breakpoint.
   Zero geometry math; "full width minus rail" comes free.
2. **All rules under ONE ancestor gate**: `.chat-docked` class on `<body>`; every override
   selector starts `.chat-docked .chat ...` appended as ONE labeled block (`/* v6.7: SHRINK-EXPAND CHAT BAR */`)
   at END of `<style>` (repo append-only convention).
3. **Plain-language toggle** (UX seat): button in `.chat-head` labeled **"Shrink" / "Expand"**
   with chevron (▾ when expanded, ▴ when docked). NEVER the word "dock" in UI copy.
   aria-label swaps accordingly; focus stays on the toggle after click.
4. **The bar reads as THE AGENT, alive** (UX seat): portrait avatar (assets/portraits/<id>_512.png,
   fallback initials ring) + agent name + gold presence dot ("online") + ONE truncated last-message
   line (ellipsis) + REAL input row (placeholder "Ask anything...") + unread gold dot when a reply
   lands while shrunk. Sending from the bar gives visible confirmation <=1s (preview line updates +
   brief highlight pulse).
5. Click anywhere on the bar (except input/toggle) expands back. Toggle always works both ways.

## Implementation anchors (verified by impl seat)
- Chat DOM: `<section class="chat">` ~L826-829 (`.chat-head` holds #chatWho/#chatCtx/#soundBtn;
  `.chat-body` #chatBody; `.chat-in` #chatInput).
- Early script block ~L721 (runs before main markup) applies localStorage BEFORE paint:
  `try{ if(localStorage.getItem('ccChatShrunk')==='1') document.documentElement.classList.add('chat-docked'); }catch(e){}`
  (use documentElement to survive body-not-parsed-yet; CSS selectors target html.chat-docked body ...)
- Poll safety: the 8s fetchState->refreshState (L982) must NOT clobber the bar's preview mid-typing.
  Guard: renderShrunkBar() early-returns when document.activeElement is the bar input OR state
  signature (agent id + last msg text + unread count) unchanged. Mirror the v6.6.2/v6.6.4 guards.
- Unread detection: hook the existing message-render path; increment unread when shrunk && message
  from agent; clear on expand or on input focus/send.
- Send-from-bar: reuse the existing send handler; on success update bar preview immediately.

## Constraints (unchanged)
Additive-only CSS · no removals of listeners/DOM · no orbit engine changes · filter pills stay in
rail · search stays in topbar · calendar docked · ink/gold/cream only · real data only.

## Mobile (<=600px)
Bar spans full width, sits above safe-area (env(safe-area-inset-bottom)), input >=44px tall,
16px font (iOS zoom rule). Drawer/hamburger untouched. Test 390x844 BOTH states.

## Acceptance criteria
- [ ] Fresh load default: ZERO visual delta vs current prod (byte-equivalent rendering path untouched).
- [ ] Shrink -> orbit visibly taller; bar shows avatar+name+dot+preview+input; send works from bar w/ <=1s confirmation.
- [ ] Expand -> exact pre-shrink layout restored; unread dot cleared.
- [ ] Reload while shrunk: stays shrunk, NO flash of expanded state.
- [ ] Reply lands while shrunk -> unread dot appears; expands/clears correctly.
- [ ] Two consecutive 8s polls while shrunk + typing: preview NOT reset, input NOT cleared.
- [ ] node --check clean; console clean through toggle/send/poll cycles (CDP).
- [ ] Screenshots 1600x950 AND 390x844, BOTH states, vision-verified.
- [ ] Commit EARLY as "v6.7: shrink-expand chat bar (default unchanged)" then push after QA.

## Ship lane (parent/mechanical, not the builder)
Parent reviews screenshots -> scp index.html to VPS per atrium-command-center deploy recipe ->
docker compose up -d --force-recreate command-center -> Lane E prod battery.
