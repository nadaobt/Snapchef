import argparse
import csv
from collections import Counter, defaultdict
from pathlib import Path

from PIL import Image

import recognizer
from produce_config import PRODUCE

EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
NO_DETECTION = "(ingen)"


def find_images(folder):
    """Finner alle bilder; mappenavnet er fasiten."""
    images = []
    for class_dir in sorted(Path(folder).iterdir()):
        if not class_dir.is_dir() or class_dir.name not in PRODUCE:
            continue
        for path in sorted(class_dir.iterdir()):
            if path.suffix.lower() in EXTENSIONS:
                images.append((class_dir.name, path))
    return images


def set_weights(w_clip):
    """Endrer vektingen mellom CLIP og regelmotoren (summen er alltid 1)."""
    recognizer.W_CLIP = w_clip
    recognizer.W_RULES = 1.0 - w_clip


def run(images, use_clip):
    """Gjenkjenner hvert bilde uten minnet og gir (riktig, gjetning, sti)."""
    rows = []
    for truth, path in images:
        with Image.open(path) as img:
            result = recognizer.recognize(
                img, multi=False, use_clip=use_clip, min_conf=0.0, use_memory=False
            )
        detections = result["detections"]
        guess = detections[0]["best_guess"] if detections else NO_DETECTION
        rows.append((truth, guess, path))
    return rows


def accuracy(rows):
    """Andel riktige i prosent."""
    if not rows:
        return 0.0
    return sum(1 for truth, guess, _ in rows if truth == guess) / len(rows) * 100


def print_report(rows):
    """Skriver treff per grønnsak og vanligste feil."""
    correct = Counter()
    total = Counter()
    confusion = defaultdict(Counter)
    for truth, guess, _ in rows:
        total[truth] += 1
        confusion[truth][guess] += 1
        if guess == truth:
            correct[truth] += 1

    print(f"\n{'Grønnsak':<14}{'Riktig':>8}{'Totalt':>8}{'Treff':>8}  Vanligste feil")
    for name in total:
        wrong = [(g, n) for g, n in confusion[name].most_common() if g != name]
        mistake = f"{wrong[0][0]} ({wrong[0][1]}x)" if wrong else "-"
        print(f"{name:<14}{correct[name]:>8}{total[name]:>8}{correct[name] / total[name] * 100:>7.0f}%  {mistake}")

    print(f"\nTotal treffsikkerhet: {accuracy(rows):.0f}% på {len(rows)} bilder")


def save_csv(rows, filename):
    """Lagrer ett resultat per bilde i en CSV-fil."""
    with open(filename, "w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["riktig", "gjetning", "korrekt", "fil"])
        for truth, guess, path in rows:
            writer.writerow([truth, guess, truth == guess, str(path)])
    print(f"Resultatene er lagret i {filename}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("folder", help="mappe med en undermappe per grønnsak")
    parser.add_argument("--no-clip", action="store_true", help="bruk kun regelmotoren")
    parser.add_argument("--w-clip", type=float, default=None, help="vekt for CLIP mellom 0 og 1 (standard 0.65)")
    parser.add_argument("--compare-weights", action="store_true", help="prøv flere vekter og sammenlign")
    parser.add_argument("--save", default=None, help="lagre resultatene i en CSV-fil")
    args = parser.parse_args()

    images = find_images(args.folder)
    if not images:
        print("Fant ingen bilder. Sjekk mappestrukturen.")
        return

    use_clip = not args.no_clip

    if args.compare_weights:
        if not use_clip:
            print("--compare-weights krever CLIP. Fjern --no-clip.")
            return
        print(f"Sammenligner vekter på {len(images)} bilder (tar litt tid)...\n")
        print(f"{'W_CLIP':>8}{'W_RULES':>9}{'Treff':>8}")
        # Prøver flere vekter og husker den beste
        best = None
        for w in (0.0, 0.25, 0.5, 0.65, 0.8, 1.0):
            set_weights(w)
            score = accuracy(run(images, use_clip=True))
            print(f"{w:>8.2f}{1 - w:>9.2f}{score:>7.0f}%")
            if best is None or score > best[1]:
                best = (w, score)
        print(f"\nBeste vekt: W_CLIP = {best[0]:.2f} ({best[1]:.0f}% treff)")
        return

    if args.w_clip is not None:
        set_weights(args.w_clip)
    if use_clip:
        print(f"Vekting: W_CLIP = {recognizer.W_CLIP:.2f}, W_RULES = {recognizer.W_RULES:.2f}")
    else:
        print("Kun regelmotoren (uten CLIP)")

    rows = run(images, use_clip)
    print_report(rows)
    if args.save:
        save_csv(rows, args.save)


if __name__ == "__main__":
    main()