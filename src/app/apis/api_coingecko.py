from fastapi import APIRouter, Depends, HTTPException
from typing import List
from app.core.coingecko import CoinGeckoClient
from app.models.schemas import *
from app.utils.exceptions import handle_api_error

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
def get_coin_market(vs_currency: str = "usd", order: str = "market_cap_desc", per_page: int = 100, page: int = 1):  
    """
    Obtiene el mercado de criptomonedas.
    
    - **vs_currency**: Moneda contra la que se comparan los precios (ej. 'usd')
    - **order**: Orden de los resultados (ej. 'market_cap_desc', 'volume_desc', etc.)
    - **per_page**: Número de resultados por página
    - **page**: Número de página a obtener
    """
    try:
        market_data = client.get_coin_market(vs_currency=vs_currency, order=order, per_page=per_page, page=page)
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