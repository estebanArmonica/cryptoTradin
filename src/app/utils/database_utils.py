# app/utils/database_utils.py
import decimal
import json
import asyncpg
import os
from typing import Optional
from datetime import datetime

# Configuración de PostgreSQL desde variables de entorno
DATABASE_CONFIG = {
    "host": os.getenv("PGHOST"),
    "user": os.getenv("PGUSER"),
    "password": os.getenv("PGPASSWORD"),
    "database": os.getenv("PGDATABASE"),
    "port": os.getenv("PGPORT"),
    "ssl": "require"
}

async def get_user_balance(user_id: int) -> decimal.Decimal:
    """Obtiene el balance USD de un usuario"""
    conn = await asyncpg.connect(**DATABASE_CONFIG)
    try:
        result = await conn.fetchrow(
            "SELECT usd_balance FROM user_balances WHERE user_id = $1",
            user_id
        )
        
        if result:
            return decimal.Decimal(str(result['usd_balance']))
        else:
            # Crear registro si no existe
            await conn.execute(
                "INSERT INTO user_balances (user_id, usd_balance) VALUES ($1, 0.00)",
                user_id
            )
            return decimal.Decimal('0.00')
    finally:
        await conn.close()

async def update_user_balance(user_id: int, amount: decimal.Decimal, transaction_type: str):
    """Actualiza el balance de un usuario"""
    current_balance = await get_user_balance(user_id)
    
    if transaction_type == 'deposit':
        new_balance = current_balance + amount
    elif transaction_type == 'withdrawal':
        if current_balance < amount:
            raise ValueError("Saldo insuficiente para el retiro")
        new_balance = current_balance - amount
    else:
        raise ValueError("Tipo de transacción no válido")
    
    conn = await asyncpg.connect(**DATABASE_CONFIG)
    try:
        await conn.execute(
            "UPDATE user_balances SET usd_balance = $1, updated_at = CURRENT_TIMESTAMP WHERE user_id = $2",
            float(new_balance), user_id
        )
    finally:
        await conn.close()
    
    return new_balance

async def record_transaction(user_id: int, transaction_id: str, amount: decimal.Decimal, 
                           currency: str, status: str, transaction_type: str, braintree_data: dict = None):
    """Registra una transacción en la base de datos"""
    conn = await asyncpg.connect(**DATABASE_CONFIG)
    try:
        await conn.execute(
            """INSERT INTO transactions 
            (user_id, transaction_id, amount, currency, status, type, braintree_data) 
            VALUES ($1, $2, $3, $4, $5, $6, $7)""",
            user_id, transaction_id, float(amount), currency, status, transaction_type, 
            json.dumps(braintree_data) if braintree_data else None
        )
    finally:
        await conn.close()

async def verify_session(session_token: str) -> Optional[int]:
    """Verifica si una sesión es válida y devuelve el user_id"""
    conn = await asyncpg.connect(**DATABASE_CONFIG)
    try:
        result = await conn.fetchrow(
            "SELECT user_id FROM sessions WHERE session_token = $1 AND expires_at > $2",
            session_token, datetime.now()
        )
        return result['user_id'] if result else None
    finally:
        await conn.close()