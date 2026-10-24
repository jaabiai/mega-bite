#!/usr/bin/env python3
"""Render the style boards that are shown to the channel owner for approval.

The stills come from the real timeline (EDL + real word timings + real screen frames) and
the same overlay engine that renders the final video, so what is approved is exactly what
will be rendered.

Outputs (video-edit/previews/):
  01_style_overview.jpg    palette A in context (caption, CTAs, scenes, toast, end card)
  02_palette_options.jpg   3 palettes side by side
  03_font_options.jpg      3 fonts side by side
  04_grade_before_after.jpg
"""
import json
import os
import sys

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_timeline  # noqa: E402
import render_base  # noqa: E402
from common import MAIN, ROOT, WORK, sh, style_for  # noqa: E402
from edl import EDL  # noqa: E402

OUT = os.path.join(ROOT, "previews")
STILLS = os.path.join(WORK, "stills")
os.makedirs(OUT, exist_ok=True)
os.makedirs(STILLS, exist_ok=True)

TL = build_timeline.build()
words = TL["words"]


def chunk(text_part, after=0.0):
    return next(w for w in words if w["start"] >= after and text_part in w["text"])


w_msg = chunk("message")
T_CAP = round(w_msg["start"] + .55 * (w_msg["end"] - w_msg["start"]), 3)
sub1 = next(c for c in TL["cta"] if c["type"] == "subscribe")

# name -> (time, caption of the still)
STILLS_T = {
    "caption": (T_CAP, "Intro: title + one-word caption with moving neon underline | logo top-right"),
    "subscribe_a": (sub1["start"] + sub1["clickAt"] - .15, "Subscribe reminder - lands as 'subscribe' is spoken"),
    "subscribe_b": (sub1["start"] + sub1["clickAt"] + .95, "...click -> Subscribed, bell rings"),
    "sceneA": (15.0, "Phone scene: zoom + spotlight + step title"),
    "sceneT": (39.0, "Phone scene + periodic subscribe notification"),
    "sceneD": (46.9, "Phone scene: long-press highlight"),
    "sceneE": (50.6, "Phone scene: the 4 effect options"),
    "sceneF": (61.0, "Effect walkthrough: progress chips (Slam / Loud / Gentle / Invisible Ink)"),
    "sceneL": (98.4, "Reveal: spotlight on the scratched bubbles"),
    "coming": (55.6, "Presenter shot + 'coming up' chips"),
    "icons": (106.7, "B-roll + Share / Copy-link reminder"),
    "end": (116.0, "End card"),
}


def base_frame(t, name):
    """Picture under the overlay at time t, framed + graded exactly like render_base."""
    t = min(t, EDL["main_duration"] - 0.1)            # the end card sits on a frozen last frame
    shot = next(s for s in EDL["base"] if s["start"] <= t < s["end"])
    dst = os.path.join(STILLS, f"base_{name}.jpg")
    if shot["kind"] == "talk":
        vf = render_base.talk_filter(shot, shot["end"] - shot["start"])
        sh(f'ffmpeg -v error -y -ss {t:.3f} -i "{MAIN}" -frames:v 1 -vf "{vf}" -q:v 2 "{dst}"')
    else:
        src = os.path.join(render_base.BROLL, shot["clip"] + ".mp4")
        vf = render_base.broll_filter(shot, shot["end"] - shot["start"])
        sh(f'ffmpeg -v error -y -ss {shot["ss"] + (t - shot["start"]):.3f} -i "{src}" -frames:v 1 -vf "{vf}" -q:v 2 "{dst}"')
    return dst


def render(tag, palette, font, names):
    tl_path = os.path.join(STILLS, "tl.json")
    st_path = os.path.join(STILLS, f"style_{tag}.json")
    json.dump(TL, open(tl_path, "w"))
    json.dump(style_for(palette, font), open(st_path, "w"))
    times = ",".join(f"{STILLS_T[n][0]:.3f}" for n in names)
    outdir = os.path.join(STILLS, tag)
    sh(f'node "{ROOT}/render/render_overlay.js" --tl "{tl_path}" --style "{st_path}" --out "{outdir}" '
       f'--times {times} --names {",".join(names)} --workers 3', cwd=os.path.join(ROOT, "render"))
    res = {}
    for n in names:
        ov = Image.open(os.path.join(outdir, n + ".png")).convert("RGBA")
        base = Image.open(base_frame(STILLS_T[n][0], n)).convert("RGBA")
        base.alpha_composite(ov)
        res[n] = base.convert("RGB")
        res[n].save(os.path.join(outdir, n + "_comp.jpg"), quality=92)
    return res


def label(img, text, size=34, pad=14):
    d = ImageDraw.Draw(img)
    f = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", size)
    w = d.textlength(text, font=f)
    d.rounded_rectangle((pad, pad, pad * 2 + w + 8, pad * 2 + size + 8), 14, fill=(0, 0, 0, 215))
    d.text((pad + 10, pad + 6), text, font=f, fill=(255, 255, 255))
    return img


def grid(imgs, cols, w, gap=16, bg=(24, 24, 28)):
    h = int(w * imgs[0].size[1] / imgs[0].size[0])
    rows = (len(imgs) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * w + (cols + 1) * gap, rows * h + (rows + 1) * gap), bg)
    for i, im in enumerate(imgs):
        sheet.paste(im.resize((w, h), Image.LANCZOS), (gap + (i % cols) * (w + gap), gap + (i // cols) * (h + gap)))
    return sheet


if __name__ == "__main__":
    A = render("A_montserrat", "A_ember", "montserrat", list(STILLS_T))
    cells = [label(A[n].copy(), STILLS_T[n][1], size=36) for n in STILLS_T]
    grid(cells, 3, 840).save(os.path.join(OUT, "01_style_overview.jpg"), quality=90)
    A["caption"].save(os.path.join(OUT, "01a_caption_closeup.jpg"), quality=90)

    names = ["caption", "sceneD", "sceneF"]
    P = {"A": A}
    for key, pal in (("B", "B_lime"), ("C", "C_magenta")):
        P[key] = render(f"{key}_montserrat", pal, "montserrat", names)
    tag = {"A": "A  Ember (amber neon)", "B": "B  Lime Pulse (neon lime)", "C": "C  Magenta Dusk (neon pink/violet)"}
    cells = [label(P[k][n].copy(), tag[k], size=38) for n in names for k in "ABC"]
    grid(cells, 3, 840).save(os.path.join(OUT, "02_palette_options.jpg"), quality=90)

    F = {"Montserrat ExtraBold": A}
    for key, lab in (("sora", "Sora ExtraBold"), ("poppins", "Poppins ExtraBold")):
        F[lab] = render(f"A_{key}", "A_ember", key, ["caption", "sceneF"])
    cells = [label(F[lab][n].copy(), lab, size=38) for n in ("caption", "sceneF") for lab in F]
    grid(cells, 3, 840).save(os.path.join(OUT, "03_font_options.jpg"), quality=90)

    raw = os.path.join(STILLS, "grade_before.jpg")
    sh(f'ffmpeg -v error -y -ss 55.0 -i "{MAIN}" -frames:v 1 -vf "scale=1920:1080:flags=lanczos" -q:v 2 "{raw}"')
    aft = os.path.join(STILLS, "grade_after.jpg")
    sh(f'ffmpeg -v error -y -ss 55.0 -i "{MAIN}" -frames:v 1 -vf "scale=1920:1080:flags=lanczos,{render_base.GRADE}" -q:v 2 "{aft}"')
    grid([label(Image.open(raw).convert("RGB"), "Before (as shot)"),
          label(Image.open(aft).convert("RGB"), "After (colour-corrected + graded)")], 2, 1100).save(
        os.path.join(OUT, "04_grade_before_after.jpg"), quality=90)
    print("boards written to", OUT)
