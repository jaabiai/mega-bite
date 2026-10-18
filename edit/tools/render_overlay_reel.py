"""Render the 9:16 reel overlay (edit/overlay_reel) to transparent PNG frames.

  render_overlay_reel.py render <f0> <f1> <outdir>
  render_overlay_reel.py dump   <outdir> t1 [t2 ...]       reel seconds
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
    browser = await pw.chromium.launch(executable_path=CHROME, args=["--no-sandbox", "--disable-gpu", "--font-render-hinting=none",
                                                                      "--allow-file-access-from-files"])
    page = await browser.new_page(viewport={"width": 1080, "height": 1920})
    await page.goto(f"file://{EDIT}/overlay_reel/index.html")
    tl = json.load(open(f"{EDIT}/data/reel_timeline.json"))
    # make sure every face/weight is loaded before anything is measured
    await page.evaluate("""() => Promise.all(['800 100px Sora','700 60px Poppins','600 30px Poppins','500 30px Poppins','800 60px Poppins']
        .map(f => document.fonts.load(f)))""")
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
            if (n - f0) % 100 == 0:
                print(f"reel overlay {n}/{f1}", flush=True)
        await browser.close()


async def dump(outdir, times):
    os.makedirs(outdir, exist_ok=True)
    async with async_playwright() as pw:
        browser, page = await open_page(pw)
        for t in times:
            await page.evaluate(f"renderAt({t})")
            await page.screenshot(path=f"{outdir}/rov_{t:06.2f}.png", omit_background=True)
        await browser.close()


if __name__ == "__main__":
    if sys.argv[1] == "render":
        asyncio.run(render_frames(int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]))
    else:
        asyncio.run(dump(sys.argv[2], [float(x) for x in sys.argv[3:]]))
