import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from app.core.coingecko import CoinGeckoClient
from app.models.schemas import PricePrediction, TradingSignal
import logging

logger = logging.getLogger(__name__)

class PredictionService:
    def __init__(self):
        self.client = CoinGeckoClient()
    
    def calculate_moving_averages(self, prices: List[float], window_sizes: List[int] = [5, 10, 20]):
        """Calcula medias móviles para diferentes ventanas."""
        ma_results = {}
        for window in window_sizes:
            if len(prices) >= window:
                ma = sum(prices[-window:]) / window
                ma_results[f'ma_{window}'] = ma
        return ma_results
    
    def calculate_rsi(self, prices: List[float], period: int = 14):
        """Calcula el RSI (Relative Strength Index)."""
        if len(prices) < period + 1:
            return 50  # Valor neutral si no hay suficientes datos
        
        changes = [prices[i] - prices[i-1] for i in range(1, len(prices))]
        gains = [change for change in changes if change > 0]
        losses = [-change for change in changes if change < 0]
        
        avg_gain = sum(gains[-period:]) / period if gains else 0
        avg_loss = sum(losses[-period:]) / period if losses else 0
        
        if avg_loss == 0:
            return 100
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def predict_price_trend(self, historical_data: List[List], time_frame_hours: int = 24):
        """Predice la tendencia del precio."""
        if not historical_data or len(historical_data) < 10:
            return None
        
        prices = [price[1] for price in historical_data]
        timestamps = [price[0] for price in historical_data]
        
        # Calcular métricas técnicas
        current_price = prices[-1]
        ma_5 = self.calculate_moving_averages(prices, [5]).get('ma_5', current_price)
        ma_10 = self.calculate_moving_averages(prices, [10]).get('ma_10', current_price)
        rsi = self.calculate_rsi(prices)
        
        # Análisis de tendencia
        price_change = ((current_price - prices[0]) / prices[0]) * 100
        recent_change = ((current_price - prices[-5]) / prices[-5]) * 100 if len(prices) >= 5 else 0
        
        # Lógica de predicción simple (mejorable con ML)
        if rsi < 30 and current_price < ma_5 and current_price < ma_10:
            # Sobreventa - probable rebote alcista
            predicted_change = abs(recent_change) * 0.5  # Recuperación del 50% de la caída
            trend = "bullish"
            confidence = min(0.8, (30 - rsi) / 30)  # Más confianza cuanto más sobreventa
        elif rsi > 70 and current_price > ma_5 and current_price > ma_10:
            # Sobrecompra - probable corrección
            predicted_change = -abs(recent_change) * 0.3  # Corrección del 30% de la subida
            trend = "bearish"
            confidence = min(0.8, (rsi - 70) / 30)
        else:
            # Tendencia neutral
            predicted_change = recent_change * 0.5  # Continúa tendencia pero más suave
            trend = "bullish" if predicted_change > 0 else "bearish"
            confidence = 0.5
        
        predicted_price = current_price * (1 + predicted_change / 100)
        
        return PricePrediction(
            coin_id="",  # Se setea después
            current_price=current_price,
            predicted_price=predicted_price,
            change_percentage=predicted_change,
            predicted_trend=trend,
            confidence=confidence,
            timeframe_hours=time_frame_hours
        )
    
    def generate_trading_signals(self, historical_data: List[List], current_price: float):
        """Genera señales de trading basadas en análisis técnico."""
        if not historical_data:
            return []
        
        prices = [price[1] for price in historical_data]
        signals = []
        
        # Calcular indicadores
        rsi = self.calculate_rsi(prices)
        ma_5 = self.calculate_moving_averages(prices, [5]).get('ma_5', current_price)
        ma_20 = self.calculate_moving_averages(prices, [20]).get('ma_20', current_price)
        
        # Señal de compra (sobreventa + tendencia alcista)
        if rsi < 30 and current_price > ma_20:
            signals.append(TradingSignal(
                type="BUY",
                price=current_price,
                reason=f"RSI en sobreventa ({rsi:.1f}) y precio sobre media 20 días",
                confidence="high",
                timestamp=datetime.now().isoformat(),
                time_frame="24h"
            ))
        
        # Señal de venta (sobrecompra)
        elif rsi > 70:
            signals.append(TradingSignal(
                type="SELL",
                price=current_price,
                reason=f"RSI en sobrecompra ({rsi:.1f})",
                confidence="medium",
                timestamp=datetime.now().isoformat(),
                time_frame="24h"
            ))
        
        # Señal de tendencia alcista
        elif current_price > ma_5 and ma_5 > ma_20:
            signals.append(TradingSignal(
                type="BUY",
                price=current_price,
                reason="Tendencia alcista fuerte (precio > MA5 > MA20)",
                confidence="medium",
                timestamp=datetime.now().isoformat(),
                time_frame="24h"
            ))
        
        # Señal neutral si no hay señales fuertes
        if not signals:
            signals.append(TradingSignal(
                type="HOLD",
                price=current_price,
                reason="Mercado en rango lateral, esperar señales más claras",
                confidence="low",
                timestamp=datetime.now().isoformat(),
                time_frame="24h"
            ))
        
        return signals

prediction_service = PredictionService()