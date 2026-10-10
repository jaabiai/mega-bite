"""Bootstrap for the vertical Reel (1080x1920).

The landscape engine in ../../hinglish_landscape/tools is imported READ-ONLY (never modified).  Its modules take the frame sizes from
`hl_common` at import time, so a copy of hl_common with the vertical sizes is installed in sys.modules BEFORE any hl_* module is imported:

    output  W x H   = 1080 x 1920      (9:16)
    working WW x WH =  720 x 1280      (scenes are rendered here and upscaled 1.5x, like the landscape build)

Import this module first in every Reel script.
"""
import importlib.util
import os
import sys

sys.dont_write_bytecode = True                       # never touch the landscape tools' __pycache__

HERE = os.path.dirname(os.path.abspath(__file__))
REELS = os.path.abspath(os.path.join(HERE, ".."))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))              # chalo_jantar_mantar/
HLT = os.path.join(ROOT, "hinglish_landscape", "tools")

for p in (HLT, HERE):
    if p not in sys.path:
        sys.path.insert(0, p)

if "hl_common" in sys.modules and sys.modules["hl_common"].W != 1080:
    raise RuntimeError("hl_common was imported before rl_common: import rl_common first")
if "hl_common" not in sys.modules:
    _spec = importlib.util.spec_from_file_location("hl_common", os.path.join(HLT, "hl_common.py"))
    _m = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_m)
    _m.W, _m.H, _m.WW, _m.WH = 1080, 1920, 720, 1280
    sys.modules["hl_common"] = _m

import hl_common as C                                 # noqa: E402  (patched copy)

assert (C.W, C.H, C.WW, C.WH) == (1080, 1920, 720, 1280)

# the clip
CLIP_START = 104.0                                    # song seconds (01:44.000)
CLIP_END = 155.0                                      # song seconds (02:35.000)
CLIP_DUR = CLIP_END - CLIP_START                      # 51.000 s
FPS = 30
NFRAMES = int(round(CLIP_DUR * FPS))                  # 1530
