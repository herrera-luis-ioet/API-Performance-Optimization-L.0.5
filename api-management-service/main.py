from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
import os
from typing import Dict, Any

# Initialize FastAPI app
app = FastAPI(
    title="API Management Service",
    description="Service for managing and optimizing API performance",
    version="0.1.0"
)

# Configure CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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

# Startup event handler
@app.on_event("startup")
async def startup_event() -> None:
    """
    Perform startup tasks when the application starts.
    """
    # Load configuration
    app.state.config = load_config()

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