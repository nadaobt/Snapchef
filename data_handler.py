import json
import re
from pathlib import Path
import streamlit as st

BASE_DIR = Path(__file__).resolve().parent
INGREDIENTS_FILE = BASE_DIR / "ingredients.json"
RECIPES_FILE = BASE_DIR / "recipes.json"

# Synonymer og engelske navn per ingrediens (nøkler med små bokstaver og æøå)
SYNONYM_MAP = {
    "melk": ["melk", "lettmelk", "helmelk", "skummetmelk"],
    "mel": ["mel", "hvetemel", "siktet hvetemel"],
    "løk": ["løk", "gulløk", "onion"],
    "hvitløk": ["hvitløk", "garlic"],
    "eple": ["eple", "epler"],
    "tomat": ["tomat", "tomater", "tomato"],
    "gulrot": ["gulrot", "gulrotter", "carrot"],
    "potet": ["potet", "poteter"],
}

# Leser JSON; modified_time fornyer cachen når filen endres
@st.cache_data
def read_json(path, modified_time):
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)

# Små bokstaver, uten spesialtegn og doble mellomrom
def normalize_text(text):
    text = str(text or "").casefold().strip()
    text = text.replace("-", " ")
    text = re.sub(r"[^\w\s]", " ", text)  # \w dekker også æ, ø og å
    text = re.sub(r"\s+", " ", text)
    return text.strip()

# Sann hvis teksten matcher ingrediensen (eksakt, synonym eller helt ord)
def ingredients_match(detected_text, ingredient_name):
    det_norm = normalize_text(detected_text)
    ing_norm = normalize_text(ingredient_name)

    if not det_norm or not ing_norm:
        return False

    if det_norm == ing_norm:
        return True

    synonyms = SYNONYM_MAP.get(ing_norm, [])
    for syn in synonyms:
        if re.search(r"\b" + re.escape(syn) + r"\b", det_norm):
            return True

    pattern = r"\b" + re.escape(ing_norm) + r"\b"
    return bool(re.search(pattern, det_norm))

# Leser ingredienslisten og fjerner duplikater
def load_ingredients():
    if not INGREDIENTS_FILE.exists():
        st.error(f"Fant ikke filen: {INGREDIENTS_FILE.name}")
        return []

    try:
        data = read_json(str(INGREDIENTS_FILE), INGREDIENTS_FILE.stat().st_mtime)
    except Exception as error:
        st.error(f"Kunne ikke lese ingredients.json: {error}")
        return []

    if isinstance(data, dict):
        data = data.get("ingredients", data.get("ingredienser", []))

    if not isinstance(data, list):
        st.error("ingredients.json ma inneholde en liste.")
        return []

    ingredients = []
    seen = set()

    for item in data:
        if isinstance(item, str):
            name = item
            category = "Annet"
        elif isinstance(item, dict):
            name = item.get("name") or item.get("ingredienser") or item.get("ingrediens") or item.get("ingredient") or item.get("tittel") or ""
            category = item.get("category") or item.get("catagory") or item.get("kategori") or "Annet"
        else:
            continue

        name = str(name).strip()
        category = str(category).strip()
        if not name:
            continue

        normalized_name = normalize_text(name)
        if normalized_name in seen:
            continue
        seen.add(normalized_name)

        ingredients.append({"name": name, "category": category})

    return ingredients

# Leser oppskriftene og gir feltene like navn
def load_recipes():
    if not RECIPES_FILE.exists():
        st.warning(f"Fant ikke filen: {RECIPES_FILE.name}")
        return []

    try:
        data = read_json(str(RECIPES_FILE), RECIPES_FILE.stat().st_mtime)
    except Exception as error:
        st.error(f"Kunne ikke lese recipes.json: {error}")
        return []

    if isinstance(data, dict):
        data = data.get("recipes", data.get("oppskrifter", []))

    if not isinstance(data, list):
        st.error("recipes.json ma inneholde en liste.")
        return []

    recipes = []

    for item in data:
        if not isinstance(item, dict):
            continue

        title = item.get("tittel") or item.get("name") or item.get("title") or "Oppskrift uten navn"
        raw_ingredients = item.get("ingredienser") or item.get("ingredients") or []
        if isinstance(raw_ingredients, str):
            raw_ingredients = [raw_ingredients]

        ingredient_names = []
        for ingredient in raw_ingredients:
            if isinstance(ingredient, str):
                ingredient_names.append(ingredient)
            elif isinstance(ingredient, dict):
                name = ingredient.get("name") or ingredient.get("ingrediens") or ingredient.get("ingredient") or ingredient.get("navn")
                if name:
                    ingredient_names.append(str(name))

        ingredients_with_amount = item.get("ingredienser_med_mengde") or item.get("ingredients_with_amount") or []
        if isinstance(ingredients_with_amount, str):
            ingredients_with_amount = [ingredients_with_amount]

        instructions = item.get("instruksjoner") or item.get("instructions") or item.get("fremgangsmate") or []
        if isinstance(instructions, str):
            instructions = [instructions]

        nutrition = item.get("naeringsinnhold_per_porsjon") or item.get("nutrition") or {}

        recipes.append({
            "id": item.get("id", ""),
            "title": str(title),
            "category": item.get("kategori") or item.get("category") or "Annet",
            "cuisine": item.get("kjokken") or item.get("cuisine") or "Internasjonal",
            "allergies": item.get("allergier") or item.get("allergies") or [],
            "nutrition": nutrition,
            "time": item.get("tilberedningstid_min") or item.get("tilberedningstid_minutter") or item.get("preparation_time") or item.get("time"),
            "portions": item.get("porsjoner") or item.get("portions") or 1,
            "ingredients": ingredient_names,
            "ingredients_with_amount": ingredients_with_amount,
            "instructions": instructions,
            "image_url": item.get("bilde_url") or item.get("image_url") or "",
        })

    return recipes

# Ganger alle tall i mengden med porsjonsfaktoren
def scale_amount_string(mengde_str, factor):
    if factor == 1.0 or not mengde_str:
        return mengde_str

    def replace_num(match):
        val = float(match.group(0))
        new_val = val * factor
        if new_val.is_integer():
            return str(int(new_val))
        return f"{new_val:.1f}".rstrip("0").rstrip(".")

    return re.sub(r"\b\d+(?:\.\d+)?\b", replace_num, str(mengde_str))

# Finner passende oppskrifter, sortert etter flest treff
def find_matching_recipes(recipes, selected_ingredients, selected_cuisine="Alle", selected_allergies=None):
    if selected_allergies is None:
        selected_allergies = []

    matches = []

    for recipe in recipes:
        if selected_cuisine != "Alle" and recipe["cuisine"] != selected_cuisine:
            continue

        # Oppskriften må ha alle valgte kostholdsmerker
        if selected_allergies:
            if any(allergy not in recipe["allergies"] for allergy in selected_allergies):
                continue

        recipe_ingredients = recipe["ingredients"]
        matched = []
        missing = []

        for recipe_ing in recipe_ingredients:
            if any(ingredients_match(recipe_ing, sel_ing) for sel_ing in selected_ingredients):
                matched.append(recipe_ing)
            else:
                missing.append(recipe_ing)

        if matched:
            unique_total = len(set(normalize_text(ri) for ri in recipe_ingredients))
            unique_matched = len(set(normalize_text(m) for m in matched))
            percentage = unique_matched / unique_total * 100 if unique_total else 0

            matches.append({
                "recipe": recipe,
                "matched": list(dict.fromkeys(matched)),
                "missing": list(dict.fromkeys(missing)),
                "percentage": percentage,
                "count": unique_matched,
            })

    matches.sort(
        key=lambda result: (result["count"], result["percentage"]),
        reverse=True,
    )

    return matches