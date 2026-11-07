// Headless Chromium renders of the offline viewer (node + playwright).
// usage: node render.js config.json   (config: {html, shots:[{file, state, view, caption, sub}], width, height, scale})
const fs = require('fs');
let playwright;
try { playwright = require('playwright'); } catch (e) { playwright = require('/opt/node22/lib/node_modules/playwright'); }
(async () => {
  const cfg = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
  const args = ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist',
                '--enable-webgl', '--disable-gpu-sandbox'];
  let browser;
  try { browser = await playwright.chromium.launch({args}); }
  catch (e) { browser = await playwright.chromium.launch({args, executablePath: '/opt/pw-browsers/chromium'}); }
  const page = await browser.newPage({viewport: {width: cfg.width || 800, height: cfg.height || 600},
                                      deviceScaleFactor: cfg.scale || 2});
  page.on('console', m => { if (m.type() === 'error') console.error('[page]', m.text()); });
  page.on('pageerror', e => console.error('[pageerror]', e.message));
  await page.goto('file://' + cfg.html + '?shot=1');
  await page.waitForFunction(() => window.viewer && window.viewer.ready, null, {timeout: 180000});
  for (const s of cfg.shots) {
    await page.evaluate((s) => {
      const v = window.viewer;
      v.set(Object.assign({mode:'pack', haul:false, explode:false, fea:false, mannequin:false, torso:19, fit:false, harness:true, full:false, lid:false, xray:false, bp:true, posts:false, gap:null}, s.state || {}));
      if (s.cam) v.camera(s.cam.pos, s.cam.tgt, s.cam.fov); else v.view(s.view || 'hero');
      v.caption(s.caption || '', s.sub || '');
    }, s);
    await page.waitForTimeout(400);
    await page.evaluate(() => window.viewer.renderNow());
    await page.screenshot({path: s.file});
    console.log('wrote', s.file);
  }
  await browser.close();
})().catch(e => { console.error(e); process.exit(1); });
