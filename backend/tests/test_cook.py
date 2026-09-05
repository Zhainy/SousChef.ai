def _cook(client, ingredientes, nombre="Pollo al limón"):
    return client.post(
        "/api/recipes/cook",
        json={"nombre": nombre, "ingredientes": ingredientes},
    )


def _cantidad(client, nombre):
    items = client.get("/api/ingredients").json()
    return next((i["cantidad"] for i in items if i["nombre"] == nombre), 0)


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


def test_cook_matches_without_accent(client):
    res = _cook(client, [{"nombre": "atun", "cantidad": 1, "unidad": "lata"}])
    assert res.status_code == 200
    assert res.json()["ok"] is True
    assert _cantidad(client, "atún") == 1


def test_cook_matches_plural_and_singular(client):
    res = _cook(client, [{"nombre": "tomates", "cantidad": 1}])
    assert res.status_code == 200
    assert _cantidad(client, "tomate") == 2


def test_cook_requires_ingredients(client):
    res = client.post("/api/recipes/cook", json={"nombre": "Vacio", "ingredientes": []})
    assert res.status_code == 400
    assert "ingredientes" in res.json()["detail"]


def test_cook_tolerates_invalid_tiempo_minutos(client):
    res = _cook(client, [{"nombre": "tomate", "cantidad": 1}])
    res = client.post(
        "/api/recipes/cook",
        json={
            "nombre": "Pollo al limón",
            "tiempo_minutos": 0,
            "ingredientes": [{"nombre": "tomate", "cantidad": 1}],
        },
    )
    assert res.status_code == 200


def test_cook_drops_invalid_ingredients(client):
    res = client.post(
        "/api/recipes/cook",
        json={
            "nombre": "Mix",
            "ingredientes": [
                {"nombre": "tomate", "cantidad": 1},
                {"nombre": "basura", "cantidad": 0},
                {"nombre": "", "cantidad": 5},
            ],
        },
    )
    assert res.status_code == 200
    body = res.json()
    assert [d["nombre"] for d in body["descontados"]] == ["tomate"]


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
    # Confirma que fue eliminado de la lista de ingredientes disponibles
    assert not any(i["nombre"] == "atún" for i in client.get("/api/ingredients").json())


def test_cook_insufficient_grams_reports_detail(client):
    res = _cook(client, [{"nombre": "atún", "cantidad": 300, "unidad": "g"}])
    assert res.status_code == 409
    faltante = res.json()["detail"]["faltantes"][0]
    assert faltante["motivo"] == "stock insuficiente"
    assert "280 g" in faltante["detalle"]
    assert _cantidad(client, "atún") == 2


def test_cook_converts_package_with_gramos_por_unidad_to_grams(client):
    items = client.get("/api/ingredients").json()
    pasta = next(i for i in items if i["nombre"] == "pasta")
    client.patch(
        f"/api/ingredients/{pasta['id']}",
        json={
            "cantidad": 3.0,
            "unidad": "paquete",
            "gramos_por_unidad": 500.0,
        },
    )
    res = _cook(client, [{"nombre": "pasta", "cantidad": 200, "unidad": "gramos"}])
    assert res.status_code == 200
    body = res.json()
    assert body["ok"] is True
    assert _cantidad(client, "pasta") == 2.6


def test_cook_converts_spoons_to_grams(client):
    res = _cook(client, [{"nombre": "mantequilla", "cantidad": 1, "unidad": "cucharada"}])
    assert res.status_code == 200
    assert _cantidad(client, "mantequilla") == 85.0
