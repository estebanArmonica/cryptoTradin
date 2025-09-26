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

#=========================================================================================
# Nuevos modelos para los nuevos endpoints
#=========================================================================================

class CoinDetail(BaseModel):
    """
    Modelo de detalle de criptomoneda.
    """
    id: str
    symbol: str
    name: str
    description: Dict[str, Any]
    market_data: Dict[str, Any]
    genesis_date: Optional[str] = None
    hashing_algorithm: Optional[str] = None
    links: Dict[str, Any]
    image: Dict[str, Any]
    last_updated: str

class CoinTicker(BaseModel):
    """
    Modelo de ticker de criptomoneda.
    """
    base: str
    target: str
    market: Dict[str, Any]
    last: float
    volume: float
    converted_last: Dict[str, float]
    converted_volume: Dict[str, float]
    trust_score: str
    bid_ask_spread_percentage: Optional[float] = None
    timestamp: str
    last_traded_at: str
    last_fetch_at: str
    is_anomaly: bool
    is_stale: bool
    trade_url: Optional[str] = None
    token_info_url: Optional[str] = None
    coin_id: Optional[str] = None
    target_coin_id: Optional[str] = None

class CoinHistoricalById(BaseModel):
    """
    Modelo de datos históricos de criptomoneda por ID, nombre, precio, mercado y estadisticas.
    """
    id: str
    symbol: str
    name: str
    market_data: Dict[str, Any]
    community_data: Dict[str, Any]
    developer_data: Dict[str, Any]
    public_interest_stats: Dict[str, Any]
    last_updated: str

class CoinMarketChart(BaseModel):
    """
    Modelo de datos de mercado de criptomoneda en un rango de fechas.
    """
    prices: List[List[float]]
    market_caps: List[List[float]]
    total_volumes: List[List[float]]

#=========================================================================================
# MODELOS NUEVOS
#=========================================================================================

class CoinHistory(BaseModel):
    """
    Modelo de datos históricos de criptomoneda por ID y fecha.
    """
    id: str
    symbol: str
    name: str
    localization: Dict[str, str] = Field(default_factory=dict)
    image: Dict[str, str]
    market_data: Dict[str, Any]
    community_data: Dict[str, Any]
    developer_data: Dict[str, Any]
    public_interest_stats: Dict[str, Any]

class CoinMarketChartRange(BaseModel):
    """
    Modelo de datos de mercado en un rango de tiempo específico.
    """
    prices: List[List[float]]
    market_caps: List[List[float]]
    total_volumes: List[List[float]]

class OHLCData(BaseModel):
    """
    Modelo de datos OHLC (Open, High, Low, Close).
    """
    timestamp: int
    open: float
    high: float
    low: float
    close: float

class Exchange(BaseModel):
    """
    Modelo básico de exchange.
    """
    id: str
    name: str
    year_established: Optional[int] = None
    country: Optional[str] = None
    description: Optional[str] = None
    url: str
    image: str
    has_trading_incentive: Optional[bool] = False
    trust_score: Optional[int] = None
    trust_score_rank: Optional[int] = None
    trade_volume_24h_btc: Optional[float] = None
    trade_volume_24h_btc_normalized: Optional[float] = None

class ExchangeIdName(BaseModel):
    """
    Modelo para ID y nombre de exchange.
    """
    id: str
    name: str

class ExchangeDetail(BaseModel):
    """
    Modelo detallado de exchange.
    """
    id: str
    name: str
    year_established: Optional[int] = None
    country: Optional[str] = None
    description: Optional[str] = None
    url: str
    image: str
    facebook_url: Optional[str] = None
    reddit_url: Optional[str] = None
    telegram_url: Optional[str] = None
    slack_url: Optional[str] = None
    other_url_1: Optional[str] = None
    other_url_2: Optional[str] = None
    twitter_handle: Optional[str] = None
    has_trading_incentive: bool = False
    centralized: bool = True
    public_notice: Optional[str] = None
    alert_notice: Optional[str] = None
    trust_score: int
    trust_score_rank: int
    trade_volume_24h_btc: float
    trade_volume_24h_btc_normalized: float
    tickers: List[Dict[str, Any]] = Field(default_factory=list)
    status_updates: List[Dict[str, Any]] = Field(default_factory=list)

class ExchangeTickers(BaseModel):
    """
    Modelo para tickers de exchange.
    """
    name: str
    tickers: List[Dict[str, Any]]
    tickers_count: int

class VolumeChartData(BaseModel):
    """
    Modelo para datos de volumen de exchange.
    """
    timestamp: int
    volume: float

class TrendingCoins(BaseModel):
    """
    Modelo para criptomonedas en tendencia.
    """
    coins: List[Dict[str, Any]] = Field(default_factory=list)
    nfts: List[Dict[str, Any]] = Field(default_factory=list)
    categories: List[Dict[str, Any]] = Field(default_factory=list)

class AssetPlatform(BaseModel):
    """
    Modelo para plataformas de activos.
    """
    id: str
    chain_identifier: Optional[int] = None
    name: str
    shortname: str

class ExchangeRates(BaseModel):
    """
    Modelo para tasas de cambio.
    """
    rates: Dict[str, Dict[str, Any]]

#=========================================================================================
# Modelos para endpoints adicionales (NFTs, Derivados, Índices)
#=========================================================================================

class NFTItem(BaseModel):
    """
    Modelo básico para NFT.
    """
    id: str
    contract_address: str
    asset_platform_id: str
    name: str
    symbol: str
    image: Dict[str, str]

class NFTDetail(BaseModel):
    """
    Modelo detallado para NFT.
    """
    id: str
    contract_address: str
    asset_platform_id: str
    name: str
    symbol: str
    image: Dict[str, str]
    description: Optional[str] = None
    native_currency: str
    floor_price: Optional[Dict[str, Any]] = None
    market_cap: Optional[Dict[str, Any]] = None
    volume_24h: Optional[Dict[str, Any]] = None
    floor_price_in_usd_24h_percentage_change: Optional[float] = None

class Derivative(BaseModel):
    """
    Modelo para derivados.
    """
    market: str
    symbol: str
    index_id: str
    price: Optional[float] = None
    price_percentage_change_24h: Optional[float] = None
    contract_type: str
    index: float
    basis: float
    spread: float
    funding_rate: float
    open_interest: float
    volume_24h: float
    last_traded_at: int
    expired_at: Optional[int] = None

class DerivativeExchange(BaseModel):
    """
    Modelo para exchange de derivados.
    """
    id: str
    name: str
    open_interest_btc: Optional[float] = None
    trade_volume_24h_btc: Optional[str] = None
    number_of_perpetual_pairs: Optional[int] = None
    number_of_futures_pairs: Optional[int] = None
    image: str
    year_established: Optional[int] = None
    country: Optional[str] = None
    description: Optional[str] = None
    url: Optional[str] = None

class Index(BaseModel):
    """
    Modelo para índices.
    """
    name: str
    id: str
    market: str
    last: Optional[float] = None
    is_multi_asset_composite: Optional[bool] = None

class IndexDetail(BaseModel):
    """
    Modelo detallado para índice.
    """
    name: str
    id: str
    market: str
    last: float
    is_multi_asset_composite: bool
    indexes: List[Dict[str, Any]]

#=========================================================================================
# Modelos para respuestas de búsqueda y filtros
#=========================================================================================

class SearchResponse(BaseModel):
    """
    Modelo para respuesta de búsqueda.
    """
    coins: List[SearchQuery]
    exchanges: List[Dict[str, Any]] = Field(default_factory=list)
    icos: List[Dict[str, Any]] = Field(default_factory=list)
    categories: List[Dict[str, Any]] = Field(default_factory=list)
    nfts: List[Dict[str, Any]] = Field(default_factory=list)

class GlobalMarketCapChart(BaseModel):
    """
    Modelo para gráfico de capitalización de mercado global.
    """
    market_cap: List[List[float]]
    volume: List[List[float]]

class TokenPrice(BaseModel):
    """
    Modelo para precio de token por dirección de contrato.
    """
    token_address: str
    prices: Dict[str, float]

#=========================================================================================
# Modelos para respuestas paginadas
#=========================================================================================

class PaginatedResponse(BaseModel):
    """
    Modelo base para respuestas paginadas.
    """
    page: int
    per_page: int
    total: int
    total_pages: int

class PaginatedCoins(PaginatedResponse):
    """
    Modelo para lista paginada de criptomonedas.
    """
    coins: List[CoinMarket]

class PaginatedExchanges(PaginatedResponse):
    """
    Modelo para lista paginada de exchanges.
    """
    exchanges: List[Exchange]

#=========================================================================================
# Modelos para estadísticas y métricas
#=========================================================================================

class MarketStats(BaseModel):
    """
    Modelo para estadísticas de mercado.
    """
    total_market_cap: Dict[str, float]
    total_volume: Dict[str, float]
    market_cap_percentage: Dict[str, float]
    market_cap_change_percentage_24h_usd: float
    updated_at: int

class CoinStats(BaseModel):
    """
    Modelo para estadísticas de criptomoneda.
    """
    coin_id: str
    price_change_24h: float
    price_change_percentage_24h: float
    market_cap_change_24h: float
    market_cap_change_percentage_24h: float
    circulating_supply: float
    total_supply: float
    max_supply: Optional[float] = None
    ath: float
    ath_change_percentage: float
    ath_date: Dict[str, str]
    atl: float
    atl_change_percentage: float
    atl_date: Dict[str, str]
    last_updated: str

#=========================================================================================
# Modelos para datos de comunidad y desarrolladores
#=========================================================================================

class CommunityData(BaseModel):
    """
    Modelo para datos de comunidad.
    """
    facebook_likes: Optional[int] = None
    twitter_followers: Optional[int] = None
    reddit_average_posts_48h: Optional[float] = None
    reddit_average_comments_48h: Optional[float] = None
    reddit_subscribers: Optional[int] = None
    reddit_accounts_active_48h: Optional[int] = None
    telegram_channel_user_count: Optional[int] = None

class DeveloperData(BaseModel):
    """
    Modelo para datos de desarrolladores.
    """
    forks: Optional[int] = None
    stars: Optional[int] = None
    subscribers: Optional[int] = None
    total_issues: Optional[int] = None
    closed_issues: Optional[int] = None
    pull_requests_merged: Optional[int] = None
    pull_request_contributors: Optional[int] = None
    code_additions_deletions_4_weeks: Optional[Dict[str, int]] = None
    commit_count_4_weeks: Optional[int] = None

#=========================================================================================
# Modelos para datos de contratos
#=========================================================================================

class ContractInfo(BaseModel):
    """
    Modelo para información de contrato.
    """
    contract_address: str
    platform_id: str
    name: str
    symbol: str
    decimals: int
    image: Dict[str, str]

class ContractMarketData(BaseModel):
    """
    Modelo para datos de mercado de contrato.
    """
    contract_address: str
    platform_id: str
    current_price: Dict[str, float]
    market_cap: Dict[str, float]
    total_volume: Dict[str, float]
    price_change_24h: float
    price_change_percentage_24h: float
    market_cap_change_24h: float
    market_cap_change_percentage_24h: float
    last_updated: str

#=============================================================================
# FIN DE MODELOS NUEVOS
#=============================================================================

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