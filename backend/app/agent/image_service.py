import re
from pathlib import Path
from typing import Any

import httpx

from ..config import settings

IMAGE_URL_TEMPLATE = "/static/recipes/{recipe_hash}.png"
MEALDB_SEARCH_URL = "https://www.themealdb.com/api/json/v1/1/search.php"
COMMONS_API_URL = "https://commons.wikimedia.org/w/api.php"
USER_AGENT = "SousChef.ai/0.1"

TRANSLATION_MAP = {
    "pollo": "chicken",
    "arroz": "rice",
    "pasta": "pasta",
    "espagueti": "spaghetti",
    "fideos": "pasta",
    "carne": "beef",
    "res": "beef",
    "ternera": "beef",
    "cerdo": "pork",
    "pescado": "fish",
    "salmon": "salmon",
    "salmón": "salmon",
    "atun": "tuna",
    "atún": "tuna",
    "tomate": "tomato",
    "queso": "cheese",
    "huevo": "egg",
    "huevos": "eggs",
    "patata": "potato",
    "patatas": "potatoes",
    "papa": "potato",
    "papas": "potatoes",
    "cebolla": "onion",
    "ajo": "garlic",
    "zanahoria": "carrot",
    "lechuga": "lettuce",
    "ensalada": "salad",
    "sopa": "soup",
    "caldo": "broth",
    "lentejas": "lentils",
    "garbanzos": "chickpeas",
    "frijoles": "beans",
    "alubias": "beans",
    "pan": "bread",
    "manzana": "apple",
    "naranja": "orange",
    "limon": "lemon",
    "limón": "lemon",
    "chocolate": "chocolate",
    "tarta": "pie",
    "pastel": "cake",
    "bizcocho": "cake",
    "galletas": "cookies",
}

STOPWORDS = {
    "de",
    "del",
    "con",
    "y",
    "en",
    "el",
    "la",
    "los",
    "las",
    "un",
    "una",
    "al",
    "a",
    "para",
    "por",
    "su",
    "sus",
    "como",
    "sin",
    "sobre",
    "casero",
    "casera",
}


def _clean_words(text: str) -> list[str]:
    return re.findall(r"\b[a-záéíóúñA-ZÁÉÍÓÚÑ]+\b", text.lower())


def _translate_query(text: str) -> str:
    words = _clean_words(text)
    translated = [TRANSLATION_MAP.get(w, w) for w in words]
    return " ".join(translated)


def _image_path(recipe_hash: str) -> Path:
    return Path(settings.static_dir) / f"{recipe_hash}.png"


def image_url_for(recipe_hash: str) -> str | None:
    if _image_path(recipe_hash).exists():
        return IMAGE_URL_TEMPLATE.format(recipe_hash=recipe_hash)
    return None


def _save_image(recipe_hash: str, data: bytes) -> str | None:
    path = _image_path(recipe_hash)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return image_url_for(recipe_hash)


DISH_CATEGORIES = {
    "sopa": {"en": "soup", "es": "sopa"},
    "caldo": {"en": "soup", "es": "caldo"},
    "crema": {"en": "soup", "es": "crema"},
    "consomé": {"en": "soup", "es": "consome"},
    "pasta": {"en": "pasta", "es": "pasta"},
    "fideos": {"en": "pasta", "es": "fideos"},
    "espagueti": {"en": "spaghetti", "es": "espagueti"},
    "tallarines": {"en": "pasta", "es": "tallarines"},
    "arroz": {"en": "rice", "es": "arroz"},
    "paella": {"en": "rice", "es": "paella"},
    "risotto": {"en": "rice", "es": "risotto"},
    "ensalada": {"en": "salad", "es": "ensalada"},
    "guiso": {"en": "stew", "es": "guiso"},
    "estofado": {"en": "stew", "es": "estofado"},
    "pollo": {"en": "chicken", "es": "pollo"},
    "carne": {"en": "beef", "es": "carne"},
    "pescado": {"en": "fish", "es": "pescado"},
}


def _detect_category(text: str) -> dict[str, str] | None:
    words = _clean_words(text)
    for w in words:
        if w in DISH_CATEGORIES:
            return DISH_CATEGORIES[w]
    return None


def _meal_db_thumb(recipe: dict[str, Any]) -> str | None:
    nombre = str(recipe.get("nombre", "")).strip()
    if not nombre:
        return None

    words = _clean_words(nombre)
    meaningful = [w for w in words if w not in STOPWORDS]
    if not meaningful:
        meaningful = words

    cat_info = _detect_category(nombre)
    category_en = cat_info["en"] if cat_info else None

    # Solo buscar en inglés en TheMealDB (TheMealDB no tiene recetas en español)
    queries: list[str] = []
    translated_meaningful = [TRANSLATION_MAP.get(w, w) for w in meaningful]
    if len(translated_meaningful) >= 2:
        queries.append(" ".join(translated_meaningful[:2]))
    if category_en:
        other_words = [tw for tw in translated_meaningful if tw != category_en]
        if other_words:
            queries.append(f"{category_en} {other_words[0]}")
            queries.append(f"{other_words[0]} {category_en}")
        queries.append(category_en)
    for tw in translated_meaningful:
        queries.append(tw)

    seen = set()
    unique_queries = []
    for q in queries:
        q_clean = q.strip()
        if q_clean and q_clean not in seen:
            seen.add(q_clean)
            unique_queries.append(q_clean)

    for query in unique_queries:
        try:
            res = httpx.get(MEALDB_SEARCH_URL, params={"s": query}, timeout=6)
            if res.status_code == 429:
                break
            if res.status_code != 200:
                continue
            meals = res.json().get("meals") or []
            for meal in meals:
                meal_name = meal.get("strMeal", "").lower()
                meal_cat = meal.get("strCategory", "").lower()
                thumb = meal.get("strMealThumb")
                if not (isinstance(thumb, str) and thumb):
                    continue

                # Si detectamos categoría y el resultado tiene nombre, validar que coincida
                if category_en and meal_name:
                    if category_en in meal_name or category_en in meal_cat:
                        return thumb
                else:
                    return thumb
        except (httpx.HTTPError, ValueError, IndexError, KeyError):
            continue
    return None


def _commons_thumb(recipe: dict[str, Any]) -> str | None:
    """Busca imagen en Wikimedia Commons con filtro de fotos y términos precisos."""
    nombre = str(recipe.get("nombre", "")).strip()
    if not nombre:
        return None

    words = _clean_words(nombre)
    meaningful = [w for w in words if w not in STOPWORDS]
    if not meaningful:
        meaningful = words

    cat_info = _detect_category(nombre)

    queries: list[str] = []
    if cat_info:
        queries.append(f"filetype:bitmap plato de {cat_info['es']}")
    if len(meaningful) >= 2:
        queries.append(f"filetype:bitmap {meaningful[0]} {meaningful[1]} plato")
    if meaningful:
        queries.append(f"filetype:bitmap {meaningful[0]} plato")

    for query in queries:
        try:
            res = httpx.get(
                COMMONS_API_URL,
                params={
                    "action": "query",
                    "format": "json",
                    "generator": "search",
                    "gsrsearch": query,
                    "gsrnamespace": 6,
                    "gsrlimit": 4,
                    "prop": "imageinfo",
                    "iiprop": "url|mime",
                    "iiurlwidth": 800,
                },
                headers={"User-Agent": USER_AGENT},
                timeout=8,
            )
            if res.status_code == 429:
                break
            if res.status_code != 200:
                continue
            pages = res.json().get("query", {}).get("pages", {})
            for page in pages.values():
                title = str(page.get("title", "")).lower()
                # Filtrar documentos, escaneos de libros y vectores
                if any(title.endswith(ext) for ext in (".pdf", ".djvu", ".tif", ".tiff", ".svg")):
                    continue
                info = (page.get("imageinfo") or [{}])[0]
                mime = str(info.get("mime", "")).lower()
                if mime in ("image/jpeg", "image/png", "image/webp"):
                    thumb = info.get("thumburl")
                    if isinstance(thumb, str) and thumb:
                        return thumb
        except (httpx.HTTPError, ValueError):
            continue
    return None


def _download_image(url: str) -> bytes | None:
    try:
        res = httpx.get(
            url,
            headers={"User-Agent": USER_AGENT},
            timeout=10,
            follow_redirects=True,
        )
    except httpx.HTTPError:
        return None
    if res.status_code != 200:
        return None
    if not res.headers.get("content-type", "").startswith("image/"):
        return None
    return res.content


def generate_recipe_image(recipe: dict[str, Any], recipe_hash: str) -> str | None:
    """Obtiene la imagen para una receta.

    Pipeline:
    1. Cache en disco — retorna inmediatamente si ya existe.
    2. TheMealDB — busca por términos traducidos/clave, descarga y guarda.
    3. Wikimedia Commons — busca por términos en español, descarga y guarda.
    4. None — el frontend muestra el placeholder SVG.
    """
    if settings.image_source == "none":
        return None

    cached = image_url_for(recipe_hash)
    if cached is not None:
        return cached

    url = _meal_db_thumb(recipe) or _commons_thumb(recipe)
    if url:
        data = _download_image(url)
        if data:
            return _save_image(recipe_hash, data)

    return None
