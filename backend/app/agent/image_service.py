from pathlib import Path

import httpx

from ..config import settings

IMAGE_URL_TEMPLATE = "/static/recipes/{recipe_hash}.png"
MEALDB_SEARCH_URL = "https://www.themealdb.com/api/json/v1/1/search.php"
COMMONS_API_URL = "https://commons.wikimedia.org/w/api.php"
USER_AGENT = "SousChef.ai/0.1"


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


def _meal_db_thumb(recipe: dict) -> str | None:
    nombre = str(recipe.get("nombre", "")).strip()
    if not nombre:
        return None
    words = nombre.split()
    queries = [" ".join(words[:n]) for n in range(len(words), 0, -1)][:3]
    for query in queries:
        try:
            res = httpx.get(MEALDB_SEARCH_URL, params={"s": query}, timeout=6)
            if res.status_code == 429:
                break
            if res.status_code != 200:
                continue
            meals = res.json().get("meals") or []
            thumb = meals[0].get("strMealThumb")
            if isinstance(thumb, str) and thumb:
                return thumb
        except (httpx.HTTPError, ValueError, IndexError, KeyError):
            continue
    return None


def _commons_thumb(recipe: dict) -> str | None:
    """Busca una imagen en Wikimedia Commons por nombre de receta."""
    nombre = str(recipe.get("nombre", "")).strip()
    if not nombre:
        return None
    words = nombre.split()
    first = " ".join(words[:2]) if len(words) >= 2 else words[0]
    queries = [f"{first} food", f"{words[0]} food"]
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
                    "gsrlimit": 5,
                    "prop": "imageinfo",
                    "iiprop": "url|mime",
                    "iiurlwidth": 1280,
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
                info = (page.get("imageinfo") or [{}])[0]
                if info.get("mime", "").startswith("image/"):
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


def _web_bytes(recipe: dict) -> bytes | None:
    """Intenta obtener la imagen desde TheMealDB o Wikimedia Commons."""
    url = _meal_db_thumb(recipe) or _commons_thumb(recipe)
    if not url:
        return None
    return _download_image(url)


def generate_recipe_image(recipe: dict, recipe_hash: str) -> str | None:
    """Obtiene la imagen para una receta.

    Pipeline (Task 3b mejorará esto con Unsplash y traducción de términos):
    1. Cache en disco — retorna inmediatamente si ya existe.
    2. TheMealDB — busca por nombre de receta.
    3. Wikimedia Commons — búsqueda por palabras clave.
    4. None — el frontend muestra el placeholder SVG.
    """
    if settings.image_source == "none":
        return None

    cached = image_url_for(recipe_hash)
    if cached is not None:
        return cached

    data = _web_bytes(recipe)
    if data is None:
        return None

    return _save_image(recipe_hash, data)
