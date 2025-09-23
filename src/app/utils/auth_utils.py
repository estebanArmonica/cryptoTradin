# app/utils/auth_utils.py
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from typing import Optional
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.user import User, get_user_by_id
from app.core.database import get_db

security = HTTPBearer()

async def verify_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    Verificar token JWT y devolver usuario
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(
            credentials.credentials, 
            settings.JWT_SECRET, 
            algorithms=["HS256"]
        )
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = get_user_by_id(db, int(user_id))
    if user is None or not user.is_active:
        raise credentials_exception
    
    return user

async def get_current_user(
    current_user: User = Depends(verify_token)
) -> User:
    """
    Obtener usuario actual desde token JWT
    """
    return current_user

async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Verificar que el usuario está activo
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Inactive user"
        )
    return current_user

async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security, use_cache=False),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """
    Obtener usuario opcional (para endpoints que pueden ser públicos o privados)
    """
    if not credentials:
        return None
    
    try:
        payload = jwt.decode(
            credentials.credentials, 
            settings.JWT_SECRET, 
            algorithms=["HS256"]
        )
        user_id: str = payload.get("sub")
        if user_id is None:
            return None
    except JWTError:
        return None
    
    user = get_user_by_id(db, int(user_id))
    if user is None or not user.is_active:
        return None
    
    return user

def has_permission(user: User, required_permission: str) -> bool:
    """
    Verificar si usuario tiene permiso específico
    """
    # Implementar lógica de permisos según necesidades
    permissions = user.preferences.get("permissions", [])
    return required_permission in permissions

async def get_user_with_permission(
    required_permission: str,
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Obtener usuario solo si tiene el permiso requerido
    """
    if not has_permission(current_user, required_permission):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions"
        )
    return current_user

# Roles específicos para el trading platform
async def get_trader_user(current_user: User = Depends(get_current_user)) -> User:
    """Obtener usuario con rol de trader"""
    return await get_user_with_permission("trader", current_user)

async def get_admin_user(current_user: User = Depends(get_current_user)) -> User:
    """Obtener usuario con rol de administrador"""
    return await get_user_with_permission("admin", current_user)

async def get_verified_user(current_user: User = Depends(get_current_user)) -> User:
    """Obtener usuario verificado"""
    if not current_user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account not verified"
        )
    return current_user