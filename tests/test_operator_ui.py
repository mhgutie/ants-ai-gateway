from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_operator_ui_is_served():
    response = client.get("/ui")

    assert response.status_code == 200
    assert "ANTS Gateway" in response.text
    assert "/ui/assets/app.js" in response.text


def test_operator_ui_assets_are_served():
    js_response = client.get("/ui/assets/app.js")
    css_response = client.get("/ui/assets/styles.css")

    assert js_response.status_code == 200
    assert "runPreflight" in js_response.text
    assert css_response.status_code == 200
    assert "Operator Console" not in css_response.text
