"""Brand tokens: palettes + fonts. Palettes are *candidates* until the channel owner approves one."""
import os

FONT_DIR = os.environ.get("MB_FONT_DIR", os.path.join(os.path.dirname(__file__), "..", "assets", "fonts"))


def font_path(name):
    return os.path.join(FONT_DIR, name)


FONTS = {
    "caption": "Poppins-ExtraBold.ttf",
    "caption_active": "Poppins-Black.ttf",
    "title": "Poppins-Black.ttf",
    "label": "Poppins-SemiBold.ttf",
    "body": "Poppins-Medium.ttf",
    "display": "BebasNeue-Regular.ttf",
}


def hex2rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


# name -> tokens. No blue anywhere (owner request).
PALETTES = {
    "volt": {
        "label": "Volt Lime on Graphite",
        "accent": "#C6F432", "accent2": "#FF5C39",
        "bg0": "#0A0D0B", "bg1": "#18221B", "on_accent": "#0A0D0B", "text": "#FFFFFF",
    },
    "amber": {
        "label": "Amber Gold on Warm Black",
        "accent": "#FFC233", "accent2": "#FF6A2B",
        "bg0": "#0F0B07", "bg1": "#241A10", "on_accent": "#14100A", "text": "#FFFFFF",
    },
    "sunset": {
        "label": "Sunset Coral on Deep Plum",
        "accent": "#FF6B4A", "accent2": "#FFC24B",
        "bg0": "#14081B", "bg1": "#2E1033", "on_accent": "#1A0A1F", "text": "#FFFFFF",
    },
    "emerald": {
        "label": "Emerald Mint on Forest Black",
        "accent": "#22E3A0", "accent2": "#FFD23F",
        "bg0": "#05110D", "bg1": "#0B2B20", "on_accent": "#04120D", "text": "#FFFFFF",
    },
    "magenta": {
        "label": "Hot Magenta on Ink Black",
        "accent": "#FF3D9A", "accent2": "#FF9A3D",
        "bg0": "#0B090B", "bg1": "#2A1325", "on_accent": "#14060F", "text": "#FFFFFF",
    },
    "crimson": {
        "label": "Crimson Red on Graphite",
        "accent": "#FF3347", "accent2": "#FF8F5A",
        "bg0": "#0C0B0B", "bg1": "#2B1819", "on_accent": "#190508", "text": "#FFFFFF",
    },
    "orchid": {
        "label": "Orchid Violet on Midnight Plum",
        "accent": "#C65CFF", "accent2": "#FFB36B",
        "bg0": "#0C0710", "bg1": "#26123A", "on_accent": "#14071F", "text": "#FFFFFF",
    },
}
