from collections.abc import Generator
from typing import Annotated, Any

from fastapi import Depends
from sqlmodel import Session, SQLModel, create_engine

from .config import settings

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False},
)


def init_db() -> None:
    SQLModel.metadata.create_all(engine)
    migrate(engine)


def migrate(engine_: Any) -> None:
    from sqlalchemy import inspect, text

    cols = {c["name"] for c in inspect(engine_).get_columns("ingredient")}
    if "gramos_por_unidad" not in cols:
        with engine_.begin() as conn:
            conn.execute(text("ALTER TABLE ingredient ADD COLUMN gramos_por_unidad FLOAT"))


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session


SessionDep = Annotated[Session, Depends(get_session)]
