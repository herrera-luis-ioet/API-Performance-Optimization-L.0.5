from fastapi import Request, HTTPException
from typing import Dict, Optional
import time
import asyncio
from dataclasses import dataclass

@dataclass
class TokenBucket:
    """Token bucket for rate limiting."""
    capacity: int
    refill_rate: float
    tokens: float
    last_refill: float

class RateLimitMiddleware:
    """
    Rate limiting middleware using token bucket algorithm.
    
    Attributes:
        rate_limit: Number of requests allowed per second
        bucket_capacity: Maximum number of tokens in the bucket
        buckets: Dictionary storing token buckets for each client
    """
    
    def __init__(self, rate_limit: int = 10, bucket_capacity: int = 10):
        """
        Initialize rate limiter middleware.
        
        Args:
            rate_limit: Number of requests allowed per second
            bucket_capacity: Maximum number of tokens in the bucket
        """
        self.rate_limit = rate_limit
        self.bucket_capacity = bucket_capacity
        self.buckets: Dict[str, TokenBucket] = {}
        self._cleanup_task: Optional[asyncio.Task] = None

    async def cleanup_buckets(self) -> None:
        """Periodically clean up expired buckets."""
        while True:
            current_time = time.time()
            expired_clients = [
                client_id for client_id, bucket in self.buckets.items()
                if current_time - bucket.last_refill > 3600  # Remove buckets inactive for 1 hour
            ]
            for client_id in expired_clients:
                del self.buckets[client_id]
            await asyncio.sleep(3600)  # Run cleanup every hour

    def get_client_identifier(self, request: Request) -> str:
        """
        Get unique identifier for the client.
        
        Args:
            request: FastAPI request object
            
        Returns:
            String identifier for the client
        """
        return request.client.host if request.client else "default"

    def get_bucket(self, client_id: str) -> TokenBucket:
        """
        Get or create token bucket for a client.
        
        Args:
            client_id: Unique identifier for the client
            
        Returns:
            TokenBucket instance for the client
        """
        if client_id not in self.buckets:
            self.buckets[client_id] = TokenBucket(
                capacity=self.bucket_capacity,
                refill_rate=self.rate_limit,
                tokens=self.bucket_capacity,
                last_refill=time.time()
            )
        return self.buckets[client_id]

    def refill_bucket(self, bucket: TokenBucket) -> None:
        """
        Refill tokens in the bucket based on elapsed time.
        
        Args:
            bucket: TokenBucket instance to refill
        """
        now = time.time()
        time_passed = now - bucket.last_refill
        new_tokens = time_passed * bucket.refill_rate
        bucket.tokens = min(bucket.capacity, bucket.tokens + new_tokens)
        bucket.last_refill = now

    async def __call__(self, request: Request, call_next):
        """
        Process the request through rate limiting.
        
        Args:
            request: FastAPI request object
            call_next: Next middleware in the chain
            
        Returns:
            Response from the next middleware
            
        Raises:
            HTTPException: When rate limit is exceeded
        """
        client_id = self.get_client_identifier(request)
        bucket = self.get_bucket(client_id)
        self.refill_bucket(bucket)

        if bucket.tokens >= 1:
            bucket.tokens -= 1
            response = await call_next(request)
            return response
        else:
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded. Please try again later."
            )