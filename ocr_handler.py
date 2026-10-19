import io
import re
from difflib import SequenceMatcher
import cv2
import easyocr
import numpy as np
import streamlit as st
from PIL import Image, ImageDraw, ImageOps
from rembg import remove
from data_handler import normalize_text, ingredients_match

@st.cache_resource
def load_ocr():
    """Laster inn EasyOCR-leseren for norsk og engelsk."""
    return easyocr.Reader(["no", "en"], gpu=False)

def make_ocr_variants(image):
    """Lager ulike bildevarianter (kontrast, gråtoner, terskel) for å styrke OCR-treff[cite: 1]."""
    image_array = np.array(image.convert("RGB"))
    gray = cv2.cvtColor(image_array, cv2.COLOR_RGB2GRAY)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)
    _, threshold = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    adaptive = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 11)
    return [image_array, enhanced, threshold, adaptive]

def find_ingredient_for_text(detected_text, ingredient_records):
    """Matcher oppdaget OCR-tekst mot kjente ingredienser ved hjelp av eksakt treff og fuzzy-matching."""
    detected = normalize_text(detected_text)
    if not detected or len(detected) < 2:
        return None

    exact_matches = []
    for item in ingredient_records:
        name = item["name"]
        norm_name = normalize_text(name)
        if norm_name == "mel" and "melk" in detected:
            continue
        pattern = r"(?<!\w)" + re.escape(norm_name) + r"(?!\w)"
        if re.search(pattern, detected) or ingredients_match(detected, name):
            exact_matches.append(item)

    if exact_matches:
        return max(exact_matches, key=lambda item: len(normalize_text(item["name"])))

    words = detected.split()
    possible_texts = [detected]
    for window_size in range(1, min(4, len(words)) + 1):
        for start in range(len(words) - window_size + 1):
            possible_texts.append(" ".join(words[start:start + window_size]))

    best_match = None
    best_score = 0.0

    for item in ingredient_records:
        name = item["name"]
        normalized_name = normalize_text(name)
        if len(normalized_name) < 4:
            continue
        for candidate_text in possible_texts:
            score = SequenceMatcher(None, normalized_name, candidate_text).ratio()
            if score > best_score:
                best_score = score
                best_match = item

    if best_score >= 0.82:
        return best_match
    return None

def make_annotated_image(image, boxes):
    """Tegner grønne markeringsbokser rundt gjenkjente ingredienser på bildet."""
    annotated = image.convert("RGBA")
    draw = ImageDraw.Draw(annotated)

    for box, label in boxes:
        points = [(int(point[0]), int(point[1])) for point in box]
        draw.polygon(points, outline=(0, 220, 90, 255), width=4)
        left = min(point[0] for point in points)
        top = min(point[1] for point in points)
        text_box = draw.textbbox((left, top), label)
        text_width = text_box[2] - text_box[0]
        text_height = text_box[3] - text_box[1]
        label_top = max(0, top - text_height - 10)

        draw.rectangle((left, label_top, left + text_width + 10, label_top + text_height + 8), fill=(0, 150, 60, 230))
        draw.text((left + 5, label_top + 3), label, fill=(255, 255, 255, 255))

    return annotated

@st.cache_data(show_spinner=False)
def analyze_image(image_bytes, ingredient_records):
    """Hovedfunksjon som fjerner bakgrunn, kjører OCR og finner ingredienser i bildet[cite: 1]."""
    original = Image.open(io.BytesIO(image_bytes))
    original = ImageOps.exif_transpose(original).convert("RGB")

    removed = remove(original)
    if not isinstance(removed, Image.Image):
        removed = Image.open(io.BytesIO(removed))
    removed = removed.convert("RGBA")

    reader = load_ocr()
    variants = make_ocr_variants(original)

    detected_texts = []
    detected_boxes = []
    found_ingredients = {}
    best_text_for_ingredient = {}

    for variant in variants:
        results = reader.readtext(variant, detail=1, paragraph=False)
        for result in results:
            if len(result) < 3:
                continue
            box, text, confidence = result
            text = str(text).strip()
            if not text:
                continue
            if confidence >= 0.20:
                detected_texts.append(text)
            if confidence < 0.20:
                continue

            match = find_ingredient_for_text(text, ingredient_records)
            if match is None:
                continue

            name = match["name"]
            key = normalize_text(name)
            found_ingredients[key] = match
            detected_boxes.append((box, name))

            previous_score = best_text_for_ingredient.get(key, 0)
            if confidence > previous_score:
                best_text_for_ingredient[key] = confidence

    unique_texts = list(dict.fromkeys(detected_texts))
    unique_boxes = []
    seen_boxes = set()

    for box, name in detected_boxes:
        key = (normalize_text(name), tuple((int(point[0]), int(point[1])) for point in box))
        if key not in seen_boxes:
            seen_boxes.add(key)
            unique_boxes.append((box, name))

    annotated = make_annotated_image(removed, unique_boxes)

    original_buffer = io.BytesIO()
    original.save(original_buffer, format="PNG")
    removed_buffer = io.BytesIO()
    removed.save(removed_buffer, format="PNG")
    annotated_buffer = io.BytesIO()
    annotated.save(annotated_buffer, format="PNG")

    return {
        "original": original_buffer.getvalue(),
        "removed": removed_buffer.getvalue(),
        "annotated": annotated_buffer.getvalue(),
        "found": list(found_ingredients.values()),
        "ocr_text": unique_texts,
    }