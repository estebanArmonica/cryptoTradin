import os, asyncio, logging, time, base64
from cdp import CdpClient
from dotenv import load_dotenv
from typing import Dict, List, Optional

# para transacciones con EVM
from web3 import Web3

# para transacciones con Solana
from solana.rpc.api import Client as SolanaClient
from solana.rpc.types import TxOpts
from solders.pubkey import Pubkey as PublicKey
from solders.system_program import TransferParams, transfer
from solders.message import Message
from cdp.evm_transaction_types import TransactionRequestEIP1559

# Cargamos las variables de entorno desde el archivo .env
load_dotenv()

class CoinbaseService:
    def __init__(self):
        self.client = None
        self.logger = logging.getLogger(__name__)
        self._initialized = False
        self._initializing = False

        # configuración de redes
        self.networks_config = {
            "evm": {
                "base-sepolia": {
                    "rpc_url": "https://sepolia.base.org",
                    "explorer": "https://sepolia.basescan.org/tx/",
                    "faucet_tokens": ["eth"],
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
            Importa una cuenta EVM existente
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
            Importa una cuenta Solana existente
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
        
    # =========================================================================
    # MÉTODOS PARA ENVIAR TRANSACCIONES EVM
    # =========================================================================
    async def send_evm_transaction(self, address: str, to_address: str, value: float, network: str = "base-sepolia", token: str = "eth"):
        """
            Envía una transacción EVM
        """
        try:
            await self._ensure_initialized()

            # Configuramos Web3
            w3 = Web3(Web3.HTTPProvider(self.networks_config["evm"][network]["rpc_url"]))

            async with self._get_client() as cdp:
                # Solicitamos fondsd del faucet si es necesario
                faucet_hash = await cdp.evm.request_faucet(
                    network=network,
                    token=token,
                    address=address
                )

                if faucet_hash:
                    Web3.eth.wait_for_transaction_receipt(faucet_hash)
                    self.logger.info(f"✅ Funds received from faucet for address: {address}")

                # Enviamos la transacción
                tx_hash = await cdp.evm.send_transaction(
                    address=address,
                    transaction=TransactionRequestEIP1559(
                        to=to_address,
                        value=w3.to_wei(value, 'ether'),
                    ),
                    network=network,
                )

                explorer_url = f"{self.networks_config['evm'][network]['explorer']}{tx_hash}"
                self.logger.info(f"✅ EVM transaction sent: {tx_hash}")

                return {
                    "success": True,
                    "transaction_hash": tx_hash,
                    "explorer_url": explorer_url,
                    "from_address": address,
                    "to_address": to_address,
                    "value": value,
                    "network": network
                }
        except Exception as e:
            self.logger.error(f"❌ Error sending EVM transaction: {e}")
            return {"success": False, "error": str(e)}
        
    async def request_evm_faucet(self, address: str, network: str = "base-sepolia", token: str = "eth"):
        """
            Solicita fondos del faucet para una cuenta EVM
        """
        try:
            await self._ensure_initialized()
            
            w3 = Web3(Web3.HTTPProvider(self.network_config["evm"][network]["rpc_url"]))

            async with self._get_client() as cdp:
                faucet_hash = await cdp.evm.request_faucet(
                    address=address, 
                    network=network, 
                    token=token
                )

                if faucet_hash:
                    receipt = w3.eth.wait_for_transaction_receipt(faucet_hash)
                    self.logger.info(f"✅ Faucet funds received for {address} on {network}")
                    
                    return {
                        "success": True,
                        "transaction_hash": faucet_hash,
                        "block_number": receipt.blockNumber,
                        "network": network
                    }
                else:
                    return {"success": False, "error": "Faucet request failed"}
        except Exception as e:
            self.logger.error(f"❌ Error requesting EVM faucet: {e}")
            return {"success": False, "error": str(e)}
        
    # =========================================================================
    # MÉTODOS PARA ENVIAR TRANSACCIONES SOLANA
    # =========================================================================
    async def send_solana_transaction(self, address: str, to_address: str, amount: float, network: str = "devnet"):
        """
            Envía una transacción Solana
        """
        try:
            await self._ensure_initialized()
            
            # Configurar cliente Solana
            connection = SolanaClient(self.network_config["solana"][network]["rpc_url"])

            async with self._get_client() as cdp:
                # Solicitar fondos del faucet
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
        
    async def _wait_for_solana_balance(self, connection, address: str, max_attempts: int = 30):
        """
            Espera hasta que la cuenta Solana tenga balance
        """
        balance = 0
        attempts = 0

        while balance == 0 and attempts < max_attempts:
            balance_resp = connection.get_balance(PublicKey.from_string(address))
            balance = balance_resp.value
            if balance == 0:
                self.logger.info("Waiting for Solana funds...")
                await asyncio.sleep(1)
                attempts += 1
            else:
                self.logger.info(f"✅ Account funded with {balance / 1e9} SOL ({balance} lamports)")
                return True   
            
        if balance == 0:
            raise ValueError("Account not funded after multiple attempts")
        
    async def _send_solana_transaction_internal(self, cdp, connection, from_address: str, to_address: str, amount: float, network: str):
        """
            Envía la transacción Solana internamente
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

        self.logger.info("Sending Solana transaction...")
        tx_resp = connection.send_raw_transaction(
            decoded_signed_tx,
            opts=TxOpts(skip_preflight=False, preflight_commitment="processed"),
        )
        signature = tx_resp.value

        # Esperar confirmación
        self.logger.info("Waiting for transaction confirmation...")
        confirmation = connection.confirm_transaction(signature, commitment="processed")

        if hasattr(confirmation, "err") and confirmation.err:
            raise ValueError(f"Transaction failed: {confirmation.err}")

        explorer_url = f"{self.network_config['solana'][network]['explorer']}{signature}?cluster=devnet"
        
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
    
    async def request_solana_faucet(self, address: str, network: str = "devnet"):
        """
            Solicita fondos del faucet para una cuenta Solana
        """
        try:
            await self._ensure_initialized()
            
            connection = SolanaClient(self.network_config["solana"][network]["rpc_url"])
            
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
        
    # =========================================================================
    # GESTIÓN DE CUENTAS EVM
    # =========================================================================
    async def create_evm_account(self, name: Optional[str] = None):
        """
        Crea una nueva cuenta EVM con nombre opcional
        """
        try:
            await self._ensure_initialized()
            async with self._get_client() as cdp:
                if name:
                    # Validar nombre según requisitos de CDP
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
    
    async def get_evm_account(self, address: Optional[str] = None, name: Optional[str] = None):
        """
        Obtiene una cuenta EVM por dirección o nombre
        """
        try:
            await self._ensure_initialized()
            async with self._get_client() as cdp:
                if address:
                    account = await cdp.evm.get_account(address=address)
                elif name:
                    account = await cdp.evm.get_account(name=name)
                else:
                    return {"success": False, "error": "Se requiere address o name"}

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
        
    async def list_evm_accounts(self, page_token: Optional[str] = None):
        """
        Lista todas las cuentas EVM con paginación
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

                result = {
                    "success": True,
                    "accounts": accounts,
                    "next_page_token": response.next_page_token,
                    "has_more": bool(response.next_page_token)
                }

                return result
        except Exception as e:
            self.logger.error(f"❌ Error listing EVM accounts: {e}")
            return {"success": False, "error": str(e)}
        
    async def update_evm_account(self, address: str, name: Optional[str] = None,  account_policy: Optional[str] = None):
        """
        Actualiza una cuenta EVM (nombre o políticas)
        """
        try:
            await self._ensure_initialized()
            async with self._get_client() as cdp:
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

    # =========================================================================
    # CUENTAS INTELIGENTES EVM
    # =========================================================================
    async def create_smart_account(self, name: str, owner_address: str):
        """
        Crea una cuenta inteligente EVM
        """
        try:
            await self._ensure_initialized()
            async with self._get_client() as cdp:
                # Primero obtenemos la cuenta del owner
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
                    "is_smart_account": True
                }
                
                self.logger.info(f"✅ Smart account created: {smart_account.address}")
                return {"success": True, "account": account_data}
        except Exception as e:
            self.logger.error(f"❌ Error creating smart account: {e}")
            return {"success": False, "error": str(e)}
        
    async def get_smart_account(self, owner_address: str):
        """
        Obtiene la cuenta inteligente asociada a un owner
        """
        try:
            await self._ensure_initialized()
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
    # GESTIÓN DE CUENTAS SOLANA - MÉTODOS MEJORADOS
    # =========================================================================
    async def create_solana_account(self, name: Optional[str] = None):
        """
        Crea una nueva cuenta Solana con nombre opcional
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
        
    async def get_solana_account(self, address: Optional[str] = None, name: Optional[str] = None):
        """
        Obtiene una cuenta Solana por dirección o nombre
        """
        try:
            await self._ensure_initialized()
            async with self._get_client() as cdp:
                if address:
                    account = await cdp.solana.get_account(address=address)
                elif name:
                    account = await cdp.solana.get_account(name=name)
                else:
                    return {"success": False, "error": "Se requiere address o name"}

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
        
    async def list_solana_accounts(self, page_token: Optional[str] = None):
        """
        Lista todas las cuentas Solana con paginación
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

                result = {
                    "success": True,
                    "accounts": accounts,
                    "next_page_token": response.next_page_token,
                    "has_more": bool(response.next_page_token)
                }

                return result
        except Exception as e:
            self.logger.error(f"❌ Error listing Solana accounts: {e}")
            return {"success": False, "error": str(e)}
        
    async def update_solana_account(self, address: str, name: Optional[str] = None,  account_policy: Optional[str] = None):
        """
        Actualiza una cuenta Solana (nombre o políticas)
        """
        try:
            await self._ensure_initialized()
            async with self._get_client() as cdp:
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
        
    # =========================================================================
    # MÉTODOS AUXILIARES
    # =========================================================================
    def _validate_account_name(self, name: str) -> bool:
        """
        Valida que el nombre de la cuenta cumpla con los requisitos de CDP
        """
        if len(name) < 2 or len(name) > 36:
            return False
        
        # Solo caracteres alfanuméricos y guiones
        if not all(c.isalnum() or c == '-' for c in name):
            return False
            
        return True
    


# Instancia global del servicio
coinbase_service = CoinbaseService()
