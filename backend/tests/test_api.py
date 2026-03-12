import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_check():
    """Test health check endpoint"""
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_root_endpoint():
    """Test root endpoint"""
    response = client.get("/")
    assert response.status_code == 200
    assert "title" in response.json()


@pytest.mark.asyncio
async def test_query_endpoint():
    """Test query endpoint"""
    response = client.post(
        "/api/query",
        json={
            "query": "Luật giao thông có quy định gì về tốc độ tối đa?",
            "top_k": 5
        }
    )
    assert response.status_code == 200
    assert "answer" in response.json()
    assert "sources" in response.json()
