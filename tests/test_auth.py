def test_register_login_and_me(client):
    res = client.post("/auth/register", json={"email": "A@Example.com", "password": "password123"})
    assert res.status_code == 201
    assert res.json()["email"] == "a@example.com"

    res = client.post("/auth/login", data={"username": "a@example.com", "password": "password123"})
    assert res.status_code == 200
    token = res.json()["access_token"]

    res = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    assert res.json()["email"] == "a@example.com"


def test_duplicate_email_is_rejected(client):
    body = {"email": "dup@example.com", "password": "password123"}
    assert client.post("/auth/register", json=body).status_code == 201
    assert client.post("/auth/register", json=body).status_code == 409


def test_wrong_password(client):
    client.post("/auth/register", json={"email": "x@example.com", "password": "password123"})
    res = client.post("/auth/login", data={"username": "x@example.com", "password": "nope-nope"})
    assert res.status_code == 401


def test_protected_routes_need_token(client):
    assert client.get("/documents").status_code == 401
    bad = {"Authorization": "Bearer not-a-real-token"}
    assert client.get("/documents", headers=bad).status_code == 401


def test_short_password_rejected(client):
    res = client.post("/auth/register", json={"email": "s@example.com", "password": "short"})
    assert res.status_code == 422
