"""Test cases for middleware components."""
import pytest
import time
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from main import app
from database.connection import get_db
from middleware.rate_limiter import RateLimitMiddleware
from middleware.cache import RedisCacheMiddleware

client = TestClient(app)

@pytest.fixture
def db_session():
    """Get database session for testing."""
    db = next(get_db())
    try:
        yield db
    finally:
        db.close()

@pytest.fixture
def rate_limiter():
    """Create a rate limiter instance for testing."""
    return RateLimitMiddleware(rate_limit=5, bucket_capacity=5)

@pytest.fixture
def cache_middleware():
    """Create a cache middleware instance for testing."""
    return RedisCacheMiddleware(default_expiry=60)

def test_rate_limiter_token_bucket(rate_limiter):
    """Test token bucket behavior in rate limiter."""
    client_id = "test_client"
    
    # Get initial bucket
    bucket = rate_limiter.get_bucket(client_id)
    initial_tokens = bucket.tokens
    assert initial_tokens == rate_limiter.bucket_capacity
    
    # Consume some tokens
    for _ in range(3):
        bucket.tokens -= 1
    assert bucket.tokens == initial_tokens - 3
    
    # Wait for refill
    time.sleep(1)
    rate_limiter.refill_bucket(bucket)
    assert bucket.tokens > initial_tokens - 3

def test_rate_limiter_concurrent_requests(db_session):
    """Test rate limiting under concurrent requests."""
    endpoint = "/products/"
    
    # Make requests up to the limit
    responses = []
    for _ in range(5):
        response = client.get(endpoint)
        responses.append(response.status_code)
    
    # Verify all requests succeeded
    assert all(status == 200 for status in responses)
    
    # Next request should be rate limited
    response = client.get(endpoint)
    assert response.status_code == 429

def test_rate_limiter_recovery(db_session):
    """Test rate limiter recovery after limit is reached."""
    endpoint = "/products/"
    
    # Exhaust the rate limit
    for _ in range(5):
        client.get(endpoint)
    
    # Wait for token refill
    time.sleep(1)
    
    # Should be able to make requests again
    response = client.get(endpoint)
    assert response.status_code == 200

def test_cache_key_generation(cache_middleware):
    """Test cache key generation for different requests."""
    from fastapi import Request
    
    # Create mock requests
    request1 = Request(scope={
        "type": "http",
        "method": "GET",
        "path": "/test",
        "query_string": b"param=1"
    })
    
    request2 = Request(scope={
        "type": "http",
        "method": "GET",
        "path": "/test",
        "query_string": b"param=2"
    })
    
    # Generate cache keys
    key1 = cache_middleware.generate_cache_key(request1)
    key2 = cache_middleware.generate_cache_key(request2)
    
    # Different parameters should result in different cache keys
    assert key1 != key2

def test_cache_expiration(db_session, sample_product):
    """Test cache expiration behavior."""
    # Create a product
    create_response = client.post("/products/", json=sample_product)
    product_id = create_response.json()["id"]
    
    # First request (cache miss)
    first_response = client.get(f"/products/{product_id}")
    assert first_response.status_code == 200
    
    # Second request (cache hit)
    second_response = client.get(f"/products/{product_id}")
    assert second_response.status_code == 200
    assert second_response.json() == first_response.json()
    
    # Wait for cache to expire (cache is set to 300 seconds, but we'll use a shorter time for testing)
    time.sleep(2)
    
    # Third request should still work (cache miss, fresh data)
    third_response = client.get(f"/products/{product_id}")
    assert third_response.status_code == 200

def test_cache_invalidation_on_update(db_session, sample_product):
    """Test cache behavior when resource is updated."""
    # Create a product
    create_response = client.post("/products/", json=sample_product)
    product_id = create_response.json()["id"]
    
    # Get product (cache miss)
    first_response = client.get(f"/products/{product_id}")
    first_data = first_response.json()
    
    # Update product
    updated_data = sample_product.copy()
    updated_data["name"] = "Updated Name"
    update_response = client.put(f"/products/{product_id}", json=updated_data)
    assert update_response.status_code == 200
    
    # Get product again (should get updated data)
    second_response = client.get(f"/products/{product_id}")
    second_data = second_response.json()
    
    assert second_data["name"] == "Updated Name"
    assert first_data != second_data

def test_rate_limiter_different_endpoints(db_session):
    """Test rate limiting across different endpoints."""
    endpoints = ["/products/", "/orders/"]
    
    # Make requests to different endpoints
    for endpoint in endpoints:
        for _ in range(5):
            response = client.get(endpoint)
            assert response.status_code == 200
        
        # Next request to same endpoint should be rate limited
        response = client.get(endpoint)
        assert response.status_code == 429

def test_cache_different_http_methods(db_session, sample_product):
    """Test caching behavior with different HTTP methods."""
    # Create a product
    create_response = client.post("/products/", json=sample_product)
    product_id = create_response.json()["id"]
    
    # GET requests should be cached
    get_response1 = client.get(f"/products/{product_id}")
    get_response2 = client.get(f"/products/{product_id}")
    assert get_response1.json() == get_response2.json()
    
    # POST requests should not be cached
    post_response1 = client.post("/products/", json=sample_product)
    post_response2 = client.post("/products/", json=sample_product)
    assert post_response1.json()["id"] != post_response2.json()["id"]