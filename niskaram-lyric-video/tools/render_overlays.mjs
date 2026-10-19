// Render the transparent overlay layer (credits, Arabic title, lyric lower-third, end credits)
// as a numbered PNG sequence using headless Chromium.  Usage:
//   node tools/render_overlays.mjs <work-dir> [workers] [--frames 100,200,300]
import { chromium } from '/opt/node-tools/node_modules/playwright/index.mjs';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(here, '..');
const work = path.resolve(process.argv[2] || path.join(root, 'work'));
const nWorkers = Number(process.argv[3] || 3);
const fi = process.argv.indexOf('--frames');
const only = fi > 0 ? process.argv[fi + 1].split(',').map(Number) : null;
const tl = JSON.parse(fs.readFileSync(path.join(work, 'timeline.json'), 'utf8'));
const fps = tl.fps;
const outDir = path.join(work, only ? 'overlay_test' : 'overlay');
fs.mkdirSync(outDir, { recursive: true });
if (!only) for (const f of fs.readdirSync(outDir)) if (f.startsWith('ov_')) fs.unlinkSync(path.join(outDir, f));

const url = pathToFileURL(path.join(root, 'overlay', 'overlay.html')).href;
const [W, H] = tl.size;

async function openPage(browser) {
  const page = await browser.newPage({ viewport: { width: W, height: H }, deviceScaleFactor: 1 });
  page.on('pageerror', e => console.error('PAGE ERROR', e.message));
  await page.goto(url);
  await page.evaluate(([p, c]) => window.setup(p, c), [tl, tl.cues]);
  return page;
}

const browser0 = await chromium.launch();
const p0 = await openPage(browser0);
const iv = await p0.evaluate(() => window.intervals());
let frames = [];
if (only) frames = only;
else for (const [a, b] of iv) for (let f = Math.ceil(a * fps); f <= Math.floor(b * fps); f++) frames.push(f);
frames = [...new Set(frames)].sort((x, y) => x - y);
await browser0.close();
console.log(`${frames.length} overlay frames in ${iv.length} intervals`);
fs.writeFileSync(path.join(outDir, 'frames.json'), JSON.stringify({ fps, frames }));

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
await Promise.all(Array.from({ length: Math.min(nWorkers, frames.length) }, (_, w) => worker(w)));
console.log('overlay render done ->', outDir);
