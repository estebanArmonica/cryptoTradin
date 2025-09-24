import time
from fastapi import APIRouter, HTTPException, Depends, status
import braintree
import os, json
from dotenv import load_dotenv
from typing import Optional
from pydantic import BaseModel, Field, validator
import decimal, requests
from base64 import b64encode

from app.utils.database_utils import record_transaction, update_user_balance

# Cargar variables de entorno
load_dotenv()

# Configuración de PayPal para Payouts
PAYPAL_CLIENT_ID = "Ac6Xq9PVNP7ftJwPWrgAGxeFu17BYlCJ6YaUc6oDeEHDr_WoWAFbzvMa1LlBeWAUip1GZZZRzrTWs6Xl"
PAYPAL_SECRET = "EEfy7kNxjwgqzOiHvZ_JQftuWyCAD7-fffsGvvh5GqkELEMP3wOz6piYuyCFCLGt9zAf3xd4G0pQtAIL"
PAYPAL_BASE_URL = "https://api-m.paypal.com"  # produccion


router = APIRouter(prefix="/braintree", tags=["payments"])

# Modelos Pydantic para validación
class ClientTokenRequest(BaseModel):
    customer_id: Optional[str] = Field(None, description="ID del cliente en Braintree")
    merchant_account_id: Optional[str] = Field(None, description="ID de la cuenta de comercio")

class PaymentRequest(BaseModel):
    payment_method_nonce: str = Field(..., description="Nonce del método de pago")
    amount: decimal.Decimal = Field(..., gt=0, description="Monto de la transacción")
    device_data: Optional[str] = Field(None, description="Datos del dispositivo")
    customer_id: Optional[str] = Field(None, description="ID del cliente")
    
    @validator('amount')
    def validate_amount(cls, v):
        return v.quantize(decimal.Decimal('0.01'))

class WithdrawalRequest(BaseModel):
    amount: decimal.Decimal = Field(..., gt=0, description="Monto a retirar")
    bank_account_token: str = Field(..., description="Token de la cuenta bancaria")
    
    @validator('amount')
    def validate_amount(cls, v):
        return v.quantize(decimal.Decimal('0.01'))
    
class PayPalPayoutRequest(BaseModel):
    amount: float
    currency: str = "USD"
    recipient_email: str
    recipient_type: str = "EMAIL"
    note: str = "Retiro desde Crypto Trading Platform"
    sender_batch_id: str = None
    
    
# accedemos al token de paypal
def get_paypal_access_token():
    """Obtiene access token de PayPal"""
    auth_string = f"{PAYPAL_CLIENT_ID}:{PAYPAL_SECRET}"
    encoded_auth = b64encode(auth_string.encode()).decode()
    
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Authorization": f"Basic {encoded_auth}"
    }
    
    data = {"grant_type": "client_credentials"}
    
    response = requests.post(f"{PAYPAL_BASE_URL}/v1/oauth2/token", 
                           headers=headers, data=data)
    
    if response.status_code == 200:
        return response.json()["access_token"]
    else:
        raise Exception(f"Error obteniendo access token: {response.text}")  

@router.post("/payout")
async def create_paypal_payout(payout_data: PayPalPayoutRequest):
    """Crea un pago masivo (payout) a través de PayPal"""
    try:
        access_token = get_paypal_access_token()
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {access_token}",
            "PayPal-Request-Id": f"payout_{int(time.time())}"
        }
        
        # Generar ID único para el lote
        sender_batch_id = payout_data.sender_batch_id or f"Payout_{int(time.time())}"
        
        payout_payload = {
            "sender_batch_header": {
                "sender_batch_id": sender_batch_id,
                "email_subject": "Has recibido un pago",
                "email_message": "Has recibido un pago de Crypto Trading Platform. Gracias por usar nuestros servicios."
            },
            "items": [
                {
                    "recipient_type": payout_data.recipient_type,
                    "amount": {
                        "value": str(round(payout_data.amount, 2)),
                        "currency": payout_data.currency
                    },
                    "note": payout_data.note,
                    "receiver": payout_data.recipient_email,
                    "sender_item_id": f"item_{int(time.time())}"
                }
            ]
        }
        
        response = requests.post(
            f"{PAYPAL_BASE_URL}/v1/payments/payouts",
            headers=headers,
            json=payout_payload
        )
        
        if response.status_code in [200, 201]:
            payout_result = response.json()
            
            # Registrar la transacción en tu base de datos
            return {
                "success": True,
                "payout_batch_id": payout_result["batch_header"]["payout_batch_id"],
                "transaction_id": payout_result["batch_header"]["payout_batch_id"],
                "amount_sent": payout_data.amount,
                "recipient_email": payout_data.recipient_email,
                "status": "PENDING"
            }
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Error creando payout: {response.text}"
            )
            
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error procesando payout: {str(e)}"
        )

@router.get("/payout-status/{payout_batch_id}")
async def get_payout_status(payout_batch_id: str):
    """Verifica el estado de un payout"""
    try:
        access_token = get_paypal_access_token()
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {access_token}"
        }
        
        response = requests.get(
            f"{PAYPAL_BASE_URL}/v1/payments/payouts/{payout_batch_id}",
            headers=headers
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Error obteniendo estado: {response.text}"
            )
            
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error verificando estado: {str(e)}"
        )

# Configuración de Braintree
def get_braintree_gateway():
    environment = os.getenv("BRAINTREE_ENVIRONMENT", "sandbox").lower()
    
    if environment == "production":
        braintree_environment = braintree.Environment.Production
        print("🚀 Modo PRODUCCIÓN - Transacciones reales")
    else:
        braintree_environment = braintree.Environment.Sandbox
        print("🔧 Modo SANDBOX - Transacciones de prueba")
    
    merchant_id = os.getenv("BRAINTREE_MERCHANT_ID")
    public_key = os.getenv("BRAINTREE_PUBLIC_KEY")
    private_key = os.getenv("BRAINTREE_PRIVATE_KEY")
    
    if not all([merchant_id, public_key, private_key]):
        raise ValueError("Faltan credenciales de Braintree")
    
    return braintree.BraintreeGateway(
        braintree.Configuration(
            environment=braintree_environment,
            merchant_id=merchant_id,
            public_key=public_key,
            private_key=private_key
        )
    )

@router.post("/client-token")
async def generate_client_token(request: ClientTokenRequest = None):
    """Genera token de cliente para Braintree"""
    try:
        gateway = get_braintree_gateway()
        
        params = {}
        if request and request.customer_id:
            params["customer_id"] = request.customer_id
        if request and request.merchant_account_id:
            params["merchant_account_id"] = request.merchant_account_id
            
        client_token = gateway.client_token.generate(params)
        
        return {
            "success": True,
            "client_token": client_token,
            "environment": "production" if gateway.config.environment == braintree.Environment.Production else "sandbox"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating client token: {str(e)}"
        )

@router.post("/process-payment")
async def process_payment(payment_data: PaymentRequest):
    """Procesa un pago con Braintree"""
    try:
        gateway = get_braintree_gateway()
        
        if not payment_data.payment_method_nonce:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Payment method nonce is required"
            )
        
        if payment_data.amount <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Amount must be greater than 0"
            )
        
        transaction_params = {
            "amount": str(round(payment_data.amount, 2)),
            "payment_method_nonce": payment_data.payment_method_nonce,
            "options": {
                "submit_for_settlement": True,
                "store_in_vault_on_success": True if payment_data.customer_id else False
            }
        }
        
        if payment_data.device_data:
            transaction_params["device_data"] = payment_data.device_data
            
        if payment_data.customer_id:
            transaction_params["customer_id"] = payment_data.customer_id
        
        result = gateway.transaction.sale(transaction_params)
        
        if result.is_success:
            return {
                "success": True,
                "message": "Payment processed successfully",
                "transaction": {
                    "id": result.transaction.id,
                    "amount": result.transaction.amount,
                    "currency": result.transaction.currency_iso_code,
                    "status": result.transaction.status,
                    "created_at": result.transaction.created_at
                }
            }
        else:
            error_message = result.message
            if result.transaction:
                error_message = f"{result.message} (Transaction: {result.transaction.id})"
                
            return {
                "success": False,
                "message": error_message,
                "errors": [{"code": error.code, "message": error.message} for error in result.errors.deep_errors] if result.errors else []
            }
            
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing payment: {str(e)}"
        )

@router.post("/withdraw")
async def withdraw_to_bank(withdrawal_data: WithdrawalRequest):
    """Procesa un retiro a cuenta bancaria"""
    try:
        gateway = get_braintree_gateway()
        
        result = gateway.transaction.sale({
            "amount": str(round(withdrawal_data.amount, 2)),
            "payment_method_token": withdrawal_data.bank_account_token,
            "options": {
                "submit_for_settlement": True,
                "store_in_vault_on_success": False
            }
        })
        
        if result.is_success:
            return {
                "success": True,
                "transaction": {
                    "id": result.transaction.id,
                    "amount": result.transaction.amount,
                    "status": result.transaction.status
                }
            }
        else:
            return {
                "success": False,
                "message": result.message,
                "errors": [{"code": error.code, "message": error.message} for error in result.errors.deep_errors] if result.errors else []
            }
            
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing withdrawal: {str(e)}"
        )