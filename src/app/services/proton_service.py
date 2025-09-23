# app/services/proton_service.py
import aiohttp
import logging
import asyncio
import json
from typing import Dict, List, Any, Optional, Tuple
import os
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_DOWN
from dotenv import load_dotenv

# Importar el cliente de CoinGecko de tu proyecto
from app.core.coingecko import CoinGeckoClient
from app.utils.exceptions import CoinGeckoAPIError

load_dotenv()

logger = logging.getLogger(__name__)

class ProtonWalletService:
    def __init__(self):
        self.connected = False
        self.account_name = None
        # Configuración para producción
        self.rpc_endpoint = os.getenv('PROTON_MAINNET_RPC', 'https://proton.greymass.com')
        self.hyperion_endpoint = os.getenv('PROTON_HYPERION_ENDPOINT', 'https://proton.eosusa.io')
        self.chain_id = os.getenv('PROTON_CHAIN_ID', '384da888112027f0321850a169f737c33e53b388aad48b5adace4bab97f437e0')
        self.session = None
        self.coingecko_client = CoinGeckoClient()  # Cliente de CoinGecko de tu proyecto
        
        # Contratos de tokens de Proton con sus correspondencias en CoinGecko
        self.token_contracts = {
            "eosio.token": {
                "tokens": ["XPR"],
                "coingecko_ids": ["proton"]
            },
            "tokens.proton": {
                "tokens": ["XUSDT", "XBTC", "XETH", "XUSDC", "XDOGE", "XBNB", "XADA", "XDOT", "XLTC"],
                "coingecko_ids": ["tether", "bitcoin", "ethereum", "usd-coin", "dogecoin", "binancecoin", "cardano", "polkadot", "litecoin"]
            },
            "usdt.proton": {
                "tokens": ["USDT"],
                "coingecko_ids": ["tether"]
            },
            "btc.proton": {
                "tokens": ["BTC"],
                "coingecko_ids": ["bitcoin"]
            },
            "eth.proton": {
                "tokens": ["ETH"],
                "coingecko_ids": ["ethereum"]
            },
            "usdc.proton": {
                "tokens": ["USDC"],
                "coingecko_ids": ["usd-coin"]
            },
            "dogep.proton": {
                "tokens": ["DOGE"],
                "coingecko_ids": ["dogecoin"]
            },
            "xprtokens.proton": {
                "tokens": ["XMD", "LOAN", "SWAP"],
                "coingecko_ids": ["proton", "proton-loan", "proton-swap"]
            },
            "proton.swaps": {
                "tokens": ["PSWAP"],
                "coingecko_ids": ["proton-swap"]
            }
        }
        
        self.session_timeout = aiohttp.ClientTimeout(total=10, connect=5)
        self.cache = {}
        self.cache_timeout = timedelta(minutes=5)
        self.price_cache = {}
        self.price_cache_timeout = timedelta(minutes=2)
        
    async def initialize(self):
        """Inicializar el servicio de Proton con conexión persistente"""
        try:
            # Crear sesión persistente
            connector = aiohttp.TCPConnector(limit=100, limit_per_host=20)
            self.session = aiohttp.ClientSession(
                timeout=self.session_timeout,
                connector=connector,
                headers={'User-Agent': 'Crypto-Trading-Platform/2.0.0'}
            )
            
            # Verificar conexión con Proton
            proton_health = await self._health_check()
            if not proton_health['success']:
                logger.error(f"❌ Error conectando a Proton: {proton_health.get('error')}")
                return False
            
            # Verificar conexión con CoinGecko
            try:
                coingecko_ping = self.coingecko_client.get_ping()
                if not coingecko_ping:
                    logger.warning("⚠️ CoinGecko API no responde, usando precios de respaldo")
                else:
                    logger.info("✅ CoinGecko API conectada correctamente")
            except Exception as e:
                logger.warning(f"⚠️ Error conectando a CoinGecko: {e}")
            
            self.connected = True
            logger.info(f"✅ Proton Service inicializado correctamente")
            logger.info(f"📊 Chain ID: {proton_health['chain_id']}")
            logger.info(f"🔄 Head Block: {proton_health['head_block']}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error inicializando Proton Service: {str(e)}")
            return False
    
    async def _health_check(self):
        """Verificación de salud del endpoint RPC"""
        try:
            async with self.session.post(self.rpc_endpoint, json={
                "jsonrpc": "2.0",
                "id": "health_check",
                "method": "chain.get_info",
                "params": []
            }) as response:
                if response.status == 200:
                    data = await response.json()
                    if 'result' in data:
                        result = data['result']
                        return {
                            'success': True,
                            'chain_id': result.get('chain_id'),
                            'head_block': result.get('head_block_num'),
                            'server_version': result.get('server_version_string')
                        }
                return {'success': False, 'error': f'HTTP {response.status}'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def close(self):
        """Cerrar la sesión HTTP"""
        if self.session:
            await self.session.close()
            self.session = None
            self.connected = False
    
    async def connect_wallet(self, account_name: str, permission: str = "active"):
        """Conectar con una cuenta de Proton"""
        try:
            if not self._validate_account_name(account_name):
                return {
                    'success': False,
                    'error': 'Formato de cuenta inválido',
                    'message': 'Nombre de cuenta Proton inválido'
                }
            
            account_info = await self.get_account_info(account_name)
            if not account_info['success']:
                return {
                    'success': False,
                    'error': 'Cuenta no encontrada',
                    'message': f'La cuenta {account_name} no existe en Proton Blockchain'
                }
            
            self.connected = True
            self.account_name = account_name
            self.permission = permission
            
            # Obtener balances con precios reales
            balances = await self.get_all_balances(account_name)
            
            return {
                'success': True,
                'account': account_name,
                'permission': permission,
                'balances': balances.get('tokens', []),
                'total_value': balances.get('total_value', 0),
                'message': 'Wallet conectada exitosamente'
            }
            
        except Exception as e:
            logger.error(f"Error conectando wallet {account_name}: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'message': 'Error conectando wallet'
            }
    
    def _validate_account_name(self, account_name: str) -> bool:
        """Validar formato de nombre de cuenta Proton"""
        if not account_name or len(account_name) > 12:
            return False
        return all(c in 'abcdefghijklmnopqrstuvwxyz12345.' for c in account_name)
    
    async def get_account_info(self, account_name: str):
        """Obtener información de una cuenta Proton"""
        cache_key = f"account_info_{account_name}"
        if cache_key in self.cache:
            cached_data = self.cache[cache_key]
            if datetime.now() - cached_data['timestamp'] < self.cache_timeout:
                return cached_data['data']
        
        try:
            async with self.session.post(self.rpc_endpoint, json={
                "jsonrpc": "2.0",
                "id": f"account_{account_name}",
                "method": "chain.get_account",
                "params": {"account_name": account_name}
            }) as response:
                if response.status == 200:
                    data = await response.json()
                    if 'result' in data:
                        result = {
                            'success': True,
                            'account_info': data['result'],
                            'account': account_name
                        }
                        self.cache[cache_key] = {'data': result, 'timestamp': datetime.now()}
                        return result
                
                return {
                    'success': False,
                    'error': f'HTTP {response.status}',
                    'account': account_name
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'account': account_name
            }
    
    async def get_balance(self, account_name: str, token_contract: str = "eosio.token", symbol: str = "XPR"):
        """Obtener balance específico de un token"""
        cache_key = f"balance_{account_name}_{token_contract}_{symbol}"
        if cache_key in self.cache:
            cached_data = self.cache[cache_key]
            if datetime.now() - cached_data['timestamp'] < timedelta(seconds=30):
                return cached_data['data']
        
        try:
            payload = {
                "jsonrpc": "2.0",
                "id": f"balance_{account_name}_{token_contract}_{symbol}",
                "method": "chain.get_currency_balance",
                "params": {
                    "code": token_contract,
                    "account": account_name,
                    "symbol": symbol
                }
            }
            
            async with self.session.post(self.rpc_endpoint, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    balance = data.get('result', [])
                    
                    result = {
                        'success': True,
                        'balance': balance[0] if balance else f"0.0000 {symbol}",
                        'account': account_name,
                        'contract': token_contract,
                        'symbol': symbol,
                        'amount': float(balance[0].split(' ')[0]) if balance else 0.0
                    }
                    
                    self.cache[cache_key] = {'data': result, 'timestamp': datetime.now()}
                    return result
                
                return {
                    'success': False,
                    'error': f'HTTP {response.status}',
                    'account': account_name
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'account': account_name
            }
    
    async def get_all_balances(self, account_name: str):
        """Obtener todos los balances con precios reales de CoinGecko"""
        try:
            # Primero intentar con Hyperion
            hyperion_balances = await self._get_balances_hyperion(account_name)
            if hyperion_balances['success']:
                tokens_with_prices = await self._add_real_token_prices(hyperion_balances['tokens'])
                total_value = sum(token.get('value_usd', 0) for token in tokens_with_prices)
                
                return {
                    'success': True,
                    'account': account_name,
                    'tokens': tokens_with_prices,
                    'total_value': total_value,
                    'source': 'hyperion'
                }
            
            # Fallback al método tradicional
            traditional_balances = await self._get_balances_traditional(account_name)
            if traditional_balances['success']:
                tokens_with_prices = await self._add_real_token_prices(traditional_balances['tokens'])
                total_value = sum(token.get('value_usd', 0) for token in tokens_with_prices)
                
                return {
                    'success': True,
                    'account': account_name,
                    'tokens': tokens_with_prices,
                    'total_value': total_value,
                    'source': 'rpc'
                }
            
            return {
                'success': False,
                'error': 'No se pudieron obtener balances',
                'account': account_name
            }
            
        except Exception as e:
            logger.error(f"Error obteniendo balances para {account_name}: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'account': account_name
            }
    
    async def _get_balances_hyperion(self, account_name: str):
        """Obtener balances usando Hyperion"""
        try:
            async with self.session.get(
                f"{self.hyperion_endpoint}/v2/state/get_balances?account={account_name}",
                timeout=aiohttp.ClientTimeout(total=8)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    tokens = []
                    
                    for balance in data.get('balances', []):
                        if float(balance['amount']) > 0:
                            tokens.append({
                                "symbol": balance['currency'],
                                "amount": balance['amount'],
                                "contract": balance['contract'],
                                "amount_float": float(balance['amount'])
                            })
                    
                    return {'success': True, 'tokens': tokens}
                return {'success': False}
                
        except Exception:
            return {'success': False}
    
    async def _get_balances_traditional(self, account_name: str):
        """Método tradicional para obtener balances"""
        try:
            tasks = []
            for contract, contract_info in self.token_contracts.items():
                for symbol in contract_info['tokens']:
                    tasks.append(self.get_balance(account_name, contract, symbol))
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            tokens = []
            for result in results:
                if isinstance(result, dict) and result.get('success') and result.get('amount', 0) > 0:
                    tokens.append({
                        "symbol": result['symbol'],
                        "amount": result['balance'],
                        "contract": result['contract'],
                        "amount_float": result['amount']
                    })
            
            return {'success': True, 'tokens': tokens}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def _add_real_token_prices(self, tokens: List[Dict[str, Any]]):
        """Añadir precios reales desde CoinGecko API"""
        if not tokens:
            return tokens
        
        try:
            # Obtener todos los IDs de CoinGecko necesarios
            coingecko_ids = set()
            symbol_to_coingecko = {}
            
            for token in tokens:
                symbol = token['symbol']
                for contract_info in self.token_contracts.values():
                    if symbol in contract_info['tokens']:
                        idx = contract_info['tokens'].index(symbol)
                        if idx < len(contract_info['coingecko_ids']):
                            coingecko_id = contract_info['coingecko_ids'][idx]
                            coingecko_ids.add(coingecko_id)
                            symbol_to_coingecko[symbol] = coingecko_id
                        break
            
            # Obtener precios de CoinGecko
            coingecko_ids_list = list(coingecko_ids)
            prices = await self._get_coingecko_prices(coingecko_ids_list)
            
            # Aplicar precios a los tokens
            for token in tokens:
                symbol = token['symbol']
                coingecko_id = symbol_to_coingecko.get(symbol)
                
                if coingecko_id and coingecko_id in prices:
                    token['price_usd'] = prices[coingecko_id]
                    token['value_usd'] = token['amount_float'] * token['price_usd']
                    token['coingecko_id'] = coingecko_id
                else:
                    # Fallback a precio por defecto
                    token['price_usd'] = self._get_fallback_price(symbol)
                    token['value_usd'] = token['amount_float'] * token['price_usd']
                    token['coingecko_id'] = None
            
            return tokens
            
        except Exception as e:
            logger.error(f"Error obteniendo precios de CoinGecko: {str(e)}")
            # Fallback a precios por defecto
            for token in tokens:
                token['price_usd'] = self._get_fallback_price(token['symbol'])
                token['value_usd'] = token['amount_float'] * token['price_usd']
                token['coingecko_id'] = None
            
            return tokens
    
    async def _get_coingecko_prices(self, coin_ids: List[str]):
        """Obtener precios actuales de CoinGecko"""
        cache_key = f"coingecko_prices_{'_'.join(sorted(coin_ids))}"
        if cache_key in self.price_cache:
            cached_data = self.price_cache[cache_key]
            if datetime.now() - cached_data['timestamp'] < self.price_cache_timeout:
                return cached_data['data']
        
        try:
            # Usar el cliente de CoinGecko de tu proyecto
            prices_data = self.coingecko_client.get_price(
                ids=','.join(coin_ids),
                vs_currencies='usd'
            )
            
            result = {}
            for coin_id in coin_ids:
                if coin_id in prices_data:
                    result[coin_id] = prices_data[coin_id]['usd']
                else:
                    result[coin_id] = self._get_fallback_price(coin_id)
            
            self.price_cache[cache_key] = {'data': result, 'timestamp': datetime.now()}
            return result
            
        except CoinGeckoAPIError as e:
            logger.warning(f"CoinGecko API error: {e}")
            # Fallback a precios por defecto
            return {coin_id: self._get_fallback_price(coin_id) for coin_id in coin_ids}
        except Exception as e:
            logger.error(f"Error inesperado en CoinGecko: {e}")
            return {coin_id: self._get_fallback_price(coin_id) for coin_id in coin_ids}
    
    def _get_fallback_price(self, symbol: str):
        """Precios de respaldo para cuando CoinGecko no está disponible"""
        fallback_prices = {
            "XPR": 0.0012, "USDT": 1.0, "XUSDT": 1.0, "USDC": 1.0, "XUSDC": 1.0,
            "BTC": 43000.0, "XBTC": 43000.0, "ETH": 2300.0, "XETH": 2300.0,
            "DOGE": 0.08, "XDOGE": 0.08, "BNB": 350.0, "XBNB": 350.0,
            "ADA": 0.5, "XADA": 0.5, "DOT": 6.5, "XDOT": 6.5, "LTC": 70.0, "XLTC": 70.0,
            "XMD": 0.015, "LOAN": 0.025, "SWAP": 0.035, "PSWAP": 0.035
        }
        return fallback_prices.get(symbol, 0.0)
    
    async def get_transaction_history(self, account_name: str, limit: int = 20):
        """Obtener historial de transacciones"""
        try:
            async with self.session.get(
                f"{self.hyperion_endpoint}/v2/history/get_actions?account={account_name}&limit={limit}&sort=desc",
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return {
                        'success': True,
                        'account': account_name,
                        'transactions': data.get('actions', []),
                        'total': data.get('total', {}).get('value', 0)
                    }
                return {
                    'success': False,
                    'error': 'Error obteniendo historial',
                    'account': account_name
                }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'account': account_name
            }
    
    async def transfer(self, from_account: str, to_account: str, quantity: str, memo: str = "", contract: str = "eosio.token"):
        """Realizar una transferencia"""
        try:
            # Validar parámetros
            if not all([from_account, to_account, quantity]):
                return {
                    'success': False,
                    'error': 'Parámetros incompletos',
                    'message': 'Faltan parámetros requeridos'
                }
            
            # Validar formato de cantidad
            try:
                amount, symbol = quantity.split(' ')
                float(amount)
            except ValueError:
                return {
                    'success': False,
                    'error': 'Formato de cantidad inválido',
                    'message': 'Use el formato: "10.0000 XPR"'
                }
            
            # Obtener información de la cadena
            async with self.session.post(self.rpc_endpoint, json={
                "jsonrpc": "2.0",
                "id": "chain_info",
                "method": "chain.get_info",
                "params": []
            }) as response:
                if response.status != 200:
                    return {
                        'success': False,
                        'error': 'Error conectando a la blockchain',
                        'message': 'No se pudo conectar a Proton blockchain'
                    }
                
                chain_info = await response.json()
                chain_id = chain_info['result']['chain_id']
                head_block_num = chain_info['result']['head_block_num']
            
            # Obtener bloque de referencia
            async with self.session.post(self.rpc_endpoint, json={
                "jsonrpc": "2.0",
                "id": "block_info",
                "method": "chain.get_block",
                "params": {"block_num_or_id": head_block_num}
            }) as response:
                if response.status != 200:
                    return {
                        'success': False,
                        'error': 'Error obteniendo bloque de referencia',
                        'message': 'No se pudo obtener información del bloque'
                    }
                
                block_info = await response.json()
                ref_block_prefix = block_info['result']['ref_block_prefix']
            
            # Crear transacción
            transaction = {
                "actions": [{
                    "account": contract,
                    "name": "transfer",
                    "authorization": [{
                        "actor": from_account,
                        "permission": self.permission if hasattr(self, 'permission') else "active"
                    }],
                    "data": {
                        "from": from_account,
                        "to": to_account,
                        "quantity": quantity,
                        "memo": memo
                    }
                }],
                "context_free_actions": [],
                "context_free_data": [],
                "delay_sec": 0,
                "expiration": f"{(datetime.utcnow().timestamp() + 300):.0f}",
                "max_cpu_usage_ms": 0,
                "max_net_usage_words": 0,
                "ref_block_num": head_block_num & 0xFFFF,
                "ref_block_prefix": ref_block_prefix,
                "transaction_extensions": []
            }
            
            return {
                'success': True,
                'transaction': transaction,
                'chain_id': chain_id,
                'message': 'Transacción creada, requiere firma'
            }
            
        except Exception as e:
            logger.error(f"Error en transferencia: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': 'Error creando transacción'
            }
    
    async def push_transaction(self, signed_transaction: Dict[str, Any]):
        """Enviar una transacción firmada a la blockchain"""
        try:
            async with self.session.post(self.rpc_endpoint, json={
                "jsonrpc": "2.0",
                "id": "push_transaction",
                "method": "chain.push_transaction",
                "params": {
                    "transaction": signed_transaction['transaction'],
                    "signatures": signed_transaction['signatures']
                }
            }) as response:
                result = await response.json()
                
                if response.status == 200 and 'result' in result:
                    return {
                        'success': True,
                        'transaction_id': result['result']['transaction_id'],
                        'message': 'Transacción enviada exitosamente'
                    }
                else:
                    error = result.get('error', {}).get('details', [{}])[0].get('message', 'Error desconocido')
                    return {
                        'success': False,
                        'error': error,
                        'message': 'Error enviando transacción'
                    }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'message': 'Error enviando transacción'
            }

# Instancia global del servicio
proton_service = ProtonWalletService()

# Inicializar al importar el módulo
async def initialize_proton_service():
    await proton_service.initialize()

# Ejecutar la inicialización
try:
    loop = asyncio.get_event_loop()
    if loop.is_running():
        loop.create_task(initialize_proton_service())
    else:
        loop.run_until_complete(initialize_proton_service())
except:
    pass