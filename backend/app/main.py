from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlmodel import Session

from .config import settings
from .db import engine, init_db
from .routers import chat, ingredients, recipes
from .seed import seed_data

STATIC_ROOT = Path(settings.static_dir).parent
STATIC_ROOT.mkdir(parents=True, exist_ok=True)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    with Session(engine) as session:
        seed_data(session)
    yield


app = FastAPI(title="SousChef.ai", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ingredients.router)
app.include_router(recipes.router)
app.include_router(chat.router)

app.mount("/static", StaticFiles(directory=str(STATIC_ROOT)), name="static")

_dist = Path(settings.frontend_dist)
if _dist.is_dir():
    try:
        app.frontend("/", directory=str(_dist), fallback="index.html")
    except AttributeError:
        app.mount("/", StaticFiles(directory=str(_dist), html=True), name="frontend")
