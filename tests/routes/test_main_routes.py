import pytest
from miachat.web.app import create_app

@pytest.fixture
def client():
    app = create_app({"TESTING": True})
    with app.test_client() as client:
        yield client

def test_home_route(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"MiaChat" in response.data

def test_dashboard_route(client):
    response = client.get("/dashboard")
    assert response.status_code == 200
    assert b"Dashboard" in response.data 