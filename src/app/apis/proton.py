# app/apis/proton.py
from fastapi import APIRouter, HTTPException, Query, Depends
from app.services.proton_service import proton_service
from typing import Dict, List, Optional, Any
from app.utils.exceptions import handle_api_error
from datetime import datetime

from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/proton", tags=["Proton Wallet"])

# Modelos Pydantic para validación de datos
class TransferRequest(BaseModel):
    from_account: str
    to_account: str
    quantity: str
    memo: Optional[str] = ""
    contract: Optional[str] = "eosio.token"


@router.post("/connect")
async def connect_proton_wallet(account_name: str, permission: str = "active"):
    """
    Conectar wallet de Proton
    
    - **account_name**: Nombre de la cuenta de Proton (1-12 caracteres, a-z, 1-5)
    - **permission**: Permiso a usar (default: "active")
    """
    try:
        if not account_name:
            raise HTTPException(status_code=400, detail="El nombre de cuenta es requerido")
        
        result = await proton_service.connect_wallet(account_name, permission)
        if not result['success']:
            raise HTTPException(status_code=400, detail=result.get('message', 'Error conectando wallet'))
        
        return {
            "success": True,
            "account": result['account'],
            "permission": result['permission'],
            "balances": result.get('balances', []),
            "total_value": result.get('total_value', 0),
            "message": result.get('message', 'Wallet conectada exitosamente'),
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise handle_api_error(e, "Error conectando wallet de Proton")

@router.get("/balance/{account_name}")
async def get_proton_balance(account_name: str):
    """
    Obtener balance completo de una cuenta Proton
    
    - **account_name**: Nombre de la cuenta de Proton
    """
    try:
        if not account_name:
            raise HTTPException(status_code=400, detail="El nombre de cuenta es requerido")
        
        result = await proton_service.get_all_balances(account_name)
        if not result['success']:
            raise HTTPException(
                status_code=400, 
                detail=result.get('error', 'Error obteniendo balance')
            )
        
        return {
            "success": True,
            "account": account_name,
            "tokens": result.get('tokens', []),
            "total_value_usd": result.get('total_value', 0),
            "source": result.get('source', 'unknown'),
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise handle_api_error(e, f"Error obteniendo balance para {account_name}")

@router.get("/token-balance/{account_name}")
async def get_specific_token_balance(
    account_name: str,
    token_contract: str = Query("eosio.token", description="Contrato del token"),
    symbol: str = Query("XPR", description="Símbolo del token")
):
    """
    Obtener balance específico de un token
    
    - **account_name**: Nombre de la cuenta de Proton
    - **token_contract**: Contrato del token (default: eosio.token)
    - **symbol**: Símbolo del token (default: XPR)
    """
    try:
        if not all([account_name, token_contract, symbol]):
            raise HTTPException(status_code=400, detail="Todos los parámetros son requeridos")
        
        result = await proton_service.get_balance(account_name, token_contract, symbol)
        if not result['success']:
            raise HTTPException(
                status_code=400, 
                detail=result.get('error', 'Error obteniendo balance del token')
            )
        
        return {
            "success": True,
            "account": account_name,
            "contract": token_contract,
            "symbol": symbol,
            "balance": result['balance'],
            "amount": result.get('amount', 0.0),
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise handle_api_error(e, f"Error obteniendo balance de {symbol} para {account_name}")

"""
No borrar (se creara el mismo pero con datos mock para prueba)
@router.post("/transfer")
async def proton_transfer(transfer_data: TransferRequest):
    
    Crear transacción de transferencia en Proton
    
    - **from_account**: Cuenta de origen
    - **to_account**: Cuenta de destino  
    - **quantity**: Cantidad con símbolo (ej: "10.0000 XPR")
    - **memo**: Memo opcional para la transferencia
    - **contract**: Contrato del token (default: eosio.token)
    

    try:
        # print de forma temporal (para ver el error 422)
        print(f'Datos recibidos {transfer_data}')

        # Accede a los datos a través del objeto transfer_data
        from_account = transfer_data.from_account
        to_account = transfer_data.to_account
        quantity = transfer_data.quantity
        memo = transfer_data.memo
        contract = transfer_data.contract

        if not all([from_account, to_account, quantity]):
            raise HTTPException(status_code=400, detail="from_account, to_account y quantity son requeridos")
        
        # Validar formato de quantity
        try:
            amount, symbol = quantity.split(' ')
            float(amount)
        except ValueError:
            raise HTTPException(
                status_code=400, 
                detail="Formato de quantity inválido. Use: '10.0000 XPR'"
            )
        
        # problema principal
        result = await proton_service.transfer(from_account, to_account, quantity, memo, contract)

        if not result['success']:
            raise HTTPException(
                status_code=400, 
                detail=result.get('error', 'Error creando transacción')
            )
        
        return {
            "success": True,
            "transaction": result.get('transaction'),
            "chain_id": result.get('chain_id'),
            "message": result.get('message', 'Transacción creada exitosamente'),
            "next_step": "Firmar la transacción con una wallet compatible",
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise handle_api_error(e, "Error creando transacción de transferencia")

"""

@router.post("/transfer")
async def proton_transfer(transfer_data: TransferRequest):
    """
    Crear transacción de transferencia en Proton (VERSIÓN TEMPORAL PARA TESTING)
    """
    try:
        print(f'Datos recibidos: {transfer_data}')

        # SIMULACIÓN TEMPORAL - ELIMINAR CUANDO EL SERVICIO REAL FUNCIONE
        from_account = transfer_data.from_account
        to_account = transfer_data.to_account
        quantity = transfer_data.quantity
        memo = transfer_data.memo
        contract = transfer_data.contract

        # Validar datos básicos
        if not all([from_account, to_account, quantity]):
            raise HTTPException(status_code=400, detail="from_account, to_account y quantity son requeridos")

        # Validar formato de quantity
        try:
            amount, symbol = quantity.split(' ')
            float(amount)
        except ValueError:
            raise HTTPException(
                status_code=400, 
                detail="Formato de quantity inválido. Use: '10.0000 XPR'"
            )

        # ⚠️ SIMULACIÓN TEMPORAL - REEMPLAZAR CON EL SERVICIO REAL
        simulated_transaction = {
            "actions": [
                {
                    "account": contract,
                    "name": "transfer",
                    "authorization": [{"actor": from_account, "permission": "active"}],
                    "data": {
                        "from": from_account,
                        "to": to_account,
                        "quantity": quantity,
                        "memo": memo
                    }
                }
            ],
            "expiration": "2024-01-01T00:00:00",
            "ref_block_num": 12345,
            "ref_block_prefix": 67890,
            "max_net_usage_words": 0,
            "max_cpu_usage_ms": 0,
            "delay_sec": 0,
            "context_free_actions": [],
            "transaction_extensions": []
        }

        return {
            "success": True,
            "transaction": simulated_transaction,
            "chain_id": "aca376f206b8fc25a6ed44dbdc66547c36c6c33e3a119ffbeaef943642f0e906",  # Mainnet ID
            "message": "✅ Transacción simulada creada exitosamente (MODO TEST)",
            "next_step": "Firmar la transacción con una wallet compatible",
            "timestamp": datetime.now().isoformat(),
            "note": "⚠️ Esta es una simulación temporal para testing"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise handle_api_error(e, "Error creando transacción de transferencia")


@router.post("/push-transaction")
async def push_proton_transaction(signed_transaction: Dict[str, Any]):
    """
    Enviar transacción firmada a la blockchain de Proton
    
    - **signed_transaction**: Transacción firmada en formato JSON
    """
    try:
        if not signed_transaction or 'transaction' not in signed_transaction or 'signatures' not in signed_transaction:
            raise HTTPException(status_code=400, detail="Transacción firmada inválida")
        
        result = await proton_service.push_transaction(signed_transaction)
        if not result['success']:
            raise HTTPException(
                status_code=400, 
                detail=result.get('error', 'Error enviando transacción')
            )
        
        return {
            "success": True,
            "transaction_id": result.get('transaction_id'),
            "message": result.get('message', 'Transacción enviada exitosamente'),
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise handle_api_error(e, "Error enviando transacción a la blockchain")

@router.get("/tokens/{account_name}")
async def get_proton_tokens(account_name: str):
    """
    Obtener todos los tokens de una cuenta Proton con precios reales
    
    - **account_name**: Nombre de la cuenta de Proton
    """
    try:
        if not account_name:
            raise HTTPException(status_code=400, detail="El nombre de cuenta es requerido")
        
        result = await proton_service.get_all_balances(account_name)
        if not result['success']:
            raise HTTPException(
                status_code=400, 
                detail=result.get('error', 'Error obteniendo tokens')
            )
        
        return {
            "success": True,
            "account": account_name,
            "tokens": result.get('tokens', []),
            "total_value_usd": result.get('total_value', 0),
            "token_count": len(result.get('tokens', [])),
            "source": result.get('source', 'unknown'),
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise handle_api_error(e, f"Error obteniendo tokens para {account_name}")

@router.get("/account-info/{account_name}")
async def get_proton_account_info(account_name: str):
    """
    Obtener información completa de una cuenta Proton
    
    - **account_name**: Nombre de la cuenta de Proton
    """
    try:
        if not account_name:
            raise HTTPException(status_code=400, detail="El nombre de cuenta es requerido")
        
        result = await proton_service.get_account_info(account_name)
        if not result['success']:
            raise HTTPException(
                status_code=404, 
                detail=result.get('error', 'Cuenta no encontrada')
            )
        
        return {
            "success": True,
            "account": account_name,
            "account_info": result.get('account_info', {}),
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise handle_api_error(e, f"Error obteniendo información de {account_name}")

@router.get("/transaction-history/{account_name}")
async def get_proton_transaction_history(
    account_name: str,
    limit: int = Query(20, ge=1, le=100, description="Número máximo de transacciones")
):
    """
    Obtener historial de transacciones de una cuenta Proton
    
    - **account_name**: Nombre de la cuenta de Proton
    - **limit**: Límite de transacciones a devolver (1-100)
    """
    try:
        if not account_name:
            raise HTTPException(status_code=400, detail="El nombre de cuenta es requerido")
        
        result = await proton_service.get_transaction_history(account_name, limit)
        if not result['success']:
            raise HTTPException(
                status_code=400, 
                detail=result.get('error', 'Error obteniendo historial')
            )
        
        return {
            "success": True,
            "account": account_name,
            "transactions": result.get('transactions', []),
            "total_count": result.get('total', 0),
            "limit": limit,
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise handle_api_error(e, f"Error obteniendo historial para {account_name}")

@router.get("/supported-tokens")
async def get_supported_tokens():
    """
    Obtener lista de tokens soportados por el servicio Proton
    """
    try:
        supported_tokens = []
        for contract, contract_info in proton_service.token_contracts.items():
            for i, symbol in enumerate(contract_info['tokens']):
                coingecko_id = contract_info['coingecko_ids'][i] if i < len(contract_info['coingecko_ids']) else None
                supported_tokens.append({
                    "symbol": symbol,
                    "contract": contract,
                    "coingecko_id": coingecko_id,
                    "display_name": _get_token_display_name(symbol, coingecko_id)
                })
        
        return {
            "success": True,
            "supported_tokens": supported_tokens,
            "total_tokens": len(supported_tokens),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise handle_api_error(e, "Error obteniendo tokens soportados")

def _get_token_display_name(symbol: str, coingecko_id: str) -> str:
    """Obtener nombre para mostrar del token"""
    display_names = {
        "XPR": "Proton",
        "XUSDT": "Tether (Wrapped)",
        "XBTC": "Bitcoin (Wrapped)",
        "XETH": "Ethereum (Wrapped)",
        "XUSDC": "USD Coin (Wrapped)",
        "XDOGE": "Dogecoin (Wrapped)",
        "XBNB": "BNB (Wrapped)",
        "XADA": "Cardano (Wrapped)",
        "XDOT": "Polkadot (Wrapped)",
        "XLTC": "Litecoin (Wrapped)",
        "USDT": "Tether",
        "BTC": "Bitcoin",
        "ETH": "Ethereum",
        "USDC": "USD Coin",
        "DOGE": "Dogecoin",
        "BNB": "BNB",
        "ADA": "Cardano",
        "DOT": "Polkadot",
        "LTC": "Litecoin",
        "XMD": "Proton Market",
        "LOAN": "Proton Loan",
        "SWAP": "Proton Swap",
        "PSWAP": "Proton Swap Token"
    }
    return display_names.get(symbol, symbol)

@router.get("/health")
async def proton_health_check():
    """
    Verificar el estado del servicio Proton
    """
    try:
        health = await proton_service._health_check()
        
        return {
            "success": health['success'],
            "connected": proton_service.connected,
            "rpc_endpoint": proton_service.rpc_endpoint,
            "chain_id": health.get('chain_id'),
            "head_block": health.get('head_block'),
            "server_version": health.get('server_version'),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise handle_api_error(e, "Error verificando salud del servicio Proton")