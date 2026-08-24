# Atrium OS — v6.4: Broaden Chat Section

**Author:** Solari1 · **Date:** 2026-08-21
**File:** `~/atrium-command-center/index.html`
**Commit message:** `v6.4: broaden chat section`

## Context
Vincent reviewed the chat panel (right rail) and reported it feels too cramped — the message bubbles and input are squeezed inside the narrow right rail.

## Required changes

### A. Widen the right rail on desktop
- Current: `.app{grid-template-columns:272px 1fr 322px}` (right rail = 322px)
- Change to: `.app{grid-template-columns:252px 1fr 420px}` on desktop viewports.
  - Left rail 272px → 252px (profiles + calendar still fit)
  - Right rail 322px → 420px (chat has room)
  - Center orbit area: ~1600 - 252 - 420 - scrollbar ≈ 920px (still generous)
- Keep mobile breakpoints unchanged: at ≤1000px the right rail is already hidden; at ≤820px it's hidden; at ≤600px single-column. Chat on mobile is already full-screen modal.

### B. Improve chat readability inside the wider rail
- Increase message bubble width:
  - `.cmsg{max-width:80%}` → `.cmsg{max-width:92%}` so agent/user bubbles use more of the 420px width.
- Increase chat body padding:
  - `.right-body` padding from current `12px 14px` to `14px 16px` (if a compact value; otherwise add `.chat-body{padding:14px 16px}`).
- Slightly increase font size in chat messages and input:
  - `.cmsg{font-size:13px}` → `13.5px`
  - `.chat-in input{font-size:13.5px}` → `14px`
- Keep the chat input at full width with comfortable internal padding.

### C. Ensure the agent header at top of right rail uses the extra width
- The header currently shows avatar + name/role/rate. With 420px it should no longer truncate.
- If truncation still happens, reduce header font/padding or allow flex wrap, but prefer not to truncate.

### D. Regress checks
- Desktop (1600px): profiles rail + calendar still render fully; orbit center still prominent; chat panel feels broader.
- Tablet (768px): right rail hidden, no change expected.
- Phone (390px): single-column layout, chat modal full-screen.

## Do NOT
- Do not remove the right rail.
- Do not touch orbit engine, v6.1/v6.2/v6.3 responsive breakpoints, brand palette.
- Do not touch design-brief outputs.

## Verification (before commit)
1. `python -c "import re; open('_check.js','w').write(chr(10).join(re.findall(r'<script>(.*?)</script>', open('index.html').read(), re.S)))"`
2. `curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8800/` → 200
3. Headless Edge screenshot at 1600×950 showing chat panel open (select an agent or open chat if needed) under `$LOCALAPPDATA/Temp/cc-v64-qa/`. Vision-check: chat bubbles/input appear broader, no truncation, right rail wider than before.
4. Headless Edge screenshot at 390×844 to confirm chat modal is full-screen.
5. Commit `v6.4: broaden chat section` and push.
