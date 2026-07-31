from sqlmodel import Session, select

from .models import Ingredient
from .schemas import RecipeIngredient, StockResult


def normalize(nombre: str) -> str:
    return nombre.strip().lower()


def find_ingredient(session: Session, nombre: str) -> Ingredient | None:
    target = normalize(nombre)
    for row in session.exec(select(Ingredient)).all():
        if normalize(row.nombre) == target:
            return row
    return None


def descontar_stock(session: Session, ingredientes: list[RecipeIngredient]) -> StockResult:
    a_descontar: list[tuple[Ingredient, float]] = []
    faltantes: list[dict] = []
    for item in ingredientes:
        row = find_ingredient(session, item.nombre)
        if row is None:
            faltantes.append(
                {
                    "nombre": item.nombre,
                    "pedido": item.cantidad,
                    "disponible": 0.0,
                    "motivo": "no existe en la despensa",
                }
            )
        elif row.cantidad + 1e-9 < item.cantidad:
            faltantes.append(
                {
                    "nombre": item.nombre,
                    "pedido": item.cantidad,
                    "disponible": row.cantidad,
                    "motivo": "stock insuficiente",
                }
            )
        else:
            a_descontar.append((row, item.cantidad))

    if faltantes:
        return StockResult(ok=False, descontados=[], faltantes=faltantes)

    descontados: list[dict] = []
    for row, cantidad in a_descontar:
        row.cantidad = max(0.0, round(row.cantidad - cantidad, 4))
        descontados.append({"nombre": row.nombre, "cantidad": cantidad, "unidad": row.unidad})
    session.commit()
    for row, _ in a_descontar:
        session.refresh(row)
    return StockResult(ok=True, descontados=descontados, faltantes=[])
