import uuid


def test_register_success(client):
    email = f"new_{uuid.uuid4().hex[:8]}@test.com"
    res = client.post("/auth/register", json={"email": email, "password": "password123"})
    assert res.status_code == 200
    data = res.json()
    assert "session_token" in data
    assert data["email"] == email


def test_register_duplicate_email(client, registered_user):
    _, _, email = registered_user
    res = client.post("/auth/register", json={"email": email, "password": "password123"})
    assert res.status_code == 409


def test_login_success(client, registered_user):
    _, _, email = registered_user
    res = client.post("/auth/login", json={"email": email, "password": "testpass123"})
    assert res.status_code == 200
    assert "session_token" in res.json()


def test_login_wrong_password(client, registered_user):
    _, _, email = registered_user
    res = client.post("/auth/login", json={"email": email, "password": "wrongpass"})
    assert res.status_code == 401


def test_login_unknown_email(client):
    res = client.post("/auth/login", json={"email": "nobody@test.com", "password": "pass"})
    assert res.status_code == 401


def test_protected_without_token(client):
    res = client.get("/documents")
    assert res.status_code == 422  # missing required header → FastAPI validation error


def test_protected_with_bad_token(client):
    res = client.get("/documents", headers={"X-Session-Token": "badtoken"})
    assert res.status_code == 401


def test_logout(client, auth_headers):
    res = client.post("/auth/logout", headers=auth_headers)
    assert res.status_code == 200
    # After logout, old token should be invalid
    res2 = client.get("/documents", headers=auth_headers)
    assert res2.status_code == 401
