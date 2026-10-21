// usage: node render.js <outdir> <frame,frame,...>|<start-end> [page=index.html]
const { chromium } = require('/opt/node-tools/node_modules/playwright');
const fs = require('fs'), path = require('path');
(async () => {
  const outdir = process.argv[2];
  const spec = process.argv[3];
  const page_ = process.argv[4] || 'index.html';
  let frames = [];
  if (spec.includes('-') && !spec.includes(',')) { const [a, b] = spec.split('-').map(Number); for (let f = a; f <= b; f++) frames.push(f); }
  else frames = spec.split(',').map(Number);
  fs.mkdirSync(outdir, { recursive: true });
  const browser = await chromium.launch({ args: ['--no-sandbox', '--disable-gpu', '--font-render-hinting=none'] });
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 1 });
  page.on('pageerror', e => console.error('PAGEERR', e.message));
  page.on('console', m => { if (m.type() === 'error') console.error('CONSOLE', m.text()); });
  await page.goto('file://' + path.resolve(page_));
  await page.evaluate(() => document.fonts.ready);
  await page.waitForTimeout(300);
  await page.evaluate(() => window.seek(2));      // prime the timeline (frame 0 must not show the un-rendered CSS defaults)
  let n = 0; const t0 = Date.now();
  for (const f of frames) {
    await page.evaluate((f) => window.seek(f), f);
    await page.screenshot({ path: path.join(outdir, String(f).padStart(5, '0') + '.png'), omitBackground: true });
    if (++n % 100 === 0) console.log(n, 'frames', ((Date.now() - t0) / n).toFixed(0), 'ms/frame');
  }
  await browser.close();
  console.log('done', n);
})();
