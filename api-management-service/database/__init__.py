"""Database package initialization."""
from .connection import Base, engine, get_db, db_session
from .models import Product, Order

# Create all tables
Base.metadata.create_all(bind=engine)

__all__ = ['Base', 'engine', 'get_db', 'db_session', 'Product', 'Order']