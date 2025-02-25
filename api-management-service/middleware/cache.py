from fastapi import Request, Response
from typing import Optional, Callable, Any
import redis
import json
import hashlib
from functools import wraps
from config import settings

class RedisCacheMiddleware:
    """
    Redis-based caching middleware for FastAPI.
    
    Attributes:
        redis_client: Redis client instance
        default_expiry: Default cache expiry time in seconds
    """
    
    def __init__(
        self,
        redis_host: settings.REDIS_HOST,
        redis_port: int = 6379,
        default_expiry: int = 300
    ):
        """
        Initialize Redis cache middleware.
        
        Args:
            redis_host: Redis server host
            redis_port: Redis server port
            default_expiry: Default cache expiry time in seconds
        """
        self.redis_client = redis.Redis(
            host=redis_host,
            port=redis_port,
            decode_responses=True
        )
        self.default_expiry = default_expiry

    def generate_cache_key(self, request: Request) -> str:
        """
        Generate a unique cache key for the request.
        
        Args:
            request: FastAPI request object
            
        Returns:
            String cache key
        """
        # Create a unique key based on path and query parameters
        key_parts = [
            request.method,
            request.url.path,
            str(sorted(request.query_params.items()))
        ]
        
        # Add request body to key if present
        if hasattr(request, "body"):
            key_parts.append(str(request.body))
            
        key_string = "|".join(key_parts)
        return f"cache:{hashlib.md5(key_string.encode()).hexdigest()}"

    async def get_cached_response(self, cache_key: str) -> Optional[Response]:
        """
        Get cached response from Redis.
        
        Args:
            cache_key: Cache key to lookup
            
        Returns:
            Cached response if found, None otherwise
        """
        cached_data = self.redis_client.get(cache_key)
        if cached_data:
            try:
                data = json.loads(cached_data)
                return Response(
                    content=data["content"],
                    status_code=data["status_code"],
                    headers=data["headers"],
                    media_type=data["media_type"]
                )
            except (json.JSONDecodeError, KeyError):
                return None
        return None

    async def cache_response(
        self,
        cache_key: str,
        response: Response,
        expiry: Optional[int] = None
    ) -> None:
        """
        Cache response in Redis.
        
        Args:
            cache_key: Cache key to store under
            response: Response to cache
            expiry: Cache expiry time in seconds
        """
        response_data = {
            "content": response.body.decode(),
            "status_code": response.status_code,
            "headers": dict(response.headers),
            "media_type": response.media_type
        }
        
        self.redis_client.setex(
            cache_key,
            expiry or self.default_expiry,
            json.dumps(response_data)
        )

    def cache_response_handler(
        self,
        expiry: Optional[int] = None,
        cache_control: Optional[str] = None
    ) -> Callable:
        """
        Decorator for caching endpoint responses.
        
        Args:
            expiry: Cache expiry time in seconds
            cache_control: Cache-Control header value
            
        Returns:
            Decorator function
        """
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            async def wrapper(*args: Any, **kwargs: Any) -> Response:
                request = kwargs.get("request") or args[0]
                if not isinstance(request, Request):
                    raise ValueError("No request object found in arguments")

                cache_key = self.generate_cache_key(request)
                cached_response = await self.get_cached_response(cache_key)

                if cached_response:
                    if cache_control:
                        cached_response.headers["Cache-Control"] = cache_control
                    return cached_response

                response = await func(*args, **kwargs)
                if 200 <= response.status_code < 400:
                    await self.cache_response(cache_key, response, expiry)
                    if cache_control:
                        response.headers["Cache-Control"] = cache_control

                return response
            return wrapper
        return decorator