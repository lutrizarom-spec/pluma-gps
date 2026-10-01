def test_dashboard_route_serves_html(test_client):
    response = test_client.get("/")
    assert response.status_code == 200
    assert b"PLUMA GPS Dashboard" in response.data
    assert b"leaflet" in response.data
