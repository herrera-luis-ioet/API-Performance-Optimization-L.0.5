"""Test cases for Product API routes."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from main import app
from database.models import Product
from database.connection import get_db

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
def sample_product():
    """Create a sample product for testing."""
    return {
        "name": "Test Product",
        "description": "Test Description",
        "price": 99.99,
        "stock": 100
    }

def test_create_product(db_session, sample_product):
    """Test product creation."""
    response = client.post("/products/", json=sample_product)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == sample_product["name"]
    assert data["price"] == sample_product["price"]
    assert "id" in data

def test_create_product_invalid_data(db_session):
    """Test product creation with invalid data."""
    invalid_product = {
        "name": "",  # Invalid: empty name
        "price": -10,  # Invalid: negative price
        "stock": -5  # Invalid: negative stock
    }
    response = client.post("/products/", json=invalid_product)
    assert response.status_code == 422

def test_get_product(db_session, sample_product):
    """Test getting a product by ID."""
    # Create a product first
    create_response = client.post("/products/", json=sample_product)
    product_id = create_response.json()["id"]

    # Get the product
    response = client.get(f"/products/{product_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == product_id
    assert data["name"] == sample_product["name"]

def test_get_nonexistent_product(db_session):
    """Test getting a non-existent product."""
    response = client.get("/products/999999")
    assert response.status_code == 404

def test_list_products(db_session, sample_product):
    """Test listing products with pagination."""
    # Create multiple products
    for i in range(3):
        product = sample_product.copy()
        product["name"] = f"Test Product {i}"
        client.post("/products/", json=product)

    # Test default pagination
    response = client.get("/products/")
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0

    # Test custom pagination
    response = client.get("/products/?skip=1&limit=2")
    assert response.status_code == 200
    data = response.json()
    assert len(data) <= 2

def test_update_product(db_session, sample_product):
    """Test updating a product."""
    # Create a product first
    create_response = client.post("/products/", json=sample_product)
    product_id = create_response.json()["id"]

    # Update the product
    updated_data = {
        "name": "Updated Product",
        "description": "Updated Description",
        "price": 149.99,
        "stock": 200
    }
    response = client.put(f"/products/{product_id}", json=updated_data)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == updated_data["name"]
    assert data["price"] == updated_data["price"]

def test_update_nonexistent_product(db_session, sample_product):
    """Test updating a non-existent product."""
    response = client.put("/products/999999", json=sample_product)
    assert response.status_code == 404

def test_delete_product(db_session, sample_product):
    """Test deleting a product."""
    # Create a product first
    create_response = client.post("/products/", json=sample_product)
    product_id = create_response.json()["id"]

    # Delete the product
    response = client.delete(f"/products/{product_id}")
    assert response.status_code == 204

    # Verify product is deleted
    get_response = client.get(f"/products/{product_id}")
    assert get_response.status_code == 404

def test_delete_nonexistent_product(db_session):
    """Test deleting a non-existent product."""
    response = client.delete("/products/999999")
    assert response.status_code == 404

def test_rate_limiting(db_session, sample_product):
    """Test rate limiting middleware."""
    # Make multiple requests in quick succession
    for _ in range(101):  # Rate limit is 100
        client.get("/products/")
    
    # The 101st request should be rate limited
    response = client.get("/products/")
    assert response.status_code == 429

def test_cache_behavior(db_session, sample_product):
    """Test caching behavior."""
    # Create a product
    create_response = client.post("/products/", json=sample_product)
    product_id = create_response.json()["id"]

    # First request should hit the database
    first_response = client.get(f"/products/{product_id}")
    assert first_response.status_code == 200
    first_data = first_response.json()

    # Second request should hit the cache
    second_response = client.get(f"/products/{product_id}")
    assert second_response.status_code == 200
    second_data = second_response.json()

    # Both responses should be identical
    assert first_data == second_data