from sqlmodel import Session, select

from .models import Ingredient

SEED = [
    {"nombre": "pechuga de pollo", "cantidad": 500, "unidad": "g", "categoria": "proteínas"},
    {"nombre": "huevos", "cantidad": 6, "unidad": "piezas", "categoria": "proteínas"},
    {"nombre": "atún", "cantidad": 2, "unidad": "latas", "categoria": "proteínas"},
    {"nombre": "carne molida de res", "cantidad": 400, "unidad": "g", "categoria": "proteínas"},
    {"nombre": "tomate", "cantidad": 3, "unidad": "piezas", "categoria": "verduras"},
    {"nombre": "cebolla", "cantidad": 2, "unidad": "piezas", "categoria": "verduras"},
    {"nombre": "zanahoria", "cantidad": 300, "unidad": "g", "categoria": "verduras"},
    {"nombre": "papa", "cantidad": 500, "unidad": "g", "categoria": "verduras"},
    {"nombre": "espinaca", "cantidad": 150, "unidad": "g", "categoria": "verduras"},
    {"nombre": "brócoli", "cantidad": 250, "unidad": "g", "categoria": "verduras"},
    {"nombre": "pimiento morrón", "cantidad": 2, "unidad": "piezas", "categoria": "verduras"},
    {"nombre": "manzana", "cantidad": 4, "unidad": "piezas", "categoria": "frutas"},
    {"nombre": "plátano", "cantidad": 6, "unidad": "piezas", "categoria": "frutas"},
    {"nombre": "limón", "cantidad": 3, "unidad": "piezas", "categoria": "frutas"},
    {"nombre": "leche", "cantidad": 1, "unidad": "l", "categoria": "lácteos"},
    {"nombre": "queso rallado", "cantidad": 200, "unidad": "g", "categoria": "lácteos"},
    {"nombre": "mantequilla", "cantidad": 100, "unidad": "g", "categoria": "lácteos"},
    {"nombre": "arroz", "cantidad": 1000, "unidad": "g", "categoria": "granos"},
    {"nombre": "pasta", "cantidad": 500, "unidad": "g", "categoria": "granos"},
    {"nombre": "lentejas", "cantidad": 400, "unidad": "g", "categoria": "granos"},
    {"nombre": "aceite de oliva", "cantidad": 500, "unidad": "ml", "categoria": "especias"},
    {"nombre": "sal", "cantidad": 500, "unidad": "g", "categoria": "especias"},
    {"nombre": "ajo", "cantidad": 1, "unidad": "piezas", "categoria": "especias"},
]


def seed_data(session: Session) -> None:
    exists = session.exec(select(Ingredient).limit(1)).first()
    if exists is not None:
        return
    for item in SEED:
        session.add(Ingredient(**item))
    session.commit()
