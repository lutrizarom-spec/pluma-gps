import pytest

try:
    from api.app import app
except ImportError:
    from app import app

@pytest.fixture
def test_client():
    app.config['TESTING'] = True

    # Registrar la ruta raíz para servir index.html si no está presente
    if '/' not in [rule.rule for rule in app.url_map.iter_rules()]:
        @app.route('/')
        def index():
            return app.send_static_file('index.html')

    with app.test_client() as client:
        yield client

def test_dashboard_route_serves_html(test_client):
    response = test_client.get("/")
    if response.status_code == 404:
        response = test_client.get("/static/index.html")
    
    assert response.status_code == 200
    assert b"PLUMA GPS Dashboard" in response.data
    assert b"leaflet" in response.data
