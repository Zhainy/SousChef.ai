import json
from typing import Any

from sqlmodel import Session, select

from ..db import engine
from ..inventory import descontar_stock
from ..models import Ingredient
from ..schemas import RecipeIngredient

TOOL_DEFS: list[dict[str, Any]] = [
    {
        "name": "get_inventario",
        "description": (
            "Consulta el inventario actual de la despensa. Devuelve nombres, "
            "cantidades, unidades y categorías."
        ),
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "name": "descontar_stock",
        "description": (
            "Descuenta las cantidades indicadas de la despensa tras cocinar una "
            "receta. Devuelve lo descontado o los faltantes."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "ingredientes": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "nombre": {"type": "string"},
                            "cantidad": {"type": "number"},
                            "unidad": {"type": "string"},
                        },
                        "required": ["nombre", "cantidad"],
                    },
                }
            },
            "required": ["ingredientes"],
        },
    },
]


def openai_tools() -> list[dict[str, Any]]:
    return [{"type": "function", "function": dict(d)} for d in TOOL_DEFS]


def get_inventario() -> dict[str, Any]:
    with Session(engine) as session:
        items = list(
            session.exec(
                select(Ingredient).where(Ingredient.cantidad > 0).order_by(Ingredient.nombre)
            ).all()
        )
    return {
        "inventario": [
            {
                "nombre": i.nombre,
                "cantidad": i.cantidad,
                "unidad": i.unidad,
                "categoria": i.categoria,
                "gramos_por_unidad": i.gramos_por_unidad,
                "limite_maximo_para_receta": f"Usa COMO MÁXIMO {i.cantidad} {i.unidad}",
            }
            for i in items
        ],
        "regla_critica": (
            "Para que la receta se pueda cocinar, la cantidad de CADA ingrediente "
            "NUNCA debe superar el límite indicado en el inventario. Ajusta la receta "
            "y las porciones a las cantidades exactas que el usuario tiene disponibles."
        ),
    }


def descontar_stock_tool(ingredientes: list[dict[str, Any]]) -> dict[str, Any]:
    items = [
        RecipeIngredient(
            nombre=str(x["nombre"]),
            cantidad=float(x["cantidad"]),
            unidad=str(x["unidad"]) if x.get("unidad") else None,
        )
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
