import httpx

from app.agent import image_service as svc

# Minimal valid 1x1 PNG bytes
_PNG_BYTES = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\xcf\xc0"
    b"\x00\x00\x03\x01\x01\x00\x18\xdd\x8d\xb0\x00\x00\x00\x00IEND\xaeB`\x82"
)


def _png_bytes() -> bytes:
    return _PNG_BYTES


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


def test_web_pipeline_downloads_meal_db_image(monkeypatch, tmp_path):
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


def test_meal_db_uses_translation_for_spanish_recipe(monkeypatch, tmp_path):
    png = _png_bytes()
    searches: list[str] = []

    def fake_get(url, **kwargs):
        if "themealdb.com" in url:
            params = kwargs.get("params", {})
            query = params.get("s", "")
            searches.append(query)
            if query == "chicken rice":
                return httpx.Response(
                    200,
                    json={"meals": [{"strMealThumb": "https://cdn.example.com/chicken_rice.jpg"}]},
                )
            return httpx.Response(200, json={"meals": None})
        if url == "https://cdn.example.com/chicken_rice.jpg":
            return httpx.Response(200, headers={"content-type": "image/jpeg"}, content=png)
        raise AssertionError(f"URL inesperada: {url}")

    monkeypatch.setattr(svc.settings, "static_dir", str(tmp_path))
    monkeypatch.setattr(svc.settings, "image_source", "web")
    monkeypatch.setattr(svc.httpx, "get", fake_get)

    url = svc.generate_recipe_image({"nombre": "pollo arroz"}, "hash_translated")
    assert url == "/static/recipes/hash_translated.png"
    assert "chicken rice" in searches
    assert (tmp_path / "hash_translated.png").exists()


def test_commons_fallback_downloads_image_when_mealdb_empty(monkeypatch, tmp_path):
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
                            "123": {
                                "imageinfo": [
                                    {
                                        "mime": "image/jpeg",
                                        "thumburl": "https://thumb.wikimedia.org/guiso.jpg",
                                    }
                                ]
                            }
                        }
                    }
                },
            )
        if url == "https://thumb.wikimedia.org/guiso.jpg":
            return httpx.Response(200, headers={"content-type": "image/jpeg"}, content=png)
        raise AssertionError(f"URL inesperada: {url}")

    monkeypatch.setattr(svc.settings, "static_dir", str(tmp_path))
    monkeypatch.setattr(svc.settings, "image_source", "web")
    monkeypatch.setattr(svc.httpx, "get", fake_get)

    url = svc.generate_recipe_image({"nombre": "Guiso casero de lentejas"}, "hash_commons")
    assert url == "/static/recipes/hash_commons.png"
    assert (tmp_path / "hash_commons.png").exists()


def test_image_source_none_returns_none_without_network(monkeypatch, tmp_path):
    def boom(url, **kwargs):
        raise AssertionError(f"no se esperaba fetch a {url}")

    monkeypatch.setattr(svc.settings, "static_dir", str(tmp_path))
    monkeypatch.setattr(svc.settings, "image_source", "none")
    monkeypatch.setattr(svc.httpx, "get", boom)

    assert svc.generate_recipe_image({"nombre": "Cualquier cosa"}, "hash_none") is None
    assert not (tmp_path / "hash_none.png").exists()


def test_empty_recipe_name_returns_none(monkeypatch, tmp_path):
    monkeypatch.setattr(svc.settings, "static_dir", str(tmp_path))
    monkeypatch.setattr(svc.settings, "image_source", "web")

    assert svc.generate_recipe_image({"nombre": ""}, "hash_empty") is None
