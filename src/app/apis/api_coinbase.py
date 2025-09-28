from fastapi import APIRouter, HTTPException, Depends, Query, status
from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
from decimal import Decimal
import re

from app.services.coinbase_service import coinbase_service
from app.dependencies import get_current_user

router = APIRouter(prefix="/coinbase", tags=["Coinbase Wallet"])

# =============================================================================
# MODELOS PYDANTIC PARA VALIDACIÓN
# =============================================================================

class EVMCreateRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=36, description="Nombre opcional para la cuenta")

    @validator('name')
    def validate_name(cls, v):
        if v is not None:
            if not re.match(r'^[a-zA-Z0-9-]+$', v):
                raise ValueError('El nombre solo puede contener caracteres alfanuméricos y guiones')
        return v

class EVMImportRequest(BaseModel):
    private_key: str = Field(..., min_length=64, description="Clave privada de la cuenta EVM")
    name: Optional[str] = Field(None, min_length=2, max_length=36, description="Nombre opcional para la cuenta")

    @validator('name')
    def validate_name(cls, v):
        if v is not None:
            if not re.match(r'^[a-zA-Z0-9-]+$', v):
                raise ValueError('El nombre solo puede contener caracteres alfanuméricos y guiones')
        return v

class SolanaCreateRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=36, description="Nombre opcional para la cuenta")

    @validator('name')
    def validate_name(cls, v):
        if v is not None:
            if not re.match(r'^[a-zA-Z0-9-]+$', v):
                raise ValueError('El nombre solo puede contener caracteres alfanuméricos y guiones')
        return v

class SolanaImportRequest(BaseModel):
    private_key: str = Field(..., min_length=64, description="Clave privada de la cuenta Solana")
    name: Optional[str] = Field(None, min_length=2, max_length=36, description="Nombre opcional para la cuenta")

    @validator('name')
    def validate_name(cls, v):
        if v is not None:
            if not re.match(r'^[a-zA-Z0-9-]+$', v):
                raise ValueError('El nombre solo puede contener caracteres alfanuméricos y guiones')
        return v

class ExportRequest(BaseModel):
    name: Optional[str] = Field(None, description="Nombre de la cuenta")
    address: Optional[str] = Field(None, description="Dirección de la cuenta")

    @validator('name')
    def validate_name(cls, v):
        if v is not None:
            if len(v) < 2 or len(v) > 36:
                raise ValueError('El nombre debe tener entre 2 y 36 caracteres')
            if not re.match(r'^[a-zA-Z0-9-]+$', v):
                raise ValueError('El nombre solo puede contener caracteres alfanuméricos y guiones')
        return v

class SmartAccountRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=36, description="Nombre de la cuenta inteligente")
    owner_address: str = Field(..., description="Dirección del propietario")

    @validator('name')
    def validate_name(cls, v):
        if not re.match(r'^[a-zA-Z0-9-]+$', v):
            raise ValueError('El nombre solo puede contener caracteres alfanuméricos y guiones')
        return v

# =============================================================================
# MODELOS PARA TRANSACCIONES
# =============================================================================

class EVMTransactionRequest(BaseModel):
    address: str = Field(..., description="Dirección de la cuenta que envía")
    to_address: str = Field(..., description="Dirección de destino")
    value: float = Field(..., gt=0, description="Cantidad a enviar (en ETH)")
    network: Optional[str] = Field("base-sepolia", description="Red EVM")
    token: Optional[str] = Field("eth", description="Token a enviar")

    @validator('value')
    def validate_value(cls, v):
        if v <= 0:
            raise ValueError('El valor debe ser mayor a 0')
        return v

class EVMFaucetRequest(BaseModel):
    address: str = Field(..., description="Dirección que recibirá los fondos")
    network: Optional[str] = Field("base-sepolia", description="Red EVM")
    token: Optional[str] = Field("eth", description="Token a solicitar")

class SolanaTransactionRequest(BaseModel):
    address: str = Field(..., description="Dirección de la cuenta que envía")
    to_address: str = Field(..., description="Dirección de destino")
    amount: float = Field(..., gt=0, description="Cantidad a enviar (en SOL)")
    network: Optional[str] = Field("devnet", description="Red Solana")

    @validator('amount')
    def validate_amount(cls, v):
        if v <= 0:
            raise ValueError('El amount debe ser mayor a 0')
        return v

class SolanaFaucetRequest(BaseModel):
    address: str = Field(..., description="Dirección que recibirá los fondos")
    network: Optional[str] = Field("devnet", description="Red Solana")

# =============================================================================
# MODELOS PARA GESTIÓN DE CUENTAS
# =============================================================================

class AccountUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=36, description="Nuevo nombre para la cuenta")
    account_policy: Optional[str] = Field(None, description="ID de política a aplicar")

    @validator('name')
    def validate_name(cls, v):
        if v is not None:
            if not re.match(r'^[a-zA-Z0-9-]+$', v):
                raise ValueError('El nombre solo puede contener caracteres alfanuméricos y guiones')
        return v

# =============================================================================
# MODELOS DE RESPUESTA
# =============================================================================

class StandardResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None

class AccountResponse(BaseModel):
    success: bool
    message: str
    account: Dict[str, Any]

class AccountsListResponse(BaseModel):
    success: bool
    accounts: List[Dict[str, Any]]
    pagination: Dict[str, Any]

class TransactionResponse(BaseModel):
    success: bool
    message: str
    transaction: Dict[str, Any]

class PrivateKeyResponse(BaseModel):
    success: bool
    message: str
    private_key: str
    address: Optional[str] = None
    name: Optional[str] = None

# =============================================================================
# ENDPOINTS PARA CUENTAS EVM
# =============================================================================

@router.post(
    "/evm/create",
    response_model=AccountResponse,
    summary="Crear cuenta EVM",
    description="Crea una nueva cuenta EVM en Coinbase CDP"
)
async def create_evm_account(
    request: Optional[EVMCreateRequest] = None,
    user_id: int = Depends(get_current_user)
):
    """Crea una nueva cuenta EVM"""
    try:
        # Manejar request opcional
        name = request.name if request else None
        
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
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno creando cuenta EVM: {str(e)}"
        )

@router.post(
    "/evm/import",
    response_model=AccountResponse,
    summary="Importar cuenta EVM",
    description="Importa una cuenta EVM existente usando su clave privada"
)
async def import_evm_account(
    request: EVMImportRequest,
    user_id: int = Depends(get_current_user)
):
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
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno importando cuenta EVM: {str(e)}"
        )

@router.get(
    "/evm/accounts",
    response_model=AccountsListResponse,
    summary="Listar cuentas EVM",
    description="Obtiene la lista de todas las cuentas EVM con paginación"
)
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
                "pagination": result.get("pagination", {})
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["error"]
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno listando cuentas EVM: {str(e)}"
        )

@router.get(
    "/evm/account",
    response_model=AccountResponse,
    summary="Obtener cuenta EVM",
    description="Obtiene una cuenta EVM específica por dirección o nombre"
)
async def get_evm_account(
    address: Optional[str] = Query(None, description="Dirección de la cuenta"),
    name: Optional[str] = Query(None, description="Nombre de la cuenta"),
    user_id: int = Depends(get_current_user)
):
    """Obtiene una cuenta EVM por dirección o nombre"""
    try:
        if not address and not name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Se requiere address o name"
            )

        result = await coinbase_service.get_evm_account(address=address, name=name)
        
        if result["success"]:
            return {
                "success": True,
                "message": "Cuenta EVM obtenida exitosamente",
                "account": result["account"]
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["error"]
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno obteniendo cuenta EVM: {str(e)}"
        )

@router.put(
    "/evm/account/{address}",
    response_model=AccountResponse,
    summary="Actualizar cuenta EVM",
    description="Actualiza el nombre o políticas de una cuenta EVM"
)
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
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno actualizando cuenta EVM: {str(e)}"
        )

@router.post(
    "/evm/export",
    response_model=PrivateKeyResponse,
    summary="Exportar cuenta EVM",
    description="Exporta la clave privada de una cuenta EVM"
)
async def export_evm_account(
    request: ExportRequest,
    user_id: int = Depends(get_current_user)
):
    """Exporta la clave privada de una cuenta EVM"""
    try:
        if not request.name and not request.address:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Se requiere name o address"
            )

        result = await coinbase_service.export_evm_account(
            name=request.name,
            address=request.address
        )
        
        if result["success"]:
            return {
                "success": True,
                "message": "Clave privada exportada exitosamente",
                "private_key": result["private_key"],
                "address": result.get("address"),
                "name": result.get("name")
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["error"]
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno exportando cuenta EVM: {str(e)}"
        )

@router.get(
    "/evm/get-or-create",
    response_model=AccountResponse,
    summary="Obtener o crear cuenta EVM",
    description="Obtiene una cuenta EVM existente o crea una nueva si no existe"
)
async def get_or_create_evm_account(
    name: Optional[str] = Query(None, description="Nombre opcional para la cuenta"),
    user_id: int = Depends(get_current_user)
):
    """Obtiene o crea una cuenta EVM - CORREGIDO"""
    try:
        result = await coinbase_service.get_or_create_evm_account(name)
        
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
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno obteniendo/creando cuenta EVM: {str(e)}"
        )

# =============================================================================
# ENDPOINTS PARA CUENTAS SOLANA
# =============================================================================

@router.post(
    "/solana/create",
    response_model=AccountResponse,
    summary="Crear cuenta Solana",
    description="Crea una nueva cuenta Solana en Coinbase CDP"
)
async def create_solana_account(
    request: Optional[SolanaCreateRequest] = None,
    user_id: int = Depends(get_current_user)
):
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
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno creando cuenta Solana: {str(e)}"
        )

@router.post(
    "/solana/import",
    response_model=AccountResponse,
    summary="Importar cuenta Solana",
    description="Importa una cuenta Solana existente usando su clave privada"
)
async def import_solana_account(
    request: SolanaImportRequest,
    user_id: int = Depends(get_current_user)
):
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
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno importando cuenta Solana: {str(e)}"
        )

@router.get(
    "/solana/accounts",
    response_model=AccountsListResponse,
    summary="Listar cuentas Solana",
    description="Obtiene la lista de todas las cuentas Solana con paginación"
)
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
                "pagination": result.get("pagination", {})
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["error"]
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno listando cuentas Solana: {str(e)}"
        )

@router.get(
    "/solana/account",
    response_model=AccountResponse,
    summary="Obtener cuenta Solana",
    description="Obtiene una cuenta Solana específica por dirección o nombre"
)
async def get_solana_account(
    address: Optional[str] = Query(None, description="Dirección de la cuenta"),
    name: Optional[str] = Query(None, description="Nombre de la cuenta"),
    user_id: int = Depends(get_current_user)
):
    """Obtiene una cuenta Solana por dirección o nombre"""
    try:
        if not address and not name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Se requiere address o name"
            )

        result = await coinbase_service.get_solana_account(address=address, name=name)
        
        if result["success"]:
            return {
                "success": True,
                "message": "Cuenta Solana obtenida exitosamente",
                "account": result["account"]
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["error"]
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno obteniendo cuenta Solana: {str(e)}"
        )

@router.put(
    "/solana/account/{address}",
    response_model=AccountResponse,
    summary="Actualizar cuenta Solana",
    description="Actualiza el nombre o políticas de una cuenta Solana"
)
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
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno actualizando cuenta Solana: {str(e)}"
        )

@router.post(
    "/solana/export",
    response_model=PrivateKeyResponse,
    summary="Exportar cuenta Solana",
    description="Exporta la clave privada de una cuenta Solana"
)
async def export_solana_account(
    request: ExportRequest,
    user_id: int = Depends(get_current_user)
):
    """Exporta la clave privada de una cuenta Solana"""
    try:
        if not request.name and not request.address:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Se requiere name o address"
            )

        result = await coinbase_service.export_solana_account(
            name=request.name,
            address=request.address
        )
        
        if result["success"]:
            return {
                "success": True,
                "message": "Clave privada exportada exitosamente",
                "private_key": result["private_key"],
                "address": result.get("address"),
                "name": result.get("name")
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["error"]
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno exportando cuenta Solana: {str(e)}"
        )

@router.get(
    "/solana/get-or-create",
    response_model=AccountResponse,
    summary="Obtener o crear cuenta Solana",
    description="Obtiene una cuenta Solana existente o crea una nueva si no existe"
)
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
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno obteniendo/creando cuenta Solana: {str(e)}"
        )

# =============================================================================
# ENDPOINTS PARA CUENTAS INTELIGENTES
# =============================================================================

@router.post(
    "/smart-account/create",
    response_model=AccountResponse,
    summary="Crear cuenta inteligente",
    description="Crea una cuenta inteligente EVM con un owner específico"
)
async def create_smart_account(
    request: SmartAccountRequest,
    user_id: int = Depends(get_current_user)
):
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
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno creando cuenta inteligente: {str(e)}"
        )

@router.get(
    "/smart-account/{owner_address}",
    response_model=AccountResponse,
    summary="Obtener cuenta inteligente",
    description="Obtiene la cuenta inteligente asociada a un owner"
)
async def get_smart_account(
    owner_address: str,
    user_id: int = Depends(get_current_user)
):
    """Obtiene la cuenta inteligente asociada a un owner"""
    try:
        result = await coinbase_service.get_smart_account(owner_address=owner_address)
        
        if result["success"]:
            return {
                "success": True,
                "message": "Cuenta inteligente obtenida exitosamente",
                "account": result["account"]
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["error"]
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno obteniendo cuenta inteligente: {str(e)}"
        )

# =============================================================================
# ENDPOINTS PARA TRANSACCIONES
# =============================================================================

@router.post(
    "/evm/send-transaction",
    response_model=TransactionResponse,
    summary="Enviar transacción EVM",
    description="Envía una transacción en la red EVM especificada"
)
async def send_evm_transaction(
    request: EVMTransactionRequest,
    user_id: int = Depends(get_current_user)
):
    """Envía una transacción EVM"""
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
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno enviando transacción EVM: {str(e)}"
        )

@router.post(
    "/evm/request-faucet",
    response_model=StandardResponse,
    summary="Solicitar faucet EVM",
    description="Solicita fondos de prueba del faucet para una cuenta EVM"
)
async def request_evm_faucet(
    request: EVMFaucetRequest,
    user_id: int = Depends(get_current_user)
):
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
                "data": result
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["error"]
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno solicitando faucet EVM: {str(e)}"
        )

@router.post(
    "/solana/send-transaction",
    response_model=TransactionResponse,
    summary="Enviar transacción Solana",
    description="Envía una transacción en la red Solana especificada"
)
async def send_solana_transaction(
    request: SolanaTransactionRequest,
    user_id: int = Depends(get_current_user)
):
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
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno enviando transacción Solana: {str(e)}"
        )

@router.post(
    "/solana/request-faucet",
    response_model=StandardResponse,
    summary="Solicitar faucet Solana",
    description="Solicita fondos de prueba del faucet para una cuenta Solana"
)
async def request_solana_faucet(
    request: SolanaFaucetRequest,
    user_id: int = Depends(get_current_user)
):
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
                "data": result
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["error"]
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno solicitando faucet Solana: {str(e)}"
        )

# =============================================================================
# ENDPOINTS DE UTILIDAD
# =============================================================================

@router.get(
    "/test-connection",
    response_model=StandardResponse,
    summary="Probar conexión",
    description="Prueba la conexión con Coinbase CDP"
)
async def test_coinbase_connection(user_id: int = Depends(get_current_user)):
    """Prueba la conexión con Coinbase CDP"""
    try:
        result = await coinbase_service.test_connection()

        if result["success"]:
            return {
                "success": True,
                "message": result["message"],
                "data": {
                    "account_address": result.get("account_address"),
                    "timestamp": result.get("timestamp")
                }
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result["error"]
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno probando conexión: {str(e)}"
        )

# =============================================================================
# HEALTH CHECK
# =============================================================================

@router.get(
    "/health",
    response_model=StandardResponse,
    summary="Health Check",
    description="Verifica el estado del servicio Coinbase"
)
async def health_check():
    """Health check del servicio Coinbase"""
    try:
        # Verificar inicialización básica
        await coinbase_service._ensure_initialized()
        
        return {
            "success": True,
            "message": "Coinbase service is healthy",
            "data": {
                "status": "operational",
                "initialized": coinbase_service._initialized
            }
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Coinbase service is unavailable: {str(e)}"
        )