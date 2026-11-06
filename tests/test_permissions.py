# tests/test_permissions.py

def test_customer_cannot_access_agent_dashboard(client, test_user, auth_headers):
    # Customer attempts to view agent dashboard -> must be 403 Forbidden
    response = client.get("/agents/dashboard", headers=auth_headers)
    assert response.status_code == 403
    assert "only agents" in response.json()["detail"].lower()


def test_agent_can_access_agent_dashboard(client, test_agent_user, auth_headers_agent):
    # Registered agent views their dashboard -> 200 OK
    response = client.get("/agents/dashboard", headers=auth_headers_agent)
    assert response.status_code == 200
    data = response.json()
    assert "summary" in data
    assert data["name"] == "Delhi Agent"


def test_customer_cannot_verify_property(client, test_user, auth_headers):
    # Customer attempts to verify a property listing -> 403 Forbidden
    response = client.patch("/agents/verify/property/1?action=verified", headers=auth_headers)
    assert response.status_code == 403
    assert "only agents" in response.json()["detail"].lower()


def test_customer_cannot_register_agent_directly(client, test_user, auth_headers):
    # Only existing agents can create new agents
    response = client.post("/agents/register", headers=auth_headers, json={
        "email": "newagent@example.com",
        "password": "pass",
        "phone": "9990001112",
        "name": "New Agent",
        "city": "Mumbai",
        "fee_percent": 1.5,
        "min_fee": 1000,
        "max_fee": 25000
    })
    assert response.status_code == 403
