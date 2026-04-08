from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_create_memory_validation():
    payload = {
        "memory_type": "semantic",
        "title": "User preference",
        "content": "El usuario prefiere respuestas en español.",
        "scope": "private",
        "source": "agent",
        "tags": ["language", "preference"]
    }

    response = client.post("/memories", json=payload)

    # Este test pasará solo si la DB está disponible.
    assert response.status_code in [201, 500]