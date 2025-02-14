"""Order API routes module."""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from typing import List, Optional, Any
from pydantic import BaseModel, Field
from database.connection import get_db
from database.models import Order
from middleware.cache import RedisCacheMiddleware
from fastapi.responses import JSONResponse
from datetime import datetime
import json

# Initialize middleware
cache = RedisCacheMiddleware()

# Initialize router
router = APIRouter(prefix="/orders", tags=["orders"])

def serialize_datetime(obj: Any) -> Any:
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")

# Request/Response Models
class OrderBase(BaseModel):
    """Base order model."""
    customer_id: str = Field(..., min_length=1, max_length=255)
    total_amount: float = Field(..., gt=0)
    status: str = Field(
        default="pending",
        regex="^(pending|processing|completed|cancelled)$"
    )

    class Config:
        orm_mode = True

class OrderCreate(OrderBase):
    """Order creation model."""
    pass

class OrderResponse(OrderBase):
    """Order response model."""
    id: int
    created_at: str
    updated_at: str

class OrderUpdate(BaseModel):
    """Order update model."""
    status: str = Field(
        ...,
        regex="^(pending|processing|completed|cancelled)$"
    )

# PUBLIC_INTERFACE
@router.post("/", response_model=OrderResponse, status_code=201)
async def create_order(
    request: Request,
    order: OrderCreate,
    db: Session = Depends(get_db)
) -> Order:
    """
    Create a new order.
    
    Args:
        order: Order data
        db: Database session
        
    Returns:
        Created order
        
    Raises:
        HTTPException: When order creation fails
    """
    try:
        db_order = Order(**order.dict())
        db.add(db_order)
        db.commit()
        db.refresh(db_order)
        return  OrderResponse(
            id=db_order.id,
            customer_id=db_order.customer_id,
            total_amount=db_order.total_amount,
            status=db_order.status,            
            created_at=db_order.created_at.isoformat(), 
            updated_at=db_order.updated_at.isoformat())
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail=f"Failed to create order: {str(e)}"
        )

# PUBLIC_INTERFACE
@router.get("/{order_id}", response_model=OrderResponse)
@cache.cache_response_handler(expiry=300)  # Cache for 5 minutes
async def get_order(
    request: Request,
    order_id: int,
    db: Session = Depends(get_db)
) -> Order:
    """
    Get an order by ID.
    
    Args:
        order_id: Order ID
        db: Database session
        
    Returns:
        Order details
        
    Raises:
        HTTPException: When order is not found
    """
    order = db.query(Order).filter(Order.id == order_id).first()
   
    if not order:
        raise HTTPException(
            status_code=404,
            detail=f"Order with ID {order_id} not found"
        )
    
    response = json.dumps(order.to_dict(), default=serialize_datetime)
    content = json.loads(response)
    
    return JSONResponse(content=content)

# PUBLIC_INTERFACE
@router.get("/", response_model=List[OrderResponse])
@cache.cache_response_handler(expiry=300)  # Cache for 5 minutes
async def list_orders(
    request: Request,
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
) -> List[Order]:
    """
    List all orders with pagination and optional status filter.
    
    Args:
        skip: Number of records to skip
        limit: Maximum number of records to return
        status: Optional status filter
        db: Database session
        
    Returns:
        List of orders
    """
    query = db.query(Order)
    if status:
        if status not in ["pending", "processing", "completed", "cancelled"]:
            raise HTTPException(
                status_code=400,
                detail="Invalid status value"
            )
        query = query.filter(Order.status == status)
    
    orders = query.offset(skip).limit(limit).all()
    orders_dicts = [order.to_dict() for order in orders]
    response = json.dumps(orders_dicts, default=serialize_datetime)
    content = json.loads(response)

    return JSONResponse(content=content)

# PUBLIC_INTERFACE
@router.put("/{order_id}", response_model=OrderResponse)
async def update_order(
    request: Request,
    order_id: int,
    order_update: OrderUpdate,
    db: Session = Depends(get_db)
) -> Order:
    """
    Update an order's status.
    
    Args:
        order_id: Order ID
        order_update: Updated order status
        db: Database session
        
    Returns:
        Updated order
        
    Raises:
        HTTPException: When order is not found or update fails
    """
    db_order = db.query(Order).filter(Order.id == order_id).first()
    if not db_order:
        raise HTTPException(
            status_code=404,
            detail=f"Order with ID {order_id} not found"
        )
    
    try:
        db_order.status = order_update.status
        db.commit()
        db.refresh(db_order)
        return OrderResponse(
            id=db_order.id,
            customer_id=db_order.customer_id,
            total_amount=db_order.total_amount,
            status=db_order.status,            
            created_at=db_order.created_at.isoformat(), 
            updated_at=db_order.updated_at.isoformat())
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail=f"Failed to update order: {str(e)}"
        )

# PUBLIC_INTERFACE
@router.delete("/{order_id}", status_code=204)
async def delete_order(
    request: Request,
    order_id: int,
    db: Session = Depends(get_db)
) -> None:
    """
    Delete an order.
    
    Args:
        order_id: Order ID
        db: Database session
        
    Raises:
        HTTPException: When order is not found or deletion fails
    """
    db_order = db.query(Order).filter(Order.id == order_id).first()
    if not db_order:
        raise HTTPException(
            status_code=404,
            detail=f"Order with ID {order_id} not found"
        )
    
    try:
        db.delete(db_order)
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail=f"Failed to delete order: {str(e)}"
        )
