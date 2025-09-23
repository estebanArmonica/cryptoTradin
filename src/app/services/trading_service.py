from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.core.coingecko import CoinGeckoClient
from app.core.config import settings
import json
import os
from dotenv import load_dotenv
from typing import Dict, List, Optional
import asyncio

from app.models.schemas import CryptoAnalysis, FilterRequest
from app.services.prediction_service import prediction_service

# Cargar variables de entorno
load_dotenv()

class TradingService:
    def __init__(self):
        self.client = CoinGeckoClient()
        self.price_history = {}
        self.available_coins = []
        
    async def initialize(self):
        """Inicializa datos disponibles"""
        try:
            self.available_coins = await self.get_available_coins()
        except Exception as e:
            print(f"Error inicializando: {e}")
    
    async def get_available_coins(self):
        """Obtiene todas las criptomonedas disponibles"""
        try:
            coins = self.client.get_coins_list()
            return sorted(coins, key=lambda x: x['name'])
        except Exception as e:
            print(f"Error obteniendo coins disponibles: {e}")
            return []
        
    async def get_historical_data(self, coin_id: str, days: int = 7):
        """Obtiene datos históricos de precios"""
        try:
            data = self.client.get_coin_market_chart_by_id(
                id=coin_id, 
                vs_currency='usd', 
                days=days
            )
            return data.get('prices', [])
        except Exception as e:
            print(f"Error obteniendo datos históricos para {coin_id}: {e}")
            return []
    
    async def get_current_price(self, coin_id: str):
        """Obtiene el precio actual de una criptomoneda"""
        try:
            data = self.client.get_price(ids=coin_id, vs_currencies='usd')
            if coin_id in data:
                return data[coin_id]['usd']
            return None
        except Exception as e:
            print(f"Error obteniendo precio actual para {coin_id}: {e}")
            return None

    def get_current_timestamp(self):
        """Retorna el timestamp actual"""
        return datetime.now().isoformat()
    
    def calculate_metrics(self, prices, time_frame: str = "24h"):
        """Calcula métricas de trading con diferentes timeframes"""
        if not prices or len(prices) < 2:
            return None
            
        current_price = prices[-1][1] if prices else 0
        price_changes = []
        
        # Calcular cambios según el timeframe
        if time_frame == "1h":
            lookback = min(60, len(prices))
        elif time_frame == "24h":
            lookback = min(1440, len(prices))
        else:  # 7d
            lookback = len(prices)
        
        for i in range(max(1, len(prices) - lookback), len(prices)):
            if i > 0 and prices[i-1][1] != 0:
                change = ((prices[i][1] - prices[i-1][1]) / prices[i-1][1]) * 100
                price_changes.append(change)
        
        if not price_changes:
            return None
            
        avg_change = sum(price_changes) / len(price_changes)
        max_change = max(price_changes)
        min_change = min(price_changes)
        
        timestamps = [datetime.fromtimestamp(price[0]/1000).strftime('%Y-%m-%d %H:%M') for price in prices]
        price_values = [price[1] for price in prices]
        
        return {
            'current_price': current_price,
            'avg_change': avg_change,
            'max_change': max_change,
            'min_change': min_change,
            'trend': 'bullish' if avg_change > 0 else 'bearish',
            'timestamps': timestamps,
            'prices': price_values,
            'data_points': len(prices),
            'time_frame': time_frame
        }
    
    def generate_trading_signals(self, metrics, time_frame: str = "24h"):
        """Genera señales de trading basadas en timeframe"""
        if not metrics:
            return []
            
        signals = []
        current_price = metrics['current_price']
        
        if time_frame == "1h":
            threshold = 1.0
        elif time_frame == "24h":
            threshold = 3.0
        else:
            threshold = 10.0
        
        if metrics['avg_change'] < -threshold:
            signals.append({
                'type': 'BUY',
                'price': current_price,
                'reason': f'Precio en caída ({metrics["avg_change"]:.2f}% en {time_frame})',
                'confidence': 'high' if abs(metrics['avg_change']) > threshold * 1.5 else 'medium',
                'timestamp': self.get_current_timestamp(),
                'time_frame': time_frame
            })
        elif metrics['avg_change'] > threshold:
            signals.append({
                'type': 'SELL', 
                'price': current_price,
                'reason': f'Precio en subida ({metrics["avg_change"]:.2f}% en {time_frame})',
                'confidence': 'high' if metrics['avg_change'] > threshold * 1.5 else 'medium',
                'timestamp': self.get_current_timestamp(),
                'time_frame': time_frame
            })
        else:
            signals.append({
                'type': 'HOLD',
                'price': current_price,
                'reason': f'Mercado estable ({metrics["avg_change"]:.2f}% en {time_frame})',
                'confidence': 'low',
                'timestamp': self.get_current_timestamp(),
                'time_frame': time_frame
            })
        
        return signals
    
    async def calculate_crypto_value(self, coin_id: str, amount: float):
        """Calcula el valor en USD de una cantidad de cryptocurrency"""
        try:
            current_price = await self.get_current_price(coin_id)
            if current_price is None:
                return None
                
            return {
                'coin_id': coin_id,
                'amount': amount,
                'price_per_coin': current_price,
                'total_value_usd': amount * current_price,
                'timestamp': self.get_current_timestamp()
            }
        except Exception as e:
            print(f"Error calculando valor: {e}")
            return None
    
    async def analyze_time_frame(self, coin_id: str, start_time: str, end_time: str):
        """Analiza un timeframe específico para una cryptomoneda"""
        try:
            start_dt = datetime.fromisoformat(start_time)
            end_dt = datetime.fromisoformat(end_time)
            
            days = (end_dt - start_dt).days + 1
            prices = await self.get_historical_data(coin_id, days)
            
            filtered_prices = []
            for price in prices:
                price_time = datetime.fromtimestamp(price[0]/1000)
                if start_dt <= price_time <= end_dt:
                    filtered_prices.append(price)
            
            if not filtered_prices or len(filtered_prices) < 2:
                return None
                
            start_price = filtered_prices[0][1]
            end_price = filtered_prices[-1][1]
            if start_price == 0:
                return None
                
            price_change = ((end_price - start_price) / start_price) * 100
            
            return {
                'coin_id': coin_id,
                'start_time': start_time,
                'end_time': end_time,
                'start_price': start_price,
                'end_price': end_price,
                'price_change_percent': price_change,
                'trend': 'bullish' if price_change > 0 else 'bearish',
                'timeframe_days': days,
                'data_points': len(filtered_prices)
            }
            
        except Exception as e:
            print(f"Error analizando timeframe: {e}")
            return None
    
    async def send_email_alert(self, subject, message, to_email):
        """Envía alertas por correo"""
        try:
            smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
            smtp_port = int(os.getenv("SMTP_PORT", 587))
            sender_email = os.getenv("EMAIL_USER")
            password = os.getenv("EMAIL_PASSWORD")
            
            if not all([smtp_server, smtp_port, sender_email, password]):
                print("Error: Configuración de email incompleta")
                return False
            
            msg = MIMEMultipart()
            msg['From'] = sender_email
            msg['To'] = to_email
            msg['Subject'] = subject
            
            html_message = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 20px; }}
                    .alert {{ border: 2px solid #007bff; padding: 20px; border-radius: 10px; }}
                </style>
            </head>
            <body>
                <div class="alert">
                    <h2>🚨 Alerta de Trading</h2>
                    <p>{message}</p>
                    <p><strong>Timestamp:</strong> {self.get_current_timestamp()}</p>
                </div>
            </body>
            </html>
            """
            
            msg.attach(MIMEText(html_message, 'html'))
            
            server = smtplib.SMTP(smtp_server, smtp_port)
            server.starttls()
            server.login(sender_email, password)
            server.send_message(msg)
            server.quit()
            
            print(f"✅ Email enviado a {to_email}")
            return True
            
        except Exception as e:
            print(f"❌ Error enviando email: {e}")
            return False
        
    async def get_coin_analysis(self, coin_id: str, days: int = 30):
        """Obtiene análisis completo de una criptomoneda."""
        try:
            print(f"🔍 Analizando {coin_id} por {days} días...")
            
            historical_data = await self.get_historical_data(coin_id, days)
            current_price = await self.get_current_price(coin_id)
            
            if not historical_data or current_price is None:
                print(f"❌ No se pudieron obtener datos para {coin_id}")
                return None
            
            market_data = self.client.get_coin_market(
                vs_currency='usd',
                ids=coin_id,
                per_page=1,
                page=1
            )
            
            if market_data:
                market_info = market_data[0]
                price_change_24h = market_info.get('price_change_percentage_24h', 0)
                market_cap = market_info.get('market_cap', 0)
                volume_24h = market_info.get('total_volume', 0)
            else:
                price_change_24h = 0
                market_cap = 0
                volume_24h = 0
            
            signals = prediction_service.generate_trading_signals(historical_data, current_price)
            prediction = prediction_service.predict_price_trend(historical_data)
            
            best_action = "HOLD"
            action_reason = "Análisis neutral"
            
            if signals and len(signals) > 0:
                if signals[0].type == "BUY" and signals[0].confidence == "high":
                    best_action = "BUY"
                    action_reason = "Señal fuerte de compra detectada"
                elif signals[0].type == "SELL" and signals[0].confidence == "high":
                    best_action = "SELL"
                    action_reason = "Señal fuerte de venta detectada"
            
            limited_historical = historical_data[-100:] if len(historical_data) > 100 else historical_data
            
            # ✅ CORRECCIÓN: Usar timestamp numérico en lugar de string
            analysis = CryptoAnalysis(
                coin_id=coin_id,
                current_price=current_price,
                price_change_24h=price_change_24h,
                market_cap=market_cap,
                volume_24h=volume_24h,
                signals=signals,
                predictions=[prediction] if prediction else [],
                historical_data=[
                    {"timestamp": price[0], "price": price[1]}  # ← TIMESTAMP COMO NÚMERO
                    for price in limited_historical
                ],
                best_action=best_action,
                action_reason=action_reason
            )
            
            print(f"✅ Análisis completado para {coin_id}")
            return analysis
            
        except Exception as e:
            print(f"❌ Error en análisis de {coin_id}: {str(e)}")
            return CryptoAnalysis(
                coin_id=coin_id,
                current_price=0,
                price_change_24h=0,
                market_cap=0,
                volume_24h=0,
                signals=[],
                predictions=[],
                historical_data=[],
                best_action="HOLD",
                action_reason=f"Error en el análisis: {str(e)}"
            )
    
    async def get_filtered_coins(self, filters: FilterRequest):
        """Obtiene criptomonedas filtradas según criterios."""
        try:
            print(f"🔍 Aplicando filtros: {filters}")
            
            market_data = self.client.get_coin_market(
                vs_currency='usd',
                order='market_cap_desc',
                per_page=filters.limit * 2,
                page=1
            )
            
            filtered_coins = []
            
            for coin in market_data:
                if filters.min_price is not None and coin['current_price'] < filters.min_price:
                    continue
                if filters.max_price is not None and coin['current_price'] > filters.max_price:
                    continue
                
                if filters.min_market_cap is not None and coin['market_cap'] < filters.min_market_cap:
                    continue
                
                price_change = coin.get('price_change_percentage_24h', 0)
                if filters.trend == "bullish" and price_change <= 0:
                    continue
                if filters.trend == "bearish" and price_change >= 0:
                    continue
                
                filtered_coins.append(coin)
                
                if len(filtered_coins) >= filters.limit:
                    break
            
            print(f"✅ Filtros aplicados. Encontradas {len(filtered_coins)} monedas")
            return filtered_coins
            
        except Exception as e:
            print(f"❌ Error filtrando coins: {str(e)}")
            return []
    
    async def get_top_opportunities(self, limit: int = 10):
        """Obtiene las mejores oportunidades de trading."""
        try:
            print(f"💎 Buscando top {limit} oportunidades...")
            
            market_data = self.client.get_coin_market(
                vs_currency='usd',
                order='market_cap_desc',
                per_page=limit * 3,
                page=1
            )
            
            opportunities = []
            
            for coin in market_data:
                try:
                    coin_id = coin['id']
                    
                    historical_data = await self.get_historical_data(coin_id, 7)
                    
                    if not historical_data or len(historical_data) < 2:
                        continue
                    
                    prices = [price[1] for price in historical_data]
                    current_price = prices[-1]
                    previous_price = prices[-2] if len(prices) >= 2 else current_price
                    
                    if previous_price == 0:
                        continue
                    
                    price_change = ((current_price - previous_price) / previous_price) * 100
                    
                    if price_change < -3:
                        opportunities.append({
                            'coin': coin,
                            'signal': {
                                'type': 'BUY',
                                'confidence': 'high' if price_change < -8 else 'medium',
                                'reason': f'Caída de {abs(price_change):.1f}% en 24 horas, posible rebote',
                                'price': current_price,
                                'timestamp': self.get_current_timestamp()
                            }
                        })
                        
                except Exception as e:
                    print(f"Error analizando {coin['id']}: {e}")
                    continue
            
            opportunities.sort(key=lambda x: abs(x['signal']['price'] - x['coin']['current_price']), reverse=True)
            
            print(f"✅ Encontradas {len(opportunities)} oportunidades")
            return opportunities[:limit]
            
        except Exception as e:
            print(f"❌ Error obteniendo oportunidades: {str(e)}")
            return []

trading_service = TradingService()