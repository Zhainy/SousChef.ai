import json
from typing import Any

from sqlmodel import Session, select

from ..db import engine
from ..inventory import descontar_stock
from ..models import Ingredient
from ..schemas import RecipeIngredient


def get_inventario() -> dict[str, Any]:
    with Session(engine) as session:
        items = list(session.exec(select(Ingredient).order_by(Ingredient.nombre)).all())
    return {
        "inventario": [
            {
                "nombre": i.nombre,
                "cantidad": i.cantidad,
                "unidad": i.unidad,
                "categoria": i.categoria,
            }
            for i in items
        ]
    }


def descontar_stock_tool(ingredientes: list[dict[str, Any]]) -> dict[str, Any]:
    items = [
        RecipeIngredient(nombre=str(x["nombre"]), cantidad=float(x["cantidad"]))
        for x in ingredientes
    ]
    with Session(engine) as session:
        result = descontar_stock(session, items)
    return result.model_dump()


TOOL_REGISTRY: dict[str, Any] = {
    "get_inventario": get_inventario,
    "descontar_stock": descontar_stock_tool,
}


def execute_tool(name: str, args: dict[str, Any]) -> str:
    if name not in TOOL_REGISTRY:
        return json.dumps({"error": f"Herramienta desconocida: {name}"}, ensure_ascii=False)
    try:
        result = TOOL_REGISTRY[name](**args)
    except Exception as exc:  # noqa: BLE001
        return json.dumps({"error": str(exc)}, ensure_ascii=False)
    return json.dumps(result, ensure_ascii=False, default=str)
