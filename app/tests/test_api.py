from app.src.main import app
from fastapi.testclient import TestClient

client=TestClient(app)

# Test for check health
def test_healthz():
    response=client.get("/healthz")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data

# Test for check prometheus
def test_metrics():
    response=client.get("/metrics")
    assert response.status_code == 200
    assert "http_requests_total" in response.text

# Test for check fails
def test_fail_simulation():
    response = client.get("/items?fail=true")
    assert response.status_code == 500