import json
from functools import lru_cache
from pathlib import Path

import numpy as np

import clip_classifier

ROOT = Path(__file__).resolve().parent
MEMORY_DIR = ROOT / "memory"
SPLIT_DIR = MEMORY_DIR / "splits"

DEFAULT_THRESHOLD = 0.90     # Minste likhet for å bruke et husket svar
DUPLICATE_THRESHOLD = 0.995  # Over dette er det samme bilde


def _normalize(vector):
    """Gjør vektoren om til lengde 1."""
    vector = np.asarray(vector, dtype=np.float32).ravel()
    return vector / (np.linalg.norm(vector) + 1e-12)


class Memory:
    """Vektorer med navn. Uten mappe lagres alt bare i RAM."""

    def __init__(self, folder=None):
        self.folder = Path(folder) if folder else None
        self.vectors = None  # matrise (N, D)
        self.labels = []
        if self.folder is not None:
            self._load()

    def __len__(self):
        return len(self.labels)


    def _load(self):
        """Leser vectors.npy og labels.json hvis de finnes."""
        vec_file = self.folder / "vectors.npy"
        lab_file = self.folder / "labels.json"
        if not (vec_file.exists() and lab_file.exists()):
            return
        try:
            vectors = np.load(vec_file)
            labels = json.loads(lab_file.read_text(encoding="utf-8"))
            if len(vectors) == len(labels) and len(labels) > 0:
                self.vectors = vectors.astype(np.float32)
                self.labels = list(labels)
        except Exception:
            self.vectors, self.labels = None, []

    def _save(self):
        """Skriver vektorer og navn til disk."""
        if self.folder is None:
            return
        self.folder.mkdir(parents=True, exist_ok=True)
        vec_file = self.folder / "vectors.npy"
        lab_file = self.folder / "labels.json"
        if self.vectors is None:
            vec_file.unlink(missing_ok=True)
            lab_file.unlink(missing_ok=True)
            return
        np.save(vec_file, self.vectors)
        lab_file.write_text(json.dumps(self.labels, ensure_ascii=False, indent=2), encoding="utf-8")

    def _similarities(self, vector):
        if self.vectors is None or self.vectors.shape[1] != vector.shape[0]:
            return None
        return self.vectors @ vector  # cosinuslikhet, siden alle har lengde 1

    def add_vector(self, vector, label):
        """Lagrer en vektor med navn."""
        vector = _normalize(vector)
        sims = self._similarities(vector)

        # Samme bilde fra før: oppdater navnet i stedet for å lagre en kopi
        if sims is not None and len(sims) > 0:
            idx = int(np.argmax(sims))
            if sims[idx] >= DUPLICATE_THRESHOLD:
                self.labels[idx] = label
                self._save()
                return

        if self.vectors is None or self.vectors.shape[1] != vector.shape[0]:
            self.vectors = vector[None, :]
            self.labels = [label]
        else:
            self.vectors = np.vstack([self.vectors, vector[None, :]])
            self.labels.append(label)
        self._save()

    def add(self, image, label):
        """Lagrer et utklipp (PIL-bilde) med navn eller oppdeling."""
        self.add_vector(clip_classifier.image_embedding(image), label)

    def lookup_vector(self, vector, threshold=None):
        """Gir (navn, likhet) for det mest like utklippet, eller (None, likhet)."""
        threshold = DEFAULT_THRESHOLD if threshold is None else threshold
        sims = self._similarities(_normalize(vector))
        if sims is None or len(sims) == 0:
            return None, 0.0
        idx = int(np.argmax(sims))
        best = float(sims[idx])
        if best >= threshold:
            return self.labels[idx], best
        return None, best

    def clear(self):
        """Sletter alt i minnet."""
        self.vectors = None
        self.labels = []
        self._save()


@lru_cache(maxsize=1)
def default_memory():
    """Minnet med rettede utklipp (lagres i memory/)."""
    return Memory(MEMORY_DIR)


@lru_cache(maxsize=1)
def default_split_memory():
    """Minnet med oppdelinger (lagres i memory/splits/)."""
    return Memory(SPLIT_DIR)