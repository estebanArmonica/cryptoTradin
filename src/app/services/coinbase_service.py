import os, asyncio, logging
from cdp import CdpClient
from dotenv import load_dotenv
from typing import Dict, List, Optional

# Cargamos las variables de entorno desde el archivo .env
load_dotenv()

class CoinbaseService:
    def __init__(self):
        self.client = None
        self.logger = logging.getLogger(__name__)
        self._initialized = False
        self._initializing = False

    async def initialize(self):
        """
        Inicializa el cliente de Coinbase CDP
        """
        if self._initialized:
            return True
        
        if self._initializing:
            # Esperamos si ya está inicializado
            for i in range(10):
                await asyncio.sleep(0.1)
                if self._initialized:
                    return True
            return False

        self._initializing = True

        try:
            self.api_key_id = os.getenv("COINBASE_API_KEY_ID")
            self.api_key_secret = os.getenv("COINBASE_SECRET_KEY") 
            self.wallet_secret = os.getenv("COINBASE_WALLET_SECRET")
            
            if not all([self.api_key_id, self.api_key_secret, self.wallet_secret]):
                self.logger.error("❌ Missing Coinbase environment variables")
                self._initializing = False
                return False
            
            # Testeamos la conexión creando un cliente
            async with self._get_client() as client:
                if client:
                    self._initialized = True
                    self._initializing = False
                    self.logger.info("✅ Coinbase CDP client initialized successfully.")
                    return True
                else:
                    self._initializing = False
                    return False
                
            #self.logger.info("✅ Coinbase CDP client configuration loaded successfully.")
            #return True
        except Exception as e:
            self.logger.error(f"❌ Error initializing Coinbase CDP client: {e}")
            self._initializing = False
            return False
        
    def _get_client(self):
        """
        Crea y retorna una nueva instancia de CdpClient con la configuración
        """
        try:
            if not all([self.api_key_id, self.api_key_secret, self.wallet_secret]):
                raise Exception('Coinbase credentials not initialized')
            
            return CdpClient(
                api_key_id=self.api_key_id,
                api_key_secret=self.api_key_secret,
                wallet_secret=self.wallet_secret
            )
        except Exception as e:
            self.logger.error(f"❌ Error creating CdpClient instance: {e}")
            raise

    async def _ensure_initialized(self):
        """Asegura que el servicio esté inicializado antes de cualquier operación"""
        if not self._initialized:
            success = await self.initialize()
            if not success:
                raise Exception('Coinbase service not initialized')
        
    async def create_evm_account(self, name: Optional[str] = None):
        """
            Crea una nueva cuenta EVM
        """
        try:
            await self._ensure_initialized()
            async with self._get_client() as cdp:
                account = await cdp.evm.create_account()

                # Verificamos si el objeto account tiene nombre
                account_name = name or getattr(f"EVM_Account_{account.address[-8:]}")

                # si permite asignar nombre al crear
                try:
                    if hasattr(account, 'name'):
                        account.name = name
                except:
                    pass # sinno se puede asignar nombre, continua

                account_data = {
                    "address": account.address,
                    "name": account_name,
                    "type": "EVM",
                    "create_at": asyncio.get_event_loop().time()
                }

                self.logger.info(f"✅ EVM account created: {account.address} with name: {account_name}")
                return {"success": True, "account": account_data}
        except Exception as e:
            self.logger.error(f"❌ Error creating EVM account: {e}")
            return {"success": False, "error": str(e)}
        
    async def import_evm_account(self, private_key: str, name: Optional[str] = None):
        """
            Importta una cuenta EVM existente
        """

        try:
            await self._ensure_initialized()
            async with self._get_client() as cdp:
                account = await cdp.evm.import_account(
                    private_key=private_key,
                    name=name or "Imported_EVM_Account"
                )

                account_data = {
                    "address": account.address,
                    "name": account.name,
                    "type": "EVM",
                    "imported": True
                }

                self.logger.info(f"✅ EVM account imported: {account.address}")
                return {"success": True, "account": account_data}
        except Exception as e:
            self.logger.error(f"❌ Error importing EVM account: {e}")
            return {"success": False, "error": str(e)}
        
    async def create_solana_account(self, name: Optional[str] = None):
        """
            Crea una nueva cuenta Solana
        """

        try:
            await self._ensure_initialized()
            async with self._get_client() as cdp:
                account = await cdp.solana.create_account()

                account_data = {
                    "address": account.address,
                    "name": name or f"Solana_Account_{account.address[-8:]}",
                    "type": "Solana",
                    "create_at": asyncio.get_event_loop().time()
                }

                self.logger.info(f"✅ Solana account created: {account.address}")
                return {"success": True, "account": account_data}
        except Exception as e:
            self.logger.error(f"❌ Error creating Solana account: {e}")
            return {"success": False, "error": str(e)}
        
    async def import_solana_account(self, private_key: str, name: Optional[str] = None):
        """
            Importta una cuenta Solana existente
        """

        try:
            await self._ensure_initialized()
            async with self._get_client() as cdp:
                account = await cdp.solana.import_account(
                    private_key=private_key,
                    name=name or "Imported_Solana_Account"
                )

                account_data = {
                    "address": account.address,
                    "name": account.name,
                    "type": "Solana",
                    "imported": True
                }

                self.logger.info(f"✅ Solana account imported: {account.address}")
                return {"success": True, "account": account_data}
        except Exception as e:
            self.logger.error(f"❌ Error importing Solana account: {e}")
            return {"success": False, "error": str(e)}
        
    async def get_or_create_evm_account(self):
        """Obtiene o crea una cuenta EVM"""
        try:
            await self._ensure_initialized()
            async with self._get_client() as cdp:
                account = await cdp.evm.get_or_create_account()

                account_data = {
                    "address": account.address,
                    "name": getattr(account, "name", "Default_EVM_Account"),
                    "type": "EVM",
                    "exists": True
                }

                return {"success": True, "account": account_data}
        except Exception as e:
            self.logger.error(f"❌ Error getting/creating EVM account: {e}")
            return {"success": False, "error": str(e)}
        
    async def get_or_create_solana_account(self):
        """Obtiene o crea una cuenta Solana"""
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
        
    async def export_evm_account(self, name: Optional[str] = None, address: Optional[str] = None):
        """Exporta la clave privada de una cuenta EVM"""
        try:
            await self._ensure_initialized()
            async with self._get_client() as cdp:
                if name:
                    private_key = await cdp.evm.export_account(name=name)
                elif address:
                    private_key = await cdp.evm.export_account(address=address)
                else:
                    return {"success": False, "error": "Se requiere name o address"}
                
                return {"success": True, "private_key": private_key}
                
        except Exception as e:
            self.logger.error(f"❌ Error exporting EVM account: {e}")
            return {"success": False, "error": str(e)}
        
    async def export_solana_account(self, name: Optional[str] = None, address: Optional[str] = None):
        """Exporta la clave privada de una cuenta Solana"""
        try:
            await self._ensure_initialized()
            async with self._get_client() as cdp:
                if name:
                    private_key = await cdp.solana.export_account(name=name)
                elif address:
                    private_key = await cdp.solana.export_account(address=address)
                else:
                    return {"success": False, "error": "Se requiere name o address"}
                
                return {"success": True, "private_key": private_key}
                
        except Exception as e:
            self.logger.error(f"❌ Error exporting Solana account: {e}")
            return {"success": False, "error": str(e)}
        
    async def create_smart_account(self, name: str, owner_address: str):
        """Crea una cuenta inteligente EVM"""
        try:
            await self._ensure_initialized()
            async with self._get_client() as cdp:
                # Primero necesitamos el objeto account del owner
                owner_account = await cdp.evm.get_or_create_account()
                
                smart_account = await cdp.evm.get_or_create_smart_account(
                    name=name, 
                    owner=owner_account
                )
                
                account_data = {
                    "address": smart_account.address,
                    "name": name,
                    "type": "Smart_Account",
                    "owner": owner_address,
                    "is_smart_account": True
                }
                
                self.logger.info(f"✅ Smart account created: {smart_account.address}")
                return {"success": True, "account": account_data}
        except Exception as e:
            self.logger.error(f"❌ Error creating smart account: {e}")
            return {"success": False, "error": str(e)}
        
    async def test_connection(self):
        """ Prueba la conexión con Coinbase CDP"""
        try:
            success = await self.initialize()
            if not success:
                return {
                    "success": False, 
                    "error": "Failed to initialize Coinbase service"
                }
            
            async with self._get_client() as cdp:
                # Intentamos una operacion simple como listar cuentas
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
                        "success": True,  # La conexión está bien pero no hay cuentas
                        "message": f"Conexión establecida pero error en operación: {str(e)}",
                        "account_address": None
                    }
        except Exception as e:
            self.logger.error(f"❌ Error testing connection: {e}")
            return {
                "success": False, 
                "error": f"Error de conexión: {str(e)}"
            }
        
# Instancia global del servicio
coinbase_service = CoinbaseService()
