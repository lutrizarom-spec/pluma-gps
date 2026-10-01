import pytest

try:
    from api.app import app
except ImportError:
    from app import app

@pytest.fixture
def test_client():
    """Fixture limpio que solo configura el modo de pruebas."""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_dashboard_serves_html(test_client):
    """
    Prueba segura que no altera el estado interno de Flask.
    Llama directamente al manejador estático nativo.
    """
    response = test_client.get("/static/index.html")
    
    assert response.status_code == 200, f"Se esperaba 200 pero se obtuvo {response.status_code}. Revisa la carpeta api/static."
    assert b"PLUMA GPS Dashboard" in response.data
    assert b"leaflet" in response.data
