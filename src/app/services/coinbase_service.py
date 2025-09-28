import os
import asyncio
import logging
import base64
from typing import Dict, List, Optional, Any
from decimal import Decimal

from cdp import CdpClient
from dotenv import load_dotenv

# Para transacciones con EVM
from web3 import Web3
from web3.exceptions import TransactionNotFound

# Para transacciones con Solana
from solana.rpc.api import Client as SolanaClient
from solana.rpc.types import TxOpts
from solders.pubkey import Pubkey as PublicKey
from solders.system_program import TransferParams, transfer
from solders.message import Message
from cdp.evm_transaction_types import TransactionRequestEIP1559

# Cargamos las variables de entorno
load_dotenv()

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


class CoinbaseService:
    """
    Servicio para interactuar con Coinbase CDP con mejores prácticas.
    """
    
    def __init__(self):
        self.client = None
        self.logger = logging.getLogger(__name__)
        self._initialized = False
        self._initializing = False
        self._lock = asyncio.Lock()

        # Configuración centralizada de redes
        self.networks_config = {
            "evm": {
                "base-sepolia": {
                    "rpc_url": "https://sepolia.base.org",
                    "explorer": "https://sepolia.basescan.org/tx/",
                    "faucet_tokens": ["eth"],
                    "chain_id": 84532
                }
            },
            "solana": {
                "devnet": {
                    "rpc_url": "https://api.devnet.solana.com",
                    "explorer": "https://solscan.io/tx/",
                    "faucet_tokens": ["sol"],
                }
            }
        }

    async def initialize(self) -> bool:
        """
        Inicializa el cliente de Coinbase CDP con manejo seguro de concurrencia.
        """
        async with self._lock:
            if self._initialized:
                return True
            
            if self._initializing:
                # Esperar si ya se está inicializando
                for _ in range(30):  # 3 segundos máximo
                    await asyncio.sleep(0.1)
                    if self._initialized:
                        return True
                return False

            self._initializing = True

            try:
                # Validar variables de entorno
                self.api_key_id = os.getenv("COINBASE_API_KEY_ID")
                self.api_key_secret = os.getenv("COINBASE_SECRET_KEY") 
                self.wallet_secret = os.getenv("COINBASE_WALLET_SECRET")
                
                missing_vars = []
                if not self.api_key_id:
                    missing_vars.append("COINBASE_API_KEY_ID")
                if not self.api_key_secret:
                    missing_vars.append("COINBASE_SECRET_KEY")
                if not self.wallet_secret:
                    missing_vars.append("COINBASE_WALLET_SECRET")
                
                if missing_vars:
                    self.logger.error(f"❌ Missing environment variables: {', '.join(missing_vars)}")
                    return False

                # Testear conexión creando cliente
                async with self._get_client() as client:
                    if client:
                        self._initialized = True
                        self.logger.info("✅ Coinbase CDP client initialized successfully")
                        return True
                    else:
                        self.logger.error("❌ Failed to create CDP client")
                        return False
                        
            except Exception as e:
                self.logger.error(f"❌ Error initializing Coinbase CDP client: {e}")
                return False
            finally:
                self._initializing = False

    def _get_client(self) -> CdpClient:
        """
        Crea y retorna una nueva instancia de CdpClient.
        """
        try:
            return CdpClient(
                api_key_id=self.api_key_id,
                api_key_secret=self.api_key_secret,
                wallet_secret=self.wallet_secret
            )
        except Exception as e:
            self.logger.error(f"❌ Error creating CdpClient: {e}")
            raise

    async def _ensure_initialized(self) -> None:
        """Asegura que el servicio esté inicializado antes de operaciones."""
        if not self._initialized:
            success = await self.initialize()
            if not success:
                raise Exception("Coinbase service not initialized")

    # =========================================================================
    # MÉTODOS PARA CUENTAS EVM
    # =========================================================================

    async def create_evm_account(self, name: Optional[str] = None) -> Dict[str, Any]:
        """
        Crea una nueva cuenta EVM con nombre opcional.
        """
        try:
            await self._ensure_initialized()
            
            async with self._get_client() as cdp:
                if name:
                    # Validar nombre antes de crear
                    if not self._validate_account_name(name):
                        return {
                            "success": False, 
                            "error": "Nombre inválido. Debe tener 2-36 caracteres alfanuméricos y guiones"
                        }
                    
                    account = await cdp.evm.get_or_create_account(name=name)
                else:
                    account = await cdp.evm.create_account()
                    name = f"EVM_Account_{account.address[-8:]}"

                account_data = {
                    "address": account.address,
                    "name": name,
                    "type": "EVM",
                    "created_at": asyncio.get_event_loop().time(),
                    "is_named": bool(name)
                }

                self.logger.info(f"✅ EVM account created: {account.address} with name: {name}")
                return {"success": True, "account": account_data}
                
        except Exception as e:
            self.logger.error(f"❌ Error creating EVM account: {e}")
            return {"success": False, "error": str(e)}

    async def import_evm_account(self, private_key: str, name: Optional[str] = None) -> Dict[str, Any]:
        """
        Importa una cuenta EVM existente.
        """
        try:
            await self._ensure_initialized()
            
            # Validar formato de private key
            if not self._validate_private_key(private_key):
                return {"success": False, "error": "Formato de clave privada inválido"}

            async with self._get_client() as cdp:
                account_name = name or f"Imported_EVM_{private_key[-8:]}"
                
                account = await cdp.evm.import_account(
                    private_key=private_key,
                    name=account_name
                )

                account_data = {
                    "address": account.address,
                    "name": account.name,
                    "type": "EVM",
                    "imported": True,
                    "created_at": asyncio.get_event_loop().time()
                }

                self.logger.info(f"✅ EVM account imported: {account.address}")
                return {"success": True, "account": account_data}
                
        except Exception as e:
            self.logger.error(f"❌ Error importing EVM account: {e}")
            return {"success": False, "error": str(e)}

    async def get_evm_account(self, address: Optional[str] = None, name: Optional[str] = None) -> Dict[str, Any]:
        """
        Obtiene una cuenta EVM por dirección o nombre.
        """
        try:
            await self._ensure_initialized()
            
            if not address and not name:
                return {"success": False, "error": "Se requiere address o name"}

            async with self._get_client() as cdp:
                if address:
                    # Validar formato de dirección
                    if not self._validate_evm_address(address):
                        return {"success": False, "error": "Formato de dirección EVM inválido"}
                    account = await cdp.evm.get_account(address=address)
                else:
                    account = await cdp.evm.get_account(name=name)

                account_data = {
                    "address": account.address,
                    "name": getattr(account, 'name', 'Unnamed'),
                    "type": "EVM",
                    "policies": getattr(account, 'policies', [])
                }

                return {"success": True, "account": account_data}
                
        except Exception as e:
            self.logger.error(f"❌ Error getting EVM account: {e}")
            return {"success": False, "error": str(e)}

    async def list_evm_accounts(self, page_token: Optional[str] = None) -> Dict[str, Any]:
        """
        Lista todas las cuentas EVM con paginación.
        """
        try:
            await self._ensure_initialized()
            
            async with self._get_client() as cdp:
                response = await cdp.evm.list_accounts(page_token=page_token)
                
                accounts = []
                for account in response.accounts:
                    accounts.append({
                        "address": account.address,
                        "name": getattr(account, 'name', 'Unnamed'),
                        "type": "EVM",
                        "policies": getattr(account, 'policies', [])
                    })

                return {
                    "success": True,
                    "accounts": accounts,
                    "pagination": {
                        "next_page_token": response.next_page_token,
                        "has_more": bool(response.next_page_token)
                    }
                }
                
        except Exception as e:
            self.logger.error(f"❌ Error listing EVM accounts: {e}")
            return {"success": False, "error": str(e)}

    async def update_evm_account(self, address: str, name: Optional[str] = None, 
                               account_policy: Optional[str] = None) -> Dict[str, Any]:
        """
        Actualiza una cuenta EVM (nombre o políticas).
        """
        try:
            await self._ensure_initialized()
            
            if not self._validate_evm_address(address):
                return {"success": False, "error": "Formato de dirección EVM inválido"}

            update_data = {}
            if name:
                if not self._validate_account_name(name):
                    return {
                        "success": False, 
                        "error": "Nombre inválido. Debe tener 2-36 caracteres alfanuméricos y guiones"
                    }
                update_data["name"] = name
            
            if account_policy:
                update_data["account_policy"] = account_policy

            if not update_data:
                return {"success": False, "error": "No se proporcionaron datos para actualizar"}

            async with self._get_client() as cdp:
                updated_account = await cdp.evm.update_account(
                    address=address,
                    update=update_data
                )

                account_data = {
                    "address": updated_account.address,
                    "name": getattr(updated_account, 'name', 'Unnamed'),
                    "type": "EVM",
                    "policies": getattr(updated_account, 'policies', [])
                }

                self.logger.info(f"✅ EVM account updated: {address}")
                return {"success": True, "account": account_data}
                
        except Exception as e:
            self.logger.error(f"❌ Error updating EVM account: {e}")
            return {"success": False, "error": str(e)}

    async def export_evm_account(self, name: Optional[str] = None, 
                               address: Optional[str] = None) -> Dict[str, Any]:
        """
        Exporta la clave privada de una cuenta EVM.
        """
        try:
            await self._ensure_initialized()
            
            if not name and not address:
                return {"success": False, "error": "Se requiere name o address"}

            async with self._get_client() as cdp:
                if name:
                    private_key = await cdp.evm.export_account(name=name)
                else:
                    if not self._validate_evm_address(address):
                        return {"success": False, "error": "Formato de dirección EVM inválido"}
                    private_key = await cdp.evm.export_account(address=address)

                # Registrar de forma segura (sin mostrar clave completa)
                self.logger.info(f"✅ EVM account exported: {address or name}")
                
                return {
                    "success": True, 
                    "private_key": private_key,
                    "address": address,
                    "name": name
                }
                
        except Exception as e:
            self.logger.error(f"❌ Error exporting EVM account: {e}")
            return {"success": False, "error": str(e)}

    async def get_or_create_evm_account(self, name: Optional[str] = None) -> Dict[str, Any]:
        """
        Obtiene o crea una cuenta EVM por defecto - CORREGIDO
        """
        try:
            await self._ensure_initialized()
            
            async with self._get_client() as cdp:
                # ✅ CORREGIDO: Manejar correctamente get_or_create_account
                try:
                    # Primero intentar obtener una cuenta existente si hay nombre
                    if name:
                        account = await cdp.evm.get_account(name=name)
                    else:
                        # Si no hay nombre, intentar obtener cualquier cuenta existente
                        accounts = await cdp.evm.list_accounts()
                        if accounts and len(accounts.accounts) > 0:
                            account = accounts.accounts[0]
                        else:
                            # Si no hay cuentas, crear una nueva
                            account = await cdp.evm.create_account()
                except Exception as e:
                    # Si falla al obtener cuenta existente, crear una nueva
                    self.logger.warning(f"Error obteniendo cuenta existente, creando nueva: {e}")
                    account = await cdp.evm.create_account()

                # Asignar nombre si se proporcionó y la cuenta no lo tiene
                if name and not getattr(account, 'name', None):
                    try:
                        await cdp.evm.update_account(
                            address=account.address,
                            update={"name": name}
                        )
                        account.name = name
                    except Exception as e:
                        self.logger.warning(f"No se pudo asignar nombre a la cuenta: {e}")

                account_data = {
                    "address": account.address,
                    "name": getattr(account, 'name', name or f"EVM_Account_{account.address[-8:]}"),
                    "type": "EVM",
                    "exists": True,
                    "created_at": asyncio.get_event_loop().time()
                }

                self.logger.info(f"✅ EVM account obtained/created: {account_data['address']}")
                return {"success": True, "account": account_data}
                
        except Exception as e:
            self.logger.error(f"❌ Error getting/creating EVM account: {e}")
            return {"success": False, "error": str(e)}
    # =========================================================================
    # MÉTODOS PARA CUENTAS SOLANA
    # =========================================================================

    async def create_solana_account(self, name: Optional[str] = None) -> Dict[str, Any]:
        """
        Crea una nueva cuenta Solana con nombre opcional.
        """
        try:
            await self._ensure_initialized()
            
            async with self._get_client() as cdp:
                if name:
                    if not self._validate_account_name(name):
                        return {
                            "success": False, 
                            "error": "Nombre inválido. Debe tener 2-36 caracteres alfanuméricos y guiones"
                        }
                    
                    account = await cdp.solana.get_or_create_account(name=name)
                else:
                    account = await cdp.solana.create_account()
                    name = f"Solana_Account_{account.address[-8:]}"

                account_data = {
                    "address": account.address,
                    "name": name,
                    "type": "Solana",
                    "created_at": asyncio.get_event_loop().time(),
                    "is_named": bool(name)
                }

                self.logger.info(f"✅ Solana account created: {account.address} with name: {name}")
                return {"success": True, "account": account_data}
                
        except Exception as e:
            self.logger.error(f"❌ Error creating Solana account: {e}")
            return {"success": False, "error": str(e)}

    async def import_solana_account(self, private_key: str, name: Optional[str] = None) -> Dict[str, Any]:
        """
        Importa una cuenta Solana existente.
        """
        try:
            await self._ensure_initialized()
            
            # Validar formato de private key
            if not self._validate_private_key(private_key):
                return {"success": False, "error": "Formato de clave privada inválido"}

            async with self._get_client() as cdp:
                account_name = name or f"Imported_Solana_{private_key[-8:]}"
                
                account = await cdp.solana.import_account(
                    private_key=private_key,
                    name=account_name
                )

                account_data = {
                    "address": account.address,
                    "name": account.name,
                    "type": "Solana",
                    "imported": True,
                    "created_at": asyncio.get_event_loop().time()
                }

                self.logger.info(f"✅ Solana account imported: {account.address}")
                return {"success": True, "account": account_data}
                
        except Exception as e:
            self.logger.error(f"❌ Error importing Solana account: {e}")
            return {"success": False, "error": str(e)}

    async def get_solana_account(self, address: Optional[str] = None, 
                               name: Optional[str] = None) -> Dict[str, Any]:
        """
        Obtiene una cuenta Solana por dirección o nombre.
        """
        try:
            await self._ensure_initialized()
            
            if not address and not name:
                return {"success": False, "error": "Se requiere address o name"}

            async with self._get_client() as cdp:
                if address:
                    # Validar formato de dirección Solana
                    if not self._validate_solana_address(address):
                        return {"success": False, "error": "Formato de dirección Solana inválido"}
                    account = await cdp.solana.get_account(address=address)
                else:
                    account = await cdp.solana.get_account(name=name)

                account_data = {
                    "address": account.address,
                    "name": getattr(account, 'name', 'Unnamed'),
                    "type": "Solana",
                    "policies": getattr(account, 'policies', [])
                }

                return {"success": True, "account": account_data}
                
        except Exception as e:
            self.logger.error(f"❌ Error getting Solana account: {e}")
            return {"success": False, "error": str(e)}

    async def list_solana_accounts(self, page_token: Optional[str] = None) -> Dict[str, Any]:
        """
        Lista todas las cuentas Solana con paginación.
        """
        try:
            await self._ensure_initialized()
            
            async with self._get_client() as cdp:
                response = await cdp.solana.list_accounts(page_token=page_token)
                
                accounts = []
                for account in response.accounts:
                    accounts.append({
                        "address": account.address,
                        "name": getattr(account, 'name', 'Unnamed'),
                        "type": "Solana",
                        "policies": getattr(account, 'policies', [])
                    })

                return {
                    "success": True,
                    "accounts": accounts,
                    "pagination": {
                        "next_page_token": response.next_page_token,
                        "has_more": bool(response.next_page_token)
                    }
                }
                
        except Exception as e:
            self.logger.error(f"❌ Error listing Solana accounts: {e}")
            return {"success": False, "error": str(e)}

    async def update_solana_account(self, address: str, name: Optional[str] = None,
                                  account_policy: Optional[str] = None) -> Dict[str, Any]:
        """
        Actualiza una cuenta Solana (nombre o políticas).
        """
        try:
            await self._ensure_initialized()
            
            if not self._validate_solana_address(address):
                return {"success": False, "error": "Formato de dirección Solana inválido"}

            update_data = {}
            if name:
                if not self._validate_account_name(name):
                    return {
                        "success": False, 
                        "error": "Nombre inválido. Debe tener 2-36 caracteres alfanuméricos y guiones"
                    }
                update_data["name"] = name
            
            if account_policy:
                update_data["account_policy"] = account_policy

            if not update_data:
                return {"success": False, "error": "No se proporcionaron datos para actualizar"}

            async with self._get_client() as cdp:
                updated_account = await cdp.solana.update_account(
                    address=address,
                    update=update_data
                )

                account_data = {
                    "address": updated_account.address,
                    "name": getattr(updated_account, 'name', 'Unnamed'),
                    "type": "Solana",
                    "policies": getattr(updated_account, 'policies', [])
                }

                self.logger.info(f"✅ Solana account updated: {address}")
                return {"success": True, "account": account_data}
                
        except Exception as e:
            self.logger.error(f"❌ Error updating Solana account: {e}")
            return {"success": False, "error": str(e)}

    async def export_solana_account(self, name: Optional[str] = None, 
                                  address: Optional[str] = None) -> Dict[str, Any]:
        """
        Exporta la clave privada de una cuenta Solana.
        """
        try:
            await self._ensure_initialized()
            
            if not name and not address:
                return {"success": False, "error": "Se requiere name o address"}

            async with self._get_client() as cdp:
                if name:
                    private_key = await cdp.solana.export_account(name=name)
                else:
                    if not self._validate_solana_address(address):
                        return {"success": False, "error": "Formato de dirección Solana inválido"}
                    private_key = await cdp.solana.export_account(address=address)

                self.logger.info(f"✅ Solana account exported: {address or name}")
                
                return {
                    "success": True, 
                    "private_key": private_key,
                    "address": address,
                    "name": name
                }
                
        except Exception as e:
            self.logger.error(f"❌ Error exporting Solana account: {e}")
            return {"success": False, "error": str(e)}

    async def get_or_create_solana_account(self) -> Dict[str, Any]:
        """
        Obtiene o crea una cuenta Solana por defecto.
        """
        try:
            await self._ensure_initialized()
            
            async with self._get_client() as cdp:
                account = await cdp.solana.get_or_create_account()
                
                account_data = {
                    "address": account.address,
                    "name": getattr(account, 'name', 'Default_Solana_Account'),
                    "type": "Solana",
                    "exists": True
                }
                
                return {"success": True, "account": account_data}
                
        except Exception as e:
            self.logger.error(f"❌ Error getting/creating Solana account: {e}")
            return {"success": False, "error": str(e)}

    # =========================================================================
    # MÉTODOS PARA CUENTAS INTELIGENTES
    # =========================================================================

    async def create_smart_account(self, name: str, owner_address: str) -> Dict[str, Any]:
        """
        Crea una cuenta inteligente EVM.
        """
        try:
            await self._ensure_initialized()
            
            if not self._validate_account_name(name):
                return {
                    "success": False, 
                    "error": "Nombre inválido. Debe tener 2-36 caracteres alfanuméricos y guiones"
                }

            if not self._validate_evm_address(owner_address):
                return {"success": False, "error": "Formato de dirección owner inválido"}

            async with self._get_client() as cdp:
                # Obtener la cuenta del owner
                owner_account = await cdp.evm.get_account(address=owner_address)
                
                smart_account = await cdp.evm.get_or_create_smart_account(
                    name=name, 
                    owner=owner_account
                )
                
                account_data = {
                    "address": smart_account.address,
                    "name": name,
                    "type": "Smart_Account",
                    "owner": owner_address,
                    "is_smart_account": True,
                    "created_at": asyncio.get_event_loop().time()
                }
                
                self.logger.info(f"✅ Smart account created: {smart_account.address}")
                return {"success": True, "account": account_data}
                
        except Exception as e:
            self.logger.error(f"❌ Error creating smart account: {e}")
            return {"success": False, "error": str(e)}

    async def get_smart_account(self, owner_address: str) -> Dict[str, Any]:
        """
        Obtiene la cuenta inteligente asociada a un owner.
        """
        try:
            await self._ensure_initialized()
            
            if not self._validate_evm_address(owner_address):
                return {"success": False, "error": "Formato de dirección owner inválido"}

            async with self._get_client() as cdp:
                owner_account = await cdp.evm.get_account(address=owner_address)
                smart_account = await cdp.evm.get_or_create_smart_account(owner=owner_account)
                
                account_data = {
                    "address": smart_account.address,
                    "name": getattr(smart_account, 'name', 'Unnamed'),
                    "type": "Smart_Account",
                    "owner": owner_address,
                    "is_smart_account": True
                }
                
                return {"success": True, "account": account_data}
                
        except Exception as e:
            self.logger.error(f"❌ Error getting smart account: {e}")
            return {"success": False, "error": str(e)}

    # =========================================================================
    # MÉTODOS PARA TRANSACCIONES EVM
    # =========================================================================

    async def send_evm_transaction(self, address: str, to_address: str, value: float, 
                                 network: str = "base-sepolia", token: str = "eth") -> Dict[str, Any]:
        """
        Envía una transacción EVM.
        """
        try:
            await self._ensure_initialized()
            
            # Validaciones
            if not self._validate_evm_address(address):
                return {"success": False, "error": "Formato de dirección from inválido"}
            
            if not self._validate_evm_address(to_address):
                return {"success": False, "error": "Formato de dirección to inválido"}
            
            if value <= 0:
                return {"success": False, "error": "El valor debe ser mayor a 0"}

            # Obtener configuración de red
            network_config = self.networks_config["evm"].get(network)
            if not network_config:
                return {"success": False, "error": f"Red {network} no soportada"}

            # Configurar Web3
            w3 = Web3(Web3.HTTPProvider(network_config["rpc_url"]))
            
            async with self._get_client() as cdp:
                # Solicitar faucet si es necesario
                try:
                    faucet_hash = await cdp.evm.request_faucet(
                        network=network,
                        token=token,
                        address=address
                    )
                    
                    if faucet_hash:
                        self.logger.info(f"🔄 Waiting for faucet transaction: {faucet_hash}")
                        receipt = w3.eth.wait_for_transaction_receipt(faucet_hash)
                        self.logger.info(f"✅ Faucet funds received for: {address}")
                except Exception as faucet_error:
                    self.logger.warning(f"⚠️ Faucet request failed: {faucet_error}")

                # Enviar transacción
                tx_hash = await cdp.evm.send_transaction(
                    address=address,
                    transaction=TransactionRequestEIP1559(
                        to=to_address,
                        value=w3.to_wei(value, 'ether'),
                    ),
                    network=network,
                )

                explorer_url = f"{network_config['explorer']}{tx_hash}"
                self.logger.info(f"✅ EVM transaction sent: {tx_hash}")

                return {
                    "success": True,
                    "transaction_hash": tx_hash,
                    "explorer_url": explorer_url,
                    "from_address": address,
                    "to_address": to_address,
                    "value": value,
                    "network": network,
                    "token": token
                }
                
        except Exception as e:
            self.logger.error(f"❌ Error sending EVM transaction: {e}")
            return {"success": False, "error": str(e)}

    async def request_evm_faucet(self, address: str, network: str = "base-sepolia", 
                               token: str = "eth") -> Dict[str, Any]:
        """
        Solicita fondos del faucet para una cuenta EVM.
        """
        try:
            await self._ensure_initialized()
            
            if not self._validate_evm_address(address):
                return {"success": False, "error": "Formato de dirección inválido"}
            
            network_config = self.networks_config["evm"].get(network)
            if not network_config:
                return {"success": False, "error": f"Red {network} no soportada"}

            w3 = Web3(Web3.HTTPProvider(network_config["rpc_url"]))

            async with self._get_client() as cdp:
                faucet_hash = await cdp.evm.request_faucet(
                    address=address, 
                    network=network, 
                    token=token
                )

                if faucet_hash:
                    self.logger.info(f"🔄 Waiting for faucet transaction: {faucet_hash}")
                    receipt = w3.eth.wait_for_transaction_receipt(faucet_hash)
                    self.logger.info(f"✅ Faucet funds received for {address} on {network}")
                    
                    return {
                        "success": True,
                        "transaction_hash": faucet_hash,
                        "block_number": receipt.blockNumber,
                        "network": network,
                        "token": token
                    }
                else:
                    return {"success": False, "error": "Faucet request failed"}
                    
        except Exception as e:
            self.logger.error(f"❌ Error requesting EVM faucet: {e}")
            return {"success": False, "error": str(e)}

    # =========================================================================
    # MÉTODOS PARA TRANSACCIONES SOLANA
    # =========================================================================

    async def send_solana_transaction(self, address: str, to_address: str, amount: float, 
                                    network: str = "devnet") -> Dict[str, Any]:
        """
        Envía una transacción Solana.
        """
        try:
            await self._ensure_initialized()
            
            # Validaciones
            if not self._validate_solana_address(address):
                return {"success": False, "error": "Formato de dirección from inválido"}
            
            if not self._validate_solana_address(to_address):
                return {"success": False, "error": "Formato de dirección to inválido"}
            
            if amount <= 0:
                return {"success": False, "error": "El amount debe ser mayor a 0"}

            network_config = self.networks_config["solana"].get(network)
            if not network_config:
                return {"success": False, "error": f"Red {network} no soportada"}

            # Configurar cliente Solana
            connection = SolanaClient(network_config["rpc_url"])

            async with self._get_client() as cdp:
                # Solicitar faucet si es necesario
                await cdp.solana.request_faucet(address, token="sol")
                
                # Esperar a que los fondos estén disponibles
                await self._wait_for_solana_balance(connection, address)
                
                # Enviar transacción
                tx_result = await self._send_solana_transaction_internal(
                    cdp, connection, address, to_address, amount, network
                )
                
                return tx_result
                
        except Exception as e:
            self.logger.error(f"❌ Error sending Solana transaction: {e}")
            return {"success": False, "error": str(e)}

    async def request_solana_faucet(self, address: str, network: str = "devnet") -> Dict[str, Any]:
        """
        Solicita fondos del faucet para una cuenta Solana.
        """
        try:
            await self._ensure_initialized()
            
            if not self._validate_solana_address(address):
                return {"success": False, "error": "Formato de dirección inválido"}
            
            network_config = self.networks_config["solana"].get(network)
            if not network_config:
                return {"success": False, "error": f"Red {network} no soportada"}

            connection = SolanaClient(network_config["rpc_url"])
            
            async with self._get_client() as cdp:
                await cdp.solana.request_faucet(address, token="sol")
                
                # Esperar y verificar balance
                await self._wait_for_solana_balance(connection, address)
                
                balance_resp = connection.get_balance(PublicKey.from_string(address))
                balance_sol = balance_resp.value / 1e9

                return {
                    "success": True,
                    "address": address,
                    "balance_sol": balance_sol,
                    "balance_lamports": balance_resp.value,
                    "network": network
                }
                
        except Exception as e:
            self.logger.error(f"❌ Error requesting Solana faucet: {e}")
            return {"success": False, "error": str(e)}

    async def _wait_for_solana_balance(self, connection, address: str, max_attempts: int = 30) -> bool:
        """
        Espera hasta que la cuenta Solana tenga balance.
        """
        balance = 0
        attempts = 0

        while balance == 0 and attempts < max_attempts:
            try:
                balance_resp = connection.get_balance(PublicKey.from_string(address))
                balance = balance_resp.value
                if balance == 0:
                    self.logger.info(f"🔄 Waiting for Solana funds... ({attempts + 1}/{max_attempts})")
                    await asyncio.sleep(2)
                    attempts += 1
                else:
                    self.logger.info(f"✅ Account funded with {balance / 1e9} SOL")
                    return True
            except Exception as e:
                self.logger.warning(f"⚠️ Error checking balance: {e}")
                await asyncio.sleep(2)
                attempts += 1

        if balance == 0:
            raise ValueError("Account not funded after multiple attempts")
        return True

    async def _send_solana_transaction_internal(self, cdp, connection, from_address: str, 
                                              to_address: str, amount: float, network: str) -> Dict[str, Any]:
        """
        Envía la transacción Solana internamente.
        """
        # Convertir a lamports
        lamports_to_send = int(amount * 1e9)
        
        from_pubkey = PublicKey.from_string(from_address)
        to_pubkey = PublicKey.from_string(to_address)

        # Obtener blockhash reciente
        blockhash_resp = connection.get_latest_blockhash()
        blockhash = blockhash_resp.value.blockhash

        # Crear instrucción de transferencia
        transfer_params = TransferParams(
            from_pubkey=from_pubkey,
            to_pubkey=to_pubkey,
            lamports=lamports_to_send,
        )
        transfer_instr = transfer(transfer_params)

        # Crear mensaje
        message = Message.new_with_blockhash(
            [transfer_instr],
            from_pubkey,
            blockhash,
        )

        # Serializar transacción
        sig_count = bytes([1])  # 1 firma
        empty_sig = bytes([0] * 64)  # firma vacía
        message_bytes = bytes(message)
        tx_bytes = sig_count + empty_sig + message_bytes
        serialized_tx = base64.b64encode(tx_bytes).decode("utf-8")

        # Firmar transacción
        signed_tx_response = await cdp.solana.sign_transaction(
            from_address,
            transaction=serialized_tx,
        )

        # Decodificar y enviar transacción
        decoded_signed_tx = base64.b64decode(signed_tx_response.signed_transaction)

        self.logger.info("🔄 Sending Solana transaction...")
        tx_resp = connection.send_raw_transaction(
            decoded_signed_tx,
            opts=TxOpts(skip_preflight=False, preflight_commitment="processed"),
        )
        signature = tx_resp.value

        # Esperar confirmación
        self.logger.info("🔄 Waiting for transaction confirmation...")
        confirmation = connection.confirm_transaction(signature, commitment="processed")

        if hasattr(confirmation, "err") and confirmation.err:
            raise ValueError(f"Transaction failed: {confirmation.err}")

        explorer_url = f"{self.networks_config['solana'][network]['explorer']}{signature}?cluster=devnet"
        
        self.logger.info(f"✅ Solana transaction sent: {explorer_url}")

        return {
            "success": True,
            "transaction_hash": str(signature),
            "explorer_url": explorer_url,
            "from_address": from_address,
            "to_address": to_address,
            "amount": amount,
            "lamports": lamports_to_send,
            "network": network
        }

    # =========================================================================
    # MÉTODOS DE UTILIDAD
    # =========================================================================

    async def test_connection(self) -> Dict[str, Any]:
        """
        Prueba la conexión con Coinbase CDP.
        """
        try:
            success = await self.initialize()
            if not success:
                return {
                    "success": False, 
                    "error": "Failed to initialize Coinbase service"
                }
            
            async with self._get_client() as cdp:
                # Intentar una operación simple
                try:
                    accounts = await cdp.evm.list_accounts()
                    account_address = accounts[0].address if accounts else "No accounts"
                    
                    return {
                        "success": True,
                        "message": "Conexión con Coinbase CDP establecida correctamente",
                        "account_address": account_address,
                        "timestamp": "2024-01-01T00:00:00Z"
                    }
                except Exception as e:
                    return {
                        "success": True,
                        "message": f"Conexión establecida pero error en operación: {str(e)}",
                        "account_address": None
                    }
        except Exception as e:
            self.logger.error(f"❌ Error testing connection: {e}")
            return {
                "success": False, 
                "error": f"Error de conexión: {str(e)}"
            }

    def _validate_account_name(self, name: str) -> bool:
        """
        Valida que el nombre de la cuenta cumpla con los requisitos de CDP.
        """
        if not name or len(name) < 2 or len(name) > 36:
            return False
        
        # Solo caracteres alfanuméricos y guiones
        if not all(c.isalnum() or c == '-' for c in name):
            return False
            
        return True

    def _validate_private_key(self, private_key: str) -> bool:
        """
        Valida el formato básico de una private key.
        """
        if not private_key:
            return False
        
        # Validación básica - ajustar según el formato esperado
        return len(private_key) >= 64

    def _validate_evm_address(self, address: str) -> bool:
        """
        Valida una dirección EVM.
        """
        try:
            return Web3.is_address(address)
        except:
            return False

    def _validate_solana_address(self, address: str) -> bool:
        """
        Valida una dirección Solana.
        """
        try:
            PublicKey.from_string(address)
            return True
        except:
            return False


# Instancia global del servicio
coinbase_service = CoinbaseService()