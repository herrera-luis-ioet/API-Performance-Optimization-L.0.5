from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
import os
from typing import Dict, Any
from middleware.rate_limiter import RateLimitMiddleware
from middleware.cache import RedisCacheMiddleware
from middleware.logging_middleware import StructuredLoggingMiddleware
from monitoring import setup_monitoring, setup_monitoring_routes
from routers import products, orders
from mangum import Mangum

# Initialize FastAPI app
app = FastAPI(
    title="API Management Service",
    description="Service for managing and optimizing API performance",
    version="0.1.0"
)

# Configure middleware
# Set up monitoring
setup_monitoring(app)

# Add structured logging middleware first to capture all requests
app.add_middleware(StructuredLoggingMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure rate limiting middleware
app.add_middleware(
    RateLimitMiddleware,
    rate_limit=int(os.getenv("RATE_LIMIT", "10")),
    bucket_capacity=int(os.getenv("BUCKET_CAPACITY", "10"))
)

# Custom exception handler for generic exceptions
@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Global exception handler for unhandled exceptions.
    
    Args:
        request: The incoming request
        exc: The exception that was raised
        
    Returns:
        JSONResponse with error details
    """
    return JSONResponse(
        status_code=500,
        content={
            "message": "Internal server error",
            "detail": str(exc),
            "path": request.url.path
        }
    )

# Health check endpoint
@app.get("/health")
async def health_check() -> Dict[str, str]:
    """
    Health check endpoint to verify service status.
    
    Returns:
        Dict containing service status
    """
    return {"status": "healthy"}

# Configuration loading
def load_config() -> Dict[str, Any]:
    """
    Load configuration from environment variables.
    
    Returns:
        Dict containing configuration values
    """
    return {
        "environment": os.getenv("ENVIRONMENT", "development"),
        "debug": os.getenv("DEBUG", "False").lower() == "true",
        "port": int(os.getenv("PORT", "8000")),
    }

app.include_router(products.router)
app.include_router(orders.router)

# Startup event handler
@app.on_event("startup")
async def startup_event() -> None:
    """
    Perform startup tasks when the application starts.
    """
    # Load configuration
    app.state.config = load_config()
    
    # Set up monitoring routes
    setup_monitoring_routes(app)

# Shutdown event handler
@app.on_event("shutdown")
async def shutdown_event() -> None:
    """
    Perform cleanup tasks when the application shuts down.
    """
    pass  # Add cleanup tasks as needed

if __name__ == "__main__":
    config = load_config()
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=config["port"],
        reload=config["debug"]
    )

handler = Mangum(app, lifespan="off")