// node render_bg.js <outdir> <start-end>
const { chromium } = require('/opt/node-tools/node_modules/playwright');
const fs = require('fs'), path = require('path');
(async () => {
  const outdir = process.argv[2]; const [a, b] = process.argv[3].split('-').map(Number);
  fs.mkdirSync(outdir, { recursive: true });
  const browser = await chromium.launch({ args: ['--no-sandbox', '--disable-gpu'] });
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 1 });
  await page.goto('file://' + path.resolve(__dirname, 'bg.html'));
  const t0 = Date.now();
  for (let f = a; f <= b; f++) {
    await page.evaluate((f) => window.draw(f), f);
    await page.screenshot({ path: path.join(outdir, String(f).padStart(4, '0') + '.png') });
    if ((f - a + 1) % 50 === 0) console.log(f - a + 1, 'frames', ((Date.now() - t0) / (f - a + 1)).toFixed(0), 'ms/frame');
  }
  await browser.close(); console.log('done');
})();
