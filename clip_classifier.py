from collections import defaultdict
from functools import lru_cache

import numpy as np

from produce_config import NEGATIVE_PROMPTS, PRODUCE, UNKNOWN_LABEL

# Navnet på CLIP-modellen vi bruker 
MODEL_NAME = "openai/clip-vit-base-patch32"


def clip_available():
    try:
        import torch  
        import transformers 
        return True
    except ImportError:
        return False


@lru_cache(maxsize=1)
def _pipeline():
    # og at vi gjenbruker den ferdig lastede modellen etterpå (sparer tid).
    from transformers import pipeline
    return pipeline("zero-shot-image-classification", model=MODEL_NAME)


def classify(image):
    # Tar inn et bilde og returnerer hvor sannsynlig det er at det er hver
    owner = {}
    for name, cfg in PRODUCE.items():
        for prompt in cfg["prompts"]:
            owner[prompt] = name
    # "Negative" beskrivelser (ting som ikke er frukt/grønt) havner under "ukjent"
    for prompt in NEGATIVE_PROMPTS:
        owner[prompt] = UNKNOWN_LABEL

    # CLIP sammenligner bildet med alle tekstbeskrivelsene og gir en score til hver
    results = _pipeline()(image, candidate_labels=list(owner), hypothesis_template="{}")

    # Slår sammen scorene per vare (summerer alle beskrivelsene som hører til samme vare)
    scores = defaultdict(float)
    for r in results:
        scores[owner[r["label"]]] += float(r["score"])
    return dict(scores)


def image_embedding(image):
    # Nyttig for å sammenligne bilder med hverandre (likhet mellom bilder).
    import torch

    pipe = _pipeline()
    processor = getattr(pipe, "image_processor", None) or getattr(pipe, "feature_extractor", None)
    inputs = processor(images=image.convert("RGB"), return_tensors="pt")
    inputs = {k: v.to(pipe.model.device) for k, v in inputs.items()}

    # no_grad = vi trener ikke modellen her, bare bruker den (raskere og bruker mindre minne)
    with torch.no_grad():
        features = pipe.model.get_image_features(**inputs)

    if not torch.is_tensor(features):
        embeds = getattr(features, "image_embeds", None)
        features = embeds if embeds is not None else features.pooler_output

    # Gjør om til en vanlig numpy-vektor
    vector = features[0].detach().cpu().numpy().astype(np.float32)
    return vector / (np.linalg.norm(vector) + 1e-12)