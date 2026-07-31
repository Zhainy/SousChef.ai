from io import BytesIO
from pathlib import Path

from google import genai
from google.genai import types
from PIL import Image

from ..config import settings

IMAGE_URL_TEMPLATE = "/static/recipes/{recipe_hash}.png"


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


def generate_recipe_image(recipe: dict, recipe_hash: str) -> str | None:
    cached = image_url_for(recipe_hash)
    if cached is not None:
        return cached
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
    path = _image_path(recipe_hash)
    path.parent.mkdir(parents=True, exist_ok=True)
    img = Image.open(BytesIO(part.inline_data.data))
    img = _crop_16_9(img)
    img.save(path)
    return image_url_for(recipe_hash)


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
