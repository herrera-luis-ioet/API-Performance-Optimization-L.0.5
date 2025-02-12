"""Test cases for Order API routes."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from main import app
from database.models import Order
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
def sample_order():
    """Create a sample order for testing."""
    return {
        "customer_id": "CUST123",
        "total_amount": 299.99,
        "status": "pending"
    }

def test_create_order(db_session, sample_order):
    """Test order creation."""
    response = client.post("/orders/", json=sample_order)
    assert response.status_code == 201
    data = response.json()
    assert data["customer_id"] == sample_order["customer_id"]
    assert data["total_amount"] == sample_order["total_amount"]
    assert data["status"] == "pending"
    assert "id" in data

def test_create_order_invalid_data(db_session):
    """Test order creation with invalid data."""
    invalid_order = {
        "customer_id": "",  # Invalid: empty customer_id
        "total_amount": -10,  # Invalid: negative amount
        "status": "invalid_status"  # Invalid: invalid status
    }
    response = client.post("/orders/", json=invalid_order)
    assert response.status_code == 422

def test_get_order(db_session, sample_order):
    """Test getting an order by ID."""
    # Create an order first
    create_response = client.post("/orders/", json=sample_order)
    order_id = create_response.json()["id"]

    # Get the order
    response = client.get(f"/orders/{order_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == order_id
    assert data["customer_id"] == sample_order["customer_id"]

def test_get_nonexistent_order(db_session):
    """Test getting a non-existent order."""
    response = client.get("/orders/999999")
    assert response.status_code == 404

def test_list_orders(db_session, sample_order):
    """Test listing orders with pagination and status filtering."""
    # Create multiple orders with different statuses
    statuses = ["pending", "processing", "completed"]
    for i, status in enumerate(statuses):
        order = sample_order.copy()
        order["status"] = status
        client.post("/orders/", json=order)

    # Test default pagination
    response = client.get("/orders/")
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0

    # Test custom pagination
    response = client.get("/orders/?skip=1&limit=2")
    assert response.status_code == 200
    data = response.json()
    assert len(data) <= 2

    # Test status filtering
    response = client.get("/orders/?status=pending")
    assert response.status_code == 200
    data = response.json()
    assert all(order["status"] == "pending" for order in data)

def test_list_orders_invalid_status(db_session):
    """Test listing orders with invalid status."""
    response = client.get("/orders/?status=invalid_status")
    assert response.status_code == 400

def test_update_order_status(db_session, sample_order):
    """Test updating an order's status."""
    # Create an order first
    create_response = client.post("/orders/", json=sample_order)
    order_id = create_response.json()["id"]

    # Test all valid status transitions
    valid_statuses = ["processing", "completed", "cancelled"]
    for status in valid_statuses:
        response = client.put(f"/orders/{order_id}", json={"status": status})
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == status

def test_update_order_invalid_status(db_session, sample_order):
    """Test updating an order with invalid status."""
    # Create an order first
    create_response = client.post("/orders/", json=sample_order)
    order_id = create_response.json()["id"]

    # Try to update with invalid status
    response = client.put(f"/orders/{order_id}", json={"status": "invalid_status"})
    assert response.status_code == 422

def test_update_nonexistent_order(db_session):
    """Test updating a non-existent order."""
    response = client.put("/orders/999999", json={"status": "processing"})
    assert response.status_code == 404

def test_delete_order(db_session, sample_order):
    """Test deleting an order."""
    # Create an order first
    create_response = client.post("/orders/", json=sample_order)
    order_id = create_response.json()["id"]

    # Delete the order
    response = client.delete(f"/orders/{order_id}")
    assert response.status_code == 204

    # Verify order is deleted
    get_response = client.get(f"/orders/{order_id}")
    assert get_response.status_code == 404

def test_delete_nonexistent_order(db_session):
    """Test deleting a non-existent order."""
    response = client.delete("/orders/999999")
    assert response.status_code == 404

def test_rate_limiting(db_session, sample_order):
    """Test rate limiting middleware."""
    # Make multiple requests in quick succession
    for _ in range(101):  # Rate limit is 100
        client.get("/orders/")
    
    # The 101st request should be rate limited
    response = client.get("/orders/")
    assert response.status_code == 429

def test_cache_behavior(db_session, sample_order):
    """Test caching behavior."""
    # Create an order
    create_response = client.post("/orders/", json=sample_order)
    order_id = create_response.json()["id"]

    # First request should hit the database
    first_response = client.get(f"/orders/{order_id}")
    assert first_response.status_code == 200
    first_data = first_response.json()

    # Second request should hit the cache
    second_response = client.get(f"/orders/{order_id}")
    assert second_response.status_code == 200
    second_data = second_response.json()

    # Both responses should be identical
    assert first_data == second_data

def test_order_status_transitions(db_session, sample_order):
    """Test order status transitions through the order lifecycle."""
    # Create an order
    create_response = client.post("/orders/", json=sample_order)
    order_id = create_response.json()["id"]
    
    # Test valid status transitions
    transitions = [
        ("pending", "processing"),
        ("processing", "completed"),
        ("processing", "cancelled")
    ]
    
    for current_status, next_status in transitions:
        # Update to current status
        client.put(f"/orders/{order_id}", json={"status": current_status})
        
        # Update to next status
        response = client.put(f"/orders/{order_id}", json={"status": next_status})
        assert response.status_code == 200
        assert response.json()["status"] == next_status"""Unit tests for order routes."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from main import app
from database.models import Order
from database.connection import get_db

# Test client setup
client = TestClient(app)

# Database session fixture
@pytest.fixture
def db_session():
    """Get database session for testing."""
    db = next(get_db())
    try:
        yield db
    finally:
        db.close()

# Test data fixtures
@pytest.fixture
def sample_order_data():
    """Sample order data for testing."""
    return {
        "customer_id": "test_customer",
        "total_amount": 100.0,
        "status": "pending"
    }

@pytest.fixture
def create_test_orders(db_session):
    """Create multiple test orders with different statuses."""
    orders = [
        Order(customer_id="customer1", total_amount=100.0, status="pending"),
        Order(customer_id="customer2", total_amount=200.0, status="processing"),
        Order(customer_id="customer3", total_amount=300.0, status="completed"),
        Order(customer_id="customer4", total_amount=400.0, status="cancelled")
    ]
    for order in orders:
        db_session.add(order)
    db_session.commit()
    
    yield orders
    
    # Cleanup
    for order in orders:
        db_session.delete(order)
    db_session.commit()

# Test case ORD-001: Test order creation and status transitions
def test_order_status_transitions(db_session, sample_order_data):
    """Test order creation and status transitions."""
    # Create order with pending status
    response = client.post("/orders/", json=sample_order_data)
    assert response.status_code == 201
    order_id = response.json()["id"]
    assert response.json()["status"] == "pending"
    
    # Update order status to processing
    response = client.put(f"/orders/{order_id}", json={"status": "processing"})
    assert response.status_code == 200
    assert response.json()["status"] == "processing"
    
    # Update order status to completed
    response = client.put(f"/orders/{order_id}", json={"status": "completed"})
    assert response.status_code == 200
    assert response.json()["status"] == "completed"
    
    # Cleanup
    db_session.query(Order).filter(Order.id == order_id).delete()
    db_session.commit()

def test_invalid_status_transition(db_session, sample_order_data):
    """Test invalid order status transition."""
    # Create order
    response = client.post("/orders/", json=sample_order_data)
    order_id = response.json()["id"]
    
    # Try to update with invalid status
    response = client.put(f"/orders/{order_id}", json={"status": "invalid_status"})
    assert response.status_code == 422  # Validation error
    
    # Cleanup
    db_session.query(Order).filter(Order.id == order_id).delete()
    db_session.commit()

# Test case ORD-002: Test order listing with status filtering
def test_order_listing_with_status_filter(db_session, create_test_orders):
    """Test order listing with status filtering."""
    # Test filtering by pending status
    response = client.get("/orders/?status=pending")
    assert response.status_code == 200
    orders = response.json()
    assert len(orders) == 1
    assert orders[0]["status"] == "pending"
    
    # Test filtering by processing status
    response = client.get("/orders/?status=processing")
    assert response.status_code == 200
    orders = response.json()
    assert len(orders) == 1
    assert orders[0]["status"] == "processing"
    
    # Test filtering by completed status
    response = client.get("/orders/?status=completed")
    assert response.status_code == 200
    orders = response.json()
    assert len(orders) == 1
    assert orders[0]["status"] == "completed"

def test_order_listing_pagination(db_session, create_test_orders):
    """Test order listing pagination."""
    # Test with limit
    response = client.get("/orders/?limit=2")
    assert response.status_code == 200
    orders = response.json()
    assert len(orders) == 2
    
    # Test with skip
    response = client.get("/orders/?skip=2&limit=2")
    assert response.status_code == 200
    orders = response.json()
    assert len(orders) == 2
    assert orders[0]["customer_id"] != create_test_orders[0].customer_id

def test_invalid_status_filter(db_session):
    """Test invalid status filter."""
    response = client.get("/orders/?status=invalid_status")
    assert response.status_code == 400
    assert "Invalid status value" in response.json()["detail"]
