from fastapi import APIRouter, HTTPException, Depends, Query, status
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
import decimal
from app.services.coinbase_service import coinbase_service
from app.dependencies import get_current_user

router = APIRouter(prefix="/coinbase", tags=["Coinbase Wallet"])

# creamos modelos con Pydantic para validacion de datos
class EVMCreateRequest(BaseModel):
    name: Optional[str] = Field(None, description="Nombre opcional para la cuenta")

class EVMImportRequest(BaseModel):
    private_key: str = Field(..., description="Clave privada de la cuenta EVM")
    name: Optional[str] = Field(None, description="Nombre opcional para la cuenta")

class SolanaCreateRequest(BaseModel):
    name: Optional[str] = Field(None, description="Nombre opcional para la cuenta")

class SolanaImportRequest(BaseModel):
    private_key: str = Field(..., description="Clave privada de la cuenta Solana")
    name: Optional[str] = Field(None, description="Nombre opcional para la cuenta")

class ExportRequest(BaseModel):
    name: Optional[str] = Field(None, description="Nombre de la cuenta")
    address: Optional[str] = Field(None, description="Dirección de la cuenta")

class SmartAccountRequest(BaseModel):
    name: str = Field(..., description="Nombre de la cuenta inteligente")
    owner_address: str = Field(..., description="Dirección del propietario")

# ==========================================================================================
# modelos para las transacciones
#EVM
class EVMTransactionRequest(BaseModel):
    address: str = Field(..., description="Dirección de la cuenta que envía")
    to_address: str = Field(..., description="Dirección de destino")
    value: float = Field(..., ge=0.000001, description="Cantidad a enviar (en ETH)")
    network: Optional[str] = Field("base-sepolia", description="Red EVM")
    token: Optional[str] = Field("eth", description="Token a enviar")

class EVMFaucetRequest(BaseModel):
    address: str = Field(..., description="Dirección que recibirá los fondos")
    network: Optional[str] = Field("base-sepolia", description="Red EVM")
    token: Optional[str] = Field("eth", description="Token a solicitar")

# Solana
class SolanaTransactionRequest(BaseModel):
    address: str = Field(..., description="Dirección de la cuenta que envía")
    to_address: str = Field(..., description="Dirección de destino")
    amount: float = Field(..., ge=0.000001, description="Cantidad a enviar (en SOL)")
    network: Optional[str] = Field("devnet", description="Red Solana")

class SolanaFaucetRequest(BaseModel):
    address: str = Field(..., description="Dirección que recibirá los fondos")
    network: Optional[str] = Field("devnet", description="Red Solana")

# ==========================================================================================
# modelos para gestionar cuentas
class AccountGetRequest(BaseModel):
    address: Optional[str] = Field(None, description="Dirección de la cuenta")
    name: Optional[str] = Field(None, description="Nombre de la cuenta")

class AccountUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, description="Nuevo nombre para la cuenta")
    account_policy: Optional[str] = Field(None, description="ID de política a aplicar")

class SmartAccountRequest(BaseModel):
    name: str = Field(..., description="Nombre de la cuenta inteligente")
    owner_address: str = Field(..., description="Dirección del propietario")

# ==========================================================================================

# creamos los endpoints
@router.post("/evm/create")
async def create_evm_account(request: Optional[EVMCreateRequest] = None, user_id: int = Depends(get_current_user)):
    """ Crea una nueva cuenta EVM"""

    try:
        # manejamos el caso cuando request es None
        name = request.name if request and request.name else None

        result = await coinbase_service.create_evm_account(name)

        if result["success"]:
            return {
                "success": True,
                "message": "Cuenta EVM creada exitosamente",
                "account": result["account"]
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["error"]
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creando cuenta EVM: {str(e)}"
        )
    
@router.post("/evm/import")
async def import_evm_account(request: EVMImportRequest, user_id: int = Depends(get_current_user)):
    """Importa una cuenta EVM existente"""
    try:
        result = await coinbase_service.import_evm_account(
            private_key=request.private_key,
            name=request.name
        )
        
        if result["success"]:
            return {
                "success": True,
                "message": "Cuenta EVM importada exitosamente",
                "account": result["account"]
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["error"]
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error importando cuenta EVM: {str(e)}"
        )
    
@router.post("/solana/create")
async def create_solana_account(request: SolanaCreateRequest = None, user_id: int = Depends(get_current_user)):
    """Crea una nueva cuenta Solana"""
    try:
        name = request.name if request else None
        result = await coinbase_service.create_solana_account(name)
        
        if result["success"]:
            return {
                "success": True,
                "message": "Cuenta Solana creada exitosamente",
                "account": result["account"]
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["error"]
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creando cuenta Solana: {str(e)}"
        )
    
@router.post("/solana/import")
async def import_solana_account(request: SolanaImportRequest, user_id: int = Depends(get_current_user)):
    """Importa una cuenta Solana existente"""
    try:
        result = await coinbase_service.import_solana_account(
            private_key=request.private_key,
            name=request.name
        )
        
        if result["success"]:
            return {
                "success": True,
                "message": "Cuenta Solana importada exitosamente",
                "account": result["account"]
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["error"]
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error importando cuenta Solana: {str(e)}"
        )
    
@router.get("/evm/get-or-create")
async def get_or_create_evm_account(user_id: int = Depends(get_current_user)):
    """Obtiene o crea una cuenta EVM"""
    try:
        result = await coinbase_service.get_or_create_evm_account()
        
        if result["success"]:
            return {
                "success": True,
                "message": "Cuenta EVM obtenida/creada exitosamente",
                "account": result["account"]
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["error"]
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error obteniendo/creando cuenta EVM: {str(e)}"
        )
    
@router.get("/solana/get-or-create")
async def get_or_create_solana_account(user_id: int = Depends(get_current_user)):
    """Obtiene o crea una cuenta Solana"""
    try:
        result = await coinbase_service.get_or_create_solana_account()
        
        if result["success"]:
            return {
                "success": True,
                "message": "Cuenta Solana obtenida/creada exitosamente",
                "account": result["account"]
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["error"]
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error obteniendo/creando cuenta Solana: {str(e)}"
        )
    
@router.post("/evm/export")
async def export_evm_account(request: ExportRequest, user_id: int = Depends(get_current_user)):
    """Exporta la clave privada de una cuenta EVM"""
    try:
        result = await coinbase_service.export_evm_account(
            name=request.name,
            address=request.address
        )
        
        if result["success"]:
            return {
                "success": True,
                "message": "Clave privada exportada exitosamente",
                "private_key": result["private_key"]
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["error"]
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error exportando cuenta EVM: {str(e)}"
        )
    
@router.post("/solana/export")
async def export_solana_account(request: ExportRequest, user_id: int = Depends(get_current_user)):
    """Exporta la clave privada de una cuenta Solana"""
    try:
        result = await coinbase_service.export_solana_account(
            name=request.name,
            address=request.address
        )
        
        if result["success"]:
            return {
                "success": True,
                "message": "Clave privada exportada exitosamente",
                "private_key": result["private_key"]
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["error"]
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error exportando cuenta Solana: {str(e)}"
        )
    
@router.post("/smart-account/create")
async def create_smart_account(request: SmartAccountRequest, user_id: int = Depends(get_current_user)):
    """Crea una cuenta inteligente EVM"""
    try:
        result = await coinbase_service.create_smart_account(
            name=request.name,
            owner_address=request.owner_address
        )
        
        if result["success"]:
            return {
                "success": True,
                "message": "Cuenta inteligente creada exitosamente",
                "account": result["account"]
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["error"]
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creando cuenta inteligente: {str(e)}"
        )
    
@router.get("/test-connection")
async def test_coinbase_connection(user_id: int = Depends(get_current_user)):
    """Prueba la conexión con Coinbase CDP"""
    try:
        result = await coinbase_service.test_connection()

        if result["success"]:
            return {
                "success": True,
                "message": result["message"],
                "account_address": result.get("account_address"),
                "timestamp": "2024-01-01T00:00:00Z"
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result["error"]
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error probando conexión: {str(e)}"
        )
    
# =============================================================================
# ENDPOINTS PARA TRANSACCIONES
# =============================================================================
@router.post("/evm/send-transaction")
async def send_evm_transaction(request: EVMTransactionRequest, user_id: int = Depends(get_current_user)):
    """Envia una transacción EVM"""
    try:
        result = await coinbase_service.send_evm_transaction(
            address=request.address,
            to_address=request.to_address,
            value=request.value,
            network=request.network,
            token=request.token
        )

        if result["success"]:
            return {
                "success": True,
                "message": "Transacción EVM enviada exitosamente",
                "transaction": result
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["error"]
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error enviando transacción EVM: {str(e)}"
        )
    
@router.post("/evm/request-faucet")
async def request_evm_faucet(request: EVMFaucetRequest, user_id: int = Depends(get_current_user)):
    """Solicita fondos del faucet para una cuenta EVM"""
    try:
        result = await coinbase_service.request_evm_faucet(
            address=request.address,
            network=request.network,
            token=request.token
        )
        
        if result["success"]:
            return {
                "success": True,
                "message": "Fondos solicitados exitosamente",
                "faucet": result
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["error"]
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error solicitando faucet EVM: {str(e)}"
        )
    
@router.post("/solana/send-transaction")
async def send_solana_transaction(request: SolanaTransactionRequest, user_id: int = Depends(get_current_user)):
    """Envía una transacción Solana"""
    try:
        result = await coinbase_service.send_solana_transaction(
            address=request.address,
            to_address=request.to_address,
            amount=request.amount,
            network=request.network
        )
        
        if result["success"]:
            return {
                "success": True,
                "message": "Transacción Solana enviada exitosamente",
                "transaction": result
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["error"]
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error enviando transacción Solana: {str(e)}"
        )
    
@router.post("/solana/request-faucet")
async def request_solana_faucet(request: SolanaFaucetRequest, user_id: int = Depends(get_current_user)):
    """Solicita fondos del faucet para una cuenta Solana"""
    try:
        result = await coinbase_service.request_solana_faucet(
            address=request.address,
            network=request.network
        )
        
        if result["success"]:
            return {
                "success": True,
                "message": "Fondos SOL solicitados exitosamente",
                "faucet": result
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["error"]
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error solicitando faucet Solana: {str(e)}"
        )
    
# =============================================================================
# ENDPOINTS PARA GESTIÓN DE CUENTAS EVM
# =============================================================================
@router.get("/evm/accounts")
async def list_evm_accounts(
    page_token: Optional[str] = Query(None, description="Token para paginación"),
    user_id: int = Depends(get_current_user)
):
    """Lista todas las cuentas EVM"""
    try:
        result = await coinbase_service.list_evm_accounts(page_token=page_token)
        
        if result["success"]:
            return {
                "success": True,
                "accounts": result["accounts"],
                "pagination": {
                    "next_page_token": result["next_page_token"],
                    "has_more": result["has_more"]
                }
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["error"]
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error listando cuentas EVM: {str(e)}"
        )
    
@router.get("/evm/account")
async def get_evm_account(
    address: Optional[str] = Query(None, description="Dirección de la cuenta"),
    name: Optional[str] = Query(None, description="Nombre de la cuenta"),
    user_id: int = Depends(get_current_user)
):
    """Obtiene una cuenta EVM por dirección o nombre"""
    try:
        result = await coinbase_service.get_evm_account(address=address, name=name)
        
        if result["success"]:
            return {
                "success": True,
                "account": result["account"]
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["error"]
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error obteniendo cuenta EVM: {str(e)}"
        )
    
@router.put("/evm/account/{address}")
async def update_evm_account(
    address: str,
    request: AccountUpdateRequest,
    user_id: int = Depends(get_current_user)
):
    """Actualiza una cuenta EVM (nombre o políticas)"""
    try:
        result = await coinbase_service.update_evm_account(
            address=address,
            name=request.name,
            account_policy=request.account_policy
        )
        
        if result["success"]:
            return {
                "success": True,
                "message": "Cuenta EVM actualizada exitosamente",
                "account": result["account"]
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["error"]
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error actualizando cuenta EVM: {str(e)}"
        )
    
# =============================================================================
# ENDPOINTS PARA CUENTAS INTELIGENTES EVM
# =============================================================================
@router.post("/evm/smart-account")
async def create_smart_account(request: SmartAccountRequest, user_id: int = Depends(get_current_user)):
    """Crea una cuenta inteligente EVM"""
    try:
        result = await coinbase_service.create_smart_account(
            name=request.name,
            owner_address=request.owner_address
        )
        
        if result["success"]:
            return {
                "success": True,
                "message": "Cuenta inteligente creada exitosamente",
                "account": result["account"]
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["error"]
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating smart account: {str(e)}"
        )
    
@router.get("/evm/smart-account/{owner_address}")
async def get_smart_account(owner_address: str, user_id: int = Depends(get_current_user)):
    """Obtiene la cuenta inteligente asociada a un owner"""
    try:
        result = await coinbase_service.get_smart_account(owner_address=owner_address)
        
        if result["success"]:
            return {
                "success": True,
                "account": result["account"]
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["error"]
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting smart account: {str(e)}"
        )
    
# =============================================================================
# ENDPOINTS PARA GESTIÓN DE CUENTAS SOLANA
# =============================================================================
@router.get("/solana/accounts")
async def list_solana_accounts(
    page_token: Optional[str] = Query(None, description="Token para paginación"),
    user_id: int = Depends(get_current_user)
):
    """Lista todas las cuentas Solana"""
    try:
        result = await coinbase_service.list_solana_accounts(page_token=page_token)
        
        if result["success"]:
            return {
                "success": True,
                "accounts": result["accounts"],
                "pagination": {
                    "next_page_token": result["next_page_token"],
                    "has_more": result["has_more"]
                }
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["error"]
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error listing Solana accounts: {str(e)}"
        )

@router.get("/solana/account")
async def get_solana_account(
    address: Optional[str] = Query(None, description="Dirección de la cuenta"),
    name: Optional[str] = Query(None, description="Nombre de la cuenta"),
    user_id: int = Depends(get_current_user)
):
    """Obtiene una cuenta Solana por dirección o nombre"""
    try:
        result = await coinbase_service.get_solana_account(address=address, name=name)
        
        if result["success"]:
            return {
                "success": True,
                "account": result["account"]
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["error"]
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting Solana account: {str(e)}"
        )

@router.put("/solana/account/{address}")
async def update_solana_account(
    address: str,
    request: AccountUpdateRequest,
    user_id: int = Depends(get_current_user)
):
    """Actualiza una cuenta Solana (nombre o políticas)"""
    try:
        result = await coinbase_service.update_solana_account(
            address=address,
            name=request.name,
            account_policy=request.account_policy
        )
        
        if result["success"]:
            return {
                "success": True,
                "message": "Cuenta Solana actualizada exitosamente",
                "account": result["account"]
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["error"]
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating Solana account: {str(e)}"
        )