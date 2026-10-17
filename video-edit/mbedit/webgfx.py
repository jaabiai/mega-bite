"""Chromium-rendered vector sprites (CTA buttons, icons).  Run once:  python -m mbedit.webgfx

Playwright drives the pre-installed Chromium (never `playwright install`).  Output PNGs are cached in
$MB_WORK/assets and loaded as premultiplied sprites by the compositor.
"""
import asyncio
import os
import sys

from .common import WORK

ASSETS = os.path.join(WORK, "assets")
CHROME = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"

ICONS = {
    "bell": "M12 22c1.1 0 2-.9 2-2h-4c0 1.1.89 2 1.99 2zm6-6v-5c0-3.07-1.64-5.64-4.5-6.32V4c0-.83-.67-1.5-1.5-1.5s-1.5.67-1.5 1.5v.68C7.63 5.36 6 7.92 6 11v5l-2 2v1h16v-1l-2-2z",
    "like": "M1 21h4V9H1v12zm22-11c0-1.1-.9-2-2-2h-6.31l.95-4.57.03-.32c0-.41-.17-.79-.44-1.06L14.17 1 7.59 7.59C7.22 7.95 7 8.45 7 9v10c0 1.1.9 2 2 2h9c.83 0 1.54-.5 1.84-1.22l3.02-7.05c.09-.23.14-.47.14-.73v-2z",
    "comment": "M21.99 4c0-1.1-.89-2-1.99-2H4c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h14l4 4-.01-18z",
    "share": "M18 16.08c-.76 0-1.44.3-1.96.77L8.91 12.7c.05-.23.09-.46.09-.7s-.04-.47-.09-.7l7.05-4.11c.54.5 1.25.81 2.04.81 1.66 0 3-1.34 3-3s-1.34-3-3-3-3 1.34-3 3c0 .24.04.47.09.7L8.04 9.81C7.5 9.31 6.79 9 6 9c-1.66 0-3 1.34-3 3s1.34 3 3 3c.79 0 1.5-.31 2.04-.81l7.12 4.16c-.05.21-.08.43-.08.65 0 1.61 1.31 2.92 2.92 2.92 1.61 0 2.92-1.31 2.92-2.92s-1.31-2.92-2.92-2.92z",
    "check": "M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z",
    "play": "M8 5v14l11-7z",
    "arrow_down": "M20 12l-1.41-1.41L13 16.17V4h-2v12.17l-5.58-5.59L4 12l8 8 8-8z",
    "link": "M3.9 12c0-1.71 1.39-3.1 3.1-3.1h4V7H7c-2.76 0-5 2.24-5 5s2.24 5 5 5h4v-1.9H7c-1.71 0-3.1-1.39-3.1-3.1zM8 13h8v-2H8v2zm9-6h-4v1.9h4c1.71 0 3.1 1.39 3.1 3.1s-1.39 3.1-3.1 3.1h-4V17h4c2.76 0 5-2.24 5-5s-2.24-5-5-5z",
}


def svg(name, size, color="#fff", extra=""):
    return f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" {extra}><path d="{ICONS[name]}" fill="{color}"/></svg>'


BASE_CSS = """
*{box-sizing:border-box;margin:0;padding:0}
html,body{background:transparent}
body{font-family:'Inter','Inter Display',sans-serif;-webkit-font-smoothing:antialiased}
.wrap{display:inline-block;padding:44px}
.pill{display:flex;align-items:center;justify-content:center;gap:26px;color:#fff;font-weight:900;letter-spacing:1px;
      box-shadow:0 14px 34px rgba(0,0,0,.50), 0 0 0 4px rgba(255,255,255,.14) inset, 0 3px 0 rgba(255,255,255,.38) inset}
"""


def pill(w, h, bg, text, icon, size, fs, extra_style=""):
    return f"""<div class="wrap"><div class="pill" style="width:{w}px;height:{h}px;border-radius:{h//2}px;background:{bg};font-size:{fs}px;{extra_style}">
      {svg(icon, size)}<span>{text}</span></div></div>"""


SPRITES = {
    # name: html body
    "cta_subscribe": pill(660, 180, "linear-gradient(180deg,#ff5252,#d50000)", "SUBSCRIBE", "bell", 84, 76),
    "cta_subscribed": pill(660, 180, "linear-gradient(180deg,#5b6170,#343845)", "SUBSCRIBED", "check", 84, 70),
    "cta_like": pill(520, 160, "linear-gradient(180deg,#34a2ff,#1565e8)", "LIKE", "like", 84, 72),
    "cta_comment": pill(620, 160, "linear-gradient(180deg,#9a7bff,#5a3df0)", "COMMENT", "comment", 76, 66),
    "cta_share": pill(520, 160, "linear-gradient(180deg,#27d79a,#0aa57a)", "SHARE", "share", 76, 72),
    "bell_gold": f'<div class="wrap">{svg("bell", 150, "#ffcc2f", "style=\"filter:drop-shadow(0 8px 14px rgba(0,0,0,.5))\"")}</div>',
    "badge_link": pill(560, 150, "linear-gradient(180deg,#34a2ff,#1565e8)", "LINK BELOW", "arrow_down", 76, 56),
    "cursor": """<div class="wrap" style="padding:16px"><svg width="96" height="110" viewBox="0 0 24 28">
        <path d="M3 2v20l5.2-5 3.6 8.4 3-1.3-3.5-8.2H19z" fill="#fff" stroke="#111" stroke-width="1.6" stroke-linejoin="round"/></svg></div>""",
    "icon_play": f'<div class="wrap" style="padding:10px"><div style="width:150px;height:150px;border-radius:75px;background:rgba(0,0,0,.55);display:flex;align-items:center;justify-content:center;box-shadow:0 0 0 5px rgba(255,255,255,.9) inset">{svg("play", 90)}</div></div>',
}


async def _build(force=False):
    from playwright.async_api import async_playwright
    os.makedirs(ASSETS, exist_ok=True)
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path=CHROME, args=["--no-sandbox"])
        pg = await b.new_page(viewport={"width": 1400, "height": 700}, device_scale_factor=1)
        for name, body in SPRITES.items():
            out = os.path.join(ASSETS, name + ".png")
            if os.path.exists(out) and not force:
                continue
            await pg.set_content(f"<html><head><style>{BASE_CSS}</style></head><body>{body}</body></html>")
            await pg.wait_for_timeout(50)
            el = await pg.query_selector(".wrap")
            await el.screenshot(path=out, omit_background=True)
            print("built", name)
        await b.close()


def build(force=False):
    asyncio.run(_build(force))


if __name__ == "__main__":
    build(force="--force" in sys.argv)
