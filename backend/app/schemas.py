from pydantic import BaseModel, Field


class IngredientCreate(BaseModel):
    nombre: str = Field(min_length=1, max_length=120)
    cantidad: float = Field(gt=0)
    unidad: str = Field(min_length=1, max_length=40)
    categoria: str = Field(min_length=1, max_length=40)


class IngredientUpdate(BaseModel):
    nombre: str | None = Field(default=None, min_length=1, max_length=120)
    cantidad: float | None = Field(default=None, gt=0)
    unidad: str | None = Field(default=None, min_length=1, max_length=40)
    categoria: str | None = Field(default=None, min_length=1, max_length=40)


class RecipeIngredient(BaseModel):
    nombre: str = Field(min_length=1, max_length=120)
    cantidad: float = Field(gt=0)


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


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]
