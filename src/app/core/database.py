# src/app/core/database.py
import logging
from typing import AsyncGenerator, Optional
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import QueuePool
from sqlalchemy import text
from contextlib import asynccontextmanager

from src.app.core.config import settings
from src.app.core.cache import redis_client

logger = logging.getLogger(__name__)

# Base para modelos SQLAlchemy
Base = declarative_base()

class DatabaseManager:
    def __init__(self):
        self.engine = None
        self.async_session_factory = None
        self.is_connected = False
    
    async def init_db(self):
        """Inicializar la conexión a la base de datos"""
        try:
            # Crear engine asíncrono
            self.engine = create_async_engine(
                settings.DATABASE_URL,
                echo=settings.ENVIRONMENT == "development",
                poolclass=QueuePool,
                pool_size=20,
                max_overflow=10,
                pool_timeout=30,
                pool_recycle=1800,
                pool_pre_ping=True,
                connect_args={
                    "timeout": 30,
                    "server_settings": {
                        "application_name": settings.APP_NAME,
                        "timezone": "UTC"
                    }
                }
            )
            
            # Crear session factory
            self.async_session_factory = sessionmaker(
                self.engine,
                class_=AsyncSession,
                expire_on_commit=False,
                autoflush=False
            )
            
            # Test connection
            async with self.engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            
            self.is_connected = True
            logger.info("✅ Base de datos conectada exitosamente")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error conectando a la base de datos: {e}")
            self.is_connected = False
            return False
    
    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Context manager para obtener una sesión de base de datos
        """
        if not self.is_connected or not self.async_session_factory:
            raise RuntimeError("Database not initialized")
        
        session: AsyncSession = self.async_session_factory()
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            await session.close()
    
    async def get_db(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Dependency para FastAPI que provee una sesión de base de datos
        """
        async with self.get_session() as session:
            yield session
    
    async def create_tables(self):
        """Crear todas las tablas en la base de datos"""
        if not self.is_connected:
            await self.init_db()
        
        try:
            async with self.engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            logger.info("✅ Tablas de la base de datos creadas exitosamente")
        except Exception as e:
            logger.error(f"❌ Error creando tablas: {e}")
            raise
    
    async def drop_tables(self):
        """Eliminar todas las tablas (solo para desarrollo/testing)"""
        if not self.is_connected:
            await self.init_db()
        
        try:
            async with self.engine.begin() as conn:
                await conn.run_sync(Base.metadata.drop_all)
            logger.info("✅ Tablas de la base de datos eliminadas")
        except Exception as e:
            logger.error(f"❌ Error eliminando tablas: {e}")
            raise
    
    async def health_check(self) -> bool:
        """Verificar el estado de la base de datos"""
        if not self.is_connected:
            return False
        
        try:
            async with self.engine.connect() as conn:
                result = await conn.execute(text("SELECT 1"))
                return result.scalar() == 1
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False
    
    async def close(self):
        """Cerrar conexiones de la base de datos"""
        if self.engine:
            await self.engine.dispose()
            self.is_connected = False
            logger.info("✅ Conexiones de base de datos cerradas")

# Instancia global de la base de datos
database_manager = DatabaseManager()

# Dependency para FastAPI
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency que provee una sesión de base de datos para FastAPI routes
    """
    async with database_manager.get_session() as session:
        yield session

async def get_db_session() -> AsyncSession:
    """
    Obtener una sesión de base de datos directamente
    """
    async with database_manager.get_session() as session:
        return session

# Funciones de utilidad para la base de datos
async def init_database():
    """Inicializar la base de datos al iniciar la aplicación"""
    try:
        success = await database_manager.init_db()
        if success:
            # Crear tablas si no existen (solo en desarrollo)
            if settings.ENVIRONMENT in ["development", "testing"]:
                await database_manager.create_tables()
        return success
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        return False

async def close_database():
    """Cerrar conexiones de base de datos al apagar la aplicación"""
    await database_manager.close()

# Modelos base con funcionalidades comunes
class BaseModel:
    """Clase base con funcionalidades comunes para todos los modelos"""
    
    @classmethod
    async def get_by_id(cls, session: AsyncSession, id: int):
        """Obtener un registro por ID"""
        return await session.get(cls, id)
    
    @classmethod
    async def get_all(cls, session: AsyncSession, skip: int = 0, limit: int = 100):
        """Obtener todos los registros con paginación"""
        from sqlalchemy import select
        result = await session.execute(
            select(cls).offset(skip).limit(limit)
        )
        return result.scalars().all()
    
    async def save(self, session: AsyncSession):
        """Guardar el objeto en la base de datos"""
        session.add(self)
        await session.commit()
        await session.refresh(self)
        return self
    
    async def delete(self, session: AsyncSession):
        """Eliminar el objeto de la base de datos"""
        await session.delete(self)
        await session.commit()

# Mixins para funcionalidades comunes
class TimestampMixin:
    """Mixin para añadir timestamps de creación y actualización"""
    from sqlalchemy import Column, DateTime, func
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

class SoftDeleteMixin:
    """Mixin para soft delete"""
    from sqlalchemy import Column, Boolean
    is_deleted = Column(Boolean, default=False, nullable=False)
    
    async def soft_delete(self, session: AsyncSession):
        """Marca el registro como eliminado (soft delete)"""
        self.is_deleted = True
        await self.save(session)
    
    @classmethod
    async def get_active(cls, session: AsyncSession, skip: int = 0, limit: int = 100):
        """Obtener solo registros activos (no eliminados)"""
        from sqlalchemy import select
        result = await session.execute(
            select(cls).where(cls.is_deleted == False).offset(skip).limit(limit)
        )
        return result.scalars().all()

# Event handlers para la base de datos
@asynccontextmanager
async def lifespan(app):
    """
    Lifespan manager para FastAPI que maneja la inicialización y cierre de la base de datos
    """
    # Startup
    logger.info("Starting application...")
    
    # Inicializar Redis
    await redis_client.init_redis()
    
    # Inicializar base de datos
    db_success = await init_database()
    if not db_success:
        logger.error("Failed to initialize database")
    
    yield
    
    # Shutdown
    logger.info("Shutting down application...")
    await close_database()
    await redis_client.close()