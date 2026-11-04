from fastapi.testclient import TestClient


def test_health(client: TestClient) -> None:
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}


def test_openapi_docs_available(client: TestClient) -> None:
    assert client.get("/docs").status_code == 200
