import json
import re
from difflib import SequenceMatcher
from pathlib import Path
import streamlit as st

# Setter opp stier til mapper og filer for data
BASE_DIR = Path(__file__).resolve().parent
INGREDIENTS_FILE = BASE_DIR / "ingredients.json"
RECIPES_FILE = BASE_DIR / "recipes.json"

@st.cache_data
def read_json(path, modified_time):
    """Hjelpefunksjon for å lese JSON-filer effektivt med Streamlit-caching."""
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)

def normalize_text(text):
    """Gjør tekst enklere å sammenligne ved å fjerne store bokstaver, spesialtegn og mellomrom."""
    text = str(text or "").casefold().strip()
    text = text.replace("-", " ")
    text = re.sub(r"[^\w\sæøå]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()

def ingredients_match(ing_a, ing_b):
    """Sjekker om to ingredienser matcher, med unntak for misvisende ord som mel og melk."""
    a = normalize_text(ing_a)
    b = normalize_text(ing_b)
    if not a or not b:
        return False
    if a == b:
        return True
    if a in b or b in a:
        if a == "mel" and ("melk" in b or "melk" in a):
            return False
        if b == "mel" and ("melk" in a or "melk" in b):
            return False
        return True
    return False

def load_ingredients():
    """Laster inn og renser ingredienslisten fra ingredients.json[cite: 1, 2]."""
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
        st.error("ingredients.json må inneholde en liste.")
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

def load_recipes():
    """Laster inn og strukturerer oppskrifter fra recipes.json[cite: 1, 3]."""
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
        st.error("recipes.json må inneholde en liste.")
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

        instructions = item.get("instruksjoner") or item.get("instructions") or item.get("fremgangsmåte") or []
        if isinstance(instructions, str):
            instructions = [instructions]

        recipes.append({
            "id": item.get("id", ""),
            "title": str(title),
            "category": item.get("kategori") or item.get("category") or "Annet",
            "time": item.get("tilberedningstid_min") or item.get("tilberedningstid_minutter") or item.get("preparation_time") or item.get("time"),
            "portions": item.get("porsjoner") or item.get("portions"),
            "ingredients": ingredient_names,
            "ingredients_with_amount": ingredients_with_amount,
            "instructions": instructions,
            "image_url": item.get("bilde_url") or item.get("image_url") or "",
        })

    return recipes

def find_matching_recipes(recipes, selected_ingredients):
    """Sammenligner brukerens valgte ingredienser med oppskrifter og beregner matchprosent."""
    matches = []

    for recipe in recipes:
        recipe_ingredients = recipe["ingredients"]
        matched = []
        missing = []

        for recipe_ing in recipe_ingredients:
            is_matched = False
            for sel_ing in selected_ingredients:
                if ingredients_match(recipe_ing, sel_ing):
                    is_matched = True
                    break
            if is_matched:
                matched.append(recipe_ing)
            else:
                missing.append(recipe_ing)

        if matched:
            percentage = (
                len(set(normalize_text(m) for m in matched)) / len(set(normalize_text(ri) for ri in recipe_ingredients)) * 100
                if recipe_ingredients
                else 0
            )

            matches.append({
                "recipe": recipe,
                "matched": list(dict.fromkeys(matched)),
                "missing": list(dict.fromkeys(missing)),
                "percentage": percentage,
                "count": len(set(normalize_text(m) for m in matched)),
            })

    # Sorterer oppskriftene etter flest treff og høyest matchprosent
    matches.sort(
        key=lambda result: (result["count"], result["percentage"]),
        reverse=True,
    )

    return matches