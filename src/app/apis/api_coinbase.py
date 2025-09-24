from fastapi import APIRouter, HTTPException, Depends, status
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