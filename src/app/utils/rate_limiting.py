# app/utils/rate_limiting.py
from fastapi import HTTPException, Request, status
from functools import wraps
from typing import Callable, Optional, Dict, Any
import time
from datetime import datetime, timedelta
from app.core.cache import redis_client
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

class RateLimiter:
    def __init__(self):
        self.rate_limits = {}
    
    async def is_rate_limited(
        self, 
        identifier: str, 
        max_requests: int, 
        time_window: int
    ) -> bool:
        """
        Verificar si un identificador ha excedido el límite de tasa
        """
        if not redis_client.redis_client:
            return False
        
        key = f"rate_limit:{identifier}"
        
        try:
            # Obtener contador actual
            current_count = await redis_client.get(key)
            if current_count is None:
                # Primer request en la ventana de tiempo
                await redis_client.setex(key, time_window, 1)
                return False
            
            current_count = int(current_count)
            if current_count >= max_requests:
                return True
            
            # Incrementar contador
            await redis_client.redis_client.incr(key)
            return False
            
        except Exception as e:
            logger.error(f"Error in rate limiting: {e}")
            return False

def rate_limit(
    max_requests: int = 60, 
    time_window: int = 60,
    identifier_func: Optional[Callable[[Request], str]] = None
):
    """
    Decorador para limitar tasa de requests
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            # Obtener identificador único para rate limiting
            if identifier_func:
                identifier = identifier_func(request)
            else:
                identifier = await default_identifier(request)
            
            # Verificar rate limiting
            is_limited = await redis_client.is_rate_limited(
                f"{func.__name__}:{identifier}",
                max_requests,
                time_window
            )
            
            if is_limited:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Rate limit exceeded. Try again in {time_window} seconds.",
                    headers={"Retry-After": str(time_window)}
                )
            
            return await func(request, *args, **kwargs)
        return wrapper
    return decorator

async def default_identifier(request: Request) -> str:
    """
    Identificador por defecto para rate limiting (IP + endpoint)
    """
    client_ip = request.client.host if request.client else "unknown"
    endpoint = request.url.path
    return f"{client_ip}:{endpoint}"

def per_user_identifier(request: Request) -> str:
    """
    Identificador basado en usuario autenticado
    """
    # Esto asume que el usuario está autenticado y tenemos su ID en el request
    user_id = getattr(request.state, "user_id", "anonymous")
    endpoint = request.url.path
    return f"user:{user_id}:{endpoint}"

def per_ip_identifier(request: Request) -> str:
    """
    Identificador basado en IP del cliente
    """
    client_ip = request.client.host if request.client else "unknown"
    endpoint = request.url.path
    return f"ip:{client_ip}:{endpoint}"

# Rate limiters preconfigurados
def public_rate_limit(max_requests: int = 60, time_window: int = 60):
    """Rate limiting para endpoints públicos (por IP)"""
    return rate_limit(max_requests, time_window, per_ip_identifier)

def user_rate_limit(max_requests: int = 30, time_window: int = 60):
    """Rate limiting para endpoints de usuario (por user ID)"""
    return rate_limit(max_requests, time_window, per_user_identifier)

def sensitive_operation_rate_limit(max_requests: int = 5, time_window: int = 300):
    """Rate limiting para operaciones sensibles (login, transferencias)"""
    return rate_limit(max_requests, time_window, per_user_identifier)

# Clase para manejar rate limits globales
class GlobalRateLimiter:
    def __init__(self):
        self.redis = redis_client
    
    async def check_global_rate_limit(self, resource: str, max_requests: int, time_window: int) -> bool:
        """Verificar límite global para un recurso"""
        key = f"global_rate_limit:{resource}"
        
        try:
            current_count = await self.redis.get(key)
            if current_count is None:
                await self.redis.setex(key, time_window, 1)
                return False
            
            current_count = int(current_count)
            if current_count >= max_requests:
                return True
            
            await self.redis.redis_client.incr(key)
            return False
            
        except Exception as e:
            logger.error(f"Error in global rate limiting: {e}")
            return False

# Instancia global
global_rate_limiter = GlobalRateLimiter()

# Rate limiting para endpoints específicos
async def proton_api_rate_limiter(request: Request):
    """Rate limiting específico para API de Proton"""
    identifier = await default_identifier(request)
    is_limited = await redis_client.is_rate_limited(
        f"proton_api:{identifier}",
        100,  # 100 requests por minuto
        60
    )
    return not is_limited