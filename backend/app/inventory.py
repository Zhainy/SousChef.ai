from sqlmodel import Session, select

from .models import Ingredient
from .schemas import RecipeIngredient, StockResult


def normalize(nombre: str) -> str:
    return nombre.strip().lower()


_UNIT_CLASSES: dict[str, tuple[str, float]] = {
    "g": ("mass", 1.0),
    "kg": ("mass", 1000.0),
    "ml": ("volume", 1.0),
    "l": ("volume", 1000.0),
    "pieza": ("count", 1.0),
    "piezas": ("count", 1.0),
    "unidad": ("count", 1.0),
    "unidades": ("count", 1.0),
    "lata": ("cans", 1.0),
    "latas": ("cans", 1.0),
    "sobre": ("packs", 1.0),
    "sobres": ("packs", 1.0),
    "bolsa": ("packs", 1.0),
    "bolsas": ("packs", 1.0),
    "paquete": ("packs", 1.0),
    "paquetes": ("packs", 1.0),
    "cucharada": ("spoons", 1.0),
    "cucharadas": ("spoons", 1.0),
    "cucharadita": ("spoons", 1.0),
    "cucharaditas": ("spoons", 1.0),
    "pizca": ("pinch", 1.0),
    "al gusto": ("taste", 1.0),
}


def _unidad_info(unidad: str | None) -> tuple[str, float] | None:
    if not unidad:
        return None
    return _UNIT_CLASSES.get(unidad.strip().lower())


def _grams(cantidad: float, unidad: str | None, gramos_por_unidad: float | None) -> float | None:
    """Convierte una cantidad a gramos si la unidad lo permite, si no devuelve None."""
    info = _unidad_info(unidad)
    if info is None:
        return None
    unit_class, factor = info
    if unit_class == "mass":
        return cantidad * factor
    if unit_class in {"count", "cans", "packs"} and gramos_por_unidad:
        return cantidad * gramos_por_unidad
    return None


def find_ingredient(session: Session, nombre: str) -> Ingredient | None:
    target = normalize(nombre)
    for row in session.exec(select(Ingredient)).all():
        if normalize(row.nombre) == target:
            return row
    return None


def _formato(num: float) -> str:
    return str(int(num)) if float(num).is_integer() else str(round(num, 2))


def _detalle(row: Ingredient, stock_grams: float) -> str:
    info = _unidad_info(row.unidad)
    if info is not None and info[0] == "mass":
        return f"disponible: {_formato(stock_grams)} g"
    return f"disponible: {_formato(row.cantidad)} {row.unidad} (≈ {_formato(stock_grams)} g)"


def _faltante(
    item: RecipeIngredient,
    row: Ingredient,
    motivo: str,
    detalle: str | None = None,
) -> dict:
    return {
        "nombre": item.nombre,
        "pedido": item.cantidad,
        "disponible": row.cantidad,
        "unidad": row.unidad,
        "gramos_por_unidad": row.gramos_por_unidad,
        "motivo": motivo,
        "detalle": detalle,
    }


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
                    "unidad": None,
                    "gramos_por_unidad": None,
                    "motivo": "no existe en la despensa",
                    "detalle": None,
                }
            )
            continue
        stock_info = _unidad_info(row.unidad)
        req_info = _unidad_info(item.unidad)
        stock_grams = _grams(row.cantidad, row.unidad, row.gramos_por_unidad)
        req_grams = _grams(item.cantidad, item.unidad, None)
        if stock_grams is not None and req_grams is not None:
            if stock_grams + 1e-9 < req_grams:
                faltantes.append(
                    _faltante(
                        item,
                        row,
                        "stock insuficiente",
                        _detalle(row, stock_grams),
                    )
                )
                continue
            if stock_info is not None and stock_info[0] == "mass":
                deduccion = req_grams / stock_info[1]
            elif row.gramos_por_unidad:
                deduccion = req_grams / row.gramos_por_unidad
            else:
                deduccion = item.cantidad
            a_descontar.append((row, deduccion))
            continue
        if stock_info is not None and req_info is not None:
            if stock_info[0] != req_info[0]:
                faltantes.append(
                    _faltante(
                        item,
                        row,
                        f"unidad incompatible ({item.unidad} vs {row.unidad})",
                    )
                )
                continue
            stock_cantidad = row.cantidad * stock_info[1]
            pedido_cantidad = item.cantidad * req_info[1]
        else:
            stock_cantidad = row.cantidad
            pedido_cantidad = item.cantidad
        if stock_cantidad + 1e-9 < pedido_cantidad:
            faltantes.append(
                _faltante(
                    item,
                    row,
                    "stock insuficiente",
                    f"disponible: {_formato(row.cantidad)} {row.unidad}",
                )
            )
        else:
            a_descontar.append(
                (row, item.cantidad * req_info[1] / stock_info[1])
                if stock_info is not None and req_info is not None
                else (row, item.cantidad)
            )

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
