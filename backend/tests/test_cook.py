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


def test_cook_matches_equivalent_units(client):
    res = _cook(client, [{"nombre": "atún", "cantidad": 1, "unidad": "lata"}])
    assert res.status_code == 200
    assert _cantidad(client, "atún") == 1


def test_cook_converts_units_in_same_class(client):
    res = _cook(client, [{"nombre": "arroz", "cantidad": 0.5, "unidad": "kg"}])
    assert res.status_code == 200
    body = res.json()
    assert body["descontados"][0]["cantidad"] == 500
    assert _cantidad(client, "arroz") == 500


def test_cook_reports_incompatible_units(client):
    res = _cook(client, [{"nombre": "tomate", "cantidad": 200, "unidad": "g"}])
    assert res.status_code == 409
    body = res.json()
    motivo = body["detail"]["faltantes"][0]["motivo"]
    assert "unidad incompatible" in motivo
    assert _cantidad(client, "tomate") == 3


def test_cook_converts_grams_when_container_has_gramos_por_unidad(client):
    res = _cook(client, [{"nombre": "atún", "cantidad": 280, "unidad": "g"}])
    assert res.status_code == 200
    body = res.json()
    assert body["descontados"][0]["cantidad"] == 2
    assert _cantidad(client, "atún") == 0


def test_cook_insufficient_grams_reports_detail(client):
    res = _cook(client, [{"nombre": "atún", "cantidad": 300, "unidad": "g"}])
    assert res.status_code == 409
    faltante = res.json()["detail"]["faltantes"][0]
    assert faltante["motivo"] == "stock insuficiente"
    assert "280 g" in faltante["detalle"]
    assert _cantidad(client, "atún") == 2
