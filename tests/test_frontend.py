import pytest

try:
    from api.app import app
except ImportError:
    from app import app

@pytest.fixture
def test_client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_dashboard_route_serves_html(test_client):
    response = test_client.get("/")
    assert response.status_code == 200
    assert b"PLUMA GPS Dashboard" in response.data
    assert b"leaflet" in response.data
