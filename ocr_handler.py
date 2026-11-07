import io
import re
from datetime import datetime
import cv2
import easyocr
import numpy as np
import streamlit as st
from PIL import Image, ImageOps, ImageEnhance
from rembg import remove
from data_handler import normalize_text, ingredients_match
import difflib

@st.cache_resource
def load_ocr():
    return easyocr.Reader(["no", "en"], gpu=False)

def find_ingredient_for_text(detected_text, ingredient_records):
    
    detected = normalize_text(detected_text)
    if not detected or len(detected) < 3:
        return None
        
    ingredient_names = [item["name"] for item in ingredient_records]
    
    # Sjekker direkte via ingredients_match
    for item in ingredient_records:
        if ingredients_match(detected, item["name"]):
            return item
            
    # Fuzzy matching (difflib) for å fange opp små skrivefeil eller flertall
    all_names = [normalize_text(n) for n in ingredient_names]
    matches = difflib.get_close_matches(detected, all_names, n=1, cutoff=0.75)
    if matches:
        matched_norm = matches[0]
        for item in ingredient_records:
            if normalize_text(item["name"]) == matched_norm:
                return item
                
    return None

def _build_text_mask(ocr_boxes, width, height):
    mask = np.zeros((height, width), dtype=np.uint8)
    for box, _ in ocr_boxes:
        points = np.array([(int(pt[0]), int(pt[1])) for pt in box], dtype=np.int32)
        cv2.fillPoly(mask, [points], 255)
    
    kernel = np.ones((30, 30), np.uint8)
    mask = cv2.dilate(mask, kernel, iterations=1)
    return mask

@st.cache_data(show_spinner=False)
def analyze_image(image_bytes, ingredient_records):
    original = Image.open(io.BytesIO(image_bytes))
    original = ImageOps.exif_transpose(original).convert("RGB")
    
    # Enkel bildeforbedring med CLAHE
    img_np = np.array(original)
    lab = cv2.cvtColor(img_np, cv2.COLOR_RGB2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    cl = clahe.apply(l)
    enhanced_rgb = cv2.cvtColor(cv2.merge((cl, a, b)), cv2.COLOR_LAB2RGB)
    enhanced_pil = Image.fromarray(enhanced_rgb)
    
    removed = remove(enhanced_pil)
    if not isinstance(removed, Image.Image):
        removed = Image.open(io.BytesIO(removed))
    removed = removed.convert("RGBA")
    
    background = Image.new("RGB", removed.size, (255, 255, 255))
    background.paste(removed, mask=removed.split()[3])
    
    ocr_input_np = np.array(background)
    reader = load_ocr()
    results = reader.readtext(ocr_input_np, detail=1, paragraph=False)
    
    detected_texts = []
    detected_boxes = []
    found_ingredients = {}
    
    for result in results:
        if len(result) < 3:
            continue
        box, text, confidence = result
        text = str(text).strip()
        
        if not text or confidence < 0.40:
            continue
            
        detected_texts.append(text)
        match = find_ingredient_for_text(text, ingredient_records)
        if match:
            name = match["name"]
            found_ingredients[normalize_text(name)] = match
            detected_boxes.append((box, name))
    
    text_mask = _build_text_mask(detected_boxes, original.width, original.height)
    
    return {
        "original": io.BytesIO(image_bytes).getvalue(),
        "removed": background,       
        "removed_pil": removed,     
        "found": list(found_ingredients.values()),
        "ocr_boxes": detected_boxes,
        "ocr_text": list(dict.fromkeys(detected_texts)),
        "text_mask": text_mask,
    }