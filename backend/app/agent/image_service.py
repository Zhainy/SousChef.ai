import time
from io import BytesIO
from pathlib import Path

import httpx
from google import genai
from google.genai import types
from PIL import Image

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


def _prompt(recipe: dict) -> str:
    ingredientes = ", ".join(str(i.get("nombre", "")) for i in recipe.get("ingredientes", []))
    return (
        "Fotografía gastronómica profesional y apetitosa de este plato ya servido, "
        "iluminación natural cálida, encuadre a 45 grados, fondo neutro. "
        f"Plato: {recipe.get('nombre', '')}. "
        f"Ingredientes principales: {ingredientes}. "
        "Sin texto, sin marcas de agua."
    )


def _crop_16_9(img: Image.Image) -> Image.Image:
    """Recorta al centro a 16:9 para eliminar bandas negras del generador."""
    w, h = img.size
    target = 16 / 9
    if w / h > target:
        new_w = int(h * target)
        left = (w - new_w) // 2
        return img.crop((left, 0, left + new_w, h))
    new_h = int(w / target)
    top = (h - new_h) // 2
    return img.crop((0, top, w, top + new_h))


def _save_image(recipe_hash: str, data: bytes) -> str | None:
    path = _image_path(recipe_hash)
    path.parent.mkdir(parents=True, exist_ok=True)
    img = Image.open(BytesIO(data))
    img = _crop_16_9(img)
    img.save(path)
    return image_url_for(recipe_hash)


def _gemini_bytes(recipe: dict) -> bytes | None:
    if not settings.gemini_api_key:
        return None
    client = genai.Client(api_key=settings.gemini_api_key)
    try:
        response = client.models.generate_content(
            model=settings.image_model,
            contents=_prompt(recipe),
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE"],
                image_config=types.ImageConfig(aspect_ratio="16:9"),
            ),
        )
        part = next(p for p in response.candidates[0].content.parts if p.inline_data is not None)
    except Exception:
        return None
    return part.inline_data.data


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
    nombre = str(recipe.get("nombre", "")).strip()
    if not nombre:
        return None
    words = nombre.split()
    first = " ".join(words[:2]) if len(words) >= 2 else words[0]
    queries = [f"{first} comida", f"{words[0]} comida"]
    for i, query in enumerate(queries):
        if i > 0:
            time.sleep(1)
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
    url = _meal_db_thumb(recipe) or _commons_thumb(recipe)
    if not url:
        return None
    return _download_image(url)


def generate_recipe_image(recipe: dict, recipe_hash: str) -> str | None:
    cached = image_url_for(recipe_hash)
    if cached is not None:
        return cached
    data: bytes | None = None
    if settings.image_source in ("auto", "gemini"):
        data = _gemini_bytes(recipe)
    if data is None and settings.image_source in ("auto", "web"):
        data = _web_bytes(recipe)
    if data is None:
        return None
    return _save_image(recipe_hash, data)
