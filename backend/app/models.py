from datetime import UTC, datetime

from sqlmodel import Field, SQLModel

CATEGORIAS = {
    "proteínas",
    "verduras",
    "frutas",
    "lácteos",
    "granos",
    "especias",
    "otros",
}

UNIDADES = {
    "g",
    "kg",
    "ml",
    "l",
    "piezas",
    "unidades",
    "cucharadas",
    "cucharaditas",
    "pizca",
    "al gusto",
}


def utcnow() -> datetime:
    return datetime.now(UTC)


class Ingredient(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    nombre: str = Field(index=True, unique=True)
    cantidad: float = Field(ge=0)
    unidad: str
    categoria: str
    created_at: datetime = Field(default_factory=utcnow)
