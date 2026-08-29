// v10.1 QA (runs ON THE VPS, headless chromium via playwright): 
// 1) rest state: NO edges/lines anywhere, drift active
// 2) click agent: ball freezes, node eases to front-center, relations lit, dashed filaments, no comets
// 3) edge cap <= 30 at click; hold-deepdive lifts cap
// 4) deselect: spin resumes; fps sample; console exceptions collected
const { chromium } = require('playwright');
const fs = require('fs');
const OUT = '/home/atrium/cc-qa/shots/';
(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1600, height: 950 } });
  const errors = [];
  page.on('pageerror', e => errors.push('PAGEERROR ' + String(e).slice(0, 250)));
  page.on('console', m => { if (m.type() === 'error') errors.push('CONSOLE ' + m.text().slice(0, 250)); });
  await page.goto('http://127.0.0.1:8899/', { waitUntil: 'load', timeout: 30000 });
  // wait for /state populating the HUD
  let ready = false;
  for (let i = 0; i < 40; i++) {
    ready = await page.evaluate(() => { const el = document.getElementById('hudLive'); return !!(el && el.textContent.includes('nodes')); });
    if (ready) break;
    await page.waitForTimeout(1000);
  }
  console.log('RENDER_READY', ready);
  await page.waitForTimeout(2500);
  fs.mkdirSync(OUT, { recursive: true });
  const shot = n => page.screenshot({ path: OUT + n });
  // --- rest behaviour ---
  await shot('rest.png');
  const rest1 = await page.evaluate(() => { const p = worldPos(agentNodes[0].id), pr = project(p.x, p.y, p.z); return { x: Math.round(pr.x), y: Math.round(pr.y) }; });
  await page.waitForTimeout(1600);
  const rest2 = await page.evaluate(() => { const p = worldPos(agentNodes[0].id), pr = project(p.x, p.y, p.z); return { x: Math.round(pr.x), y: Math.round(pr.y) }; });
  console.log('REST_SPIN_DELTA_PX', Math.abs(rest1.x - rest2.x) + Math.abs(rest1.y - rest2.y), '(should be >0: drift active)');
  const restCounts = await page.evaluate(() => {
    // count visible line-ish strokes at rest by sampling the edges loop state
    return { selected: selected.id, focusEdges: focusEdges.length, rotTarget: !!v10RotTarget };
  });
  console.log('REST_STATE', JSON.stringify(restCounts), '(focusEdges must be 0, rotTarget false)');
  // --- click the first agent ---
  const picked = await page.evaluate(() => { selectNode(agentNodes[0].id); return { id: agentNodes[0].id, name: agentNodes[0].name }; });
  console.log('SELECTED', JSON.stringify(picked));
  await page.waitForTimeout(4500); // ease + zoom settle
  const focus = await page.evaluate(() => {
    const n = nodeMap[selected.id];
    const p = worldPos(selected.id), pr = project(p.x, p.y, p.z);
    return {
      name: n.name, projX: Math.round(pr.x), projY: Math.round(pr.y),
      cx: Math.round(cx), cy: Math.round(cy),
      offCenterPx: Math.round(Math.hypot(pr.x - cx, pr.y - cy)),
      rotResidual: v10RotTarget ? { dx: Math.round((v10RotTarget.x - rotX) * 1000) / 1000, dy: Math.round((v10RotTarget.y - rotY) * 1000) / 1000 } : null,
      focusEdges: focusEdges.length, focusSetSize: focusSet.size, zoom: Math.round(cam.zoom * 100) / 100
    };
  });
  console.log('FOCUS_CHECK', JSON.stringify(focus), '(offCenterPx should be small; rotResidual ~0 within ease tolerance)');
  await shot('selected.png');
  // rotation frozen? sample rotY twice
  const rot1 = await page.evaluate(() => rotY);
  await page.waitForTimeout(1500);
  const rot2 = await page.evaluate(() => rotY);
  console.log('SELECTED_ROT_DELTA', Math.abs(rot2 - rot1).toFixed(6), '(should be ~0: frozen on selection)');
  // --- edge cap + hold deepdive ---
  const caps = await page.evaluate(() => {
    const before = focusEdges.length;
    selectNodeDeep(agentNodes[1].id);
    const deep = focusEdges.length;
    const total = G.edges.filter(e => e.source === agentNodes[1].id || e.target === agentNodes[1].id).length;
    deselectNode();
    return { clickCap: before, deepCount: deep, deepTotalAvailable: total };
  });
  console.log('CAPS', JSON.stringify(caps), '(clickCap<=30; deepCount == deepTotalAvailable)');
  await page.waitForTimeout(1200);
  const resumed = await page.evaluate(() => ({ rotTarget: !!v10RotTarget, selected: selected.id }));
  console.log('DESELECT_STATE', JSON.stringify(resumed), '(rotTarget false, selected null)');
  const rotA = await page.evaluate(() => rotY);
  await page.waitForTimeout(1500);
  const rotB = await page.evaluate(() => rotY);
  console.log('RESUMED_SPIN_DELTA', Math.abs(rotB - rotA).toFixed(6), '(>0: drift back on)');
  // --- fps ---
  const fps = await page.evaluate(() => new Promise(res => { const t0 = performance.now(); let n = 0; const tick = () => { n++; if (performance.now() - t0 < 2000) requestAnimationFrame(tick); else res(Math.round(n / 2)); }; requestAnimationFrame(tick); }));
  console.log('FPS_AVG', fps);
  console.log('EXCEPTIONS', errors.length, errors.slice(0, 3).join(' | '));
  await browser.close();
})().catch(e => { console.error('HARNESS_ERR', e); process.exit(1); });