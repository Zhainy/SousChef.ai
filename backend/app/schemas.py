from pydantic import BaseModel, Field


class IngredientCreate(BaseModel):
    nombre: str = Field(min_length=1, max_length=120)
    cantidad: float = Field(gt=0)
    unidad: str = Field(min_length=1, max_length=40)
    categoria: str = Field(min_length=1, max_length=40)
    gramos_por_unidad: float | None = Field(default=None, gt=0)


class IngredientUpdate(BaseModel):
    nombre: str | None = Field(default=None, min_length=1, max_length=120)
    cantidad: float | None = Field(default=None, gt=0)
    unidad: str | None = Field(default=None, min_length=1, max_length=40)
    categoria: str | None = Field(default=None, min_length=1, max_length=40)
    gramos_por_unidad: float | None = Field(default=None, gt=0)


class RecipeIngredient(BaseModel):
    nombre: str = Field(min_length=1, max_length=120)
    cantidad: float = Field(gt=0)
    unidad: str | None = None


class Recipe(BaseModel):
    nombre: str = Field(min_length=1, max_length=160)
    resumen: str | None = None
    tiempo_minutos: int | None = Field(default=None, ge=1, le=1440)
    ingredientes: list[RecipeIngredient] = Field(min_length=1)
    instrucciones: str | None = None


class StockResult(BaseModel):
    ok: bool
    descontados: list[dict]
    faltantes: list[dict]


def normalize_recipe(data: dict) -> Recipe | None:
    """Coacciona la salida del LLM a un Recipe válido, descartando campos inválidos."""
    # Soporte para respuestas anidadas tipo {"mensaje": "...", "receta": {...}}
    if isinstance(data.get("receta"), dict):
        data = data["receta"]
    elif isinstance(data.get("recipe"), dict):
        data = data["recipe"]

    nombre = str(data.get("nombre") or data.get("name") or "").strip()
    if not nombre:
        return None

    ingredientes: list[RecipeIngredient] = []
    raw_ingredientes = (
        data.get("ingredientes")
        or data.get("ingredients")
        or data.get("items")
        or data.get("ingrediente")
        or []
    )
    for ing in raw_ingredientes:
        if isinstance(ing, str):
            name = ing.strip()
            if name:
                ingredientes.append(RecipeIngredient(nombre=name[:120], cantidad=1.0, unidad=None))
            continue
        if not isinstance(ing, dict):
            continue
        name = str(
            ing.get("nombre")
            or ing.get("name")
            or ing.get("item")
            or ing.get("ingrediente")
            or ""
        ).strip()
        if not name:
            continue
        cant_raw = (
            ing.get("cantidad")
            if ing.get("cantidad") is not None
            else (
                ing.get("amount")
                if ing.get("amount") is not None
                else (ing.get("quantity") if ing.get("quantity") is not None else 1.0)
            )
        )
        try:
            cantidad = float(cant_raw)
        except (TypeError, ValueError):
            continue
        if cantidad <= 0:
            continue
        unidad = ing.get("unidad") or ing.get("unit")
        unidad = unidad.strip() if isinstance(unidad, str) and unidad.strip() else None
        ingredientes.append(
            RecipeIngredient(
                nombre=name[:120],
                cantidad=cantidad,
                unidad=unidad[:40] if unidad else None,
            )
        )
    if not ingredientes:
        return None

    resumen = data.get("resumen") or data.get("summary") or data.get("description")
    resumen = resumen.strip() if isinstance(resumen, str) and resumen.strip() else None
    tiempo_raw = data.get("tiempo_minutos") if data.get("tiempo_minutos") is not None else (
        data.get("prep_time") or data.get("time_minutes") or data.get("tiempo")
    )
    try:
        tiempo = int(tiempo_raw)
    except (TypeError, ValueError):
        tiempo = None
    if tiempo is not None and not 1 <= tiempo <= 1440:
        tiempo = None
    instrucciones = data.get("instrucciones") or data.get("instructions") or data.get("pasos")
    if isinstance(instrucciones, list):
        steps = [
            f"{idx + 1}. {p}" if not str(p).startswith(f"{idx + 1}.") else str(p)
            for idx, p in enumerate(instrucciones)
        ]
        instrucciones = "\n".join(steps)
    instrucciones = (
        instrucciones.strip() if isinstance(instrucciones, str) and instrucciones.strip() else None
    )

    return Recipe(
        nombre=nombre[:160],
        resumen=resumen,
        tiempo_minutos=tiempo,
        ingredientes=ingredientes,
        instrucciones=instrucciones,
    )


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    force_recipe: bool = False
