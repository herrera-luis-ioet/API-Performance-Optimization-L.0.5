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
        "stock": 100,
        "image": None  # Default to None to test optional nature
    }

@pytest.fixture
def sample_product_with_image():
    """Create a sample product with image for testing."""
    return {
        "name": "Test Product with Image",
        "description": "Test Description",
        "price": 99.99,
        "stock": 100,
        "image": "https://example.com/test-image.jpg"
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
                "name": "Test Product",
                "price": 10.99,
                "stock": 100,
                "image": "not_a_valid_url"  # Invalid: not a valid URL format
            },
            "expected_error": "image"
        },
        {
            "data": {
                "name": "Test Product",
                "price": 10.99,
                "stock": 100,
                "image": "ftp://invalid-protocol.com/image.jpg"  # Invalid: unsupported protocol
            },
            "expected_error": "image"
        },
        {
            "data": {
                "name": "Test Product",
                "price": 10.99,
                "stock": 100,
                "image": "a" * 256  # Invalid: image URL too long
            },
            "expected_error": "image"
        },
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
            "name": "Product with Image",
            "description": "Product with a valid image URL",
            "price": 199.99,
            "stock": 75,
            "image": "https://example.com/images/product.jpg"
        },
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

def test_create_product_with_image(db_session, sample_product_with_image):
    """Test product creation with image field."""
    response = client.post("/products/", json=sample_product_with_image)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == sample_product_with_image["name"]
    assert data["image"] == sample_product_with_image["image"]
    assert "id" in data

def test_create_product_without_image(db_session, sample_product):
    """Test product creation without image field (optional field)."""
    # Ensure image is None in sample_product
    sample_product["image"] = None
    response = client.post("/products/", json=sample_product)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == sample_product["name"]
    assert data["image"] is None
    assert "id" in data

def test_update_product_image(db_session, sample_product, sample_product_with_image):
    """Test updating product image field."""
    # Create a product first without image
    create_response = client.post("/products/", json=sample_product)
    product_id = create_response.json()["id"]
    
    # Update the product to add an image
    updated_data = sample_product_with_image.copy()
    response = client.put(f"/products/{product_id}", json=updated_data)
    assert response.status_code == 200
    data = response.json()
    assert data["image"] == updated_data["image"]
    
    # Update the product to remove the image
    updated_data["image"] = None
    response = client.put(f"/products/{product_id}", json=updated_data)
    assert response.status_code == 200
    data = response.json()
    assert data["image"] is None
    
    # Update with a different image URL
    updated_data["image"] = "https://example.com/new-image.jpg"
    response = client.put(f"/products/{product_id}", json=updated_data)
    assert response.status_code == 200
    data = response.json()
    assert data["image"] == updated_data["image"]
    
    # Verify image persistence after update
    get_response = client.get(f"/products/{product_id}")
    assert get_response.status_code == 200
    get_data = get_response.json()
    assert get_data["image"] == updated_data["image"]

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

def test_image_field_validation(db_session):
    """Test image field validation with various scenarios."""
    test_cases = [
        {
            "data": {
                "name": "Test Product",
                "price": 10.99,
                "stock": 100,
                "image": "https://example.com/valid-image.jpg"  # Valid HTTPS URL
            },
            "expected_status": 201
        },
        {
            "data": {
                "name": "Test Product",
                "price": 10.99,
                "stock": 100,
                "image": "http://example.com/image.jpg"  # Valid HTTP URL
            },
            "expected_status": 201
        },
        {
            "data": {
                "name": "Test Product",
                "price": 10.99,
                "stock": 100,
                "image": ""  # Empty string
            },
            "expected_status": 422
        },
        {
            "data": {
                "name": "Test Product",
                "price": 10.99,
                "stock": 100,
                "image": "   "  # Whitespace only
            },
            "expected_status": 422
        }
    ]

    for test_case in test_cases:
        response = client.post("/products/", json=test_case["data"])
        assert response.status_code == test_case["expected_status"], \
            f"Expected status {test_case['expected_status']} for image: {test_case['data']['image']}"
        
        if test_case["expected_status"] == 201:
            data = response.json()
            assert data["image"] == test_case["data"]["image"]

def test_image_field_in_list_products(db_session, sample_product, sample_product_with_image):
    """Test image field presence in product listing."""
    # Create products with and without images
    client.post("/products/", json=sample_product)
    client.post("/products/", json=sample_product_with_image)
    
    # Test listing products
    response = client.get("/products/")
    assert response.status_code == 200
    data = response.json()
    
    # Verify both products are listed with correct image fields
    products_with_image = [p for p in data if p["image"] is not None]
    products_without_image = [p for p in data if p["image"] is None]
    
    assert len(products_with_image) > 0, "No products with image found"
    assert len(products_without_image) > 0, "No products without image found"
    
    # Verify image URLs are preserved in listing
    product_with_image = next(p for p in data if p["image"] is not None)
    assert product_with_image["image"] == sample_product_with_image["image"]

def test_bulk_image_updates(db_session):
    """Test bulk updates of product images."""
    # Create multiple products with different image scenarios
    products = [
        {
            "name": "Product 1",
            "description": "Test Description 1",
            "price": 99.99,
            "stock": 100,
            "image": "https://example.com/image1.jpg"
        },
        {
            "name": "Product 2",
            "description": "Test Description 2",
            "price": 149.99,
            "stock": 150,
            "image": None
        },
        {
            "name": "Product 3",
            "description": "Test Description 3",
            "price": 199.99,
            "stock": 200,
            "image": "https://example.com/image3.jpg"
        }
    ]
    
    created_products = []
    for product in products:
        response = client.post("/products/", json=product)
        assert response.status_code == 201
        created_products.append(response.json())
    
    # Update images for all products
    for product in created_products:
        new_image = "https://example.com/updated-image.jpg"
        update_data = {
            "name": product["name"],
            "description": product["description"],
            "price": product["price"],
            "stock": product["stock"],
            "image": new_image
        }
        
        response = client.put(f"/products/{product['id']}", json=update_data)
        assert response.status_code == 200
        updated_data = response.json()
        assert updated_data["image"] == new_image
        
        # Verify through GET request
        get_response = client.get(f"/products/{product['id']}")
        assert get_response.status_code == 200
        get_data = get_response.json()
        assert get_data["image"] == new_image

def test_image_field_special_characters(db_session):
    """Test image field with URLs containing special characters."""
    test_cases = [
        {
            "name": "Product with URL Encoded Image",
            "description": "Test Description",
            "price": 99.99,
            "stock": 100,
            "image": "https://example.com/image%20with%20spaces.jpg"
        },
        {
            "name": "Product with Query Parameters",
            "description": "Test Description",
            "price": 99.99,
            "stock": 100,
            "image": "https://example.com/image.jpg?size=large&format=webp"
        },
        {
            "name": "Product with Hash Fragment",
            "description": "Test Description",
            "price": 99.99,
            "stock": 100,
            "image": "https://example.com/image.jpg#fragment"
        }
    ]
    
    for test_case in test_cases:
        # Create product
        response = client.post("/products/", json=test_case)
        assert response.status_code == 201
        data = response.json()
        assert data["image"] == test_case["image"]
        
        # Verify retrieval
        get_response = client.get(f"/products/{data['id']}")
        assert get_response.status_code == 200
        get_data = get_response.json()
        assert get_data["image"] == test_case["image"]

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
