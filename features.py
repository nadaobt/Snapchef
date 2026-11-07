import numpy as np
import cv2


def color_histogram(rgb_img, mask):
    """
    Beregner fargefordelingen for pikslene i masken.
    """
    hsv = cv2.cvtColor(rgb_img, cv2.COLOR_RGB2HSV)
    h, s, v = cv2.split(hsv)

    valid_pixels = mask & (s > 10)  # Fjern helt grå/hvite bakgrunnsrester
    total_valid = np.sum(valid_pixels)

    bins = {
        "red": 0, "orange": 0, "yellow": 0, "green": 0,
        "blue": 0, "purple": 0, "brown": 0, "white": 0, "dark": 0
    }

    if total_valid == 0:
        return bins

    h_v = h[valid_pixels]
    s_v = s[valid_pixels]
    v_v = v[valid_pixels]

    for hi, si, vi in zip(h_v, s_v, v_v):
        if vi < 50:
            # 1. Mørke piksler 
            bins["dark"] += 1
        elif vi > 220 and si < 30:
            # 2. Nesten hvite piksler 
            bins["white"] += 1
        elif 10 <= hi < 25 and si > 100 and vi < 120:
            # 3. Brun = oransje/gul fargetone, men mørk
            bins["brown"] += 1
        else:
            # 4. Fargetone 
            if hi < 10 or hi > 170:
                bins["red"] += 1
            elif hi < 22:
                bins["orange"] += 1
            elif hi < 35:
                bins["yellow"] += 1
            elif hi < 85:
                bins["green"] += 1
            elif hi < 130:
                bins["blue"] += 1
            elif hi < 160:
                bins["purple"] += 1
            else:
                bins["red"] += 1  # 160-170 regnes som rødlig

    # Normaliser slik at summen blir 1.0
    return {k: count / total_valid for k, count in bins.items()}


def aspect_ratio(mask):
    """Hvor avlangt objektet er: lengste side / korteste side av boksen rundt masken."""
    ys, xs = np.where(mask)
    if len(xs) == 0 or len(ys) == 0:
        return 1.0
    w = xs.max() - xs.min() + 1
    h = ys.max() - ys.min() + 1
    return float(max(w, h)) / float(min(w, h))