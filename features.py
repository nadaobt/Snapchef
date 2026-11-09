import numpy as np
import cv2

# Fargeboksene histogrammet bruker (samme navn som i produce_config.py)
COLOR_NAMES = ["red", "orange", "yellow", "green", "blue", "purple", "brown", "white", "dark"]


def color_histogram(rgb_img, mask):
    """Andel piksler i hver fargeboks (HSV); summen blir 1."""
    hsv = cv2.cvtColor(rgb_img, cv2.COLOR_RGB2HSV)
    # int16 for trygge sammenligninger
    h, s, v = [channel.astype(np.int16) for channel in cv2.split(hsv)]

    valid_pixels = mask & (s > 10)  # Hopp over grå piksler
    total_valid = int(np.sum(valid_pixels))

    if total_valid == 0:
        return {name: 0 for name in COLOR_NAMES}

    h = h[valid_pixels]
    s = s[valid_pixels]
    v = v[valid_pixels]

    # Rekkefølgen er viktig: mørk, hvit og brun sjekkes før fargetonen
    # 1. Mørke piksler (f.eks. aubergine, avokado)
    dark = v < 50
    # 2. Nesten hvite piksler (f.eks. blomkål, hvitløk)
    white = ~dark & (v > 220) & (s < 30)
    # 3. Brun: oransje fargetone, men mørk (f.eks. potet, kiwi)
    brown = ~dark & ~white & (h >= 10) & (h < 25) & (s > 100) & (v < 120)
    # 4. Resten sorteres etter fargetone (H går fra 0 til 180)
    rest = ~(dark | white | brown)

    groups = {
        "dark": dark,
        "white": white,
        "brown": brown,
        "red": rest & ((h < 10) | (h >= 160)),  # 160-180 regnes også som rødlig
        "orange": rest & (h >= 10) & (h < 22),
        "yellow": rest & (h >= 22) & (h < 35),
        "green": rest & (h >= 35) & (h < 85),
        "blue": rest & (h >= 85) & (h < 130),
        "purple": rest & (h >= 130) & (h < 160),
    }

    # Normaliser slik at summen blir 1.0
    return {name: float(np.sum(groups[name])) / total_valid for name in COLOR_NAMES}


def aspect_ratio(mask):
    """Lengste side delt på korteste (1 = rundt, høyt tall = avlangt)."""
    ys, xs = np.where(mask)
    if len(xs) == 0 or len(ys) == 0:
        return 1.0
    w = xs.max() - xs.min() + 1
    h = ys.max() - ys.min() + 1
    return float(max(w, h)) / float(min(w, h))