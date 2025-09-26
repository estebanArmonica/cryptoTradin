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
        
    #====================================================================================
    # NUEVOS MÉTODOS AGREGADOS
    #====================================================================================
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    def get_coin_by_id(self, id):
        """Obtiene información de datoa actuales de una criptomoneda específica por su ID"""
        try:
            return self.client.get_coin_by_id(id=id)
        except Exception as e:
            raise CoinGeckoAPIError(f"Error al obtener datos de la criptomoneda por ID: {str(e)}")
        
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    def get_coin_ticker_by_id(self, id):
        """Obtiene los tickers de una criptomoneda específica por su ID"""
        try:
            return self.client.get_coin_ticker_by_id(id=id)
        except Exception as e:
            raise CoinGeckoAPIError(f"Error al obtener tickers de la criptomoneda por ID: {str(e)}")
        
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    def get_coin_history_by_id(self, id, date, localization='false'):
        """Obtiene datos históricos de una criptomoneda (nombre, precio, mercado, estadísticas) en una fecha dada para una moneda"""
        try:
            return self.client.get_coin_history_by_id(id=id, date=date, localization=localization)
        except Exception as e:
            raise CoinGeckoAPIError(f"Error al obtener datos históricos de la criptomoneda por ID: {str(e)}")
        
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    def get_coin_market_chart_range_by_id(self, id, vs_currency, from_timestamp, to_timestamp):
        """Obtiene datos de mercado (precio, capitalización de mercado, volumen) en un rango de tiempo específico para una criptomoneda"""
        try:
            return self.client.get_coin_market_chart_range_by_id(
                id=id,
                vs_currency=vs_currency,
                from_timestamp=from_timestamp,
                to_timestamp=to_timestamp
            )
        except Exception as e:
            raise CoinGeckoAPIError(f"Error al obtener datos de mercado en rango de tiempo para la criptomoneda por ID: {str(e)}")
        
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    def get_coin_ohlc_by_id_range(self, id, vs_currency, days):
        """Obtiene datos OHLC (Open, High, Low, Close) en un rango de tiempo específico para una criptomoneda"""
        try:
            return self.client.get_coin_ohlc_by_id(
                id=id,
                vs_currency=vs_currency,
                days=days
            )
        except Exception as e:
            raise CoinGeckoAPIError(f"Error al obtener datos OHLC en rango de tiempo para la criptomoneda por ID: {str(e)}")

    #====================================================================================
    # MÉTODOS DE CONTRATO (DATOS HISTORICOS)
    #====================================================================================
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    def get_coin_info_from_contract_address_by_id(self):
        """Obtiene información detallada de una criptomoneda a partir de su dirección de contrato"""
        try:
            return self.client.get_coin_info_from_contract_address_by_id()
        except Exception as e:
            raise CoinGeckoAPIError(f"Error al obtener información de la criptomoneda desde la dirección del contrato: {str(e)}")   
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    def get_coin_market_chart_from_contract_address_by_id(self):
        """Obtiene datos de mercado (precio, capitalización de mercado, volumen) a partir de la dirección del contrato"""
        try:
            return self.client.get_coin_market_chart_from_contract_address_by_id()
        except Exception as e:
            raise CoinGeckoAPIError(f"Error al obtener datos de mercado desde la dirección del contrato: {str(e)}")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    ) 
    def get_coin_market_chart_range_from_contract_address_by_id(self):
        """Obtenga datos históricos de mercado incluyen precio, tope de mercado y volumen de 24h en un rango de marca de tiempo (auto de granularidad) de una dirección de contrat"""
        try:
            return self.client.get_coin_market_chart_range_from_contract_address_by_id()
        except Exception as e:
            raise CoinGeckoAPIError(f"Error al obtener datos de mercado en rango de tiempo desde la dirección del contrato: {str(e)}")

    #===================================================================================
    # METODOS DE EXCHANGES
    #===================================================================================
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    ) 
    def get_exchanges_list(self):
        """Obtiene una lista de todos los exchanges"""
        try:
            return self.client.get_exchanges_list()
        except Exception as e:
            raise CoinGeckoAPIError(f"Error al obtener lista de exchanges: {str(e)}")
        
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    def get_exchanges_id_name_lis(self):
        """Obtiene una lista de IDs y nombres de todos los exchanges"""
        try:
            return self.client.get_exchanges_id_name_list()
        except Exception as e:
            raise CoinGeckoAPIError(f"Error al obtener lista de IDs y nombres de exchanges: {str(e)}")
        
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    def get_exchanges_by_id(self, id):
        """Obtiene información detallada de un exchange específico por su ID"""
        try:
            return self.client.get_exchanges_by_id(id=id)
        except Exception as e:
            raise CoinGeckoAPIError(f"Error al obtener información del exchange por ID: {str(e)}")
        
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    def get_exchanges_tickers_by_id(self, id):
        """Obtiene los tickers de un exchange específico por su ID"""
        try:
            return self.client.get_exchanges_tickers_by_id(id=id)
        except Exception as e:
            raise CoinGeckoAPIError(f"Error al obtener tickers del exchange por ID: {str(e)}")
        
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    def get_exchanges_volume_chart_by_id(self, id, days):
        """Obtiene datos de volumen de un exchange específico por su ID en los últimos 'n' días"""
        try:
            return self.client.get_exchanges_volume_chart_by_id(id=id, days=days)
        except Exception as e:
            raise CoinGeckoAPIError(f"Error al obtener datos de volumen del exchange por ID: {str(e)}")
        
    #===================================================================================
    # METODOS DE INDEXES
    #===================================================================================
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    def get_indexes(self):
        """Obtiene una lista de todos los índices"""
        try:
            return self.client.get_indexes()
        except Exception as e:
            raise CoinGeckoAPIError(f"Error al obtener lista de índices: {str(e)}")
        
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    def get_indexes_by_market_id_and_index_id(self, market_id, index_id):
        """Obtiene información detallada de un índice específico por su ID de mercado e ID de índice"""
        try:
            return self.client.get_indexes_by_market_id_and_index_id(market_id=market_id, index_id=index_id)
        except Exception as e:
            raise CoinGeckoAPIError(f"Error al obtener información del índice por ID de mercado e ID de índice: {str(e)}")
        
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    def get_indexes_list(self):
        """Obtiene una lista de todos los índices con sus IDs y nombres"""
        try:
            return self.client.get_indexes_list()
        except Exception as e:
            raise CoinGeckoAPIError(f"Error al obtener lista de IDs y nombres de índices: {str(e)}")
        
    #===================================================================================
    # METODOS DE DERIVADOS
    #===================================================================================
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    ) 
    def get_derivatives(self):
        """Obtiene una lista de todos los derivados"""
        try:
            return self.client.get_derivatives()
        except Exception as e:
            raise CoinGeckoAPIError(f"Error al obtener lista de derivados: {str(e)}")
        
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    def get_derivatives_exchanges(self):
        """Obtiene una lista de todos los exchanges de derivados"""
        try:
            return self.client.get_derivatives_exchanges()
        except Exception as e:
            raise CoinGeckoAPIError(f"Error al obtener lista de exchanges de derivados: {str(e)}")
        
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    def get_derivatives_exchanges_by_id(self, id):
        """Obtiene información detallada de un exchange de derivados específico por su ID"""
        try:
            return self.client.get_derivatives_exchanges_by_id(id=id)
        except Exception as e:
            raise CoinGeckoAPIError(f"Error al obtener información del exchange de derivados por ID: {str(e)}")
        
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    def get_derivatives_exchanges_list(self):
        """Obtiene una lista de todos los exchanges de derivados con sus IDs y nombres"""
        try:
            return self.client.get_derivatives_exchanges_list()
        except Exception as e:
            raise CoinGeckoAPIError(f"Error al obtener lista de IDs y nombres de exchanges de derivados: {str(e)}")
        
    #===================================================================================
    # METODOS DE NFT
    #===================================================================================
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    def get_nfts_list(self):
        """Obtiene una lista de todos los NFTs"""
        try:
            return self.client.get_nfts_list()
        except Exception as e:
            raise CoinGeckoAPIError(f"Error al obtener lista de NFTs: {str(e)}")
        
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    def get_nfts_by_id(self, id):
        """Obtiene información detallada de un NFT específico por su ID"""
        try:
            return self.client.get_nfts_by_id(id=id)
        except Exception as e:
            raise CoinGeckoAPIError(f"Error al obtener información del NFT por ID: {str(e)}")
        
    # en duda si existe este metodo en la libreria
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    def get_nfts_collection_by_asset_platform_id_and_contract_address(self, asset_platform_id, contract_address):
        """Obtiene información de una colección de NFTs por su ID de plataforma de activos y dirección de contrato"""
        try:
            return self.client.get_nfts_collection_by_asset_platform_id_and_contract_address(
                asset_platform_id=asset_platform_id,
                contract_address=contract_address
            )
        except Exception as e:
            raise CoinGeckoAPIError(f"Error al obtener información de la colección de NFTs por ID de plataforma de activos y dirección de contrato: {str(e)}")
        
    
    #===================================================================================
    # METODOS DE EXCHANGES RATES
    #===================================================================================
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    def get_exchange_rates(self):
        """Obtiene las tasas de cambio actuales"""
        try:
            return self.client.get_exchange_rates()
        except Exception as e:
            raise CoinGeckoAPIError(f"Error al obtener tasas de cambio: {str(e)}")
        
    #===================================================================================
    # METODOS DE TENDENCIAS
    #===================================================================================
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    def get_search_trending(self):
        """Obtiene las criptomonedas más buscadas"""
        try:
            return self.client.get_search_trending()
        except Exception as e:
            raise CoinGeckoAPIError(f"Error al obtener criptomonedas más buscadas: {str(e)}")
        
    #===================================================================================
    # METODOS DE GLOBAL
    #===================================================================================
    # tambien en duda si se pueda usar ya que es version pro
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    def get_global_market_cap_chart(self, vs_currency, days):
        """Obtiene datos históricos del tope de mercado global en los últimos 'n' días"""
        try:
            return self.client.get_global_market_cap_chart(vs_currency=vs_currency, days=days)
        except Exception as e:
            raise CoinGeckoAPIError(f"Error al obtener datos históricos del tope de mercado global: {str(e)}")
        
    #===================================================================================
    # METODOS DE PRECIO
    #===================================================================================
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    def get_token_price(self, id, contract_addresses, vs_currencies):
        """Obtiene el precio de un token específico por su ID y dirección de contrato"""
        try:
            return self.client.get_token_price(id=id, contract_addresses=contract_addresses, vs_currencies=vs_currencies)
        except Exception as e:
            raise CoinGeckoAPIError(f"Error al obtener precio del token por ID y dirección de contrato: {str(e)}")
        
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    def get_supported_vs_currencies(self):
        """Obtiene una lista de todas las monedas compatibles"""
        try:
            return self.client.get_supported_vs_currencies()
        except Exception as e:
            raise CoinGeckoAPIError(f"Error al obtener lista de monedas compatibles: {str(e)}")
        
    #===================================================================================
    # METODOS DE PLATAFORMAS DE ACTIVOS
    #===================================================================================
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    def get_asset_platforms(self):
        """Obtiene una lista de todas las plataformas de activos"""
        try:
            return self.client.get_asset_platforms()
        except Exception as e:
            raise CoinGeckoAPIError(f"Error al obtener lista de plataformas de activos: {str(e)}")
    