import uuid
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.db.models import Base
from app.db.session import get_db
from app.main import create_app

TEST_DB_URL = "sqlite:///./test.db"


@pytest.fixture(scope="session")
def engine():
    e = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
    # SQLite doesn't enforce foreign keys by default
    @event.listens_for(e, "connect")
    def set_sqlite_pragma(dbapi_conn, _):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(e)
    yield e
    Base.metadata.drop_all(e)
    e.dispose()


@pytest.fixture
def db(engine):
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.rollback()
    session.close()


@pytest.fixture
def client(db, monkeypatch):
    # Mock the Redis ingest queue so tests don't need a running Redis
    mock_queue = MagicMock()
    monkeypatch.setattr("app.api.routes.documents.ingest_queue", mock_queue)
    app = create_app()
    app.dependency_overrides[get_db] = lambda: db
    return TestClient(app)


@pytest.fixture
def registered_user(client):
    """Register a user and return (session_token, user_id, email)."""
    email = f"user_{uuid.uuid4().hex[:8]}@test.com"
    res = client.post("/auth/register", json={"email": email, "password": "testpass123"})
    assert res.status_code == 200
    data = res.json()
    return data["session_token"], data["user_id"], email


@pytest.fixture
def auth_headers(registered_user):
    token, _, _ = registered_user
    return {"X-Session-Token": token}
