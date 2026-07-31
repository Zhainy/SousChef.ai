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
    nombre = str(data.get("nombre") or "").strip()
    if not nombre:
        return None

    ingredientes: list[RecipeIngredient] = []
    for ing in data.get("ingredientes") or []:
        if not isinstance(ing, dict):
            continue
        name = str(ing.get("nombre") or "").strip()
        if not name:
            continue
        try:
            cantidad = float(ing.get("cantidad"))
        except (TypeError, ValueError):
            continue
        if cantidad <= 0:
            continue
        unidad = ing.get("unidad")
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

    resumen = data.get("resumen")
    resumen = resumen.strip() if isinstance(resumen, str) and resumen.strip() else None
    try:
        tiempo = int(data.get("tiempo_minutos"))
    except (TypeError, ValueError):
        tiempo = None
    if tiempo is not None and not 1 <= tiempo <= 1440:
        tiempo = None
    instrucciones = data.get("instrucciones")
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
