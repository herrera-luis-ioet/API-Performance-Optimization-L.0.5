"""Database models module."""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Enum
from .connection import Base

class BaseModel(Base):
    """Base model with common fields."""
    
    __abstract__ = True
    
    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {column.name: getattr(self, column.name) for column in self.__table__.columns}

class Product(BaseModel):
    """Product model."""
    
    __tablename__ = "products"
    
    name = Column(String(255), nullable=False)
    description = Column(String(1000))
    price = Column(Float, nullable=False)
    stock = Column(Integer, nullable=False, default=0)

class Order(BaseModel):
    """Order model."""
    
    __tablename__ = "orders"
    
    customer_id = Column(String(255), nullable=False)
    total_amount = Column(Float, nullable=False)
    status = Column(
        Enum('pending', 'processing', 'completed', 'cancelled', name='order_status'),
        nullable=False,
        default='pending'
    )