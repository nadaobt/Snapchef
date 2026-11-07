import math
from produce_config import PRODUCE

# Farge er viktigere enn form for grønnsaker
COLOR_WEIGHT = 0.70
SHAPE_WEIGHT = 0.30
SOFTMAX_TEMPERATURE = 10.0  # Høyere = skarpere forskjell mellom beste og dårligste
NEUTRAL_SCORE = 0.5         # Brukes hvis en råvare mangler farger eller form

# Skriv en advarsel en gang hvis noen råvarer mangler felt
_missing = [name for name, cfg in PRODUCE.items() if "colors" not in cfg or "aspect" not in cfg]
if _missing:
    print(f"[rules.py] Advarsel: disse råvarene mangler 'colors' eller 'aspect' i produce_config.py: {_missing}")


def _intersection(observed, expected):
    keys = set(observed) | set(expected)
    return sum(min(observed.get(k, 0.0), expected.get(k, 0.0)) for k in keys)


def _shape_score(aspect, low, high):
    # Innenfor forventet form gir full score 
    if low <= aspect <= high:
        return 1.0
    # Utenfor området synker scoren raskt jo lenger unna formen er 
    ratio = aspect / low if aspect < low else high / aspect
    return max(ratio, 0.0) ** 2


def raw_scores(histogram, aspect):
    scores = {}
    for name, cfg in PRODUCE.items():
        profiles = cfg.get("colors") or []
        color = max((_intersection(histogram, p) for p in profiles), default=NEUTRAL_SCORE)

        aspect_range = cfg.get("aspect")
        shape = _shape_score(aspect, *aspect_range) if aspect_range else NEUTRAL_SCORE

        scores[name] = COLOR_WEIGHT * color + SHAPE_WEIGHT * shape
    return scores


def normalized(histogram, aspect):
    scores = raw_scores(histogram, aspect)
    exps = {k: math.exp(v * SOFTMAX_TEMPERATURE) for k, v in scores.items()}
    total = sum(exps.values())
    return {k: v / total for k, v in exps.items()}