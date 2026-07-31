from io import BytesIO

import httpx
from PIL import Image

from app.agent import image_service as svc


def _png_bytes() -> bytes:
    buf = BytesIO()
    Image.new("RGB", (640, 480), (180, 60, 40)).save(buf, format="PNG")
    return buf.getvalue()


def test_uses_cached_image_without_fetching(monkeypatch, tmp_path):
    recipe_hash = "abc123"
    (tmp_path / f"{recipe_hash}.png").write_bytes(_png_bytes())
    monkeypatch.setattr(svc.settings, "static_dir", str(tmp_path))

    def boom(url, **kwargs):
        raise AssertionError(f"no se esperaba fetch a {url}")

    monkeypatch.setattr(svc.httpx, "get", boom)
    assert svc.generate_recipe_image({"nombre": "Pollo al limón"}, recipe_hash) == (
        f"/static/recipes/{recipe_hash}.png"
    )


def test_web_fallback_downloads_meal_db_image(monkeypatch, tmp_path):
    png = _png_bytes()

    def fake_get(url, **kwargs):
        if "themealdb.com" in url:
            return httpx.Response(
                200,
                json={"meals": [{"strMealThumb": "https://cdn.example.com/meal.jpg"}]},
            )
        if url == "https://cdn.example.com/meal.jpg":
            return httpx.Response(
                200,
                headers={"content-type": "image/jpeg"},
                content=png,
            )
        raise AssertionError(f"URL inesperada: {url}")

    monkeypatch.setattr(svc.settings, "static_dir", str(tmp_path))
    monkeypatch.setattr(svc.settings, "image_source", "web")
    monkeypatch.setattr(svc.httpx, "get", fake_get)

    url = svc.generate_recipe_image({"nombre": "Pancakes"}, "hash1")
    assert url == "/static/recipes/hash1.png"
    assert (tmp_path / "hash1.png").exists()


def test_web_fallback_uses_commons_for_spanish_names(monkeypatch, tmp_path):
    png = _png_bytes()

    def fake_get(url, **kwargs):
        if "themealdb.com" in url:
            return httpx.Response(200, json={"meals": None})
        if "commons.wikimedia.org" in url:
            return httpx.Response(
                200,
                json={
                    "query": {
                        "pages": {
                            "1": {
                                "title": "File:Pollo al limón.jpg",
                                "imageinfo": [
                                    {
                                        "mime": "image/jpeg",
                                        "thumburl": "https://upload.wikimedia.org/thumb.jpg",
                                    }
                                ],
                            }
                        }
                    }
                },
            )
        if url == "https://upload.wikimedia.org/thumb.jpg":
            return httpx.Response(200, headers={"content-type": "image/jpeg"}, content=png)
        raise AssertionError(f"URL inesperada: {url}")

    monkeypatch.setattr(svc.settings, "static_dir", str(tmp_path))
    monkeypatch.setattr(svc.settings, "image_source", "web")
    monkeypatch.setattr(svc.httpx, "get", fake_get)

    url = svc.generate_recipe_image({"nombre": "Pollo al limón"}, "hash3")
    assert url == "/static/recipes/hash3.png"
    assert (tmp_path / "hash3.png").exists()


def test_web_fallback_keeps_placeholder_when_not_found(monkeypatch, tmp_path):
    def fake_get(url, **kwargs):
        return httpx.Response(200, json={"meals": None})

    monkeypatch.setattr(svc.settings, "static_dir", str(tmp_path))
    monkeypatch.setattr(svc.settings, "image_source", "web")
    monkeypatch.setattr(svc.httpx, "get", fake_get)

    assert svc.generate_recipe_image({"nombre": "Budín básico"}, "hash2") is None
    assert not (tmp_path / "hash2.png").exists()
