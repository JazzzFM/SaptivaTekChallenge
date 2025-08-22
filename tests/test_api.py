import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def test_read_docs(client):
    response = client.get("/docs")
    assert response.status_code == 200

def test_create_prompt(client):
    response = client.post("/prompt", json={"prompt": "test prompt"})
    assert response.status_code == 200
    data = response.json()
    assert data["prompt"] == "test prompt"
    assert "response" in data
    assert "id" in data
    assert "created_at" in data

def test_search_similar(client):
    # First, create a prompt to have some data
    client.post("/prompt", json={"prompt": "another test prompt"})

    response = client.get("/similar?query=test")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)

def test_search_similar_with_negative_k(client):
    response = client.get("/similar?query=test&k=-1")
    assert response.status_code == 422 # Unprocessable Entity

def test_search_similar_with_k_zero(client):
    response = client.get("/similar?query=test&k=0")
    assert response.status_code == 422 # Unprocessable Entity

def test_create_prompt_with_empty_prompt(client):
    response = client.post("/prompt", json={"prompt": ""})
    assert response.status_code == 422 # Unprocessable Entity

def test_search_similar_with_no_results(client):
    response = client.get("/similar?query=a_very_unique_query_that_should_not_have_any_similar_results")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 0
