from fastapi import APIRouter, HTTPException

from ..db import SessionDep
from ..inventory import descontar_stock
from ..schemas import StockResult, normalize_recipe

router = APIRouter(prefix="/api/recipes", tags=["recetas"])


@router.post("/cook", response_model=StockResult)
def cook_recipe(payload: dict, session: SessionDep) -> StockResult:
    recipe = normalize_recipe(payload)
    if recipe is None:
        raise HTTPException(status_code=400, detail="La receta no tiene ingredientes válidos.")
    result = descontar_stock(session, recipe.ingredientes)
    if not result.ok:
        raise HTTPException(status_code=409, detail={"faltantes": result.faltantes})
    return result
