#!/usr/bin/env python3
"""Thumbnails (1280x720) and share cards (1080x1350) for the YouTube / Instagram launch.

Backgrounds are frames of the finished picture ($WORK/base.mp4 for the film, $WORK/reels/<id>/base.mp4 for the reels), the text is set
in the film's fonts (Uroob, Cinzel).  Output: youtube/thumbnails/*.jpg, youtube/share_cards/*.jpg
"""
import json, os, pathlib, subprocess, sys, textwrap
ROOT = pathlib.Path(__file__).resolve().parent.parent
WORK = pathlib.Path(os.environ['WORK'])
OUT = ROOT / 'youtube'
TMP = WORK / 'yt_tmp'; TMP.mkdir(exist_ok=True)
FONTS = ROOT / 'fonts'
LOGO = ROOT / 'inputs' / 'logo_badge.png'

CSS = f"""
@font-face {{ font-family:'Uroob'; src:url('file://{FONTS}/uroob-regular-nodotcircle.woff2') format('woff2'); }}
@font-face {{ font-family:'Cinzel'; font-weight:600; src:url('file://{FONTS}/cinzel-latin-600-normal.woff2') format('woff2'); }}
@font-face {{ font-family:'Cinzel'; font-weight:700; src:url('file://{FONTS}/cinzel-latin-700-normal.woff2') format('woff2'); }}
@font-face {{ font-family:'Aref'; font-weight:700; src:url('file://{FONTS}/aref-ruqaa-arabic-700-normal.woff2') format('woff2'); }}
html,body {{ margin:0; background:#000; }}
.stage {{ position:relative; overflow:hidden; background-size:cover; background-position:center; }}
.abs {{ position:absolute; }}
.gold {{ background-image:linear-gradient(180deg,#fff8dc 0%,#f6dc8e 35%,#e0b04a 70%,#f3d98a 100%); -webkit-background-clip:text; background-clip:text; color:transparent; }}
.neon {{ height:10px; border-radius:6px; background:linear-gradient(90deg,#ff9a1f,#ffd978 55%,#fff); box-shadow:0 0 6px #fff,0 0 18px #ffb62e,0 0 46px rgba(255,150,20,.85),0 0 90px rgba(255,120,0,.5); }}
.pill {{ font:700 30px 'Cinzel',serif; letter-spacing:.2em; color:#1a1206; background:linear-gradient(180deg,#ffe9a8,#e0b04a); padding:10px 26px 8px; border-radius:40px; box-shadow:0 6px 22px rgba(0,0,0,.5); }}
.brand {{ font:600 24px 'Cinzel',serif; letter-spacing:.32em; color:#f4ead0; text-shadow:0 2px 10px rgba(0,0,0,.9); }}
"""

def frame(src, t, dst, vf):
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', str(t), '-i', str(src), '-frames:v', '1', '-vf', vf, '-q:v', '2', '-update', '1', str(dst)], check=True)

def shot(html_path, out, w, h, quality=90):
    js = TMP / 'shot.mjs'
    js.write_text(f"""import {{ chromium }} from '/opt/node-tools/node_modules/playwright/index.mjs';
const b = await chromium.launch(); const p = await b.newPage({{ viewport: {{ width: {w}, height: {h} }} }});
await p.goto('file://{html_path}'); await p.evaluate(() => document.fonts.ready); await p.waitForTimeout(400);
await p.screenshot({{ path: '{out}', type: 'jpeg', quality: {quality} }}); await b.close();""")
    subprocess.run(['node', str(js)], check=True)

def thumb(name, bg, big, small, pill):
    """big = (text, font px, neon width px); small = optional line under the neon rule.  Text, rule and line flow in one column."""
    html = f"""<meta charset=utf8><style>{CSS}
.stage {{ width:1280px; height:720px; background-image:url('file://{bg}'); }}
.shade {{ inset:0; background:linear-gradient(90deg,rgba(2,4,8,.88) 0%,rgba(2,4,8,.66) 45%,rgba(2,4,8,0) 78%), linear-gradient(0deg,rgba(2,4,8,.55) 0%,rgba(2,4,8,0) 35%); }}
.col {{ left:58px; top:148px; display:flex; flex-direction:column; align-items:flex-start; }}
.big {{ font:400 {big[1]}px/1.02 'Uroob',sans-serif; white-space:pre; filter:drop-shadow(0 8px 26px rgba(0,0,0,.85)); }}
.small {{ margin:22px 0 0 6px; font:700 34px 'Cinzel',serif; letter-spacing:.22em; color:#f4ead0; text-shadow:0 3px 14px rgba(0,0,0,.9); }}
.neon {{ margin:14px 0 0 4px; width:{big[2]}px; }}
.pill {{ left:64px; top:58px; }}
.logo {{ left:56px; bottom:44px; width:104px; height:104px; filter:drop-shadow(0 4px 14px rgba(0,0,0,.7)); }}
.brand {{ left:178px; bottom:84px; }}
</style><div class=stage><div class="abs shade"></div>
<div class="abs pill">{pill}</div>
<div class="abs col"><div class="big gold">{big[0]}</div><div class="neon"></div>{f'<div class="small">{small}</div>' if small else ''}</div>
<img class="abs logo" src="file://{LOGO}"><div class="abs brand">MIRAYA STUDIO</div></div>"""
    hp = TMP / f'{name}.html'; hp.write_text(html, encoding='utf8')
    out = OUT / 'thumbnails' / f'{name}.jpg'; out.parent.mkdir(parents=True, exist_ok=True)
    shot(hp, out, 1280, 720, 92); print('wrote', out, f'{out.stat().st_size / 1e3:.0f} KB')

def card(name, bg, lines, tag):
    body = ''.join(f'<div>{l}</div>' for l in lines)
    html = f"""<meta charset=utf8><style>{CSS}
.stage {{ width:1080px; height:1350px; background-image:url('file://{bg}'); }}
.shade {{ inset:0; background:linear-gradient(0deg,rgba(2,4,8,.94) 0%,rgba(2,4,8,.78) 34%,rgba(2,4,8,.15) 62%,rgba(2,4,8,0) 100%); }}
.q {{ left:70px; right:70px; bottom:250px; font:400 118px/1.12 'Uroob',sans-serif; color:#fff7dd; text-shadow:0 6px 28px rgba(0,0,0,.85),0 0 34px rgba(255,200,90,.45); }}
.neon {{ left:72px; bottom:226px; width:300px; }}
.foot {{ left:70px; bottom:70px; display:flex; align-items:center; gap:26px; }}
.foot img {{ width:112px; height:112px; filter:drop-shadow(0 4px 14px rgba(0,0,0,.7)); }}
.tag {{ font:600 28px 'Cinzel',serif; letter-spacing:.26em; color:#f4ead0; }}
.sub {{ font:600 21px 'Cinzel',serif; letter-spacing:.3em; color:#e3bd62; margin-top:10px; }}
</style><div class=stage><div class="abs shade"></div><div class="abs q">{body}</div><div class="abs neon"></div>
<div class="abs foot"><img src="file://{LOGO}"><div><div class=tag>MIRAYA STUDIO</div><div class=sub>{tag}</div></div></div></div>"""
    hp = TMP / f'{name}.html'; hp.write_text(html, encoding='utf8')
    out = OUT / 'share_cards' / f'{name}.jpg'; out.parent.mkdir(parents=True, exist_ok=True)
    shot(hp, out, 1080, 1350, 92); print('wrote', out, f'{out.stat().st_size / 1e3:.0f} KB')

def main():
    film = WORK / 'base.mp4'
    # --- thumbnails: 16:9 crop of the 2.39:1 picture
    crop = "crop=1429:804:{x}:0,scale=1280:720,eq=saturation=1.12:contrast=1.06"
    frame(film, 7.0, TMP / 'tA.jpg', crop.format(x=0) + ',hflip')                  # mosque at night, mirrored so the minarets sit on the right
    frame(film, 26.0, TMP / 'tB.jpg', crop.format(x=0))                           # the hourglass on black
    frame(film, 233.5, TMP / 'tC.jpg', crop.format(x=0))                          # sunrise over the ocean
    thumb('thumb_A_niskaram', TMP / 'tA.jpg', ('നിസ്കാരം', 230, 500), 'MALAYALAM ISLAMIC SONG', 'OFFICIAL LYRIC VIDEO')
    thumb('thumb_B_khabar', TMP / 'tB.jpg', ('ഖബറിലെ ആദ്യത്തെ\nചോദ്യം…', 150, 520), None, 'NISKARAM · NEW MALAYALAM SONG')
    thumb('thumb_C_iruloka', TMP / 'tC.jpg', ('ഇരുലോക\nവിജയം', 185, 470), None, 'NISKARAM · OFFICIAL LYRIC VIDEO')
    # --- share cards from the reel pictures (4:5 crop of the 9:16 frame)
    R = WORK / 'reels'
    v = "crop=1080:1350:0:{y},eq=saturation=1.08:contrast=1.05"
    frame(R / 'r1_khabar' / 'base.mp4', 5.0, TMP / 'c1.jpg', v.format(y=140))
    frame(R / 'r2_sujood' / 'base.mp4', 8.0, TMP / 'c2.jpg', v.format(y=430))
    frame(R / 'r3_jannah' / 'base.mp4', 25.0, TMP / 'c3.jpg', v.format(y=120))
    card('card_1_khabar', TMP / 'c1.jpg', ['ഖബറിലെ ആദ്യത്തെ ചോദ്യം വരും,', 'നിസ്കരിച്ചോയെന്ന് റബ്ബ് ചോദിക്കും!'], 'NISKARAM')
    card('card_2_sujood', TMP / 'c2.jpg', ['സുജൂദോളം വലിയൊരു', 'മരുന്നില്ലെടോ!'], 'NISKARAM')
    card('card_3_jannah', TMP / 'c3.jpg', ['നിസ്കാര വഴിയിൽ ഉറച്ചുനിന്നാൽ,', 'ഇരുലോക വിജയമണഞ്ഞിടും നീ…'], 'NISKARAM')

if __name__ == '__main__':
    main()
