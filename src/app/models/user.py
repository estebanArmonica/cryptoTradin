# app/models/user.py
from sqlalchemy import Column, Integer, String, Boolean, DateTime, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import uuid
from passlib.context import CryptContext
from jose import JWTError, jwt
from pydantic import BaseModel, EmailStr

from app.core.config import settings

Base = declarative_base()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Modelo Pydantic para usuarios
class UserBase(BaseModel):
    email: EmailStr
    username: str
    proton_account: Optional[str] = None
    is_active: Optional[bool] = True

class UserCreate(UserBase):
    password: str

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    username: Optional[str] = None
    proton_account: Optional[str] = None
    password: Optional[str] = None

class UserInDB(UserBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# Modelo de base de datos
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    proton_account = Column(String, unique=True, index=True, nullable=True)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    preferences = Column(JSON, default=dict)
    last_login = Column(DateTime, nullable=True)

    def verify_password(self, password: str) -> bool:
        """Verificar contraseña"""
        return pwd_context.verify(password, self.hashed_password)

    def get_jwt_token(self) -> str:
        """Generar token JWT para el usuario"""
        expires = datetime.utcnow() + timedelta(hours=settings.JWT_EXPIRE_HOURS)
        to_encode = {
            "sub": str(self.id),
            "email": self.email,
            "username": self.username,
            "exp": expires
        }
        return jwt.encode(to_encode, settings.JWT_SECRET, algorithm="HS256")

# Funciones de utilidad para usuarios
def get_password_hash(password: str) -> str:
    """Hashear contraseña"""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verificar contraseña"""
    return pwd_context.verify(plain_password, hashed_password)

def create_user(db: Session, user_data: UserCreate) -> User:
    """Crear nuevo usuario"""
    hashed_password = get_password_hash(user_data.password)
    db_user = User(
        email=user_data.email,
        username=user_data.username,
        proton_account=user_data.proton_account,
        hashed_password=hashed_password
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def get_user_by_email(db: Session, email: str) -> Optional[User]:
    """Obtener usuario por email"""
    return db.query(User).filter(User.email == email).first()

def get_user_by_username(db: Session, username: str) -> Optional[User]:
    """Obtener usuario por username"""
    return db.query(User).filter(User.username == username).first()

def get_user_by_proton_account(db: Session, proton_account: str) -> Optional[User]:
    """Obtener usuario por cuenta Proton"""
    return db.query(User).filter(User.proton_account == proton_account).first()

def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
    """Obtener usuario por ID"""
    return db.query(User).filter(User.id == user_id).first()

def update_user(db: Session, user_id: int, update_data: UserUpdate) -> Optional[User]:
    """Actualizar usuario"""
    user = get_user_by_id(db, user_id)
    if not user:
        return None
    
    if update_data.email:
        user.email = update_data.email
    if update_data.username:
        user.username = update_data.username
    if update_data.proton_account:
        user.proton_account = update_data.proton_account
    if update_data.password:
        user.hashed_password = get_password_hash(update_data.password)
    
    db.commit()
    db.refresh(user)
    return user

def authenticate_user(db: Session, username: str, password: str) -> Optional[User]:
    """Autenticar usuario"""
    user = get_user_by_username(db, username)
    if not user:
        user = get_user_by_email(db, username)
    
    if not user or not user.verify_password(password):
        return None
    
    if not user.is_active:
        return None
    
    # Actualizar último login
    user.last_login = datetime.utcnow()
    db.commit()
    
    return user