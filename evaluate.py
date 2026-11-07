import argparse
from collections import Counter, defaultdict
from pathlib import Path

from PIL import Image

import recognizer
from produce_config import PRODUCE

EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("folder")
    parser.add_argument("--no-clip", action="store_true")
    args = parser.parse_args()

    correct = Counter()
    total = Counter()
    confusion = defaultdict(Counter)

    for class_dir in sorted(Path(args.folder).iterdir()):
        if not class_dir.is_dir() or class_dir.name not in PRODUCE:
            continue
        for path in sorted(class_dir.iterdir()):
            if path.suffix.lower() not in EXTENSIONS:
                continue
            result = recognizer.recognize(Image.open(path), multi=False, use_clip=not args.no_clip, min_conf=0.0)
            guess = result["detections"][0]["best_guess"]
            total[class_dir.name] += 1
            # Lagrer hva programmet gjettet, slik at vi kan se hva som blir forvekslet med hva
            confusion[class_dir.name][guess] += 1
            if guess == class_dir.name:
                correct[class_dir.name] += 1

    if not total:
        print("Fant ingen bilder. Sjekk mappestrukturen.")
        return

    print(f"\n{'Grønnsak':<14}{'Riktig':>8}{'Totalt':>8}{'Treff':>8}  Vanligste feil")
    for name in total:
        wrong = [(g, n) for g, n in confusion[name].most_common() if g != name]
        mistake = f"{wrong[0][0]} ({wrong[0][1]}x)" if wrong else "-"
        print(f"{name:<14}{correct[name]:>8}{total[name]:>8}{correct[name] / total[name] * 100:>7.0f}%  {mistake}")

    overall = sum(correct.values()) / sum(total.values()) * 100
    print(f"\nTotal treffsikkerhet: {overall:.0f}% på {sum(total.values())} bilder")


if __name__ == "__main__":
    main()
