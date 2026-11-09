import io
import json
from functools import lru_cache
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageOps

import clip_classifier
import features
import rules
import memory as memory_module
from produce_config import PRODUCE, UNKNOWN_LABEL

W_CLIP = 0.65    # Vekt for CLIP
W_RULES = 0.35   # Vekt for farge- og formreglene
MAX_SIDE = 1024  # Bildet krympes til maks 1024 piksler

# Farger for tegning (RGB)
COLOR_ACCEPTED = (0, 120, 255)   # blå: godkjent råvare
COLOR_UNKNOWN = (150, 150, 150)  # grå: ukjent objekt
SPLIT_COLORS = [(0, 120, 255), (255, 140, 0), (0, 200, 120)]  # blå, oransje, grønn


@lru_cache(maxsize=1)
def _rembg_session():
    """Lager rembg-økten en gang."""
    try:
        from rembg import new_session
        return new_session("u2net")
    except Exception:
        return None


def segment(image):
    """Lager en maske av objektene: bruker alfakanalen, ellers rembg."""
    try:
        if image.mode == "RGBA":
            alpha = np.array(image)[..., 3]
            if not np.all(alpha == 255) and (alpha < 240).any():
                mask = alpha > 40
                if mask.any():
                    return mask, True
    except Exception:
        pass

    # Ingen alfakanal: fjern bakgrunnen med rembg
    try:
        from rembg import remove
        session = _rembg_session()
        removed = remove(image.convert("RGB"), session=session)
        if isinstance(removed, bytes):
            removed = Image.open(io.BytesIO(removed))
        elif not isinstance(removed, Image.Image):
            removed = Image.fromarray(removed)

        alpha = np.array(removed.convert("RGBA"))[..., 3]
        mask = alpha > 40
        if mask.any():
            return mask, True
    except Exception:
        pass

    # Reserve: hele bildet regnes som objekt
    return np.ones((image.height, image.width), dtype=bool), False


def split_objects(mask, multi=True, min_fraction=0.002, max_objects=20):
    """Deler masken i separate objekter med connected components."""
    height, width = mask.shape

    def whole():
        ys, xs = np.where(mask)
        if len(xs) == 0:
            return [((0, 0, width, height), np.ones_like(mask))]
        x0, x1, y0, y1 = int(xs.min()), int(xs.max()), int(ys.min()), int(ys.max())
        return [((x0, y0, max(1, x1 - x0 + 1), max(1, y1 - y0 + 1)), mask)]

    if not multi:
        return whole()

    m8 = mask.astype(np.uint8) * 255
    # Fjern små støyprikker, og gi hver flekk sitt eget nummer
    m8 = cv2.morphologyEx(m8, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    count, labels, stats, _ = cv2.connectedComponentsWithStats(m8, connectivity=8)

    objects = []
    for i in range(1, count):
        comp_mask = (labels == i)
        area = int(np.sum(comp_mask))
        # Behold bare objekter større enn 0,2 % av bildet
        if area >= min_fraction * height * width:
            ys, xs = np.where(comp_mask)
            if len(xs) > 0 and len(ys) > 0:
                x1, x2 = int(xs.min()), int(xs.max())
                y1, y2 = int(ys.min()), int(ys.max())
                box_w = max(1, x2 - x1 + 1)
                box_h = max(1, y2 - y1 + 1)
                objects.append(((x1, y1, box_w, box_h), comp_mask, area))

    if not objects:
        return whole()

    # Største objekter først
    objects.sort(key=lambda o: o[2], reverse=True)
    return [(bbox, m) for bbox, m, _ in objects[:max_objects]]


# Oppdeling av utklipp med flere produkter

COLOR_SPLIT_SPATIAL = 40.0   # hvor mye posisjon teller i forhold til farge
COLOR_SPLIT_LIGHTNESS = 0.3  # lysstyrke teller lite, slik at skygger ikke lager egne grupper


def color_split(crop_rgb, mask, n_parts):
    """Deler utklippet i n_parts deler etter farge og posisjon med k-means."""
    mask = mask.astype(bool)
    total = int(mask.sum())
    if n_parts <= 1 or total < 100:
        return [mask]

    h, w = mask.shape
    lab = cv2.cvtColor(crop_rgb.astype(np.uint8), cv2.COLOR_RGB2LAB).astype(np.float32)
    ys, xs = np.where(mask)
    scale = COLOR_SPLIT_SPATIAL / max(h, w)

    # Hver piksel: lysstyrke, to fargetall (LAB) og posisjon
    feats = np.column_stack([
        COLOR_SPLIT_LIGHTNESS * lab[ys, xs, 0],  # lysstyrke
        lab[ys, xs, 1],                          # grønn <-> rød
        lab[ys, xs, 2],                          # blå <-> gul
        xs * scale,                              # posisjon
        ys * scale,
    ]).astype(np.float32)

    sample = feats
    if len(feats) > 20000:  # raskere på store utklipp
        idx = np.random.default_rng(0).choice(len(feats), 20000, replace=False)
        sample = feats[idx]

    # Finn midtpunktene, og gi hver piksel til nærmeste
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 50, 0.5)
    _, _, centers = cv2.kmeans(sample, n_parts, None, criteria, 5, cv2.KMEANS_PP_CENTERS)

    distances = ((feats[:, None, :] - centers[None, :, :]) ** 2).sum(axis=2)
    assign = np.argmin(distances, axis=1)

    k = max(3, int(round(min(h, w) * 0.03)) | 1)  # oddetall
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k))

    # Rydd hver del og fjern små biter
    parts = []
    for c in range(n_parts):
        part = np.zeros((h, w), np.uint8)
        part[ys[assign == c], xs[assign == c]] = 255
        part = cv2.morphologyEx(part, cv2.MORPH_OPEN, kernel)
        part = cv2.morphologyEx(part, cv2.MORPH_CLOSE, kernel)
        part = (part > 0) & mask

        count, labels, stats, _ = cv2.connectedComponentsWithStats(part.astype(np.uint8), connectivity=8)
        clean = np.zeros_like(part)
        for i in range(1, count):
            if stats[i, cv2.CC_STAT_AREA] >= 0.02 * total:
                clean |= labels == i

        if clean.sum() >= 0.05 * total:
            parts.append(clean)

    return parts if len(parts) >= 2 else [mask]


def line_split(mask, angle_deg, position):
    """Deler masken i to med en rett linje (0° = loddrett, posisjon 0–1)."""
    mask = mask.astype(bool)
    total = int(mask.sum())
    if total < 50:
        return [mask]

    h, w = mask.shape
    theta = np.deg2rad(angle_deg)
    ys, xs = np.mgrid[0:h, 0:w]
    projection = xs * np.cos(theta) + ys * np.sin(theta)  # avstand langs linjens normal

    values = projection[mask]
    cut = values.min() + (values.max() - values.min()) * position
    side = projection < cut

    parts = [p for p in (mask & side, mask & ~side) if p.sum() >= 0.03 * total]
    return parts if len(parts) == 2 else [mask]


def parts_from_recipe(crop_rgb, mask, recipe):
    """Gjenskaper en lagret oppdeling."""
    if recipe.get("method") == "color":
        return color_split(crop_rgb, mask, int(recipe.get("n_parts", 2)))
    return line_split(mask, float(recipe.get("angle", 0)), float(recipe.get("position", 0.5)))


def _crop_rgb(result, det):
    """Klipper ut objektets boks fra bildet."""
    rgb = np.array(result["image"].convert("RGB"))
    x, y, w, h = det["bbox"]
    return rgb[y:y + h, x:x + w]


def make_split_parts(result, det, method, n_parts=2, angle=0, position=0.5):
    """Lager delene for en deteksjon. method = 'color' eller 'line'."""
    if method == "color":
        return color_split(_crop_rgb(result, det), det["mask"], n_parts)
    return line_split(det["mask"], angle, position)


def split_preview(result, det, parts, min_side=260):
    """Bilde som viser hvordan utklippet blir delt (hver del i sin farge)."""
    crop = _crop_rgb(result, det).astype(np.float32)
    mask = det["mask"].astype(bool)

    out = np.full_like(crop, 30.0)
    out[mask] = crop[mask]
    if len(parts) >= 2:
        for part, color in zip(parts, SPLIT_COLORS):
            out[part] = 0.5 * out[part] + 0.5 * np.array(color, dtype=np.float32)

    image = Image.fromarray(out.clip(0, 255).astype(np.uint8))
    if min(image.size) < min_side:
        factor = min_side / min(image.size)
        image = image.resize((int(image.width * factor), int(image.height * factor)), Image.NEAREST)
    return image


# Gjenkjenning av ett objekt

def _analyze_crop(crop_rgb, crop_mask, bbox, clip_used, min_conf=0.30,
                  use_memory=True, memory=None, memory_threshold=None):
    """Gjenkjenner ett utklipp og gir en deteksjon (eller None)."""
    if crop_rgb.size == 0 or not crop_mask.any():
        return None

    # Regler: farge og form
    histogram = features.color_histogram(crop_rgb, crop_mask)
    aspect = features.aspect_ratio(crop_mask)
    rule_probs = rules.normalized(histogram, aspect)

    # Grå bakgrunn, så CLIP bare ser objektet
    clean = np.where(crop_mask[..., None], crop_rgb, 200).astype(np.uint8)
    crop_image = Image.fromarray(clean)

    unknown = 0.0
    if clip_used:
        try:
            clip_scores = clip_classifier.classify(crop_image)
            unknown = clip_scores.pop(UNKNOWN_LABEL, 0.0)
            total = sum(clip_scores.values()) or 1.0
            # Bland CLIP og reglene
            final = {
                name: W_CLIP * (clip_scores.get(name, 0.0) / total) + W_RULES * rule_probs[name]
                for name in PRODUCE
            }
        except Exception:
            final = rule_probs
    else:
        final = rule_probs

    ranking = sorted(final.items(), key=lambda kv: kv[1], reverse=True)
    best, confidence = ranking[0]
    # Godkjent hvis sikker nok og ikke ligner «ukjent»
    accepted = confidence >= min_conf and unknown < 0.55

    # Minnet overstyrer hvis brukeren har rettet et lignende utklipp
    from_memory = False
    memory_similarity = 0.0
    if clip_used and use_memory:
        try:
            store = memory if memory is not None else memory_module.default_memory()
            if len(store) > 0:
                vector = clip_classifier.image_embedding(crop_image)
                remembered, memory_similarity = store.lookup_vector(vector, memory_threshold)
                if remembered in PRODUCE:
                    best, confidence = remembered, memory_similarity
                    ranking = [(remembered, memory_similarity)] + [r for r in ranking if r[0] != remembered]
                    accepted = True
                    from_memory = True
        except Exception:
            pass

    return {
        "bbox": tuple(int(v) for v in bbox),
        "label": best if accepted else None,
        "label_no": PRODUCE[best]["no"] if accepted else "Ukjent",
        "best_guess": best,
        "confidence": float(confidence),
        "unknown": float(unknown),
        "ranking": ranking,
        "crop": crop_image,
        "mask": crop_mask,
        "aspect": aspect,
        "histogram": histogram,
        "from_memory": from_memory,
        "memory_similarity": float(memory_similarity),
    }


def _detections_from_parts(crop_rgb, parts, bbox, clip_used, min_conf=0.30,
                           use_memory=True, memory=None, memory_threshold=None):
    """Gjenkjenner hver del som en egen deteksjon."""
    if len(parts) < 2:
        return []

    x, y = int(bbox[0]), int(bbox[1])
    new_detections = []
    for part in parts:
        ys, xs = np.where(part)
        if len(xs) == 0:
            continue
        px0, px1, py0, py1 = int(xs.min()), int(xs.max()), int(ys.min()), int(ys.max())
        sub_rgb = crop_rgb[py0:py1 + 1, px0:px1 + 1]
        sub_mask = part[py0:py1 + 1, px0:px1 + 1]
        sub_bbox = (x + px0, y + py0, px1 - px0 + 1, py1 - py0 + 1)

        new_det = _analyze_crop(sub_rgb, sub_mask, sub_bbox, clip_used, min_conf,
                                use_memory, memory, memory_threshold)
        if new_det is not None:
            new_det["split_from_merged"] = True
            new_detections.append(new_det)

    return new_detections if len(new_detections) >= 2 else []


def _auto_split(crop_rgb, crop_mask, bbox, det, clip_used, min_conf, memory_threshold):
    """Deler utklippet automatisk hvis et lignende er delt opp før."""
    try:
        store = memory_module.default_split_memory()
        if len(store) == 0:
            return []
        vector = clip_classifier.image_embedding(det["crop"])
        recipe_text, _ = store.lookup_vector(vector, memory_threshold)
        if not recipe_text:
            return []
        recipe = json.loads(recipe_text)
        parts = parts_from_recipe(crop_rgb, crop_mask, recipe)
        new_detections = _detections_from_parts(crop_rgb, parts, bbox, clip_used, min_conf,
                                                True, None, memory_threshold)
        for new_det in new_detections:
            new_det["auto_split"] = True
        return new_detections
    except Exception:
        return []


def recognize(image, multi=True, use_clip=True, min_conf=0.30, exclude_mask=None,
              use_memory=True, memory=None, memory_threshold=None):
    """Finner og gjenkjenner alle råvarer i bildet."""
    orig_image = ImageOps.exif_transpose(image)
    mask, segmentation_used = segment(orig_image)

    image = orig_image.convert("RGB")
    image.thumbnail((MAX_SIDE, MAX_SIDE))
    rgb = np.array(image)
    img_h, img_w = rgb.shape[:2]

    # Masken må ha samme størrelse som det krympede bildet
    if mask.shape != (img_h, img_w):
        mask_np = (mask.astype(np.uint8)) * 255
        mask_resized = cv2.resize(mask_np, (img_w, img_h), interpolation=cv2.INTER_NEAREST)
        mask = mask_resized > 127

    ex_resized = None
    if exclude_mask is not None:
        try:
            ex_np = np.array(exclude_mask)
            if len(ex_np.shape) == 3:
                ex_np = cv2.cvtColor(ex_np, cv2.COLOR_RGB2GRAY)
            ex_resized = cv2.resize(ex_np, (img_w, img_h), interpolation=cv2.INTER_NEAREST)
        except Exception:
            pass

    objects = split_objects(mask, multi=multi)

    clip_used = bool(use_clip and clip_classifier.clip_available())
    # Automatisk oppdeling brukes bare med appens eget minne
    use_auto_split = clip_used and use_memory and memory is None and multi
    detections = []

    for (x, y, w, h), obj_mask in objects:
        # Hold boksen innenfor bildet
        x = max(0, min(x, img_w - 1))
        y = max(0, min(y, img_h - 1))
        w = max(1, min(w, img_w - x))
        h = max(1, min(h, img_h - y))

        # Hopp over objekter som overlapper tekst (emballasje)
        if ex_resized is not None:
            crop_ex = ex_resized[y:y + h, x:x + w]
            crop_obj_mask = obj_mask[y:y + h, x:x + w]
            if np.any((crop_ex > 127) & crop_obj_mask):
                continue

        crop_rgb = rgb[y:y + h, x:x + w]
        crop_mask = obj_mask[y:y + h, x:x + w]

        det = _analyze_crop(crop_rgb, crop_mask, (x, y, w, h),
                            clip_used, min_conf, use_memory, memory, memory_threshold)
        if det is None:
            continue

        # Del opp automatisk hvis et lignende utklipp er delt før
        if use_auto_split:
            parts = _auto_split(crop_rgb, crop_mask, (x, y, w, h), det, clip_used, min_conf, memory_threshold)
            if parts:
                detections.extend(parts)
                continue

        detections.append(det)

    return {
        "image": image,
        "detections": detections,
        "clip_used": clip_used,
        "segmentation_used": segmentation_used,
        "settings": {"min_conf": min_conf, "use_memory": use_memory, "memory_threshold": memory_threshold},
    }


def split_detection(result, det, parts):
    """Gjenkjenner delene etter en manuell oppdeling."""
    settings = result.get("settings", {})
    return _detections_from_parts(
        _crop_rgb(result, det), parts, det["bbox"], result.get("clip_used", False),
        settings.get("min_conf", 0.30), settings.get("use_memory", True),
        None, settings.get("memory_threshold"),
    )


def unique_labels(result):
    """Navnene på godkjente råvarer, uten duplikater."""
    labels = [d["label"] for d in result["detections"] if d["label"]]
    return list(dict.fromkeys(labels))


# Tegning

def _font_candidates():
    """Skrifter som har æ, ø og å. Den første som finnes blir brukt."""
    candidates = [
        "arial.ttf",                                          # Windows
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/segoeui.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",       # macOS
        "/Library/Fonts/Arial.ttf",
        "DejaVuSans.ttf",                                     # Linux
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    try:  # matplotlib har DejaVuSans med seg hvis det er installert
        import matplotlib
        candidates.append(str(Path(matplotlib.get_data_path()) / "fonts" / "ttf" / "DejaVuSans.ttf"))
    except Exception:
        pass
    return candidates


@lru_cache(maxsize=16)
def label_font(size=20):
    """Finner en skrift med æ, ø og å (OpenCV mangler dem)."""
    for candidate in _font_candidates():
        try:
            return ImageFont.truetype(candidate, size)
        except OSError:
            continue
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


def draw_label(draw, text, position, color, size=20):
    """Tegner en merkelapp med hvit bakgrunn (enkel versjon, uten flytting)."""
    font = label_font(size)
    x, y = position
    left, top, right, bottom = draw.textbbox((x, y), text, font=font)
    draw.rectangle((left - 3, top - 2, right + 3, bottom + 2), fill=(255, 255, 255))
    draw.text((x, y), text, fill=color, font=font)


def _overlaps(a, b):
    """Sann hvis to bokser overlapper."""
    return not (a[2] < b[0] or a[0] > b[2] or a[3] < b[1] or a[1] > b[3])


def draw_labels(image, labels, size=20):
    """Tegner merkelapper (tekst, (x, y), farge) og flytter dem som overlapper."""
    draw = ImageDraw.Draw(image)
    font = label_font(size)
    img_w, img_h = image.size
    placed = []

    for text, (x, y), color in labels:
        left, top, right, bottom = draw.textbbox((0, 0), text, font=font)
        text_w, text_h = right - left, bottom - top
        step = text_h + 8

        x = max(0, min(int(x), img_w - text_w - 6))

        best_box, best_y = None, None
        for offset in (0, -step, step, -2 * step, 2 * step, -3 * step, 3 * step):
            ny = int(y) + offset
            if ny < 0 or ny + text_h + 4 > img_h:
                continue
            box = (x - 3, ny - 2, x + text_w + 3, ny + text_h + 4)
            if not any(_overlaps(box, p) for p in placed):
                best_box, best_y = box, ny
                break
        if best_box is None:
            best_y = max(0, int(y))
            best_box = (x - 3, best_y - 2, x + text_w + 3, best_y + text_h + 4)

        draw.rectangle(best_box, fill=(255, 255, 255))
        draw.text((x, best_y - top), text, fill=color, font=font)
        placed.append(best_box)

    return image


def largest_contour(mask):
    """Finner den største ytre konturen i en maske og glatter den litt ut."""
    if mask is None or not np.any(mask):
        return None
    contours, _ = cv2.findContours(
        mask.astype(np.uint8) * 255, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )
    if not contours:
        return None
    c = max(contours, key=cv2.contourArea)
    epsilon = 0.002 * cv2.arcLength(c, True)
    return cv2.approxPolyDP(c, epsilon, True)


def label_text(det):
    """Teksten som vises på bildet for en deteksjon."""
    name = det.get("label_no", "Ukjent")
    if det.get("user_status"):
        return f"{name} ({det['user_status']})"
    if det.get("from_memory"):
        return f"{name} (husket)"
    return f"{name} ({det['confidence'] * 100:.0f}%)"


def annotate(result):
    """Tegner konturer og navn: blått for godkjent, grått for ukjent."""
    canvas = np.array(result["image"].convert("RGB"))
    labels = []

    for i, det in enumerate(result["detections"], start=1):
        x, y, w, h = det["bbox"]
        color = COLOR_ACCEPTED if det["label"] else COLOR_UNKNOWN

        contour = largest_contour(det.get("mask"))
        if contour is not None and len(contour) >= 3:
            contour = (contour + np.array([[[x, y]]])).astype(np.int32)
            cv2.polylines(canvas, [contour], True, color, 3, cv2.LINE_AA)
        else:
            cv2.rectangle(canvas, (x, y), (x + w, y + h), color, 3)

        labels.append((f"{i}. {label_text(det)}", (x, max(0, y - 26)), color))

    return draw_labels(Image.fromarray(canvas), labels, size=20)