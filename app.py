import json
import time
import uuid
import hashlib
from pathlib import Path

import numpy as np
import cv2
import streamlit as st
from PIL import Image

from data_handler import load_ingredients, load_recipes, find_matching_recipes, scale_amount_string
from ocr_handler import analyze_image
import recognizer
import memory
from produce_config import PRODUCE

# Stier
ROOT = Path(__file__).resolve().parent
DATASET_DIR = ROOT / "dataset"

# Farger for tegning (RGB)
OCR_COLOR = (0, 220, 90)     # grønn: tekst
VEG_COLOR = (0, 120, 255)    # blå: grønnsaker

# Sideoppsett
st.set_page_config(
    page_title="Snapchef",
    layout="wide",
)

# Tittel og introduksjonstekst
st.title("Snapchef")
st.write("Bildeanalyse: 1. Original -> 2. Kvalitetsforbedring og bakgrunnsfjerning -> 3. Annotert med OCR og grønnsaker")

# Sidemeny for minnet
with st.sidebar:
    st.header("Minne")
    mem = memory.default_memory()
    split_mem = memory.default_split_memory()
    st.write(f"Husker {len(mem)} rettede utklipp og {len(split_mem)} oppdelinger.")
    st.caption(
        "Når du retter en grønnsak eller deler opp et utklipp, husker systemet det "
        "neste gang den ser noe som ligner."
    )
    # Slett lagrede oppdelinger
    if st.button("Glem oppdelinger"):
        split_mem.clear()
        st.session_state.pop("analysis_cache_hash", None)
        st.rerun()
    # Tøm både rettelser og oppdelinger
    if st.button("Tom hele minnet"):
        mem.clear()
        split_mem.clear()
        st.session_state.pop("analysis_cache_hash", None)
        st.rerun()

# Last inn ingredienser og oppskrifter
ingredients = load_ingredients()
recipes = load_recipes()

# Advarsel hvis ingredienslisten er tom
if not ingredients:
    st.warning("Ingredienslisten er tom. Kontroller ingredients.json.")

ingredient_names = [item["name"] for item in ingredients]

# Last opp eller ta bilde
uploaded_file = st.file_uploader(
    "Last opp bilde (png, jpg, jpeg, webp)",
    type=["png", "jpg", "jpeg", "webp"],
)

camera_file = st.camera_input("Eller ta bilde direkte med kamera")
source_file = uploaded_file or camera_file

analysis_result = None
veg_result = None

# Analyser bildet hvis det finnes et
if source_file is not None:
    image_bytes = source_file.getvalue()
    ingredient_records = tuple(
        {"name": item["name"], "category": item["category"]}
        for item in ingredients
    )

    # MD5-hash kjenner igjen samme bilde, så det ikke analyseres på nytt
    image_hash = hashlib.md5(image_bytes).hexdigest()

    # Analyser bare nye bilder
    if st.session_state.get("analysis_cache_hash") != image_hash:
        try:
            with st.spinner("Utforer kvalitetsforbedring, backgrunnfjerning, OCR og grønnsaksgjenkjenning..."):
                # CLAHE, bakgrunnsfjerning og OCR
                analysis_result = analyze_image(image_bytes, ingredient_records)

                # Visuell gjenkjenning; tekstområder hoppes over
                veg_result = recognizer.recognize(
                    analysis_result["removed_pil"],
                    multi=True,
                    use_clip=True,
                    exclude_mask=analysis_result["text_mask"],
                    use_memory=True,
                )

            # Husk resultatet mellom klikk
            st.session_state["analysis_cache_hash"] = image_hash
            st.session_state["analysis_result"] = analysis_result
            st.session_state["veg_result"] = veg_result
            st.session_state["form_version"] = st.session_state.get("form_version", 0) + 1
            st.success("Bildeanalysen er fullfort!")
        except Exception as error:
            st.error("Bildet kunne ikke analyseres.")
            with st.expander("Vis teknisk feilmelding"):
                st.code(str(error))
    else:
        # Samme bilde: bruk lagret resultat
        analysis_result = st.session_state["analysis_result"]
        veg_result = st.session_state["veg_result"]

    # Vis de tre trinnene side om side
    if analysis_result and veg_result:
        st.subheader("Trinnvis bildeprosessering")
        col_img1, col_img2, col_img3 = st.columns(3)

        # 1. Originalbilde
        with col_img1:
            st.write("**1. Originalbilde**")
            st.image(analysis_result["original"], use_container_width=True)

        # 2. Etter CLAHE og bakgrunnsfjerning
        with col_img2:
            st.write("**2. Forbedret kvalitet og bakgrunn fjernet**")
            st.image(analysis_result["removed"], use_container_width=True)

        # 3. Med tekstrammer og grønnsakskonturer
        with col_img3:
            st.write("**3. Annotert med OCR og grønnsaker**")

            # Mørk bakgrunn bak det utklippede bildet
            base_removed = analysis_result["removed_pil"].convert("RGBA")
            final_annotated_pil = Image.new("RGBA", base_removed.size, (20, 20, 20, 255))
            final_annotated_pil.paste(base_removed, mask=base_removed.split()[3])

            canvas = np.array(final_annotated_pil.convert("RGB"))
            text_labels = []

            # Gjenkjenningen brukte et krympet bilde, så koordinatene skaleres opp
            orig_w, orig_h = base_removed.size
            resized_w, resized_h = veg_result["image"].size
            scale_x = orig_w / resized_w
            scale_y = orig_h / resized_h
            font_size = max(16, int(orig_w / 45))

            # Grønne rammer rundt tekst som ga en ingrediens
            for box, label in analysis_result.get("ocr_boxes", []):
                try:
                    points = np.array([(int(pt[0]), int(pt[1])) for pt in box], dtype=np.int32)
                    cv2.polylines(canvas, [points], isClosed=True, color=OCR_COLOR, thickness=4, lineType=cv2.LINE_AA)
                    left = int(points[:, 0].min())
                    top = int(points[:, 1].min())
                    text_labels.append((label, (left, max(0, top - font_size - 8)), OCR_COLOR))
                except Exception:
                    pass

            # Blå kontur rundt hver godkjent grønnsak
            for det in veg_result.get("detections", []):
                current_label = det.get("label")
                if current_label is None:
                    continue
                try:
                    x, y, w, h = det["bbox"]
                    drawn_organic = False

                    # Kontur hvis den har minst 3 punkter
                    contour = recognizer.largest_contour(det.get("mask"))
                    if contour is not None and len(contour) >= 3:
                        pts = np.array(
                            [[int((x + pt[0][0]) * scale_x), int((y + pt[0][1]) * scale_y)] for pt in contour],
                            dtype=np.int32,
                        )
                        cv2.polylines(canvas, [pts], isClosed=True, color=VEG_COLOR, thickness=4, lineType=cv2.LINE_AA)
                        drawn_organic = True

                    # Reserve: firkant rundt objektet
                    if not drawn_organic:
                        sx, sy = int(x * scale_x), int(y * scale_y)
                        sw, sh = int(w * scale_x), int(h * scale_y)
                        cv2.rectangle(canvas, (sx, sy), (sx + sw, sy + sh), VEG_COLOR, 4)

                    text = recognizer.label_text(det)
                    text_labels.append((text, (int(x * scale_x), max(0, int(y * scale_y) - font_size - 8)), VEG_COLOR))
                except Exception:
                    pass

            # Skriv navnene med Pillow (støtter æøå) og vis bildet
            final_annotated = recognizer.draw_labels(Image.fromarray(canvas), text_labels, size=font_size)
            st.image(final_annotated, use_container_width=True)

st.divider()

final_visual_veg = []

# Skjema der brukeren retter eller fjerner objekter
if veg_result is not None and veg_result.get("detections"):
    st.subheader("Hjelp systemet a bli bedre og korriger resultater")
    st.caption(
        "Rett navnet hvis det er feil, og trykk lagre. Hvis et utklipp inneholder flere ulike produkter, "
        "del det opp forst i panelet under skjemaet. Rettingene og oppdelingene huskes til neste gang."
    )

    # Melding fra forrige lagring
    form_message = st.session_state.pop("form_message", None)
    if form_message:
        kind, text = form_message
        getattr(st, kind)(text)

    version = st.session_state.get("form_version", 0)
    options = list(PRODUCE.keys())
    detections = veg_result["detections"]

    # En rad per objekt: utklipp, navn og valg
    with st.form("feedback_form"):
        user_selections = []
        for i, det in enumerate(detections, start=1):
            col_f1, col_f2, col_f3 = st.columns([1, 4, 1.5])
            with col_f1:
                # Utklipp av objektet
                if det.get("crop") is not None:
                    st.image(det["crop"], width=60)
            with col_f2:
                # Navnet appen gjettet, kan endres
                current_guess = det.get("label") or det.get("best_guess")
                default = options.index(current_guess) if current_guess in options else 0
                extra = []
                if det.get("from_memory"):
                    extra.append("husket")
                if det.get("auto_split"):
                    extra.append("delt opp automatisk")
                elif det.get("split_from_merged"):
                    extra.append("delt opp")
                extra_text = f" - {', '.join(extra)}" if extra else ""
                chosen_key = st.selectbox(
                    f"Objekt {i} ({det.get('label_no', 'Ukjent')}{extra_text}):",
                    options,
                    index=default,
                    format_func=lambda name: PRODUCE[name]["no"],
                    key=f"fb_sel_{version}_{i}",
                )
            with col_f3:
                # Fjern objektet, eller bruk det uten å lagre
                remove_obj = st.checkbox("Fjern / Ignorer", key=f"fb_del_{version}_{i}")
                no_save = st.checkbox(
                    "Ikke lagre",
                    key=f"fb_nosave_{version}_{i}",
                    help="Brukes i oppskriftssøket, men lagres ikke i datasett eller minne.",
                )

            user_selections.append({"chosen": chosen_key, "remove": remove_obj, "no_save": no_save, "det": det})

        # Lagre endringene
        submitted = st.form_submit_button("Oppdater og lagre")
        if submitted:
            new_detections = []
            saved = 0

            for item in user_selections:
                det = item["det"]
                # Hopp over fjernede objekter
                if item["remove"]:
                    continue

                chosen_name = item["chosen"]
                det["user_status"] = "godkjent" if chosen_name == det.get("best_guess") else "rettet"
                det["label"] = chosen_name
                det["label_no"] = PRODUCE[chosen_name]["no"]

                # Lagre utklippet i dataset/ og i minnet
                if not item["no_save"] and det.get("crop") is not None:
                    folder = DATASET_DIR / chosen_name
                    folder.mkdir(parents=True, exist_ok=True)
                    det["crop"].save(folder / f"{int(time.time())}_{uuid.uuid4().hex[:6]}.png")
                    try:
                        memory.default_memory().add(det["crop"], chosen_name)
                        saved += 1
                    except Exception as error:
                        st.session_state["form_message"] = ("warning", f"Kunne ikke lagre i minnet: {error}")

                new_detections.append(det)

            # Oppdater objektlisten
            veg_result["detections"] = new_detections
            st.session_state["veg_result"] = veg_result
            st.session_state["form_version"] = version + 1
            if "form_message" not in st.session_state:
                st.session_state["form_message"] = ("success", f"Endringer lagret. {saved} utklipp lagret i datasett og minne.")
            st.rerun()

    # Panel for å dele opp objekter som henger sammen
    with st.expander("Del opp et utklipp som inneholder flere ulike produkter"):
        st.caption(
            "Velg objektet og metoden. Forhandsvisningen viser hver del i sin farge. "
            "Trykk Del opp nar det ser riktig ut. Oppdelingen huskes til neste gang."
        )

        # Velg objekt og metode
        obj_index = st.selectbox(
            "Hvilket objekt skal deles opp?",
            list(range(len(detections))),
            format_func=lambda i: f"Objekt {i + 1} ({detections[i].get('label_no', 'Ukjent')})",
            key=f"split_obj_{version}",
        )
        method = st.radio(
            "Metode",
            ["Skillelinje (manuelt)", "Etter farge (automatisk)"],
            horizontal=True,
            key=f"split_method_{version}",
            help="Skillelinje passer når produktene har lik farge. Etter farge passer når de har ulik farge.",
        )
        det_to_split = detections[obj_index]

        # Lag delene med valgt metode
        if method.startswith("Skillelinje"):
            col_s1, col_s2 = st.columns(2)
            angle = col_s1.slider(
                "Vinkel (0 = loddrett linje, 90 = vannrett linje)", 0, 179, 0, key=f"split_angle_{version}"
            )
            position = col_s2.slider(
                "Plassering av linjen (%)", 5, 95, 50, key=f"split_pos_{version}"
            ) / 100.0
            parts = recognizer.make_split_parts(veg_result, det_to_split, "line", angle=angle, position=position)
            split_recipe = {"method": "line", "angle": angle, "position": position}
        else:
            n_parts = st.selectbox("Antall ulike produkter", [2, 3], key=f"split_n_{version}")
            parts = recognizer.make_split_parts(veg_result, det_to_split, "color", n_parts=n_parts)
            split_recipe = {"method": "color", "n_parts": n_parts}

        # Forhåndsvisning før og etter
        col_p1, col_p2 = st.columns(2)
        with col_p1:
            st.image(det_to_split["crop"], caption="For", use_container_width=True)
        with col_p2:
            st.image(
                recognizer.split_preview(veg_result, det_to_split, parts),
                caption=f"Etter: {len(parts)} del(er)",
                use_container_width=True,
            )

        # Del opp og husk hvordan det ble delt
        col_b1, col_b2 = st.columns(2)
        if col_b1.button("Del opp", type="primary", disabled=len(parts) < 2, key=f"split_btn_{version}"):
            new_parts = recognizer.split_detection(veg_result, det_to_split, parts)
            if new_parts:
                remembered = ""
                try:
                    memory.default_split_memory().add(det_to_split["crop"], json.dumps(split_recipe))
                    remembered = " Oppdelingen er husket."
                except Exception as error:
                    remembered = f" (Kunne ikke huske oppdelingen: {error})"

                veg_result["detections"] = detections[:obj_index] + new_parts + detections[obj_index + 1:]
                st.session_state["veg_result"] = veg_result
                st.session_state["form_version"] = version + 1
                st.session_state["form_message"] = (
                    "info",
                    f"Objekt {obj_index + 1} ble delt i {len(new_parts)} deler.{remembered} "
                    "Sjekk navnene i skjemaet og trykk Oppdater og lagre.",
                )
                st.rerun()
            else:
                st.warning("Oppdelingen lyktes ikke. Prov en annen plassering eller metode.")

        # Analyser bildet på nytt uten oppdelinger
        if col_b2.button("Angre alle oppdelinger", key=f"split_reset_{version}"):
            st.session_state.pop("analysis_cache_hash", None)
            st.rerun()

    # Godkjente grønnsaker går videre til oppskriftssøket
    for det in veg_result["detections"]:
        if det.get("label") in PRODUCE:
            final_visual_veg.append(PRODUCE[det["label"]]["no"])
    final_visual_veg = list(dict.fromkeys(final_visual_veg))

st.divider()
res_col1, res_col2 = st.columns(2)

# Funn fra tekst (OCR)
with res_col1:
    st.write("### Produkter funnet via tekst:")
    if analysis_result and analysis_result["found"]:
        for item in analysis_result["found"]:
            st.write(f"- {item['name']} ({item['category']})")
    else:
        st.info("Ingen tekstprodukter funnet.")

# Funn fra bildet
with res_col2:
    st.write("### Godkjente grønnsaker:")
    if final_visual_veg:
        for veg in final_visual_veg:
            st.write(f"- {veg}")
    else:
        st.info("Ingen visuelle grønnsaker valgt.")

st.divider()

# Filtre
st.subheader("Filtrering og Valg")
col_filter1, col_filter2 = st.columns(2)

# Kjøkken
with col_filter1:
    cuisines = ["Alle", "Norsk", "Arabisk", "Asiatisk", "Italiensk", "Meksikansk"]
    selected_cuisine = st.selectbox("Velg internasjonalt kjøkken:", cuisines)

# Kostholdsfiltre
with col_filter2:
    selected_allergies = st.multiselect(
        "Allergifiltre:",
        options=["Glutenfri", "Laktosefri", "Vegansk"],
        default=[]
    )

# Slå sammen funn fra tekst og bilde
automatically_found = []
if analysis_result is not None:
    automatically_found.extend([item["name"] for item in analysis_result["found"]])

automatically_found.extend(final_visual_veg)

valid_defaults = list(dict.fromkeys([name for name in automatically_found if name in ingredient_names]))

# Brukeren kan fjerne eller legge til ingredienser
selected_ingredients = st.multiselect(
    "Ingredienser (automatisk funnet og manuelt lagt til)",
    options=ingredient_names,
    default=valid_defaults,
    placeholder="Søk etter for eksempel melk, tomat eller mel...",
)

st.divider()
st.subheader("Oppskrifter som passer")

# Vis oppskrifter som passer
if not recipes:
    st.info("Ingen oppskrifter er tilgjengelige.")
elif not selected_ingredients:
    st.info("Last opp et bilde eller velg minst en ingrediens for a finne passende oppskrifter.")
else:
    matching_recipes = find_matching_recipes(
        recipes,
        selected_ingredients,
        selected_cuisine,
        selected_allergies
    )

    if not matching_recipes:
        st.warning("Ingen oppskrifter matcher dine valgte ingredienser og filtre.")

    # En utvidbar boks per oppskrift
    for idx, result in enumerate(matching_recipes):
        recipe = result["recipe"]
        orig_portions = int(recipe.get("portions", 4))

        with st.expander(f"{recipe['title']} — {result['count']} ingrediens(er) matcher"):
            st.write(
                f"**Kategori:** {recipe['category']} | "
                f"**Kjøkken:** {recipe['cuisine']} | "
                f"**Tid:** {recipe.get('time', 'Uspesifisert')} min"
            )

            # Endre porsjoner; mengdene skaleres
            selected_portions = st.number_input(
                "Porsjoner:",
                min_value=1,
                max_value=20,
                value=orig_portions,
                key=f"portions_{recipe['id']}_{idx}"
            )

            factor = selected_portions / orig_portions

            # Næringsinnhold per porsjon
            nutrition = recipe.get("nutrition", {})
            if nutrition:
                st.markdown("**Næringsinnhold per porsjon:**")
                n_col1, n_col2, n_col3, n_col4 = st.columns(4)
                n_col1.metric("Kalorier", f"{nutrition.get('kalorier_kcal', 0)} kcal")
                n_col2.metric("Proteiner", f"{nutrition.get('proteiner_g', 0)} g")
                n_col3.metric("Karbohydrater", f"{nutrition.get('karbohydrater_g', 0)} g")
                n_col4.metric("Fett", f"{nutrition.get('fett_g', 0)} g")

            st.divider()

            # Ingredienser med skalerte mengder
            st.write(f"**Ingredienser (for {selected_portions} porsjoner):**")
            ing_med_mengde = recipe.get("ingredients_with_amount", [])
            if ing_med_mengde:
                for ing in ing_med_mengde:
                    if isinstance(ing, dict):
                        ing_name = ing.get("ingrediens")
                        orig_qty = ing.get("mengde", "")
                        scaled_qty = scale_amount_string(orig_qty, factor)
                        st.write(f"- {ing_name}: {scaled_qty}")
                    else:
                        st.write(f"- {ing}")
            else:
                for ing in recipe.get("ingredients", []):
                    st.write(f"- {ing}")

            # Det brukeren mangler
            if result["missing"]:
                st.write("**Du mangler:** " + ", ".join(result["missing"]))

            st.divider()

            # Fremgangsmåte
            st.write("**Fremgangsmåte:**")
            for index, instruction in enumerate(recipe["instructions"], start=1):
                st.write(f"{index}. {instruction}")