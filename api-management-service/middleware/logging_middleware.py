import logging
import time
import uuid
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import json
from logging.handlers import RotatingFileHandler
import os

# Configure logging
log_dir = "logs"
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

# Configure the root logger
logger = logging.getLogger("api_management")
logger.setLevel(logging.INFO)

# Create rotating file handler
file_handler = RotatingFileHandler(
    os.path.join(log_dir, "api.log"),
    maxBytes=10*1024*1024,  # 10MB
    backupCount=5
)

# Create formatter
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(correlation_id)s - %(message)s'
)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

# Add null correlation_id to LogRecord
logging.LogRecord = type('LogRecord', (logging.LogRecord,), {
    'correlation_id': 'null'
})

class StructuredLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for structured logging with correlation IDs and performance metrics.
    
    Attributes:
        app: The ASGI application
    """
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.logger = logger

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process the request, add correlation ID, and log request/response details.
        
        Args:
            request: The incoming request
            call_next: The next middleware in the chain
            
        Returns:
            Response from the next middleware
        """
        # Generate correlation ID
        correlation_id = str(uuid.uuid4())
        
        # Add correlation ID to request state
        request.state.correlation_id = correlation_id
        
        # Create log context
        log_context = {
            'correlation_id': correlation_id,
            'method': request.method,
            'path': request.url.path,
            'client_ip': request.client.host if request.client else None,
        }
        
        # Log request
        self.log_request(log_context)
        
        # Track timing
        start_time = time.time()
        
        try:
            # Process request
            response = await call_next(request)
            
            # Calculate duration
            duration = time.time() - start_time
            
            # Add response info to context
            log_context.update({
                'status_code': response.status_code,
                'duration': f"{duration:.3f}s"
            })
            
            # Log response
            self.log_response(log_context)
            
            # Add correlation ID to response headers
            response.headers['X-Correlation-ID'] = correlation_id
            
            return response
            
        except Exception as e:
            # Log error with context
            duration = time.time() - start_time
            log_context.update({
                'error': str(e),
                'duration': f"{duration:.3f}s"
            })
            self.log_error(log_context)
            raise
    
    def log_request(self, context: dict) -> None:
        """Log structured request information."""
        extra = {'correlation_id': context['correlation_id']}
        self.logger.info(
            f"Request received - {json.dumps(context)}",
            extra=extra
        )
    
    def log_response(self, context: dict) -> None:
        """Log structured response information."""
        extra = {'correlation_id': context['correlation_id']}
        self.logger.info(
            f"Response sent - {json.dumps(context)}",
            extra=extra
        )
    
    def log_error(self, context: dict) -> None:
        """Log structured error information."""
        extra = {'correlation_id': context['correlation_id']}
        self.logger.error(
            f"Error occurred - {json.dumps(context)}",
            extra=extra
        )