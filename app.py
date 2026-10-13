import streamlit as st
from data_handler import load_ingredients, load_recipes, find_matching_recipes, ingredients_match, normalize_text
from ocr_handler import analyze_image

# Setter opp nettsidens layout og tittel
st.set_page_config(
    page_title="Snapchef",
    layout="wide",
)

st.title("Snapchef")
st.write("Last opp et bilde, finn ingrediensene og oppdag oppskrifter.")

# Laster inn ingredienser og oppskrifter fra datafiler
ingredients = load_ingredients()
recipes = load_recipes()

if not ingredients:
    st.warning("Ingredienslisten er tom. Kontroller ingredients.json.")

ingredient_names = [item["name"] for item in ingredients]

# Grensesnitt for bildeopplasting
uploaded_file = st.file_uploader(
    "Last opp et bilde med tekst eller ingredienser på emballasjen",
    type=["png", "jpg", "jpeg", "webp"],
)

analysis_result = None

# Utfører bildeanalyse hvis brukeren har lastet opp et bilde
if uploaded_file is not None:
    image_bytes = uploaded_file.getvalue()
    ingredient_records = tuple(
        {"name": item["name"], "category": item["category"]}
        for item in ingredients
    )

    try:
        with st.spinner("Analyserer bildet, fjerner bakgrunnen og leser tekst..."):
            analysis_result = analyze_image(image_bytes, ingredient_records)

        st.success("Bildeanalysen er ferdig!")

        col1, col2, col3 = st.columns(3)

        # Viser originalbilde, bilde uten bakgrunn og markert bilde side om side
        with col1:
            st.subheader("1. Original")
            st.image(analysis_result["original"], use_container_width=True)
            st.download_button("Last ned original", data=analysis_result["original"], file_name="original.png", mime="image/png")

        with col2:
            st.subheader("2. Bakgrunn fjernet")
            st.image(analysis_result["removed"], use_container_width=True)
            st.download_button("Last ned uten bakgrunn", data=analysis_result["removed"], file_name="uten_bakgrunn.png", mime="image/png")

        with col3:
            st.subheader("3. Gjenkjent tekst")
            st.image(analysis_result["annotated"], use_container_width=True)
            st.download_button("Last ned markert bilde", data=analysis_result["annotated"], file_name="markert.png", mime="image/png")

        st.subheader("Ingredienser funnet av OCR")
        if analysis_result["found"]:
            for item in analysis_result["found"]:
                st.write(f"- {item['name']} ({item['category']})")
        else:
            st.info("Ingen ingredienser ble gjenkjent automatisk. Du kan velge ingredienser manuelt nedenfor.")

        with st.expander("Vis all tekst OCR fant"):
            if analysis_result["ocr_text"]:
                for text in analysis_result["ocr_text"]:
                    st.write(f"- {text}")
            else:
                st.write("OCR fant ingen tekst.")

    except Exception as error:
        st.error("Bildet kunne ikke analyseres. Kontroller at nødvendige biblioteker er installert.")
        with st.expander("Vis teknisk feilmelding"):
            st.code(str(error))

st.divider()
st.subheader("Velg ingrediensene dine")

automatically_found = []
if analysis_result is not None:
    automatically_found = [item["name"] for item in analysis_result["found"]]

valid_defaults = [name for name in automatically_found if name in ingredient_names]

# Multiselect-boks hvor brukeren kan velge eller legge til ingredienser manuelt
selected_ingredients = st.multiselect(
    "Ingredienser (du kan også legge til flere manuelt)",
    options=ingredient_names,
    default=valid_defaults,
    placeholder="Søk etter for eksempel melk eller mel...",
)

st.caption("Automatisk gjenkjenning er basert på tekst i bildet. Snapchef kan ikke sikkert identifisere matvarer bare ut fra utseendet.")

st.divider()
st.subheader("Oppskrifter som passer")

# Viser oppskrifter som matcher de valgte ingrediensene
if not recipes:
    st.info("Ingen oppskrifter er tilgjengelige. Kontroller recipes.json.")
elif not selected_ingredients:
    st.info("Last opp et bilde eller velg minst én ingrediens for å finne passende oppskrifter.")
else:
    matching_recipes = find_matching_recipes(recipes, selected_ingredients)

    if not matching_recipes:
        st.warning("Ingen oppskrifter matcher ingrediensene du har valgt.")

    for result in matching_recipes:
        recipe = result["recipe"]

        with st.expander(f"{recipe['title']} — {result['count']} ingrediens(er) matcher"):
            st.write(f"**Kategori:** {recipe['category']}")

            if recipe["time"]:
                st.write(f"**Tilberedningstid:** {recipe['time']} minutter")

            if recipe["portions"]:
                st.write(f"**Porsjoner:** {recipe['portions']}")

            st.progress(min(100, int(result["percentage"])))
            st.write(f"**Ingrediensmatch:** {result['percentage']:.0f} %")

            if recipe["image_url"]:
                st.image(recipe["image_url"], use_container_width=True)

            st.write("**Ingredienser i oppskriften:**")
            for ingredient in recipe["ingredients"]:
                is_selected = any(ingredients_match(ingredient, sel) for sel in selected_ingredients)
                if is_selected:
                    st.write(f"- [OK] {ingredient}")
                else:
                    st.write(f"- [ ] {ingredient}")

            if recipe["ingredients_with_amount"]:
                st.write("**Mengder:**")
                for ingredient in recipe["ingredients_with_amount"]:
                    if isinstance(ingredient, dict):
                        name = ingredient.get("name") or ingredient.get("ingrediens") or ingredient.get("ingredient") or ""
                        amount = ingredient.get("mengde") or ingredient.get("amount") or ""
                        unit = ingredient.get("enhet") or ingredient.get("unit") or ""
                        st.write(f"- {name}: {amount} {unit}".strip())
                    else:
                        st.write(f"- {ingredient}")

            if recipe["instructions"]:
                st.write("**Fremgangsmåte:**")
                for index, instruction in enumerate(recipe["instructions"], start=1):
                    st.write(f"{index}. {instruction}")

            if result["missing"]:
                st.write("**Ingredienser du kanskje mangler:** " + ", ".join(result["missing"]))