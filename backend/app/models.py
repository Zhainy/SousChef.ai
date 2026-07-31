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
    "lata",
    "latas",
    "sobre",
    "sobres",
    "bolsa",
    "bolsas",
    "paquete",
    "paquetes",
}


def utcnow() -> datetime:
    return datetime.now(UTC)


class Ingredient(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    nombre: str = Field(index=True, unique=True)
    cantidad: float = Field(ge=0)
    unidad: str
    categoria: str
    gramos_por_unidad: float | None = Field(default=None, ge=0)
    created_at: datetime = Field(default_factory=utcnow)
