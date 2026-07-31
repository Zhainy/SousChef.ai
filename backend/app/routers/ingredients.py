from fastapi import APIRouter, HTTPException, status
from sqlmodel import select

from ..db import SessionDep
from ..inventory import find_ingredient
from ..models import Ingredient
from ..schemas import IngredientCreate, IngredientUpdate

router = APIRouter(prefix="/api/ingredients", tags=["ingredientes"])


@router.get("")
def list_ingredients(session: SessionDep) -> list[Ingredient]:
    return list(
        session.exec(select(Ingredient).order_by(Ingredient.categoria, Ingredient.nombre)).all()
    )


@router.post("", response_model=Ingredient, status_code=status.HTTP_201_CREATED)
def create_ingredient(payload: IngredientCreate, session: SessionDep) -> Ingredient:
    if find_ingredient(session, payload.nombre) is not None:
        raise HTTPException(status_code=409, detail="Ya existe un ingrediente con ese nombre")
    row = Ingredient(**payload.model_dump())
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


@router.patch("/{ingredient_id}", response_model=Ingredient)
def update_ingredient(
    ingredient_id: int, payload: IngredientUpdate, session: SessionDep
) -> Ingredient:
    row = session.get(Ingredient, ingredient_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Ingrediente no encontrado")
    data = payload.model_dump(exclude_unset=True)
    if "nombre" in data:
        other = find_ingredient(session, data["nombre"])
        if other is not None and other.id != row.id:
            raise HTTPException(status_code=409, detail="Ya existe un ingrediente con ese nombre")
    for field, value in data.items():
        setattr(row, field, value)
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


@router.delete("/{ingredient_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_ingredient(ingredient_id: int, session: SessionDep) -> None:
    row = session.get(Ingredient, ingredient_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Ingrediente no encontrado")
    session.delete(row)
    session.commit()
