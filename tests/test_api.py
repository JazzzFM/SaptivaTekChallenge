import sys
import os
import time
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def test_read_docs(client):
    response = client.get("/docs")
    assert response.status_code == 200

def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "prompt-service"

def test_stats_endpoint(client):
    response = client.get("/stats")
    assert response.status_code == 200
    data = response.json()
    assert "service" in data
    assert "config" in data
    assert data["service"] == "prompt-service"

def test_create_prompt_success(client):
    response = client.post("/prompt", json={"prompt": "test prompt"})
    assert response.status_code == 200
    data = response.json()
    assert data["prompt"] == "test prompt"
    assert "response" in data
    assert "id" in data
    assert "created_at" in data
    assert "[SimResponse-" in data["response"]

def test_create_prompt_with_sanitization(client):
    # Test HTML escaping
    response = client.post("/prompt", json={"prompt": "test <script>alert('xss')</script> prompt"})
    assert response.status_code == 200
    data = response.json()
    # Should be sanitized but not rejected
    assert "&lt;" in data["prompt"]
    assert "&gt;" in data["prompt"]

def test_create_prompt_deterministic_response(client):
    # Same prompt should produce same response
    prompt = "deterministic test prompt"
    
    response1 = client.post("/prompt", json={"prompt": prompt})
    response2 = client.post("/prompt", json={"prompt": prompt})
    
    assert response1.status_code == 200
    assert response2.status_code == 200
    
    data1 = response1.json()
    data2 = response2.json()
    
    # Responses should be identical (deterministic LLM)
    assert data1["response"] == data2["response"]

def test_search_similar_success(client):
    # First, create a prompt to have some data
    client.post("/prompt", json={"prompt": "machine learning algorithms"})
    client.post("/prompt", json={"prompt": "deep learning networks"})

    response = client.get("/similar?query=artificial intelligence&k=2")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) <= 2

def test_search_similar_with_sanitization(client):
    # Create a prompt first
    client.post("/prompt", json={"prompt": "normal prompt"})
    
    # Search with potentially dangerous query
    response = client.get("/similar?query=<script>malicious</script>&k=1")
    assert response.status_code == 200  # Should be sanitized, not rejected
    data = response.json()
    assert isinstance(data, list)

def test_search_similar_edge_cases(client):
    # Test various edge cases
    test_cases = [
        ("query=test&k=-1", 422),  # Negative k
        ("query=test&k=0", 422),   # Zero k
        ("query=test&k=1001", 422), # k too large
        ("query=&k=1", 422),       # Empty query
        ("query=" + "a" * 10001 + "&k=1", 422),  # Query too long
    ]
    
    for query_params, expected_status in test_cases:
        response = client.get(f"/similar?{query_params}")
        assert response.status_code == expected_status

def test_create_prompt_validation_errors(client):
    # Test various validation errors
    test_cases = [
        ("", 422),  # Empty prompt
        ("   ", 400),  # Whitespace only (after pydantic, caught by use case)
        ("a" * 10001, 422),  # Too long
    ]
    
    for prompt, expected_status in test_cases:
        response = client.post("/prompt", json={"prompt": prompt})
        assert response.status_code == expected_status

def test_create_prompt_with_dangerous_content(client):
    # These should be rejected by security validation
    dangerous_prompts = [
        "SELECT * FROM users",
        "DROP TABLE prompts", 
        "UNION SELECT password FROM users",
    ]
    
    for prompt in dangerous_prompts:
        response = client.post("/prompt", json={"prompt": prompt})
        assert response.status_code == 400
        data = response.json()
        assert "dangerous content" in data["detail"]["detail"]

def test_search_similar_with_no_results(client):
    response = client.get("/similar?query=extremely_unique_query_12345&k=5")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 0

def test_integration_create_and_search(client):
    """Test the full workflow: create prompts and search for similar ones."""
    # Create several related prompts
    prompts = [
        "Python programming language",
        "JavaScript web development", 
        "Machine learning with Python",
        "Data science and analytics",
        "Web frameworks like Django"
    ]
    
    # Create all prompts
    created_ids = []
    for prompt in prompts:
        response = client.post("/prompt", json={"prompt": prompt})
        assert response.status_code == 200
        created_ids.append(response.json()["id"])
    
    # Search for Python-related content
    response = client.get("/similar?query=Python development&k=3")
    assert response.status_code == 200
    results = response.json()
    
    # Should get some results
    assert len(results) > 0
    assert len(results) <= 3
    
    # Results should contain Python-related prompts
    result_prompts = [r["prompt"] for r in results]
    python_related = [p for p in result_prompts if "Python" in p]
    assert len(python_related) > 0

def test_error_response_format(client):
    """Test that error responses have consistent format."""
    response = client.post("/prompt", json={"prompt": ""})
    assert response.status_code == 422
    
    # For 422 errors (Pydantic validation), format might be different
    # But our custom errors should have consistent format
    response = client.post("/prompt", json={"prompt": "SELECT * FROM users"})
    assert response.status_code == 400
    data = response.json()
    
    assert "detail" in data
    detail = data["detail"]
    assert "error" in detail
    assert "detail" in detail
    assert "error_type" in detail

def test_response_time_header(client):
    """Test that process time header is added."""
    response = client.get("/health")
    assert response.status_code == 200
    assert "X-Process-Time" in response.headers
    
    # Process time should be a valid float
    process_time = float(response.headers["X-Process-Time"])
    assert process_time >= 0

def test_concurrent_requests(client):
    """Test that the service can handle concurrent requests."""
    import threading
    
    results = []
    errors = []
    
    def make_request():
        try:
            response = client.post("/prompt", json={"prompt": f"concurrent test {time.time()}"})
            results.append(response.status_code)
        except Exception as e:
            errors.append(str(e))
    
    # Create multiple threads
    threads = []
    for i in range(5):
        thread = threading.Thread(target=make_request)
        threads.append(thread)
        thread.start()
    
    # Wait for all threads
    for thread in threads:
        thread.join()
    
    # All requests should succeed
    assert len(errors) == 0
    assert all(status == 200 for status in results)
    assert len(results) == 5
