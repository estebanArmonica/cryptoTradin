from fastapi import Request, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import asyncpg
from datetime import datetime
import os
from typing import Optional, Dict, Any
import logging
import jwt
from pydantic import BaseModel

# Configuración
logger = logging.getLogger(__name__)

# Configuración de la base de datos
DATABASE_CONFIG = {
    "host": os.getenv("PGHOST"),
    "user": os.getenv("PGUSER"),
    "password": os.getenv("PGPASSWORD"),
    "database": os.getenv("PGDATABASE"),
    "port": os.getenv("PGPORT"),
    "ssl": "require"
}

# Esquemas Pydantic para validación
class TokenData(BaseModel):
    user_id: int
    email: str

class UserSession(BaseModel):
    id: int
    nombre: str
    apellido: str
    correo: str

# Security
security = HTTPBearer()

# =============================================================================
# DEPENDENCIAS DE BASE DE DATOS
# =============================================================================

async def get_db_connection():
    """Provee una conexión a la base de datos"""
    conn = None
    try:
        conn = await asyncpg.connect(**DATABASE_CONFIG)
        yield conn
    except Exception as e:
        logger.error(f"Error connecting to database: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database connection error"
        )
    finally:
        if conn:
            await conn.close()

# =============================================================================
# DEPENDENCIAS DE AUTENTICACIÓN Y AUTORIZACIÓN
# =============================================================================

async def verify_session(session_token: str) -> Optional[int]:
    """Verifica si una sesión es válida y devuelve el user_id"""
    if not session_token:
        return None
    
    conn = None
    try:
        conn = await asyncpg.connect(**DATABASE_CONFIG)
        result = await conn.fetchrow(
            "SELECT user_id FROM sessions WHERE session_token = $1 AND expires_at > $2",
            session_token, datetime.now()
        )
        return result['user_id'] if result else None
    except Exception as e:
        logger.error(f"Error verifying session: {e}")
        return None
    finally:
        if conn:
            await conn.close()

async def get_current_user(request: Request) -> int:
    """Obtiene el usuario actual desde la cookie de sesión (requerido)"""
    session_token = request.cookies.get("session_token")
    
    if not session_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="No autenticado - Cookie de sesión requerida"
        )
    
    user_id = await verify_session(session_token)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Sesión inválida o expirada"
        )
    
    return user_id

async def get_optional_user(request: Request) -> Optional[int]:
    """Obtiene el usuario actual si existe (opcional)"""
    session_token = request.cookies.get("session_token")
    if not session_token:
        return None
    
    return await verify_session(session_token)

async def get_current_user_with_details(request: Request) -> UserSession:
    """Obtiene el usuario actual con todos sus detalles"""
    user_id = await get_current_user(request)
    
    conn = None
    try:
        conn = await asyncpg.connect(**DATABASE_CONFIG)
        user = await conn.fetchrow(
            "SELECT id, nombre, apellido, correo FROM users WHERE id = $1",
            user_id
        )
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuario no encontrado"
            )
        
        return UserSession(
            id=user['id'],
            nombre=user['nombre'],
            apellido=user['apellido'],
            correo=user['correo']
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user details: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error obteniendo detalles del usuario"
        )
    finally:
        if conn:
            await conn.close()

# =============================================================================
# DEPENDENCIAS DE VALIDACIÓN DE DATOS
# =============================================================================

async def validate_user_balance(user_id: int, required_amount: float) -> bool:
    """Valida que el usuario tenga saldo suficiente"""
    conn = None
    try:
        conn = await asyncpg.connect(**DATABASE_CONFIG)
        result = await conn.fetchrow(
            "SELECT usd_balance FROM user_balances WHERE user_id = $1",
            user_id
        )
        
        if not result:
            return False
        
        current_balance = float(result['usd_balance'])
        return current_balance >= required_amount
        
    except Exception as e:
        logger.error(f"Error validating user balance: {e}")
        return False
    finally:
        if conn:
            await conn.close()

async def validate_crypto_balance(user_id: int, coin_id: str, required_amount: float) -> bool:
    """Valida que el usuario tenga suficiente criptomoneda"""
    conn = None
    try:
        conn = await asyncpg.connect(**DATABASE_CONFIG)
        
        # Verificar si la tabla existe
        table_exists = await conn.fetchval('''
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'crypto_balances'
            )
        ''')
        
        if not table_exists:
            return False
        
        result = await conn.fetchrow(
            "SELECT balance FROM crypto_balances WHERE user_id = $1 AND coin_id = $2",
            user_id, coin_id
        )
        
        if not result:
            return False
        
        current_balance = float(result['balance'])
        return current_balance >= required_amount
        
    except Exception as e:
        logger.error(f"Error validating crypto balance: {e}")
        return False
    finally:
        if conn:
            await conn.close()

# =============================================================================
# DEPENDENCIAS DE SEGURIDAD Y ROLES
# =============================================================================

async def require_admin(user: UserSession = Depends(get_current_user_with_details)) -> UserSession:
    """Requiere que el usuario sea administrador (puedes expandir esto)"""
    # Aquí puedes agregar lógica para verificar roles de administrador
    # Por ahora, solo retorna el usuario
    return user

async def require_verified_email(user: UserSession = Depends(get_current_user_with_details)) -> UserSession:
    """Requiere que el usuario tenga email verificado"""
    # Aquí puedes agregar verificación de email
    return user

# =============================================================================
# DEPENDENCIAS DE RATE LIMITING
# =============================================================================

from collections import defaultdict
from datetime import datetime, timedelta

# Simple rate limiting storage (en producción usar Redis)
_request_logs = defaultdict(list)

async def rate_limit(
    request: Request, 
    max_requests: int = 100, 
    time_window: int = 3600  # 1 hora por defecto
):
    """Dependencia para limitar rate limiting por IP"""
    client_ip = request.client.host
    now = datetime.now()
    
    # Limpiar requests antiguos
    _request_logs[client_ip] = [
        timestamp for timestamp in _request_logs[client_ip]
        if now - timestamp < timedelta(seconds=time_window)
    ]
    
    # Verificar si excede el límite
    if len(_request_logs[client_ip]) >= max_requests:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Demasiadas requests. Límite: {max_requests} por hora"
        )
    
    # Registrar la request actual
    _request_logs[client_ip].append(now)
    
    return True

# =============================================================================
# DEPENDENCIAS ESPECÍFICAS PARA TRANSACCIONES
# =============================================================================

async def validate_transaction_amount(amount: float) -> float:
    """Valida que el monto de la transacción sea válido"""
    if amount <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El monto debe ser mayor a 0"
        )
    
    if amount > 1000000:  # Límite de $1,000,000
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El monto excede el límite permitido"
        )
    
    return amount

async def validate_coin_id(coin_id: str) -> str:
    """Valida que el coin_id sea válido"""
    if not coin_id or not coin_id.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Coin ID es requerido"
        )
    
    # Aquí podrías validar contra una lista de coins permitidos
    return coin_id.strip().lower()

# =============================================================================
# DEPENDENCIAS DE CONFIGURACIÓN
# =============================================================================

class AppConfig:
    """Configuración de la aplicación"""
    def __init__(self):
        self.email_config = {
            "smtp_server": os.getenv("SMTP_SERVER", "smtp.gmail.com"),
            "smtp_port": int(os.getenv("SMTP_PORT", "587")),
            "email": os.getenv("EMAIL_USER"),
            "password": os.getenv("EMAIL_PASSWORD"),
            "company_name": os.getenv("COMPANY_NAME", "Crypto Trading Platform"),
            "support_email": os.getenv("SUPPORT_EMAIL", "soporte@cryptotrading.com")
        }
        
        self.app_config = {
            "version": "2.0.0",
            "max_file_size": int(os.getenv("MAX_FILE_SIZE", "5242880")),  # 5MB
            "session_duration_hours": int(os.getenv("SESSION_DURATION", "24")),
            "debug": os.getenv("DEBUG", "False").lower() == "true"
        }

def get_config() -> AppConfig:
    """Provee la configuración de la aplicación"""
    return AppConfig()

# =============================================================================
# DEPENDENCIAS COMPUESTAS (COMBINACIONES)
# =============================================================================

class AuthenticatedTransaction:
    """Dependencia compuesta para transacciones autenticadas"""
    def __init__(
        self,
        user_id: int = Depends(get_current_user),
        rate_limited: bool = Depends(rate_limit)
    ):
        self.user_id = user_id
        self.rate_limited = rate_limited

class AdminAccess:
    """Dependencia compuesta para acceso de administrador"""
    def __init__(
        self,
        admin_user: UserSession = Depends(require_admin),
        rate_limited: bool = Depends(rate_limit)
    ):
        self.user = admin_user
        self.rate_limited = rate_limited

# =============================================================================
# FUNCIONES DE UTILIDAD PARA DEPENDENCIAS
# =============================================================================

async def get_user_balance(user_id: int) -> float:
    """Obtiene el balance USD de un usuario"""
    conn = None
    try:
        conn = await asyncpg.connect(**DATABASE_CONFIG)
        result = await conn.fetchrow(
            "SELECT usd_balance FROM user_balances WHERE user_id = $1",
            user_id
        )
        
        if result:
            return float(result['usd_balance'])
        else:
            # Crear registro si no existe
            await conn.execute(
                "INSERT INTO user_balances (user_id, usd_balance) VALUES ($1, 0.00)",
                user_id
            )
            return 0.0
    except Exception as e:
        logger.error(f"Error getting user balance: {e}")
        return 0.0
    finally:
        if conn:
            await conn.close()

async def get_user_crypto_balance(user_id: int, coin_id: str) -> float:
    """Obtiene el balance de una criptomoneda específica"""
    conn = None
    try:
        conn = await asyncpg.connect(**DATABASE_CONFIG)
        
        # Verificar si la tabla existe
        table_exists = await conn.fetchval('''
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'crypto_balances'
            )
        ''')
        
        if not table_exists:
            return 0.0
        
        result = await conn.fetchrow(
            "SELECT balance FROM crypto_balances WHERE user_id = $1 AND coin_id = $2",
            user_id, coin_id
        )
        
        return float(result['balance']) if result else 0.0
        
    except Exception as e:
        logger.error(f"Error getting crypto balance: {e}")
        return 0.0
    finally:
        if conn:
            await conn.close()

# Exportar dependencias principales
__all__ = [
    'get_current_user',
    'get_optional_user',
    'get_current_user_with_details',
    'require_admin',
    'require_verified_email',
    'rate_limit',
    'validate_transaction_amount',
    'validate_coin_id',
    'validate_user_balance',
    'validate_crypto_balance',
    'get_config',
    'AuthenticatedTransaction',
    'AdminAccess',
    'get_user_balance',
    'get_user_crypto_balance'
]