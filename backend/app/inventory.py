import unicodedata
from sqlmodel import Session, select

from .models import Ingredient
from .schemas import RecipeIngredient, StockResult


def normalize(nombre: str) -> str:
    s = unicodedata.normalize("NFKD", nombre.strip().lower())
    return "".join(c for c in s if not unicodedata.combining(c))


_UNIT_CLASSES: dict[str, tuple[str, float]] = {
    # Masa
    "g": ("mass", 1.0),
    "gr": ("mass", 1.0),
    "grs": ("mass", 1.0),
    "g.": ("mass", 1.0),
    "gramo": ("mass", 1.0),
    "gramos": ("mass", 1.0),
    "kg": ("mass", 1000.0),
    "kilo": ("mass", 1000.0),
    "kilos": ("mass", 1000.0),
    "kilogramo": ("mass", 1000.0),
    "kilogramos": ("mass", 1000.0),
    "kg.": ("mass", 1000.0),
    # Volumen
    "ml": ("volume", 1.0),
    "mls": ("volume", 1.0),
    "ml.": ("volume", 1.0),
    "cc": ("volume", 1.0),
    "mililitro": ("volume", 1.0),
    "mililitros": ("volume", 1.0),
    "l": ("volume", 1000.0),
    "lt": ("volume", 1000.0),
    "lts": ("volume", 1000.0),
    "l.": ("volume", 1000.0),
    "litro": ("volume", 1000.0),
    "litros": ("volume", 1000.0),
    "taza": ("volume", 250.0),
    "tazas": ("volume", 250.0),
    # Conteo / Unidades
    "pieza": ("count", 1.0),
    "piezas": ("count", 1.0),
    "unidad": ("count", 1.0),
    "unidades": ("count", 1.0),
    "ud": ("count", 1.0),
    "uds": ("count", 1.0),
    "diente": ("count", 1.0),
    "dientes": ("count", 1.0),
    "rebanada": ("count", 1.0),
    "rebanadas": ("count", 1.0),
    # Envases
    "lata": ("cans", 1.0),
    "latas": ("cans", 1.0),
    "sobre": ("packs", 1.0),
    "sobres": ("packs", 1.0),
    "bolsa": ("packs", 1.0),
    "bolsas": ("packs", 1.0),
    "paquete": ("packs", 1.0),
    "paquetes": ("packs", 1.0),
    "pqte": ("packs", 1.0),
    "pqtes": ("packs", 1.0),
    # Cucharas
    "cucharada": ("spoons", 1.0),
    "cucharadas": ("spoons", 1.0),
    "cda": ("spoons", 1.0),
    "cdas": ("spoons", 1.0),
    "cucharadita": ("spoons", 0.333),
    "cucharaditas": ("spoons", 0.333),
    "cdita": ("spoons", 0.333),
    "cditas": ("spoons", 0.333),
    # Otros
    "pizca": ("pinch", 1.0),
    "pizcas": ("pinch", 1.0),
    "al gusto": ("taste", 1.0),
}

_DEFAULT_PACK_GRAMS: dict[str, float] = {
    "pasta": 400.0,
    "fideos": 400.0,
    "espagueti": 400.0,
    "spaghetti": 400.0,
    "tallarines": 400.0,
    "macarrones": 400.0,
    "arroz": 1000.0,
    "harina": 1000.0,
    "lentejas": 1000.0,
    "garbanzos": 1000.0,
    "porotos": 1000.0,
    "frijoles": 1000.0,
    "avena": 500.0,
    "azucar": 1000.0,
}


def _unidad_info(unidad: str | None) -> tuple[str, float] | None:
    if not unidad:
        return None
    return _UNIT_CLASSES.get(unidad.strip().lower())


def _grams(
    cantidad: float,
    unidad: str | None,
    gramos_por_unidad: float | None,
    nombre: str = "",
) -> float | None:
    """Convierte una cantidad a gramos si la unidad lo permite, si no devuelve None."""
    info = _unidad_info(unidad)
    if info is None:
        return None
    unit_class, factor = info
    if unit_class == "mass":
        return cantidad * factor
    if unit_class in {"count", "cans", "packs"}:
        effective_gpu = gramos_por_unidad or _DEFAULT_PACK_GRAMS.get(normalize(nombre))
        if effective_gpu:
            return cantidad * effective_gpu
    if unit_class == "spoons":
        return cantidad * factor * 15.0
    return None


def find_ingredient(session: Session, nombre: str) -> Ingredient | None:
    target = normalize(nombre)
    rows = list(session.exec(select(Ingredient)).all())
    # 1. Coincidencia exacta sin tildes ni mayúsculas
    for row in rows:
        if normalize(row.nombre) == target:
            return row
    # 2. Coincidencia singular / plural
    for row in rows:
        rn = normalize(row.nombre)
        if (
            target == rn + "s"
            or rn == target + "s"
            or target == rn + "es"
            or rn == target + "es"
        ):
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

        # Si no tiene unidad pero la cantidad es >= 10 y el stock es de masa o paquete,
        # asumir gramos por defecto
        effective_req_unidad = item.unidad
        if effective_req_unidad is None:
            if stock_info is not None and stock_info[0] in {"mass", "packs"} and item.cantidad >= 10:
                effective_req_unidad = "g"
                req_info = _unidad_info("g")
            else:
                effective_req_unidad = row.unidad
                req_info = stock_info

        stock_grams = _grams(row.cantidad, row.unidad, row.gramos_por_unidad, row.nombre)
        req_grams = _grams(item.cantidad, effective_req_unidad, row.gramos_por_unidad, row.nombre)

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
            elif _DEFAULT_PACK_GRAMS.get(normalize(row.nombre)):
                deduccion = req_grams / _DEFAULT_PACK_GRAMS[normalize(row.nombre)]
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
        nueva_cantidad = max(0.0, round(row.cantidad - cantidad, 4))
        descontados.append({"nombre": row.nombre, "cantidad": cantidad, "unidad": row.unidad})
        if nueva_cantidad <= 0:
            row.cantidad = 0.0
            session.delete(row)
        else:
            row.cantidad = nueva_cantidad
    session.commit()
    for row, _ in a_descontar:
        if row.cantidad > 0:
            session.refresh(row)
    return StockResult(ok=True, descontados=descontados, faltantes=[])
