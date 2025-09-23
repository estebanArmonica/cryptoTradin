from pycoingecko import CoinGeckoAPI
from tenacity import retry, stop_after_attempt, wait_exponential
from app.utils.exceptions import CoinGeckoAPIError

class CoinGeckoClient:
    def __init__(self):
        self.client = CoinGeckoAPI()
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    def get_ping(self):
        """Verifica conexión con reintentos automáticos"""
        try:
            return self.client.ping()
        except Exception as e:
            raise CoinGeckoAPIError(f"Error en ping: {str(e)}")
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    def get_coins_categories(self):
        """Obtiene las categorías de criptomonedas"""
        try:
            return self.client.get_coins_categories_list()
        except Exception as e:
            raise CoinGeckoAPIError(f"Error al obtener categorías: {str(e)}")
        
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    def get_price(self, ids, vs_currencies):
        """Obtiene el precio de una criptomoneda"""
        try:
            return self.client.get_price(ids=ids, vs_currencies=vs_currencies)
        except Exception as e:
            raise CoinGeckoAPIError(f"Error al obtener precio: {str(e)}")
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    def get_coins_list(self):
        """Obtiene una lista de todas las criptomonedas"""
        try:
            return self.client.get_coins_list()
        except Exception as e:
            raise CoinGeckoAPIError(f"Error al obtener lista de criptomonedas: {str(e)}")
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    def get_coin_market(self, **kwargs):
        """Obtiene el mercado de criptomonedas"""
        try:
            return self.client.get_coins_markets(**kwargs)
        except Exception as e:
            raise CoinGeckoAPIError(f"Error al obtener mercado de criptomonedas: {str(e)}")
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    def get_global_data(self):
        """Obtiene datos globales del mercado de criptomonedas"""
        try:
            return self.client.get_global()
        except Exception as e:
            raise CoinGeckoAPIError(f"Error al obtener datos globales: {str(e)}")
        
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    def get_decentralized_finance(self):
        """Obtiene datos de finanzas descentralizadas"""
        try:
            return self.client.get_global_decentralized_finance_defi()
        except Exception as e:
            raise CoinGeckoAPIError(f"Error al obtener datos de DeFi: {str(e)}")
        
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    def get_companies_by_coin_id(self, coin_id):
        """Obtiene empresas relacionadas con una criptomoneda específica"""
        try:
            return self.client.get_companies_public_treasury_by_coin_id(coin_id=coin_id)
        except Exception as e:
            raise CoinGeckoAPIError(f"Error al obtener empresas por ID de criptomoneda: {str(e)}") 
        
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    def get_search(self, query):
        """Realiza una búsqueda de criptomonedas"""
        try:
            return self.client.search(query=query)
        except Exception as e:
            raise CoinGeckoAPIError(f"Error al realizar búsqueda: {str(e)}")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    def get_coin_market_chart_by_id(self, id, vs_currency, days):
        """Obtiene datos históricos de precios de una criptomoneda"""
        try:
            return self.client.get_coin_market_chart_by_id(
                id=id, 
                vs_currency=vs_currency, 
                days=days
            )
        except Exception as e:
            raise CoinGeckoAPIError(f"Error al obtener datos históricos: {str(e)}")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    def get_coin_ohlc(self, id, vs_currency, days):
        """Obtiene datos OHLC (Open, High, Low, Close) de una criptomoneda"""
        try:
            return self.client.get_coin_ohlc_by_id(
                id=id,
                vs_currency=vs_currency,
                days=days
            )
        except Exception as e:
            raise CoinGeckoAPIError(f"Error al obtener datos OHLC: {str(e)}")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    def get_coin_info(self, id):
        """Obtiene información detallada de una criptomoneda"""
        try:
            return self.client.get_coin_by_id(id=id)
        except Exception as e:
            raise CoinGeckoAPIError(f"Error al obtener información de la criptomoneda: {str(e)}")