from starlette.testclient import TestClient
from backend.app.main import app, health_check

def test_health_check_function():
    response = health_check()
    assert response == {"status": "ok"}

def test_health_route_exists():
    routes = [route.path for route in app.routes if hasattr(route, "path")]
    assert "/api/health" in routes

def test_frontend_root_serves_html():
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")
    assert "CareFlow" in response.text
