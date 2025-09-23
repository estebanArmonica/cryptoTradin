from fastapi import APIRouter, HTTPException, Query, Depends
from typing import List, Optional
from app.services.trading_service import trading_service
from app.models.schemas import CryptoAnalysis, FilterRequest, TradingSignal
from app.utils.exceptions import handle_api_error
from datetime import datetime

router = APIRouter()

@router.get("/global-metrics", tags=["Dashboard"])
async def get_global_metrics():
    """Métricas globales del mercado"""
    try:
        global_data = trading_service.client.get_global_data()
        return {
            "total_market_cap": global_data.get('total_market_cap', {}).get('usd', 0),
            "total_volume": global_data.get('total_volume', {}).get('usd', 0),
            "market_cap_change_24h": global_data.get('market_cap_change_percentage_24h_usd', 0),
            "active_cryptocurrencies": global_data.get('active_cryptocurrencies', 0),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise handle_api_error(e, "Error obteniendo métricas globales")

@router.get("/analysis/{coin_id}", response_model=CryptoAnalysis, tags=["Dashboard"])
async def get_coin_analysis(coin_id: str, days: int = 30):
    """Obtiene análisis completo de una criptomoneda."""
    try:
        analysis = await trading_service.get_coin_analysis(coin_id, days)
        if not analysis:
            raise HTTPException(status_code=404, detail="Análisis no disponible")
        return analysis
    except Exception as e:
        raise handle_api_error(e, f"Error obteniendo análisis de {coin_id}")

@router.post("/filter", response_model=List[dict], tags=["Dashboard"])
async def filter_coins(filters: FilterRequest):
    """Filtra criptomonedas según criterios."""
    try:
        # Usar el método existente de trading_service
        market_data = trading_service.client.get_coin_market(
            vs_currency='usd',
            order='market_cap_desc',
            per_page=filters.limit,
            page=1
        )
        
        filtered_coins = []
        
        for coin in market_data:
            # Aplicar filtros
            if filters.min_price and coin['current_price'] < filters.min_price:
                continue
            if filters.max_price and coin['current_price'] > filters.max_price:
                continue
            if filters.min_market_cap and coin['market_cap'] < filters.min_market_cap:
                continue
            
            # Filtro de tendencia
            price_change = coin.get('price_change_percentage_24h', 0)
            if filters.trend == "bullish" and price_change <= 0:
                continue
            if filters.trend == "bearish" and price_change >= 0:
                continue
            
            filtered_coins.append(coin)
        
        return filtered_coins
        
    except Exception as e:
        raise handle_api_error(e, "Error filtrando criptomonedas")

@router.get("/top-opportunities", response_model=List[dict], tags=["Dashboard"])
async def get_top_opportunities(limit: int = 10):
    """Obtiene las mejores oportunidades de trading."""
    try:
        # Obtener datos del mercado
        market_data = trading_service.client.get_coins_markets(
            vs_currency='usd',
            order='market_cap_desc',
            per_page=limit * 3,  # Obtener más para filtrar
            page=1
        )
        
        opportunities = []
        
        for coin in market_data[:limit*2]:  # Limitar el análisis
            try:
                coin_id = coin['id']
                
                # Obtener datos históricos para análisis
                historical_data = trading_service.client.get_coin_market_chart_by_id(
                    id=coin_id, 
                    vs_currency='usd', 
                    days=7
                )
                
                if not historical_data or 'prices' not in historical_data:
                    continue
                
                # Análisis simple de tendencia
                prices = [price[1] for price in historical_data['prices']]
                if len(prices) < 2:
                    continue
                
                current_price = prices[-1]
                previous_price = prices[-2] if len(prices) >= 2 else current_price
                price_change = ((current_price - previous_price) / previous_price) * 100
                
                # Considerar como oportunidad si hay una caída significativa
                if price_change < -5:  # Más del 5% de caída
                    opportunities.append({
                        'coin': coin,
                        'signal': {
                            'type': 'BUY',
                            'confidence': 'high' if price_change < -10 else 'medium',
                            'reason': f'Caída de {abs(price_change):.1f}% en 24 horas, posible rebote',
                            'price': current_price
                        }
                    })
                    
            except Exception as e:
                print(f"Error analizando {coin['id']}: {e}")
                continue
        
        # Ordenar por mayor oportunidad (mayor caída)
        opportunities.sort(key=lambda x: x['signal']['confidence'] == 'high', reverse=True)
        return opportunities[:limit]
        
    except Exception as e:
        raise handle_api_error(e, "Error obteniendo oportunidades")