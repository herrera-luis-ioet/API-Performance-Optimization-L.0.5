"""Product API routes module."""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel, Field
from database.connection import get_db
from database.models import Product
from middleware.cache import RedisCacheMiddleware

# Initialize middleware
cache = RedisCacheMiddleware()

# Initialize router
router = APIRouter(prefix="/products", tags=["products"])

# Request/Response Models
class ProductBase(BaseModel):
    """Base product model."""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    price: float = Field(..., gt=0)
    stock: int = Field(..., ge=0)

    class Config:
        orm_mode = True

class ProductCreate(ProductBase):
    """Product creation model."""
    pass

class ProductResponse(ProductBase):
    """Product response model."""
    id: int
    created_at: str
    updated_at: str

# PUBLIC_INTERFACE
@router.post("/", response_model=ProductResponse, status_code=201)
async def create_product(
    request: Request,
    product: ProductCreate,
    db: Session = Depends(get_db)
) -> Product:
    """
    Create a new product.
    
    Args:
        product: Product data
        db: Database session
        
    Returns:
        Created product
        
    Raises:
        HTTPException: When product creation fails
    """
    try:
        db_product = Product(**product.dict())
        db.add(db_product)
        db.commit()
        db.refresh(db_product)
        return db_product
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail=f"Failed to create product: {str(e)}"
        )

# PUBLIC_INTERFACE
@router.get("/{product_id}", response_model=ProductResponse)
@cache.cache_response_handler(expiry=300)  # Cache for 5 minutes
async def get_product(
    request: Request,
    product_id: int,
    db: Session = Depends(get_db)
) -> Product:
    """
    Get a product by ID.
    
    Args:
        product_id: Product ID
        db: Database session
        
    Returns:
        Product details
        
    Raises:
        HTTPException: When product is not found
    """
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(
            status_code=404,
            detail=f"Product with ID {product_id} not found"
        )
    return product

# PUBLIC_INTERFACE
@router.get("/", response_model=List[ProductResponse])
@cache.cache_response_handler(expiry=300)  # Cache for 5 minutes
async def list_products(
    request: Request,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
) -> List[Product]:
    """
    List all products with pagination.
    
    Args:
        skip: Number of records to skip
        limit: Maximum number of records to return
        db: Database session
        
    Returns:
        List of products
    """
    products = db.query(Product).offset(skip).limit(limit).all()
    return products

# PUBLIC_INTERFACE
@router.put("/{product_id}", response_model=ProductResponse)
async def update_product(
    request: Request,
    product_id: int,
    product: ProductCreate,
    db: Session = Depends(get_db)
) -> Product:
    """
    Update a product.
    
    Args:
        product_id: Product ID
        product: Updated product data
        db: Database session
        
    Returns:
        Updated product
        
    Raises:
        HTTPException: When product is not found or update fails
    """
    db_product = db.query(Product).filter(Product.id == product_id).first()
    if not db_product:
        raise HTTPException(
            status_code=404,
            detail=f"Product with ID {product_id} not found"
        )
    
    try:
        for key, value in product.dict().items():
            setattr(db_product, key, value)
        db.commit()
        db.refresh(db_product)
        return db_product
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail=f"Failed to update product: {str(e)}"
        )

# PUBLIC_INTERFACE
@router.delete("/{product_id}", status_code=204)
async def delete_product(
    request: Request,
    product_id: int,
    db: Session = Depends(get_db)
) -> None:
    """
    Delete a product.
    
    Args:
        product_id: Product ID
        db: Database session
        
    Raises:
        HTTPException: When product is not found or deletion fails
    """
    db_product = db.query(Product).filter(Product.id == product_id).first()
    if not db_product:
        raise HTTPException(
            status_code=404,
            detail=f"Product with ID {product_id} not found"
        )
    
    try:
        db.delete(db_product)
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail=f"Failed to delete product: {str(e)}"
        )
