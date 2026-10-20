// Render the transparent 9:16 overlay of one reel as a numbered PNG sequence (headless Chromium).  Usage:
//   node tools/render_reel_overlays.mjs <reel-work-dir> [workers] [--frames 10,200,300]
// <reel-work-dir>/reel.json is written by tools/reels.py: {fps, duration, reel:{...}, cues:[...] (times in reel time)}.
import { chromium } from '/opt/node-tools/node_modules/playwright/index.mjs';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(here, '..');
const dir = path.resolve(process.argv[2]);
const nWorkers = Number(process.argv[3] && !process.argv[3].startsWith('--') ? process.argv[3] : 3);
const fi = process.argv.indexOf('--frames');
const only = fi > 0 ? process.argv[fi + 1].split(',').map(Number) : null;
const job = JSON.parse(fs.readFileSync(path.join(dir, 'reel.json'), 'utf8'));
const fps = job.fps, total = Math.round(job.duration * fps);
const outDir = path.join(dir, only ? 'overlay_test' : 'overlay');
fs.mkdirSync(outDir, { recursive: true });
if (!only) for (const f of fs.readdirSync(outDir)) if (f.startsWith('ov_')) fs.unlinkSync(path.join(outDir, f));
const frames = only || Array.from({ length: total }, (_, i) => i);
const url = pathToFileURL(path.join(root, 'overlay', 'reel.html')).href;

async function openPage(browser) {
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: 1 });
  page.on('pageerror', e => console.error('PAGE ERROR', e.message));
  await page.goto(url);
  await page.evaluate(([r, c]) => window.setup(r, c), [job.reel, job.cues]);
  return page;
}

async function worker(w) {
  const browser = await chromium.launch();
  const page = await openPage(browser);
  let n = 0;
  for (let i = w; i < frames.length; i += nWorkers) {
    const f = frames[i];
    await page.evaluate(t => window.renderAt(t), f / fps);
    await page.screenshot({ path: path.join(outDir, `ov_${String(f).padStart(6, '0')}.png`), omitBackground: true, type: 'png' });
    if (++n % 100 === 0 && w === 0) console.log(`worker0: ${n * nWorkers}/${frames.length}`);
  }
  await browser.close();
}
console.log(`${frames.length} frames`);
await Promise.all(Array.from({ length: Math.min(nWorkers, frames.length) }, (_, w) => worker(w)));
console.log('reel overlay render done ->', outDir);
