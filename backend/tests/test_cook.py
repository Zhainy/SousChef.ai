def _cook(client, ingredientes, nombre="Pollo al limón"):
    return client.post(
        "/api/recipes/cook",
        json={"nombre": nombre, "ingredientes": ingredientes},
    )


def _cantidad(client, nombre):
    items = client.get("/api/ingredients").json()
    return next(i["cantidad"] for i in items if i["nombre"] == nombre)


def test_cook_success(client):
    res = _cook(
        client,
        [{"nombre": "tomate", "cantidad": 2}, {"nombre": "arroz", "cantidad": 300}],
    )
    assert res.status_code == 200
    body = res.json()
    assert body["ok"] is True
    assert len(body["descontados"]) == 2
    assert _cantidad(client, "tomate") == 1
    assert _cantidad(client, "arroz") == 700


def test_cook_insufficient_stock_returns_409(client):
    before = _cantidad(client, "tomate")
    res = _cook(client, [{"nombre": "tomate", "cantidad": 999}])
    assert res.status_code == 409
    body = res.json()
    assert body["detail"]["faltantes"][0]["motivo"] == "stock insuficiente"
    assert _cantidad(client, "tomate") == before


def test_cook_unknown_ingredient_returns_409(client):
    res = _cook(client, [{"nombre": "foie gras", "cantidad": 1}])
    assert res.status_code == 409
    body = res.json()
    assert body["detail"]["faltantes"][0]["motivo"] == "no existe en la despensa"


def test_cook_partial_failure_does_not_deduct(client):
    tomate = _cantidad(client, "tomate")
    arroz = _cantidad(client, "arroz")
    res = _cook(
        client,
        [
            {"nombre": "tomate", "cantidad": 1},
            {"nombre": "foie gras", "cantidad": 1},
        ],
    )
    assert res.status_code == 409
    assert _cantidad(client, "tomate") == tomate
    assert _cantidad(client, "arroz") == arroz


def test_cook_normalizes_names(client):
    res = _cook(client, [{"nombre": "  Tomate ", "cantidad": 1}])
    assert res.status_code == 200
    assert _cantidad(client, "tomate") == 2


def test_cook_requires_ingredients(client):
    res = client.post("/api/recipes/cook", json={"nombre": "Vacio", "ingredientes": []})
    assert res.status_code == 422
