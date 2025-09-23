from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field

# creamos un modelo de Pydantic para documentar en Swagger
class PingResponse(BaseModel):
    """
    Modelo de respuesta para la verificación del ping del servidor de CoinGecko.
    """
    success: bool
    message: str

class CoinCategory(BaseModel):
    """
    Modelo de categoría de criptomonedas.
    """
    id: str
    name: str

class CoinPrice(BaseModel):
    """
    Modelo de precio de criptomonedas.
    """
    coin_id: str
    prices: dict

class CoinListItem(BaseModel):
    """
    Modelo de elemento de la lista de criptomonedas.
    """
    id: str
    symbol: str
    name: str

class GlobalData(BaseModel):
    """
    Modelo de datos globales del mercado de criptomonedas.
    """
    active_cryptocurrencies: int
    upcoming_icos: int
    ongoing_icos: int
    ended_icos: int
    markets: int
    total_market_cap: dict
    total_volume: dict
    market_cap_percentage: dict
    market_cap_change_percentage_24h_usd: float
    updated_at: int

class DecentralizedFinance(BaseModel):
    """
    Modelo de datos de finanzas descentralizadas.
    """
    defi_market_cap: str
    eth_market_cap: str
    defi_to_eth_ratio: str
    trading_volume_24h: str
    defi_dominance: str
    top_coin_name: str
    top_coin_defi_dominance: float

class CompanyInfo(BaseModel):
    """
    Modelo de información de la empresa.
    """
    name: str
    symbol: str
    country: str
    total_holdings: float
    total_entry_value_usd: float
    total_current_value_usd: float
    percentage_of_total_supply: float

class CoinMarket(BaseModel):
    id: str
    symbol: str
    name: str
    image: str
    current_price: float
    market_cap: float
    total_volume: float
    high_24h: float
    low_24h: float
    price_change_24h: float
    price_change_percentage_24h: float
    market_cap_change_24h: float
    market_cap_change_percentage_24h: float
    circulating_supply: float
    total_supply: float
    ath: float
    ath_change_percentage: float
    last_updated: str

class SearchQuery(BaseModel):
    """
    Modelo de consulta de búsqueda.
    """
    id: str
    name: str
    api_symbol: str
    symbol: str
    market_cap_rank: Optional[int] = None
    thumb: str
    large: str

class TradingSignal(BaseModel):
    """Modelo para señales de trading."""
    type: str  # BUY, SELL, HOLD
    price: float
    reason: str
    confidence: str  # high, medium, low
    timestamp: str
    time_frame: str

class PricePrediction(BaseModel):
    """Modelo para predicciones de precio."""
    coin_id: str
    current_price: float
    predicted_price: float
    change_percentage: float
    predicted_trend: str  # bullish, bearish
    confidence: float
    timeframe_hours: int

class HistoricalDataPoint(BaseModel):
    """Modelo para puntos de datos históricos."""
    timestamp: Union[str, float, int] = Field(..., description="Timestamp en formato string, float o int")
    price: float

class CryptoAnalysis(BaseModel):
    """Modelo completo de análisis."""
    coin_id: str
    current_price: float
    price_change_24h: float
    market_cap: float
    volume_24h: float
    signals: List[TradingSignal]
    predictions: List[PricePrediction]
    historical_data: List[HistoricalDataPoint] = Field(
        default_factory=list,
        description="Lista de datos históricos de precios"
    )
    best_action: str
    action_reason: str

    class Config:
        arbitrary_types_allowed = True
        json_encoders = {
            # Asegurar que los timestamps se serialicen correctamente
            'datetime': lambda v: v.isoformat() if hasattr(v, 'isoformat') else str(v)
        }

class FilterRequest(BaseModel):
    """Modelo para filtros del dashboard."""
    time_frame: str = "24h"
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    min_market_cap: Optional[float] = None
    trend: Optional[str] = None
    limit: int = 50

# Modelos adicionales para los nuevos endpoints
class MarketPerformance(BaseModel):
    """Modelo para el rendimiento del mercado."""
    total_market_cap: float
    total_volume: float
    volume_market_cap_ratio: float
    market_cap_change_24h: float
    active_cryptocurrencies: int
    upcoming_icos: int
    ongoing_icos: int
    ended_icos: int
    markets: int
    bitcoin_dominance: float
    ethereum_dominance: float
    timestamp: str
    last_updated: Optional[int] = None

class Opportunity(BaseModel):
    """Modelo para oportunidades de trading."""
    coin: Dict[str, Any]
    signal: Dict[str, Any]

class TopCoinsResponse(BaseModel):
    """Modelo para respuesta de top coins."""
    coins: List[Dict[str, Any]]
    limit: int
    timestamp: str

class TradingMetrics(BaseModel):
    """Modelo para métricas de trading."""
    coin_id: str
    time_frame: str
    days_analyzed: int
    current_price: float
    metrics: Dict[str, Any]
    timestamp: str
    data_points: int

class CryptoValueCalculation(BaseModel):
    """Modelo para cálculo de valor de cripto."""
    coin_id: str
    amount: float
    price_per_coin: float
    total_value: float
    currency: str
    timestamp: str
    exchange_rate: float