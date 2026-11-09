from collections import defaultdict
from functools import lru_cache

import numpy as np

from produce_config import NEGATIVE_PROMPTS, PRODUCE, UNKNOWN_LABEL

MODEL_NAME = "openai/clip-vit-base-patch32"  # ca. 600 MB, lastes ned første gang


def clip_available():
    """Sann hvis torch og transformers er installert."""
    try:
        import torch  # noqa: F401
        import transformers  # noqa: F401
        return True
    except ImportError:
        return False


@lru_cache(maxsize=1)
def _pipeline():
    """Laster CLIP en gang og gjenbruker den."""
    from transformers import pipeline
    return pipeline("zero-shot-image-classification", model=MODEL_NAME)


def classify(image):
    """Sannsynlighet per grønnsak og for «ukjent», summert over beskrivelsene."""
    # Hvilken grønnsak hver beskrivelse hører til
    owner = {}
    for name, cfg in PRODUCE.items():
        for prompt in cfg["prompts"]:
            owner[prompt] = name
    for prompt in NEGATIVE_PROMPTS:
        owner[prompt] = UNKNOWN_LABEL

    results = _pipeline()(image, candidate_labels=list(owner), hypothesis_template="{}")

    scores = defaultdict(float)
    for r in results:
        scores[owner[r["label"]]] += float(r["score"])
    return dict(scores)


def image_embedding(image):
    """Gjør bildet om til en CLIP-vektor med lengde 1 (brukes av minnet)."""
    import torch

    pipe = _pipeline()
    processor = getattr(pipe, "image_processor", None) or getattr(pipe, "feature_extractor", None)
    inputs = processor(images=image.convert("RGB"), return_tensors="pt")
    inputs = {k: v.to(pipe.model.device) for k, v in inputs.items()}

    with torch.no_grad():
        features = pipe.model.get_image_features(**inputs)

    # Noen versjoner av transformers gir et objekt i stedet for en tensor
    if not torch.is_tensor(features):
        embeds = getattr(features, "image_embeds", None)
        features = embeds if embeds is not None else features.pooler_output

    # Lengde 1 gjør cosinuslikhet til et enkelt prikkprodukt
    vector = features[0].detach().cpu().numpy().astype(np.float32)
    return vector / (np.linalg.norm(vector) + 1e-12)