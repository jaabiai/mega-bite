"""Render the HTML/JS overlay to transparent PNG frames with headless Chromium.

  render_overlay.py render <f0> <f1> <outdir>       frames f0..f1-1 (30 fps) -> outdir/%06d.png
  render_overlay.py dump   <outdir> t1 [t2 ...]     transparent PNGs at the given seconds (debug)
  render_overlay.py preview <bg.png> <out.png> t    overlay composited over a still (debug)
"""
import asyncio
import json
import os
import sys

from playwright.async_api import async_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
EDIT = os.path.dirname(HERE)
CHROME = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"
FPS = 30


async def open_page(pw):
    browser = await pw.chromium.launch(executable_path=CHROME,
                                       args=["--no-sandbox", "--disable-gpu", "--font-render-hinting=none",
                                             "--allow-file-access-from-files"])
    page = await browser.new_page(viewport={"width": 1920, "height": 1080})
    await page.goto(f"file://{EDIT}/overlay/index.html")
    tl = json.load(open(f"{EDIT}/data/timeline.json"))
    await page.evaluate("tl => setTimeline(tl)", tl)
    await page.evaluate("document.fonts.ready")
    await page.wait_for_timeout(400)
    return browser, page


async def render_frames(f0, f1, outdir):
    os.makedirs(outdir, exist_ok=True)
    async with async_playwright() as pw:
        browser, page = await open_page(pw)
        for n in range(f0, f1):
            await page.evaluate(f"renderAt({n / FPS:.5f})")
            await page.screenshot(path=f"{outdir}/{n:06d}.png", omit_background=True)
            if (n - f0) % 200 == 0:
                print(f"overlay {n}/{f1}", flush=True)
        await browser.close()


async def dump(outdir, times):
    os.makedirs(outdir, exist_ok=True)
    async with async_playwright() as pw:
        browser, page = await open_page(pw)
        for t in times:
            await page.evaluate(f"renderAt({t})")
            await page.screenshot(path=f"{outdir}/ov_{t:07.2f}.png", omit_background=True)
        await browser.close()


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "render":
        asyncio.run(render_frames(int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]))
    elif cmd == "dump":
        asyncio.run(dump(sys.argv[2], [float(x) for x in sys.argv[3:]]))
