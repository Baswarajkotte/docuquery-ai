import os
import tempfile

# Configure the app for tests before it is imported.
_db_file = os.path.join(tempfile.mkdtemp(), "test.db")
os.environ["DATABASE_URL"] = f"sqlite:///{_db_file}"
os.environ["JWT_SECRET"] = "test-secret"
os.environ["ANTHROPIC_API_KEY"] = ""  # force extractive answers; no network in tests

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.database import Base, engine  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture()
def client():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as c:
        yield c


def _register_and_login(client: TestClient, email: str) -> dict[str, str]:
    client.post("/auth/register", json={"email": email, "password": "s3cret-pass"})
    res = client.post("/auth/login", data={"username": email, "password": "s3cret-pass"})
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


@pytest.fixture()
def auth_headers(client):
    return _register_and_login(client, "dev@example.com")


@pytest.fixture()
def other_headers(client):
    return _register_and_login(client, "other@example.com")
