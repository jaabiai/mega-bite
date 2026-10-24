#!/usr/bin/env node
/* Renders transparent overlay PNG frames from overlay.html.
 *
 *   node render_overlay.js --tl timeline.json --style style.json --out DIR
 *        [--from 0 --to 16]            frame range in seconds (end exclusive)
 *        [--times 1.2,5.5,12]          explicit stills instead of a range
 *        [--names a,b,c]               output names for --times (default t_<time>)
 *        [--fps 30] [--scale 1] [--workers 3]
 */
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const args = {};
for (let i = 2; i < process.argv.length; i += 2) args[process.argv[i].replace(/^--/, '')] = process.argv[i + 1];
const TL = JSON.parse(fs.readFileSync(args.tl, 'utf8'));
const STYLE = JSON.parse(fs.readFileSync(args.style, 'utf8'));
const fps = +(args.fps || TL.fps || 30);
const scale = +(args.scale || 1);
const workers = +(args.workers || 3);
const out = args.out;
fs.mkdirSync(out, { recursive: true });

let jobs = [];
if (args.times) {
  const names = args.names ? args.names.split(',') : null;
  args.times.split(',').forEach((t, i) => jobs.push({ t: +t, file: path.join(out, (names ? names[i] : 't_' + t) + '.png') }));
} else {
  const from = Math.round(+(args.from || 0) * fps), to = Math.round(+(args.to || TL.duration) * fps);
  for (let f = from; f < to; f++) jobs.push({ t: f / fps, file: path.join(out, String(f + 1).padStart(5, '0') + '.png') });
}

(async () => {
  const t0 = Date.now();
  const browser = await chromium.launch({ args: ['--font-render-hinting=none', '--disable-lcd-text', '--allow-file-access-from-files'] });
  const html = 'file://' + path.resolve(__dirname, 'overlay.html');
  let done = 0;
  async function worker(w) {
    const ctx = await browser.newContext({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: scale });
    const page = await ctx.newPage();
    page.on('pageerror', (e) => console.error('PAGE ERROR', e.message));
    page.on('console', (m) => { if (m.type() === 'error') console.error('CONSOLE', m.text()); });
    await page.addInitScript(`window.TL=${JSON.stringify(TL)};window.STYLE=${JSON.stringify(STYLE)};`);
    await page.goto(html);
    await page.waitForFunction('window.__ready === true');
    for (let i = w; i < jobs.length; i += workers) {
      const j = jobs[i];
      await page.evaluate((t) => window.renderAt(t), j.t);
      await page.screenshot({ path: j.file, omitBackground: true, type: 'png' });
      done++;
      if (done % 60 === 0 || done === jobs.length) {
        const el = (Date.now() - t0) / 1000;
        console.log(`frames ${done}/${jobs.length}  ${(done / el).toFixed(1)} fps  eta ${((jobs.length - done) / (done / el)).toFixed(0)}s`);
      }
    }
    await ctx.close();
  }
  await Promise.all(Array.from({ length: Math.min(workers, jobs.length) }, (_, w) => worker(w)));
  await browser.close();
  console.log(`done ${jobs.length} frames in ${((Date.now() - t0) / 1000).toFixed(1)}s`);
})().catch((e) => { console.error(e); process.exit(1); });
