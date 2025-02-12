import psutil
import time
from typing import Dict, Any
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from fastapi import FastAPI, Request, Response
from fastapi.responses import PlainTextResponse
import logging
from database.connection import get_db_session

# Initialize logger
logger = logging.getLogger("api_management")

# Prometheus metrics
REQUEST_COUNT = Counter(
    'http_requests_total',
    'Total HTTP requests count',
    ['method', 'endpoint', 'status']
)

REQUEST_LATENCY = Histogram(
    'http_request_duration_seconds',
    'HTTP request latency in seconds',
    ['method', 'endpoint']
)

SYSTEM_CPU_USAGE = Gauge(
    'system_cpu_usage_percent',
    'Current system CPU usage percentage'
)

SYSTEM_MEMORY_USAGE = Gauge(
    'system_memory_usage_bytes',
    'Current system memory usage in bytes'
)

API_ERRORS = Counter(
    'api_errors_total',
    'Total count of API errors',
    ['endpoint', 'error_type']
)

# PUBLIC_INTERFACE
def setup_monitoring(app: FastAPI) -> None:
    """
    Set up monitoring for the FastAPI application.
    
    Args:
        app: FastAPI application instance
    """
    @app.middleware("http")
    async def monitor_requests(request: Request, call_next):
        """Middleware to monitor request metrics."""
        path = request.url.path
        method = request.method
        
        # Skip monitoring for metrics endpoint
        if path == "/metrics":
            return await call_next(request)
        
        start_time = time.time()
        
        try:
            response = await call_next(request)
            
            # Record request count and latency
            REQUEST_COUNT.labels(
                method=method,
                endpoint=path,
                status=response.status_code
            ).inc()
            
            REQUEST_LATENCY.labels(
                method=method,
                endpoint=path
            ).observe(time.time() - start_time)
            
            return response
            
        except Exception as e:
            # Record error metrics
            API_ERRORS.labels(
                endpoint=path,
                error_type=type(e).__name__
            ).inc()
            raise

    @app.on_event("startup")
    async def start_monitoring():
        """Initialize monitoring on application startup."""
        logger.info("Monitoring system initialized")

# PUBLIC_INTERFACE
async def get_system_metrics() -> Dict[str, Any]:
    """
    Get current system metrics.
    
    Returns:
        Dict containing system metrics
    """
    cpu_percent = psutil.cpu_percent()
    memory = psutil.virtual_memory()
    
    # Update Prometheus gauges
    SYSTEM_CPU_USAGE.set(cpu_percent)
    SYSTEM_MEMORY_USAGE.set(memory.used)
    
    return {
        "cpu_usage_percent": cpu_percent,
        "memory_usage_percent": memory.percent,
        "memory_available_mb": memory.available / (1024 * 1024),
        "memory_used_mb": memory.used / (1024 * 1024)
    }

# PUBLIC_INTERFACE
async def get_application_health() -> Dict[str, str]:
    """
    Check application health including database connectivity.
    
    Returns:
        Dict containing health check results
    """
    health_status = {"status": "healthy"}
    
    try:
        # Check database connection
        session = get_db_session()
        session.execute("SELECT 1")
        health_status["database"] = "connected"
    except Exception as e:
        health_status["status"] = "unhealthy"
        health_status["database"] = "disconnected"
        logger.error(f"Database health check failed: {str(e)}")
    
    return health_status

# PUBLIC_INTERFACE
def setup_monitoring_routes(app: FastAPI) -> None:
    """
    Set up monitoring-related routes in the FastAPI application.
    
    Args:
        app: FastAPI application instance
    """
    @app.get("/metrics", response_class=PlainTextResponse)
    async def metrics():
        """Prometheus metrics endpoint."""
        return Response(
            generate_latest(),
            media_type=CONTENT_TYPE_LATEST
        )
    
    @app.get("/health/detailed")
    async def detailed_health():
        """Detailed health check endpoint."""
        health_info = await get_application_health()
        system_metrics = await get_system_metrics()
        
        return {
            "health": health_info,
            "metrics": system_metrics
        }