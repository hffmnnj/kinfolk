"""Tests for health check endpoint."""


def test_health_check(client):
    """Health check returns 200 with correct body."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


def test_api_docs_accessible(client):
    """OpenAPI docs are accessible."""
    response = client.get("/docs")
    assert response.status_code == 200
