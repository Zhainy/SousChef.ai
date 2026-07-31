def test_list_ingredients_has_seed(client):
    res = client.get("/api/ingredients")
    assert res.status_code == 200
    data = res.json()
    assert len(data) >= 15
    assert any(item["nombre"] == "tomate" for item in data)


def test_create_ingredient(client):
    payload = {
        "nombre": "champiñones",
        "cantidad": 250,
        "unidad": "g",
        "categoria": "verduras",
    }
    res = client.post("/api/ingredients", json=payload)
    assert res.status_code == 201
    body = res.json()
    assert body["nombre"] == "champiñones"
    assert body["cantidad"] == 250


def test_create_duplicate_returns_409(client):
    payload = {
        "nombre": "Tomate",
        "cantidad": 1,
        "unidad": "piezas",
        "categoria": "verduras",
    }
    res = client.post("/api/ingredients", json=payload)
    assert res.status_code == 409


def test_patch_ingredient(client):
    items = client.get("/api/ingredients").json()
    target = next(i for i in items if i["nombre"] == "tomate")
    res = client.patch(f"/api/ingredients/{target['id']}", json={"cantidad": 5})
    assert res.status_code == 200
    assert res.json()["cantidad"] == 5


def test_patch_duplicate_returns_409(client):
    items = client.get("/api/ingredients").json()
    target = next(i for i in items if i["nombre"] == "tomate")
    res = client.patch(f"/api/ingredients/{target['id']}", json={"nombre": "Leche"})
    assert res.status_code == 409


def test_patch_missing_returns_404(client):
    res = client.patch("/api/ingredients/99999", json={"cantidad": 1})
    assert res.status_code == 404


def test_delete_ingredient(client):
    items = client.get("/api/ingredients").json()
    target = next(i for i in items if i["nombre"] == "tomate")
    res = client.delete(f"/api/ingredients/{target['id']}")
    assert res.status_code == 204
    remaining = client.get("/api/ingredients").json()
    assert all(i["nombre"] != "tomate" for i in remaining)


def test_delete_missing_returns_404(client):
    res = client.delete("/api/ingredients/99999")
    assert res.status_code == 404


def test_create_invalid_cantidad(client):
    payload = {
        "nombre": "champiñones",
        "cantidad": -3,
        "unidad": "g",
        "categoria": "verduras",
    }
    res = client.post("/api/ingredients", json=payload)
    assert res.status_code == 422
