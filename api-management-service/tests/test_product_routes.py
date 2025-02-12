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
    # Test case PROD-002: Test product creation with invalid data
    test_cases = [
        {
            "data": {
                "name": "",  # Invalid: empty name
                "price": 10.99,
                "stock": 100
            },
            "expected_error": "name"
        },
        {
            "data": {
                "name": "Test Product",
                "price": -10,  # Invalid: negative price
                "stock": 100
            },
            "expected_error": "price"
        },
        {
            "data": {
                "name": "Test Product",
                "price": 10.99,
                "stock": -5  # Invalid: negative stock
            },
            "expected_error": "stock"
        },
        {
            "data": {
                "name": "T" * 256,  # Invalid: name too long
                "price": 10.99,
                "stock": 100
            },
            "expected_error": "name"
        },
        {
            "data": {
                "description": "T" * 1001,  # Invalid: description too long
                "name": "Test Product",
                "price": 10.99,
                "stock": 100
            },
            "expected_error": "description"
        }
    ]

    for test_case in test_cases:
        response = client.post("/products/", json=test_case["data"])
        assert response.status_code == 422, f"Expected 422 for invalid {test_case['expected_error']}"
        error_detail = response.json()["detail"]
        assert any(test_case["expected_error"] in error["loc"] for error in error_detail), \
            f"Expected validation error for {test_case['expected_error']}"

def test_create_product_valid_data(db_session):
    """Test product creation with valid data."""
    # Test case PROD-001: Test product creation with valid data
    test_cases = [
        {
            "name": "Basic Product",
            "price": 10.99,
            "stock": 100
        },
        {
            "name": "Product with Description",
            "description": "Test description",
            "price": 99.99,
            "stock": 50
        },
        {
            "name": "Product with Max Values",
            "description": "T" * 1000,  # Max length
            "price": 9999.99,
            "stock": 999999
        }
    ]

    for test_data in test_cases:
        response = client.post("/products/", json=test_data)
        assert response.status_code == 201, f"Failed to create product with data: {test_data}"
        data = response.json()
        assert data["name"] == test_data["name"]
        assert data["price"] == test_data["price"]
        assert data["stock"] == test_data["stock"]
        if "description" in test_data:
            assert data["description"] == test_data["description"]
        assert "id" in data
        assert "created_at" in data
        assert "updated_at" in data

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
