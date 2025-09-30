from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List
from app.core.coingecko import CoinGeckoClient
from app.models.schemas import *
from app.utils.exceptions import handle_api_error
from datetime import datetime, timedelta

router = APIRouter()
client = CoinGeckoClient()

# ruta de prueba para verificar que la API está funcionando
@router.get("/", tags=["Status"])
def read_root():
    """Ruta de prueba para verificar que la API está funcionando."""
    return {"message": "API de CoinGecko está funcionando correctamente."}

# creamos una función para verificar el ping del servidor de CoinGecko
@router.get("/ping", response_model=PingResponse, tags=["Status"])
def get_ping():
    """Verifica la conexión con el servidor de CoinGecko."""
    try:
        response = client.get_ping()
        if response:
            return {"success": True, "message": "Conexión exitosa con CoinGecko"}
        else:
            return {"success": False, "message": "Error al conectar con CoinGecko"}
    except Exception as e:
        raise handle_api_error(e, "Error al verificar el ping del servidor de CoinGecko")


# creamos una función para obtener las categorías de criptomonedas
@router.get("/categories", response_model=List[CoinCategory], tags=["Cryptocurrencies"])
def get_coin_categories():
    """Obtiene las categorías de criptomonedas disponibles en CoinGecko."""
    try:
        categories = client.get_coins_categories()
        return [{"id": cat["category_id"], "name": cat["name"]} for cat in categories]
    except Exception as e:
        raise handle_api_error(e, "Error al obtener las categorías de criptomonedas")


# creamos una función para obtener el precio de una criptomoneda
@router.get("/prices", response_model=CoinPrice, tags=["Cryptocurrencies"])
def get_prices(coin_ids: str, vs_currencies: str):
    """
    Obtiene el precio de una criptomoneda en diferentes monedas.
    
    - **coin_ids**: Identificadores separados por comas (ej. 'bitcoin,ethereum')
    - **vs_currencies**: Monedas separadas por comas (ej. 'usd,eur')
    """
    try:
        prices = client.get_price(ids=coin_ids, vs_currencies=vs_currencies)
        return {"coin_id": coin_ids, "prices": prices}
    except Exception as e:
        raise handle_api_error(e, "Error al obtener el precio de la criptomoneda")

# listamos las criptomonedas y monedas que queremos consultar
@router.get("/coins/list", response_model=List[CoinListItem], tags=["Cryptocurrencies"])
def get_coin_list():
    """Obtiene una lista de todas las criptomonedas disponibles en CoinGecko."""
    try:
        coins = client.get_coins_list()
        return [{"id": coin["id"], "symbol": coin["symbol"], "name": coin["name"]} for coin in coins]
    except Exception as e:
        raise handle_api_error(e, "Error al obtener la lista de criptomonedas")

# creamos una función para obtener el mercado de criptomonedas
@router.get("/coins/markets", response_model=List[CoinMarket], tags=["Cryptocurrencies"])
def get_coin_market(vs_currency: str = "usd", order: str = "market_cap_desc", per_page: int = 100, page: int = 1, ids: str = None):  
    """
    Obtiene el mercado de criptomonedas.
    
    - **vs_currency**: Moneda contra la que se comparan los precios (ej. 'usd')
    - **order**: Orden de los resultados (ej. 'market_cap_desc', 'volume_desc', etc.)
    - **per_page**: Número de resultados por página
    - **page**: Número de página a obtener
    - **ids**: IDs de criptomonedas separados por comas (ej. 'bitcoin,ethereum')
    """
    try:
        market_data = client.get_coin_market(vs_currency=vs_currency, order=order, per_page=per_page, page=page, ids=ids)
        return [CoinMarket(**coin) for coin in market_data]
    except Exception as e:
        raise handle_api_error(e, "Error al obtener el mercado de criptomonedas")

# creamos una función para obtener datos globales del mercado de criptomonedas
@router.get("/global", response_model=GlobalData, tags=["Market"])
def get_global_datas():
    """Obtiene datos globales del mercado de criptomonedas."""
    try:
        return client.get_global_data()
    except Exception as e:
        raise handle_api_error(e, "Error al obtener datos globales del mercado de criptomonedas")

# creamos una función para obtener el decentralizado de las criptomonedas
@router.get("/decentralized", response_model=DecentralizedFinance, tags=["Market"])
def get_decentralized_finance():
    response = client.get_decentralized_finance()
    print("Respuesta:\n", response)  # Imprime la respuesta para verificar su estructura
    """Obtiene datos de finanzas descentralizadas (DeFi) del mercado de criptomonedas."""
    try:
        response = client.get_decentralized_finance()
        return DecentralizedFinance(**response)
    except Exception as e:
        raise handle_api_error(e, "Error al obtener datos de finanzas descentralizadas")
    
# creamos una función para obtener las empresas por ID de criptomoneda
@router.get("/companies/{coin_id}", response_model=List[CompanyInfo], tags=["Companies"])
def get_companies_by_coin_ids(coin_id: str):
    """
    Obtiene empresas relacionadas con una criptomoneda específica.
    
    - **coin_id**: ID de la criptomoneda (ej. 'bitcoin')
    """
    try:
        response = client.get_companies_by_coin_id(coin_id)
        companies = response.get("companies", []) # extraemos la lista
        return [CompanyInfo(**company) for company in companies]
    except Exception as e:
        raise handle_api_error(e, f"Error al obtener empresas para la criptomoneda {coin_id}")
    
# creamos una función para buscar criptomonedas por nombre
@router.get("/search", response_model=List[SearchQuery], tags=["Cryptocurrencies"])
def search_coins(query: str):
    """
    Busca criptomonedas por nombre.

    - **query**: Nombre o parte del nombre de la criptomoneda a buscar
    """
    try:
        results = client.get_search(query=query)
        return [SearchQuery(**result) for result in results["coins"]] # extraemos la lista de resultados
    except Exception as e:
        response = handle_api_error(e, "Error al buscar criptomonedas")
        raise HTTPException(status_code=response.status_code, detail=response.body.decode('utf-8'))

#====================================================================================
# ENDPOINTS NUEVOS AGREGADOS
#====================================================================================
@router.get("/coins/{coin_id}/info", response_model=CoinDetail, tags=["Cryptocurrencies"])
def get_coin_info_by_id(coin_id: str):
    """
    Obtiene información detallada de una criptomoneda específica por su ID.
    
    - **coin_id**: ID de la criptomoneda (ej. 'bitcoin')
    """
    try:
        coin_data = client.get_coin_by_id(id=coin_id)
        return CoinDetail(**coin_data)
    except Exception as e:
        raise handle_api_error(e, f"Error al obtener información para la criptomoneda {coin_id}")

@router.get("/coins/{coin_id}/tickers", response_model=List[CoinTicker], tags=["Cryptocurrencies"])
def get_coin_tickers_by_id(coin_id: str):
    """
    Obtiene los tickers de una criptomoneda específica por su ID.
    
    - **coin_id**: ID de la criptomoneda (ej. 'bitcoin')
    """
    try:
        tickers_data = client.get_coin_ticker_by_id(id=coin_id)
        tickers = tickers_data.get("tickers", [])
        return [CoinTicker(**ticker) for ticker in tickers]
    except Exception as e:
        raise handle_api_error(e, f"Error al obtener tickers para la criptomoneda {coin_id}")

@router.get("/coins/{coin_id}/history/{date}", response_model=CoinHistory, tags=["Cryptocurrencies"])
def get_coin_history_by_id_date(coin_id: str, date: str, localization: str = 'false'):
    """
    Obtiene datos históricos de una criptomoneda en una fecha específica.
    
    - **coin_id**: ID de la criptomoneda (ej. 'bitcoin')
    - **date**: Fecha en formato 'dd-mm-yyyy' (ej. '30-12-2020')
    - **localization**: Incluir datos de localización ('true' o 'false')
    """
    try:
        history_data = client.get_coin_history_by_id(id=coin_id, date=date, localization=localization)
        return CoinHistory(**history_data)
    except Exception as e:
        raise handle_api_error(e, f"Error al obtener datos históricos para {coin_id} en la fecha {date}")


# funciones para obtener el año actual
def get_current_year_timestamps() -> tuple[int, int]:
    """
    Retorna timestamps para el año actual.
    Desde el inicio del año hasta ahora.
    """
    now = datetime.now()
    start_of_year = datetime(now.year, 1, 1)
    
    from_timestamp = int(start_of_year.timestamp())
    to_timestamp = int(now.timestamp())
    
    return from_timestamp, to_timestamp

def get_last_365_days_timestamps() -> tuple[int, int]:
    """
    Retorna timestamps de los últimos 365 días.
    """
    now = datetime.now()
    start_date = now - timedelta(days=365)
    
    from_timestamp = int(start_date.timestamp())
    to_timestamp = int(now.timestamp())
    
    return from_timestamp, to_timestamp

@router.get("/coins/{coin_id}/market_chart/range", response_model=CoinMarketChartRange, tags=["Cryptocurrencies"])
def get_coin_market_chart_range(
    coin_id: str, 
    vs_currency: str = 'usd',
):
    """
    Obtiene datos de mercado en un rango de tiempo específico.
    
    - **coin_id**: ID de la criptomoneda (ej. 'bitcoin')
    - **vs_currency**: Moneda de referencia (ej. 'usd')
    """
    try:
        # obtiene el timestamp actual
        from_timestamp, to_timestamp = get_current_year_timestamps()
        print(f"Consultando: {coin_id}, {vs_currency}, {from_timestamp} -> {to_timestamp}")
        
        chart_data = client.get_coin_market_chart_range_by_id(
            id=coin_id,
            vs_currency=vs_currency,
            from_timestamp=from_timestamp,
            to_timestamp=to_timestamp
        )
        # Verifica la estructura de los datos recibidos
        print(f"Datos recibidos - Precios: {len(chart_data.get('prices', []))} elementos")
        print(f"Datos recibidos - Market Caps: {len(chart_data.get('market_caps', []))} elementos")
        print(f"Datos recibidos - Volúmenes: {len(chart_data.get('total_volumes', []))} elementos")

        return CoinMarketChartRange(**chart_data)
    except Exception as e:
        # Log detallado del error
        print(f"Error completo: {str(e)}")
        print(f"Tipo de error: {type(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")

        raise handle_api_error(e, f"Error al obtener datos de mercado en rango para {coin_id}")

# el mismo para ultimos 30 dias
@router.get("/coins/{coin_id}/market_chart/last_days", response_model=CoinMarketChartRange, tags=["Cryptocurrencies"])
def get_coin_market_chart_last_days(
    coin_id: str, 
    vs_currency: str = "usd",
    days: int = Query(30, ge=1, le=365, description="Número de días (1-365)")
):
    """
    Obtiene datos de mercado de los últimos N días.
    
    - **coin_id**: ID de la criptomoneda (ej. 'bitcoin')
    - **vs_currency**: Moneda de referencia (ej. 'usd')
    - **days**: Número de días hacia atrás (1-365)
    """
    try:
        now = datetime.now()
        start_date = now - timedelta(days=days)
        
        from_timestamp = int(start_date.timestamp())
        to_timestamp = int(now.timestamp())
        
        print(f"Consultando últimos {days} días: {from_timestamp} -> {to_timestamp}")
        
        chart_data = client.get_coin_market_chart_range_by_id(
            id=coin_id,
            vs_currency=vs_currency,
            from_timestamp=from_timestamp,
            to_timestamp=to_timestamp
        )
        return CoinMarketChartRange(**chart_data)
    except Exception as e:
        raise handle_api_error(e, f"Error al obtener datos de los últimos {days} días para {coin_id}")

@router.get("/coins/{coin_id}/ohlc", response_model=List[OHLCData], tags=["Cryptocurrencies"])
def get_coin_ohlc(coin_id: str, vs_currency: str, days: int = Query(..., ge=1, le=365)):
    """
    Obtiene datos OHLC de una criptomoneda.
    
    - **coin_id**: ID de la criptomoneda (ej. 'bitcoin')
    - **vs_currency**: Moneda de referencia (ej. 'usd')
    - **days**: Número de días (1, 7, 14, 30, 90, 180, 365, max)
    """
    try:
        ohlc_data = client.get_coin_ohlc(id=coin_id, vs_currency=vs_currency, days=days)
        
        print(f"Datos OHLC recibidos: {len(ohlc_data)} elementos")
        if ohlc_data:
            print(f"Primer elemento: {ohlc_data[0]}")
            print(f"Tipo del primer elemento: {type(ohlc_data[0])}")
        
        # Convertir lista de listas a lista de OHLCData
        formatted_data = []
        for item in ohlc_data:
            if isinstance(item, list) and len(item) == 5:
                formatted_data.append(OHLCData.from_list(item))
            else:
                print(f"Elemento inesperado: {item}")
        
        print(f"Datos formateados: {len(formatted_data)} elementos")
        return formatted_data
    except Exception as e:
        print(f"Error en endpoint OHLC: {e}")
        print(f"Tipo de error: {type(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        raise handle_api_error(e, f"Error al obtener datos OHLC para {coin_id}")
    
#===================================================================================
# ENDPOINTS DE EXCHANGES
#===================================================================================

@router.get("/exchanges", response_model=List[Exchange], tags=["Exchanges"])
def get_exchanges_list():
    """Obtiene una lista de todos los exchanges."""
    try:
        exchanges = client.get_exchanges_list()
        return [Exchange(**exchange) for exchange in exchanges]
    except Exception as e:
        raise handle_api_error(e, "Error al obtener lista de exchanges")

@router.get("/exchanges/ids", response_model=List[ExchangeIdName], tags=["Exchanges"])
def get_exchanges_id_name_list():
    """Obtiene una lista de IDs y nombres de todos los exchanges."""
    try:
        exchanges = client.get_exchanges_id_name_lis()
        return [ExchangeIdName(**exchange) for exchange in exchanges]
    except Exception as e:
        raise handle_api_error(e, "Error al obtener lista de IDs y nombres de exchanges")

@router.get("/exchanges/{exchange_id}", response_model=ExchangeDetail, tags=["Exchanges"])
def get_exchange_by_id(exchange_id: str):
    """
    Obtiene información detallada de un exchange específico.
    
    - **exchange_id**: ID del exchange (ej. 'binance')
    """
    try:
        exchange_data = client.get_exchanges_by_id(id=exchange_id)
        return ExchangeDetail(**exchange_data)
    except Exception as e:
        raise handle_api_error(e, f"Error al obtener información del exchange {exchange_id}")

@router.get("/exchanges/{exchange_id}/tickers", response_model=ExchangeTickers, tags=["Exchanges"])
def get_exchange_tickers(exchange_id: str):
    """
    Obtiene los tickers de un exchange específico.
    
    - **exchange_id**: ID del exchange (ej. 'binance')
    """
    try:
        tickers_data = client.get_exchanges_tickers_by_id(id=exchange_id)
        return ExchangeTickers(**tickers_data)
    except Exception as e:
        raise handle_api_error(e, f"Error al obtener tickers del exchange {exchange_id}")

@router.get("/exchanges/{exchange_id}/volume_chart", response_model=List[VolumeChartData], tags=["Exchanges"])
def get_exchange_volume_chart(exchange_id: str, days: int):
    """
    Obtiene datos de volumen de un exchange en los últimos días.
    
    - **exchange_id**: ID del exchange (ej. 'binance')
    - **days**: Número de días (ej. 7, 30, 90)
    """
    try:
        volume_data = client.get_exchanges_volume_chart_by_id(id=exchange_id, days=days)
        return [VolumeChartData(timestamp=item[0], volume=item[1]) for item in volume_data]
    except Exception as e:
        raise handle_api_error(e, f"Error al obtener datos de volumen del exchange {exchange_id}")

#===================================================================================
# ENDPOINTS DE TENDENCIAS Y BÚSQUEDA
#===================================================================================

@router.get("/search/trending", response_model=TrendingCoins, tags=["Search"])
def get_search_trending():
    """Obtiene las criptomonedas más buscadas."""
    try:
        trending_data = client.get_search_trending()
        return TrendingCoins(**trending_data)
    except Exception as e:
        raise handle_api_error(e, "Error al obtener criptomonedas más buscadas")

#===================================================================================
# ENDPOINTS DE PRECIOS Y MONEDAS
#===================================================================================

@router.get("/simple/price", response_model=Dict[str, Any], tags=["Prices"])
def get_token_price(id: str, contract_addresses: str, vs_currencies: str):
    """
    Obtiene el precio de un token específico por su ID y dirección de contrato.
    
    - **id**: ID de la plataforma (ej. 'ethereum')
    - **contract_addresses**: Direcciones de contrato separadas por comas
    - **vs_currencies**: Monedas de referencia separadas por comas (ej. 'usd,eur')
    """
    try:
        price_data = client.get_token_price(
            id=id, 
            contract_addresses=contract_addresses, 
            vs_currencies=vs_currencies
        )
        return price_data
    except Exception as e:
        raise handle_api_error(e, f"Error al obtener precio del token")

@router.get("/simple/supported_vs_currencies", response_model=List[str], tags=["Prices"])
def get_supported_vs_currencies():
    """Obtiene una lista de todas las monedas compatibles."""
    try:
        currencies = client.get_supported_vs_currencies()
        return currencies
    except Exception as e:
        raise handle_api_error(e, "Error al obtener lista de monedas compatibles")

#===================================================================================
# ENDPOINTS DE PLATAFORMAS DE ACTIVOS
#===================================================================================

@router.get("/asset_platforms", response_model=List[AssetPlatform], tags=["Platforms"])
def get_asset_platforms():
    """Obtiene una lista de todas las plataformas de activos."""
    try:
        platforms = client.get_asset_platforms()
        return [AssetPlatform(**platform) for platform in platforms]
    except Exception as e:
        raise handle_api_error(e, "Error al obtener lista de plataformas de activos")

#===================================================================================
# ENDPOINTS DE TASAS DE CAMBIO
#===================================================================================

@router.get("/exchange_rates", response_model=ExchangeRates, tags=["Rates"])
def get_exchange_rates():
    """Obtiene las tasas de cambio actuales."""
    try:
        rates = client.get_exchange_rates()
        return ExchangeRates(**rates)
    except Exception as e:
        raise handle_api_error(e, "Error al obtener tasas de cambio")
    
#===================================================================================
# ENDPOINTS para trading
#===================================================================================
# Añade esto a tu api_coingecko.py

# Endpoints optimizados para trading
@router.get("/trading/prices", response_model=Dict[str, Any], tags=["Trading"])
async def get_trading_prices(coin_ids: str = "bitcoin,ethereum,solana,binancecoin,cardano"):
    """
    Endpoint optimizado específicamente para trading.
    Retorna precios esenciales para las criptos principales.
    """
    try:
        prices = client.get_trading_prices(coin_ids=coin_ids)
        return {
            "success": True,
            "data": prices,
            "timestamp": datetime.now().isoformat(),
            "cached": True  # Indica que viene de caché
        }
    except Exception as e:
        raise handle_api_error(e, "Error al obtener precios para trading")

@router.get("/trading/coin/{coin_id}/simple", response_model=Dict[str, Any], tags=["Trading"])
async def get_trading_coin_simple(coin_id: str):
    """
    Endpoint optimizado para datos básicos de trading de una moneda.
    """
    try:
        coin_data = client.get_coin_simple_data(coin_id)
        # Extraer solo los datos esenciales para trading
        essential_data = {
            "id": coin_data.get("id"),
            "symbol": coin_data.get("symbol"),
            "name": coin_data.get("name"),
            "market_data": {
                "current_price": coin_data.get("market_data", {}).get("current_price", {}),
                "price_change_24h": coin_data.get("market_data", {}).get("price_change_24h"),
                "price_change_percentage_24h": coin_data.get("market_data", {}).get("price_change_percentage_24h"),
                "market_cap": coin_data.get("market_data", {}).get("market_cap", {}),
            }
        }
        return {
            "success": True,
            "data": essential_data,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise handle_api_error(e, f"Error al obtener datos de trading para {coin_id}")

@router.get("/trading/coin/{coin_id}/chart", response_model=Dict[str, Any], tags=["Trading"])
async def get_trading_coin_chart(
    coin_id: str, 
    vs_currency: str = "usd",
    days: int = Query(1, ge=1, le=7, description="Días (1-7 para mejor performance)")
):
    """
    Endpoint optimizado para gráficos de trading.
    Limitado a 7 días máximo para mejor rendimiento.
    """
    try:
        chart_data = client.get_coin_market_chart_by_id(
            id=coin_id,
            vs_currency=vs_currency,
            days=days
        )
        
        # Optimizar datos para el frontend
        prices = chart_data.get("prices", [])
        if len(prices) > 100:  # Limitar a 100 puntos máximo
            step = len(prices) // 100
            prices = prices[::step]
        
        return {
            "success": True,
            "data": {
                "prices": prices,
                "total_volumes": chart_data.get("total_volumes", [])[:100],  # Limitar también volúmenes
            },
            "points": len(prices),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise handle_api_error(e, f"Error al obtener gráfico para {coin_id}")

@router.get("/trading/market/overview", response_model=Dict[str, Any], tags=["Trading"])
async def get_trading_market_overview():
    """
    Vista general optimizada del mercado para trading.
    """
    try:
        # Obtener solo las top 10 criptos para trading
        market_data = client.get_coin_market(per_page=10)
        
        overview = {
            "top_cryptos": [
                {
                    "id": coin["id"],
                    "symbol": coin["symbol"],
                    "name": coin["name"],
                    "current_price": coin["current_price"],
                    "price_change_24h": coin["price_change_24h"],
                    "price_change_percentage_24h": coin["price_change_percentage_24h"],
                    "market_cap": coin["market_cap"],
                }
                for coin in market_data
            ],
            "total_cryptos": len(market_data),
            "timestamp": datetime.now().isoformat()
        }
        
        return {"success": True, "data": overview}
    except Exception as e:
        raise handle_api_error(e, "Error al obtener vista general del mercado")

#==================================================================================
# CONOCER EL ESTADO DE LA API
#==================================================================================
@router.get("/health", tags=["Status"])
async def health_check():
    """Endpoint de salud para verificar el estado del servicio"""
    try:
        # Verificar conexión con CoinGecko
        ping_result = client.get_ping()
        
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "coin_gecko": "connected" if ping_result else "disconnected",
            "cache_size": len(client._cache),
            "performance": "optimized"
        }
    except Exception as e:
        return {
            "status": "degraded",
            "timestamp": datetime.now().isoformat(),
            "coin_gecko": "disconnected",
            "error": str(e)
        }


#==================================================================================
# ENDPOINTS PARA DASHBOARD
#==================================================================================
# Añade estos endpoints a tu api_coingecko.py

@router.get("/dashboard/quick-data", response_model=Dict[str, Any], tags=["Dashboard"])
async def get_dashboard_quick_data(coin_ids: str = "bitcoin,ethereum,binancecoin,solana,cardano"):
    """
    Endpoint ultra-optimizado para el dashboard.
    Retorna solo datos esenciales para múltiples monedas.
    """
    try:
        # Usar el método optimizado de trading
        prices_data = client.get_trading_prices(coin_ids=coin_ids)
        
        # Procesar datos mínimos
        quick_data = {}
        for coin_id in coin_ids.split(','):
            if coin_id in prices_data:
                coin_data = prices_data[coin_id]
                quick_data[coin_id] = {
                    "current_price": coin_data.get("usd", 0),
                    "price_change_24h": coin_data.get("usd_24h_change", 0),
                    "last_updated": datetime.now().isoformat()
                }
        
        return {
            "success": True,
            "data": quick_data,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise handle_api_error(e, "Error al obtener datos rápidos del dashboard")

@router.get("/dashboard/signals", response_model=Dict[str, Any], tags=["Dashboard"])
async def get_dashboard_signals(coin_id: str):
    """
    Endpoint optimizado para señales de trading.
    """
    try:
        # Obtener datos simples y rápidos
        coin_data = client.get_coin_simple_data(coin_id)
        
        # Calcular señal básica (simplificada para rendimiento)
        current_price = coin_data.get("market_data", {}).get("current_price", {}).get("usd", 0)
        price_change = coin_data.get("market_data", {}).get("price_change_percentage_24h", 0)
        
        # Señal simple basada en cambio de precio
        if price_change > 2:
            signal = "BUY"
            confidence = "high"
            reason = f"Fuerte tendencia alcista (+{price_change:.2f}%)"
        elif price_change < -2:
            signal = "SELL" 
            confidence = "high"
            reason = f"Fuerte tendencia bajista ({price_change:.2f}%)"
        else:
            signal = "HOLD"
            confidence = "medium"
            reason = "Mercado lateral, esperando señal clara"
        
        return {
            "success": True,
            "data": {
                "coin_id": coin_id,
                "signal": signal,
                "confidence": confidence,
                "reason": reason,
                "current_price": current_price,
                "price_change_24h": price_change,
                "timestamp": datetime.now().isoformat()
            }
        }
        
    except Exception as e:
        raise handle_api_error(e, f"Error al obtener señales para {coin_id}")
    
# Endpoints optimizados para el dashboard
@router.get("/dashboard/top-opportunities", response_model=Dict[str, Any], tags=["Dashboard"])
async def get_dashboard_opportunities(limit: int = Query(6, ge=1, le=20)):
    """
    Endpoint optimizado para oportunidades del dashboard.
    """
    try:
        # Obtener las top criptos por market cap
        market_data = client.get_coin_market(
            vs_currency="usd", 
            order="market_cap_desc", 
            per_page=limit,
            sparkline=False
        )
        
        opportunities = []
        for coin in market_data:
            # Calcular señal simple
            price_change = coin.get("price_change_percentage_24h", 0)
            if price_change > 3:
                signal = "BUY"
                confidence = "high"
            elif price_change < -3:
                signal = "SELL"
                confidence = "high"
            else:
                signal = "HOLD"
                confidence = "medium"
                
            opportunities.append({
                "coin": {
                    "id": coin["id"],
                    "name": coin["name"],
                    "symbol": coin["symbol"],
                    "current_price": coin["current_price"],
                    "price_change_percentage_24h": price_change,
                    "market_cap": coin["market_cap"]
                },
                "signal": {
                    "type": signal,
                    "confidence": confidence,
                    "reason": f"Cambio 24h: {price_change:.2f}%"
                }
            })
        
        return {
            "success": True,
            "opportunities": opportunities,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise handle_api_error(e, "Error al obtener oportunidades del dashboard")
    
#===================================================================================
# FIN DE ENDPOINTS
#===================================================================================