from fastapi import APIRouter, HTTPException

from ..db import SessionDep
from ..inventory import descontar_stock
from ..schemas import Recipe, StockResult

router = APIRouter(prefix="/api/recipes", tags=["recetas"])


@router.post("/cook", response_model=StockResult)
def cook_recipe(recipe: Recipe, session: SessionDep) -> StockResult:
    result = descontar_stock(session, recipe.ingredientes)
    if not result.ok:
        raise HTTPException(status_code=409, detail={"faltantes": result.faltantes})
    return result
