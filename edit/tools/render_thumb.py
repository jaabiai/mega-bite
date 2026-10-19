"""Render a thumbnail variant of edit/thumb/index.html.

usage: render_thumb.py <variant A|B|R> <person.png> <out.png|out.jpg> [scale=2]
A = YouTube 1280x720 (big "3" + list), B = YouTube 1280x720 (question), R = reel / shorts cover 1080x1920
The page is rendered at `scale`x and downsampled with Lanczos (crisp text); .jpg output is written at quality 95.
"""
import asyncio
import os
import sys

import cv2
from playwright.async_api import async_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
EDIT = os.path.dirname(HERE)
CHROME = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"
SIZE = {"A": (1280, 720), "B": (1280, 720), "R": (1080, 1920)}


async def main(v, person, out, scale=2):
    w, h = SIZE[v]
    async with async_playwright() as pw:
        br = await pw.chromium.launch(executable_path=CHROME, args=["--no-sandbox", "--disable-gpu", "--font-render-hinting=none",
                                                                     "--allow-file-access-from-files"])
        pg = await br.new_page(viewport={"width": w, "height": h}, device_scale_factor=scale)
        await pg.goto(f"file://{EDIT}/thumb/index.html")
        await pg.evaluate("([v, p]) => setup(v, p)", [v, f"file://{os.path.abspath(person)}"])
        await pg.wait_for_timeout(500)
        tmp = out + ".big.png"
        await pg.locator("#stage").screenshot(path=tmp)
        await br.close()
    im = cv2.imread(tmp)
    im = cv2.resize(im, (w, h), interpolation=cv2.INTER_AREA if scale > 1 else cv2.INTER_LINEAR)
    cv2.imwrite(out, im, [cv2.IMWRITE_JPEG_QUALITY, 95] if out.endswith(".jpg") else [])
    os.remove(tmp)
    print("wrote", out, im.shape, os.path.getsize(out) // 1024, "KB")


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4]) if len(sys.argv) > 4 else 2))
