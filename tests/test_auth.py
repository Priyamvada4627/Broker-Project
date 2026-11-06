# tests/test_auth.py

def test_register_user_success(client):
    response = client.post("/users/register", json={
        "email": "newuser@example.com",
        "password": "secretpassword",
        "phone": "9998887776"
    })
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "newuser@example.com"
    assert "id" in data
    # Passwords must NEVER be returned in response!
    assert "password" not in data


def test_register_duplicate_email_fails(client):
    # Register first user
    client.post("/users/register", json={
        "email": "duplicate@example.com",
        "password": "pass",
        "phone": "1112223334"
    })

    # Attempt to register with the same email
    response = client.post("/users/register", json={
        "email": "duplicate@example.com",
        "password": "pass2",
        "phone": "5556667778"
    })
    assert response.status_code == 400
    assert "already registered" in response.json()["detail"].lower()


def test_login_success(client, test_user):
    # OAuth2PasswordRequestForm expects form-data: username & password
    response = client.post("/login", data={
        "username": test_user.email,
        "password": "password123"
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_invalid_password_returns_401(client, test_user):
    # Verify our Phase 1 fix: returns 401 instead of 403 on wrong credentials
    response = client.post("/login", data={
        "username": test_user.email,
        "password": "WRONG_PASSWORD"
    })
    assert response.status_code == 401
    assert "invalid credentials" in response.json()["detail"].lower()


def test_login_nonexistent_user_returns_401(client):
    response = client.post("/login", data={
        "username": "ghost@example.com",
        "password": "anypassword"
    })
    assert response.status_code == 401


def test_get_current_user_profile(client, test_user, auth_headers):
    response = client.get("/users/me", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == test_user.email
    assert data["id"] == test_user.id


def test_get_current_user_unauthorized_without_token(client):
    response = client.get("/users/me")
    assert response.status_code == 401
