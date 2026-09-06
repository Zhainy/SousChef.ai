from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

import app.agent.tools as tools_mod
import app.db as db_mod
from app.db import get_session
from app.main import app
from app.seed import seed_data


@pytest.fixture()
def engine():
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(test_engine)
    with Session(test_engine) as session:
        seed_data(session)
    return test_engine


@pytest.fixture(autouse=True)
def patched_tools(engine: object, monkeypatch):
    monkeypatch.setattr(tools_mod, "engine", engine)
    monkeypatch.setattr(db_mod, "engine", engine)
    return engine


@pytest.fixture()
def client(engine: object, patched_tools) -> Iterator[TestClient]:
    def override_get_session():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()
