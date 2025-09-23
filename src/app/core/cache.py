# app/core/cache.py
import redis.asyncio as redis
import json
import logging
from typing import Any, Optional, Union
from functools import wraps
from app.core.config import settings

logger = logging.getLogger(__name__)

class RedisCache:
    def __init__(self):
        self.redis_client = None
    
    async def init_redis(self):
        """Inicializar conexión Redis"""
        try:
            self.redis_client = redis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True
            )
            # Test connection
            await self.redis_client.ping()
            logger.info("✅ Redis conectado exitosamente")
            return True
        except Exception as e:
            logger.error(f"❌ Error conectando a Redis: {e}")
            self.redis_client = None
            return False
    
    async def get(self, key: str) -> Optional[Any]:
        """Obtener valor desde cache"""
        if not self.redis_client:
            return None
        
        try:
            value = await self.redis_client.get(key)
            if value:
                try:
                    return json.loads(value)
                except json.JSONDecodeError:
                    return value
            return None
        except Exception as e:
            logger.error(f"Error getting key {key} from Redis: {e}")
            return None
    
    async def set(self, key: str, value: Any, expire: int = None) -> bool:
        """Guardar valor en cache"""
        if not self.redis_client:
            return False
        
        try:
            if expire:
                await self.redis_client.setex(key, expire, json.dumps(value))
            else:
                await self.redis_client.set(key, json.dumps(value))
            return True
        except Exception as e:
            logger.error(f"Error setting key {key} in Redis: {e}")
            return False
    
    async def setex(self, key: str, seconds: int, value: Any) -> bool:
        """Guardar valor en cache con expiración"""
        return await self.set(key, value, seconds)
    
    async def delete(self, key: str) -> bool:
        """Eliminar clave del cache"""
        if not self.redis_client:
            return False
        
        try:
            await self.redis_client.delete(key)
            return True
        except Exception as e:
            logger.error(f"Error deleting key {key} from Redis: {e}")
            return False
    
    async def exists(self, key: str) -> bool:
        """Verificar si clave existe"""
        if not self.redis_client:
            return False
        
        try:
            return await self.redis_client.exists(key) == 1
        except Exception as e:
            logger.error(f"Error checking existence of key {key}: {e}")
            return False
    
    async def close(self):
        """Cerrar conexión Redis"""
        if self.redis_client:
            await self.redis_client.close()

# Instancia global del cache
redis_client = RedisCache()

# Decorador para cachear resultados de funciones
def cache_result(prefix: str, expire: int = 300):
    """
    Decorador para cachear el resultado de una función async
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generar clave de cache basada en argumentos
            key_parts = [prefix]
            key_parts.extend(str(arg) for arg in args)
            key_parts.extend(f"{k}_{v}" for k, v in kwargs.items())
            cache_key = ":".join(key_parts)
            
            # Intentar obtener desde cache
            cached_result = await redis_client.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # Ejecutar función y guardar resultado
            result = await func(*args, **kwargs)
            await redis_client.setex(cache_key, expire, result)
            
            return result
        return wrapper
    return decorator

# Inicializar Redis al importar el módulo
async def init_cache():
    await redis_client.init_redis()