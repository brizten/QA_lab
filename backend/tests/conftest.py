import os
import sys
from pathlib import Path
from typing import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

os.environ["JWT_SECRET_KEY"] = "test_secret_key_that_is_long_enough_for_hs256"

from app.api.routes import test_runs as test_runs_route  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.db.database import get_db  # noqa: E402
from app.main import app  # noqa: E402


engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture
def db_session() -> Iterator[Session]:
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client(db_session: Session, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    def override_get_db() -> Iterator[Session]:
        yield db_session

    def fake_delay(test_run_id: int) -> dict[str, int]:
        return {"test_run_id": test_run_id}

    app.dependency_overrides[get_db] = override_get_db
    monkeypatch.setattr(test_runs_route.run_test_case, "delay", fake_delay)

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
