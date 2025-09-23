class CryptoDashboard {
    constructor() {
        this.currentCoin = 'bitcoin';
        this.currentData = null;
        this.useDemoMode = false;
        this.emaPeriod = 20;
        this.futurePeriods = 5;
        this.ohlcData = [];
        this.emaData = [];
        this.futureEmaData = [];
        this.autoRefreshInterval = null;
        this.autoRefreshEnabled = true;
        this.autoRefreshTime = 90000; // 1 minuto y medio
        this.init();
    }

    async init() {
        console.log("🚀 Inicializando dashboard con datos reales...");
        this.updateLastUpdatedTime();
        await this.loadGlobalMetrics();
        await this.loadOpportunities();
        this.setupEventListeners();
        await this.loadCoinData(this.currentCoin, 30);

        // Iniciar actualización automática
        this.startAutoRefresh();

        // Detectar cuando la pestaña está inactiva para optimizar recursos
        this.handleVisibilityChange();

        // Cargar configuración de notificaciones
        this.loadNotificationSettings();
    }

    setupEventListeners() {
        // Selector de moneda
        const coinSelector = document.getElementById('coinSelector');
        if (coinSelector) {
            coinSelector.addEventListener('change', (e) => {
                this.currentCoin = e.target.value;
                this.loadCoinData(this.currentCoin, 30);
            });
        }

        // Botón de recarga
        const reloadBtn = document.getElementById('reloadBtn');
        if (reloadBtn) {
            reloadBtn.addEventListener('click', () => {
                this.reloadAllData();
            });
        }

        // Botones de timeframe
        document.querySelectorAll('.timeframe-btn').forEach(btn => {
            btn.addEventListener('click', function () {
                document.querySelectorAll('.timeframe-btn').forEach(b => b.classList.remove('active'));
                this.classList.add('active');

                const timeframe = parseInt(this.getAttribute('data-timeframe'));
                dashboard.loadCoinData(dashboard.currentCoin, timeframe);
            });
        });

        // Controles EMA
        const emaPeriodInput = document.getElementById('emaPeriod');
        const futurePeriodsInput = document.getElementById('futurePeriods');
        const calculateEmaBtn = document.getElementById('calculateEmaBtn');
        const emaToggle = document.getElementById('emaToggle');
        const autoRefreshToggle = document.getElementById('autoRefreshToggle');

        if (emaPeriodInput) {
            emaPeriodInput.addEventListener('input', function () {
                const emaPeriodValue = document.getElementById('emaPeriodValue');
                if (emaPeriodValue) {
                    emaPeriodValue.textContent = this.value + ' días';
                }
                dashboard.emaPeriod = parseInt(this.value);
            });
        }

        if (futurePeriodsInput) {
            futurePeriodsInput.addEventListener('input', function () {
                const futurePeriodsValue = document.getElementById('futurePeriodsValue');
                if (futurePeriodsValue) {
                    futurePeriodsValue.textContent = this.value + ' días';
                }
                dashboard.futurePeriods = parseInt(this.value);
            });
        }

        if (calculateEmaBtn) {
            calculateEmaBtn.addEventListener('click', () => {
                this.calculateEMA();
                this.renderCandleChart();
            });
        }

        if (emaToggle) {
            emaToggle.addEventListener('change', () => {
                this.renderCandleChart();
            });
        }

        // Notificaciones
        const saveSettingsBtn = document.getElementById('saveSettingsBtn');
        const testNotificationBtn = document.getElementById('testNotificationBtn');

        if (saveSettingsBtn) {
            saveSettingsBtn.addEventListener('click', () => {
                this.saveNotificationSettings();
            });
        }

        if (testNotificationBtn) {
            testNotificationBtn.addEventListener('click', () => {
                this.sendTestNotification();
            });
        }

        // Toggle de auto-actualización
        if (autoRefreshToggle) {
            autoRefreshToggle.addEventListener('change', (e) => {
                this.autoRefreshEnabled = e.target.checked;
                if (this.autoRefreshEnabled) {
                    this.startAutoRefresh();
                } else {
                    this.stopAutoRefresh();
                }
            });
        }

        // Logout button
        const logoutBtn = document.getElementById('logoutBtn');
        if (logoutBtn) {
            logoutBtn.addEventListener('click', () => {
                this.logout();
            });
        }
    }

    // Manejar cambios de visibilidad de la pestaña
    handleVisibilityChange() {
        document.addEventListener('visibilitychange', () => {
            if (document.hidden) {
                // Pestaña oculta, pausar actualizaciones
                this.stopAutoRefresh();
            } else if (this.autoRefreshEnabled) {
                // Pestaña visible, reanudar actualizaciones si estaban activadas
                this.startAutoRefresh();
            }
        });
    }

    // Iniciar actualización automática
    startAutoRefresh() {
        // Limpiar intervalo existente
        if (this.autoRefreshInterval) {
            clearInterval(this.autoRefreshInterval);
        }

        // Mostrar badge de auto-actualización
        const autoRefreshBadge = document.getElementById('autoRefreshBadge');
        if (autoRefreshBadge) {
            autoRefreshBadge.style.display = 'inline-block';
        }

        // Iniciar nuevo intervalo
        this.autoRefreshInterval = setInterval(() => {
            this.reloadAllData();
        }, this.autoRefreshTime);

        console.log("🔄 Auto-actualización iniciada (cada " + (this.autoRefreshTime / 1000) + " segundos)");
    }

    // Detener actualización automática
    stopAutoRefresh() {
        if (this.autoRefreshInterval) {
            clearInterval(this.autoRefreshInterval);
            this.autoRefreshInterval = null;
        }

        // Ocultar badge de auto-actualización
        const autoRefreshBadge = document.getElementById('autoRefreshBadge');
        if (autoRefreshBadge) {
            autoRefreshBadge.style.display = 'none';
        }

        console.log("⏸️ Auto-actualización detenida");
    }

    updateLastUpdatedTime() {
        const now = new Date();
        const timeString = now.toLocaleTimeString();
        const lastUpdatedElement = document.getElementById('lastUpdated');
        if (lastUpdatedElement) {
            lastUpdatedElement.textContent = `Última actualización: ${timeString}`;
        }
    }

    async reloadAllData() {
        console.log("🔄 Recargando todos los datos...");
        this.useDemoMode = false;

        // Mostrar indicadores de carga
        this.showLoadingState('globalMetrics', 'opportunities', 'tradingSignals', 'predictions');
        await this.loadGlobalMetrics();
        await this.loadOpportunities();
        await this.loadCoinData(this.currentCoin, 30);
        this.updateLastUpdatedTime();
    }

    async loadGlobalMetrics() {
        try {
            console.log("📊 Cargando métricas globales...");
            
            // Intentar con el endpoint correcto primero
            let response = await fetch('/api/v1/global', {
                credentials: 'include'
            });
            
            // Si falla, intentar con el endpoint alternativo
            if (!response.ok) {
                response = await fetch('/api/v1/dashboard/global-metrics', {
                    credentials: 'include'
                });
            }
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            this.renderGlobalMetrics(data);

        } catch (error) {
            console.error('Error loading global metrics:', error);
            this.showDemoGlobalMetrics();
            this.useDemoMode = true;
        }
    }

    renderGlobalMetrics(data) {
        const globalMetrics = document.getElementById('globalMetrics');
        if (!globalMetrics) {
            console.error('Elemento globalMetrics no encontrado');
            return;
        }

        // Ajustar para la estructura de datos de diferentes endpoints
        const totalMarketCap = data.total_market_cap?.usd || data.total_market_cap || 0;
        const totalVolume = data.total_volume?.usd || data.total_volume || 0;
        const marketCapChange = data.market_cap_change_percentage_24h_usd || data.market_cap_change_24h || 0;
        const activeCryptos = data.active_cryptocurrencies || 0;

        const metricsHtml = `
            <div class="stat-card">
                <div class="stat-value text-primary">$${this.formatNumber(totalMarketCap)}</div>
                <div class="stat-label">Market Cap Total</div>
            </div>
            <div class="stat-card">
                <div class="stat-value text-success">$${this.formatNumber(totalVolume)}</div>
                <div class="stat-label">Volumen 24h</div>
            </div>
            <div class="stat-card">
                <div class="stat-value ${marketCapChange >= 0 ? 'positive-change' : 'negative-change'}">
                    ${marketCapChange?.toFixed(2) || '0.00'}%
                </div>
                <div class="stat-label">Cambio 24h</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">${this.formatNumber(activeCryptos)}</div>
                <div class="stat-label">Criptomonedas</div>
            </div>
        `;

        globalMetrics.innerHTML = metricsHtml;
    }

    showDemoGlobalMetrics() {
        const globalMetrics = document.getElementById('globalMetrics');
        if (!globalMetrics) return;

        const demoHtml = `
            <div class="stat-card">
                <div class="stat-value text-primary">$2.5T</div>
                <div class="stat-label">Market Cap Total</div>
            </div>
            <div class="stat-card">
                <div class="stat-value text-success">$100B</div>
                <div class="stat-label">Volumen 24h</div>
            </div>
            <div class="stat-card">
                <div class="stat-value positive-change">+2.5%</div>
                <div class="stat-label">Cambio 24h</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">10,000</div>
                <div class="stat-label">Criptomonedas</div>
            </div>
        `;
        globalMetrics.innerHTML = demoHtml;
    }

    async loadCoinData(coinId, days = 30) {
        try {
            console.log(`📈 Cargando datos de ${coinId}...`);
            this.showLoadingState('tradingSignals', 'predictions');

            // Primero obtener datos del mercado para esta moneda
            const marketResponse = await fetch(`/api/v1/coins/markets?vs_currency=usd&ids=${coinId}&per_page=1&page=1`, {
                credentials: 'include'
            });
            
            if (!marketResponse.ok) {
                throw new Error(`HTTP error! status: ${marketResponse.status}`);
            }
            
            const marketData = await marketResponse.json();
            const coinData = marketData[0] || {};

            // Luego obtener datos históricos
            let historicalResponse;
            try {
                historicalResponse = await fetch(`/api/v1/coins/markets?vs_currency=usd&ids=${coinId}&days=${days}&per_page=100`, {
                    credentials: 'include'
                });
            } catch (e) {
                console.log('Usando endpoint alternativo para datos históricos...');
                historicalResponse = await fetch(`/api/v1/trading/${coinId}/metrics?days=${days}`, {
                    credentials: 'include'
                });
            }

            if (!historicalResponse.ok) {
                throw new Error(`HTTP error! status: ${historicalResponse.status}`);
            }

            const historicalData = await historicalResponse.json();

            // Construir el objeto de datos combinados
            this.currentData = {
                coin_id: coinId,
                current_price: coinData.current_price || 0,
                price_change_24h: coinData.price_change_percentage_24h || 0,
                market_cap: coinData.market_cap || 0,
                volume_24h: coinData.total_volume || 0,
                historical_data: this.formatHistoricalData(historicalData, coinData)
            };

            this.renderQuickStats(this.currentData);
            this.prepareChartData(this.currentData);
            this.calculateEMA();
            this.renderCandleChart();
            this.renderTradingSignals(this.currentData);
            this.renderPredictions(this.currentData);
            this.useDemoMode = false;

        } catch (error) {
            console.error('Error loading coin data:', error);
            this.showDemoCoinData(coinId);
            this.useDemoMode = true;
        }
    }

    formatHistoricalData(data, coinData) {
        // Formatear datos según la estructura que viene de diferentes endpoints
        if (Array.isArray(data)) {
            return data.map(item => ({
                timestamp: new Date().toISOString(), // Placeholder
                open: item.current_price || 0,
                high: item.high_24h || item.current_price || 0,
                low: item.low_24h || item.current_price || 0,
                close: item.current_price || 0,
                volume: item.total_volume || 0
            }));
        } else if (data.prices && Array.isArray(data.prices)) {
            return data.prices.map(([timestamp, price]) => ({
                timestamp: new Date(timestamp).toISOString(),
                open: price,
                high: price,
                low: price,
                close: price,
                volume: 0
            }));
        } else {
            // Datos de demo como fallback
            return this.generateDemoHistoricalData(this.currentCoin);
        }
    }

    prepareChartData(data) {
        if (!data.historical_data || data.historical_data.length === 0) {
            this.ohlcData = this.generateDemoHistoricalData(this.currentCoin);
            return;
        }

        this.ohlcData = data.historical_data;
    }

    calculateEMA() {
        if (!this.ohlcData || this.ohlcData.length === 0) return;

        const closingPrices = this.ohlcData.map(item => item.close);
        const period = this.emaPeriod;

        // Calcular EMA
        let emaValues = [];
        const k = 2 / (period + 1);

        // Primer valor EMA es el promedio simple de los primeros 'period' valores
        let sum = 0;
        for (let i = 0; i < period; i++) {
            sum += closingPrices[i];
        }
        emaValues.push(sum / period);

        // Calcular EMA para los valores restantes
        for (let i = period; i < closingPrices.length; i++) {
            const ema = closingPrices[i] * k + emaValues[emaValues.length - 1] * (1 - k);
            emaValues.push(ema);
        }

        // Asignar fechas a los valores EMA
        this.emaData = [];
        for (let i = 0; i < emaValues.length; i++) {
            this.emaData.push({
                timestamp: this.ohlcData[i + period - 1].timestamp,
                value: emaValues[i]
            });
        }

        // Calcular predicción futura
        this.calculateFutureEMA(closingPrices, emaValues);

        console.log("EMA calculada para período:", period);
    }

    calculateFutureEMA(closingPrices, emaValues) {
        const period = this.emaPeriod;
        const futurePeriods = this.futurePeriods;
        const k = 2 / (period + 1);

        // Usar el último valor EMA como base para la predicción
        let lastEma = emaValues[emaValues.length - 1];
        this.futureEmaData = [];

        // Crear fechas futuras
        const lastDate = new Date(this.ohlcData[this.ohlcData.length - 1].timestamp);

        for (let i = 1; i <= futurePeriods; i++) {
            // Simular un precio futuro basado en la tendencia reciente
            const recentTrend = closingPrices[closingPrices.length - 1] - closingPrices[closingPrices.length - 5];
            const simulatedPrice = closingPrices[closingPrices.length - 1] + (recentTrend / 5) * i;

            // Calcular EMA para el precio simulado
            const futureEma = simulatedPrice * k + lastEma * (1 - k);
            lastEma = futureEma;

            // Crear fecha futura
            const futureDate = new Date(lastDate);
            futureDate.setDate(futureDate.getDate() + i);

            this.futureEmaData.push({
                timestamp: futureDate.toISOString(),
                value: futureEma
            });
        }
    }

    renderCandleChart() {
        const chartDiv = document.getElementById('candleChart');
        if (!chartDiv) return;

        if (!this.ohlcData || this.ohlcData.length === 0) {
            chartDiv.innerHTML = `
                <div class="alert alert-info">
                    <p>📊 Gráfico no disponible</p>
                    <small>No hay datos históricos</small>
                </div>
            `;
            return;
        }

        try {
            // Preparar datos para el gráfico de velas
            const dates = this.ohlcData.map(item => item.timestamp);
            const opens = this.ohlcData.map(item => item.open);
            const highs = this.ohlcData.map(item => item.high);
            const lows = this.ohlcData.map(item => item.low);
            const closes = this.ohlcData.map(item => item.close);

            // Datos para el gráfico de velas
            const candleData = [{
                type: 'candlestick',
                x: dates,
                open: opens,
                high: highs,
                low: lows,
                close: closes,
                yaxis: 'y2',
                name: 'Precio',
                increasing: { line: { color: '#28a745' } },
                decreasing: { line: { color: '#dc3545' } }
            }];

            // Agregar línea de EMA si está activado
            const emaToggle = document.getElementById('emaToggle');
            if (emaToggle && emaToggle.checked && this.emaData.length > 0) {
                candleData.push({
                    x: this.emaData.map(item => item.timestamp),
                    y: this.emaData.map(item => item.value),
                    type: 'scatter',
                    mode: 'lines',
                    name: `EMA (${this.emaPeriod})`,
                    line: { color: '#667eea', width: 2 },
                    yaxis: 'y2'
                });

                // Agregar predicción futura de EMA
                if (this.futureEmaData.length > 0) {
                    candleData.push({
                        x: this.futureEmaData.map(item => item.timestamp),
                        y: this.futureEmaData.map(item => item.value),
                        type: 'scatter',
                        mode: 'lines',
                        name: `Predicción EMA`,
                        line: { color: '#ff9900', width: 2, dash: 'dash' },
                        yaxis: 'y2'
                    });
                }
            }

            const layout = {
                title: {
                    text: `Gráfico de Velas - ${this.currentCoin.toUpperCase()} con EMA ${this.emaPeriod}`,
                    font: { size: 18, family: 'Arial', color: '#2c3e50' }
                },
                xaxis: {
                    title: 'Fecha',
                    type: 'date',
                    rangeslider: { visible: false }
                },
                yaxis: {
                    title: 'Volumen',
                    side: 'left',
                    showgrid: false
                },
                yaxis2: {
                    title: 'Precio (USD)',
                    side: 'right',
                    overlaying: 'y',
                    showgrid: true,
                    tickprefix: '$'
                },
                showlegend: true,
                plot_bgcolor: 'rgba(0,0,0,0)',
                paper_bgcolor: 'rgba(0,0,0,0)',
                margin: { l: 60, r: 60, t: 60, b: 50 },
                font: { family: 'Arial', size: 12 }
            };

            const config = {
                responsive: true,
                displayModeBar: true,
                displaylogo: false,
                modeBarButtonsToAdd: ['hoverClosestGl2d'],
                modeBarButtonsToRemove: ['autoScale2d', 'toggleSpikelines'],
                scrollZoom: true
            };

            Plotly.newPlot('candleChart', candleData, layout, config);
        } catch (error) {
            console.error('Error rendering candle chart:', error);
            chartDiv.innerHTML = `
                <div class="alert alert-warning">
                    <p>⚠️ Error mostrando gráfico</p>
                    <small>${error.message}</small>
                </div>
            `;
        }
    }

    renderQuickStats(data) {
        const quickStats = document.getElementById('quickStats');
        if (!quickStats || !data) return;

        const priceChange = typeof data.price_change_24h === 'number'
            ? data.price_change_24h
            : parseFloat(data.price_change_24h) || 0;

        const statsHtml = `
            <div class="stat-item">
                <small>Precio Actual</small>
                <h4 class="mb-0">$${data.current_price?.toFixed(2) || '0.00'}</h4>
            </div>
            <div class="stat-item">
                <small>Cambio 24h</small>
                <h4 class="mb-0 ${priceChange >= 0 ? 'text-success' : 'text-danger'}">
                    ${priceChange.toFixed(2)}%
                </h4>
            </div>
            <div class="stat-item">
                <small>Market Cap</small>
                <h4 class="mb-0">$${this.formatNumber(data.market_cap)}</h4>
            </div>
            <div class="stat-item">
                <small>Volumen 24h</small>
                <h4 class="mb-0">$${this.formatNumber(data.volume_24h)}</h4>
            </div>
        `;

        quickStats.innerHTML = statsHtml;
    }

    // redireccion a la página de simulacion
    executeTrade(type) {
        // Redirigir a la página de simulación con parámetros
        const params = new URLSearchParams({
            coin: this.currentCoin,
            action: type,
            price: this.currentData.current_price.toFixed(2)
        });

        window.location.href = `/simulacion?${params.toString()}`;
    }

    renderTradingSignals(data) {
        const signalsDiv = document.getElementById('tradingSignals');
        const tradeActionsDiv = document.getElementById('tradeActions');

        if (!signalsDiv) return;

        // Generar señales basadas en EMA
        const signals = this.generateEMASignals();

        let signalsHtml = '<h6>Señales de Trading en Tiempo Real:</h6>';
        tradeActionsDiv.innerHTML = '';

        if (signals.length === 0) {
            signalsHtml += `
                <div class="alert alert-info">
                    <p>No hay señales fuertes en este momento</p>
                    <small>Esperando cruces significativos de EMA</small>
                </div>
            `;
        } else {
            signals.forEach(signal => {
                const alertClass = signal.type === 'BUY' ? 'alert-success' : 'alert-danger';

                signalsHtml += `
                    <div class="alert ${alertClass}">
                        <div class="d-flex justify-content-between align-items-start">
                            <div>
                                <h6 class="mb-1">${signal.type} 
                                    <span class="badge bg-${signal.confidence === 'high' ? 'success' : signal.confidence === 'medium' ? 'warning' : 'secondary'}">
                                        ${signal.confidence.toUpperCase()}
                                    </span>
                                </h6>
                                <p class="mb-1">${signal.reason}</p>
                                <small class="text-muted">${new Date(signal.timestamp).toLocaleString()}</small>
                            </div>
                        </div>
                    </div>
                `;

                // mostramos el boton de comprar/vender según la señal
                if (signal.type === 'BUY') {
                    tradeActionsDiv.innerHTML = `
                        <button class="btn btn-success" id="buyBtn" 
                            onclick="dashboard.executeTrade('buy')">
                            Comprar ${this.currentCoin}
                        </button>`;
                } else if (signal.type === 'SELL') {
                    tradeActionsDiv.innerHTML = `
                        <button class="btn btn-danger" id="sellBtn" 
                            onclick="dashboard.executeTrade('sell')">
                            Vender ${this.currentCoin}
                        </button>`;
                }
            });
        }

        signalsDiv.innerHTML = signalsHtml;
    }

    generateEMASignals() {
        const signals = [];
        if (this.emaData.length < 2) return signals;

        const currentPrice = this.ohlcData[this.ohlcData.length - 1].close;
        const currentEma = this.emaData[this.emaData.length - 1].value;
        const previousEma = this.emaData[this.emaData.length - 2].value;
        const priceVsEma = ((currentPrice - currentEma) / currentEma) * 100;

        // Señal de compra: precio cruza por encima de la EMA
        if (currentPrice > currentEma && this.ohlcData[this.ohlcData.length - 2].close <= previousEma) {
            const signal = {
                type: 'BUY',
                confidence: Math.abs(priceVsEma) > 2 ? 'high' : 'medium',
                reason: `Precio cruzó por encima de la EMA${this.emaPeriod}. El precio está ${Math.abs(priceVsEma).toFixed(2)}% por encima de la EMA.`,
                price: currentPrice,
                emaValue: currentEma,
                timestamp: new Date().toISOString()
            };
            signals.push(signal);

            // Enviar notificación por email
            this.sendEmaNotification(signal);
        }

        // Señal de venta: precio cruza por debajo de la EMA
        if (currentPrice < currentEma && this.ohlcData[this.ohlcData.length - 2].close >= previousEma) {
            const signal = {
                type: 'SELL',
                confidence: Math.abs(priceVsEma) > 2 ? 'high' : 'medium',
                reason: `Precio cruzó por debajo de la EMA${this.emaPeriod}. El precio está ${Math.abs(priceVsEma).toFixed(2)}% por debajo de la EMA.`,
                price: currentPrice,
                emaValue: currentEma,
                timestamp: new Date().toISOString()
            };
            signals.push(signal);

            // Enviar notificación por email
            this.sendEmaNotification(signal);
        }

        return signals;
    }

    // Nueva función para enviar notificaciones
    async sendEmaNotification(signal) {
        try {
            // Verificar si las notificaciones están activadas
            const enabled = document.getElementById('enableNotifications');
            if (!enabled || !enabled.checked) return;

            const response = await fetch('/api/notifications/ema-alert', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                credentials: 'include',
                body: JSON.stringify({
                    coin_id: this.currentCoin,
                    signal_type: signal.type,
                    current_price: signal.price,
                    ema_value: signal.emaValue,
                    confidence: signal.confidence
                })
            });

            const result = await response.json();
            if (result.success) {
                console.log('📧 Notificación EMA enviada:', result.message);
            }
        } catch (error) {
            console.error('Error enviando notificación EMA:', error);
        }
    }

    renderPredictions(data) {
        const predictionsDiv = document.getElementById('predictions');
        if (!predictionsDiv) return;

        if (this.futureEmaData && this.futureEmaData.length > 0) {
            // Usar predicción EMA
            const currentPrice = this.ohlcData[this.ohlcData.length - 1].close;
            const lastPrediction = this.futureEmaData[this.futureEmaData.length - 1].value;
            const changePercentage = ((lastPrediction - currentPrice) / currentPrice) * 100;
            const trend = changePercentage >= 0 ? 'alcista' : 'bajista';

            let predictionsHtml = `
                <h6>Predicción para ${this.futurePeriods} días:</h6>
                <div class="card mb-3">
                    <div class="card-body">
                        <h5 class="card-title ${changePercentage >= 0 ? 'text-success' : 'text-danger'}">
                            ${changePercentage >= 0 ? '📈' : '📉'} ${Math.abs(changePercentage).toFixed(2)}%
                        </h5>
                        <p class="card-text">
                            Tendencia ${trend} esperada según EMA${this.emaPeriod}.
                        </p>
                        <div class="row">
                            <div class="col-6">
                                <small>Precio actual:</small>
                                <p class="mb-0 fw-bold">$${currentPrice.toFixed(2)}</p>
                            </div>
                            <div class="col-6">
                                <small>Predicción:</small>
                                <p class="mb-0 fw-bold">$${lastPrediction.toFixed(2)}</p>
                            </div>
                        </div>
                    </div>
                </div>
            `;

            predictionsDiv.innerHTML = predictionsHtml;
        } else {
            predictionsDiv.innerHTML = `
                <div class="alert alert-info">
                    <h6>🔮 Predicciones</h6>
                    <p>No hay predicciones disponibles</p>
                    <small>Calcule la EMA para ver predicciones</small>
                </div>
            `;
        }
    }

    showDemoCoinData(coinId) {
        const basePrice = coinId === 'bitcoin' ? 45000 :
            coinId === 'ethereum' ? 3000 :
                coinId === 'binancecoin' ? 350 : 100;

        const demoData = {
            coin_id: coinId,
            current_price: basePrice,
            price_change_24h: (Math.random() * 10 - 5),
            market_cap: basePrice * (coinId === 'bitcoin' ? 19000000 : 100000000),
            volume_24h: basePrice * (coinId === 'bitcoin' ? 500000 : 2000000),
            historical_data: this.generateDemoHistoricalData(coinId, basePrice)
        };

        this.ohlcData = demoData.historical_data;
        this.renderQuickStats(demoData);
        this.calculateEMA();
        this.renderCandleChart();

        // Mostrar advertencia
        const tradingSignals = document.getElementById('tradingSignals');
        if (tradingSignals) {
            tradingSignals.innerHTML += `
                <div class="alert alert-warning mt-3">
                    <small>⚠️ Modo offline: Datos simulados</small>
                    <button onclick="dashboard.loadCoinData('${coinId}')" class="btn btn-sm btn-outline-warning ms-2">
                        Reintentar
                    </button>
                </div>
            `;
        }
    }

    generateDemoHistoricalData(coinId, basePrice = null) {
        const price = basePrice || (coinId === 'bitcoin' ? 45000 :
            coinId === 'ethereum' ? 3000 : 100);

        const data = [];
        const now = Date.now();

        for (let i = 30; i >= 0; i--) {
            const timestamp = new Date(now - i * 86400000).toISOString();
            const open = price * (0.95 + Math.random() * 0.1);
            const close = open * (0.97 + Math.random() * 0.06);
            const high = Math.max(open, close) * (1 + Math.random() * 0.03);
            const low = Math.min(open, close) * (0.97 + Math.random() * 0.03);

            data.push({
                timestamp: timestamp,
                open: open,
                high: high,
                low: low,
                close: close,
                volume: 1000000 * (0.8 + Math.random() * 0.4)
            });
        }

        return data;
    }

    async loadOpportunities() {
        try {
            console.log("💎 Buscando oportunidades...");
            
            // Intentar diferentes endpoints para oportunidades
            let response;
            try {
                response = await fetch('/api/v1/coins/markets?vs_currency=usd&order=market_cap_desc&per_page=10&page=1', {
                    credentials: 'include'
                });
            } catch (e) {
                response = await fetch('/api/v1/dashboard/top-opportunities?limit=6', {
                    credentials: 'include'
                });
            }
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            this.renderOpportunities(Array.isArray(data) ? data : (data.opportunities || data));

        } catch (error) {
            console.error('Error loading opportunities:', error);
            this.showDemoOpportunities();
        }
    }

    renderOpportunities(opportunities) {
        const opportunitiesDiv = document.getElementById('opportunities');
        if (!opportunitiesDiv) return;

        let opportunitiesHtml = `
            <div class="row">
                <div class="col-12">
                    <div class="alert alert-info">
                        <small>💎 Top Criptomonedas por Market Cap</small>
                    </div>
                </div>
            </div>
            <div class="row">
        `;

        (opportunities || []).forEach((opp, index) => {
            const coin = opp.coin || opp;
            const signal = opp.signal || { type: 'HOLD', confidence: 'medium', reason: 'Analizando oportunidad...' };

            opportunitiesHtml += `
                <div class="col-md-4 mb-3">
                    <div class="card opportunity-card" onclick="dashboard.loadCoinData('${coin.id || 'bitcoin'}')">
                        <div class="card-body">
                            <h6 class="card-title">${coin.name || 'Unknown'} 
                                <small class="text-muted">(${coin.symbol ? coin.symbol.toUpperCase() : 'N/A'})</small>
                            </h6>
                            <p class="card-text mb-1">
                                <span class="fw-bold">$${coin.current_price ? coin.current_price.toFixed(2) : '0.00'}</span>
                                <span class="${coin.price_change_percentage_24h >= 0 ? 'text-success' : 'text-danger'} small ms-2">
                                    ${coin.price_change_percentage_24h ? coin.price_change_percentage_24h.toFixed(1) + '%' : ''}
                                </span>
                            </p>
                            <p class="card-text">
                                <span class="badge bg-${signal.type === 'BUY' ? 'success' : signal.type === 'SELL' ? 'danger' : 'warning'}">
                                    ${signal.type || 'HOLD'}
                                </span>
                                <small class="text-muted ms-1">(${signal.confidence || 'MEDIUM'})</small>
                            </p>
                            <p class="card-text small text-muted">
                                ${signal.reason ? signal.reason.substring(0, 50) + '...' : `Rank #${index + 1} por market cap`}
                            </p>
                        </div>
                    </div>
                </div>
            `;
        });

        opportunitiesHtml += '</div>';
        opportunitiesDiv.innerHTML = opportunitiesHtml;
    }

    showDemoOpportunities() {
        const demoOpportunities = [
            {
                id: 'bitcoin',
                name: 'Bitcoin',
                symbol: 'btc',
                current_price: 45000,
                price_change_percentage_24h: 2.5,
                market_cap: 875000000000
            },
            {
                id: 'ethereum',
                name: 'Ethereum',
                symbol: 'eth',
                current_price: 3000,
                price_change_percentage_24h: -1.2,
                market_cap: 360000000000
            },
            {
                id: 'binancecoin',
                name: 'BNB',
                symbol: 'bnb',
                current_price: 350,
                price_change_percentage_24h: 0.8,
                market_cap: 55000000000
            }
        ];

        this.renderOpportunities(demoOpportunities);
    }

    showLoadingState(...elementIds) {
        elementIds.forEach(id => {
            const element = document.getElementById(id);
            if (element) {
                element.innerHTML = `
                    <div class="text-center">
                        <div class="spinner-border spinner-border-sm"></div>
                        <p class="mt-2">Cargando datos en tiempo real...</p>
                    </div>
                `;
            }
        });
    }

    async saveNotificationSettings() {
        const email = document.getElementById('emailInput').value;
        const notificationType = document.getElementById('notificationType').value;
        const enabled = document.getElementById('enableNotifications').checked;

        if (!email || !this.validateEmail(email)) {
            this.showNotificationStatus('Por favor, introduce un email válido', 'danger');
            return;
        }

        try {
            const response = await fetch('/api/notifications/settings', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                credentials: 'include',
                body: JSON.stringify({
                    email: email,
                    notification_type: notificationType,
                    enabled: enabled
                })
            });

            const result = await response.json();

            if (result.success) {
                this.showNotificationStatus('Configuración guardada correctamente. Las notificaciones están ' + (enabled ? 'activadas' : 'desactivadas'), 'success');

                // Guardar también en localStorage para persistencia del frontend
                localStorage.setItem('cryptoNotificationEmail', email);
                localStorage.setItem('cryptoNotificationType', notificationType);
                localStorage.setItem('cryptoNotificationsEnabled', enabled);
            } else {
                this.showNotificationStatus('Error guardando configuración', 'danger');
            }
        } catch (error) {
            this.showNotificationStatus('Error de conexión al guardar configuración', 'danger');
        }
    }

    loadNotificationSettings() {
        // Cargar configuración desde localStorage
        const email = localStorage.getItem('cryptoNotificationEmail') || '';
        const notificationType = localStorage.getItem('cryptoNotificationType') || 'both';
        const enabled = localStorage.getItem('cryptoNotificationsEnabled') === 'true';

        // Llenar formulario
        const emailInput = document.getElementById('emailInput');
        const notificationTypeSelect = document.getElementById('notificationType');
        const enableNotifications = document.getElementById('enableNotifications');

        if (emailInput) emailInput.value = email;
        if (notificationTypeSelect) notificationTypeSelect.value = notificationType;
        if (enableNotifications) enableNotifications.checked = enabled;
    }

    sendTestNotification() {
        const email = document.getElementById('emailInput').value;

        if (!email || !this.validateEmail(email)) {
            this.showNotificationStatus('Por favor, introduce un email válido', 'danger');
            return;
        }

        // En una implementación real, aquí se conectaría con un servicio de envío de emails
        this.showNotificationStatus('Email de prueba enviado a ' + email, 'success');

        // Simular envío de email
        setTimeout(() => {
            alert(`📧 Email de prueba enviado a ${email}\nAsunto: Prueba de notificaciones de trading\nContenido: Esta es una prueba del sistema de notificaciones. Cuando se detecten señales de compra/venta, recibirás un email similar.`);
        }, 1000);
    }

    showNotificationStatus(message, type) {
        const statusDiv = document.getElementById('notificationStatus');
        if (statusDiv) {
            statusDiv.innerHTML = `
                <div class="alert alert-${type} alert-dismissible fade show">
                    ${message}
                    <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                </div>
            `;
        }
    }

    validateEmail(email) {
        const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return re.test(email);
    }

    formatNumber(num) {
        if (num === undefined || num === null) return '0.00';
        const number = parseFloat(num);
        if (isNaN(number)) return '0.00';

        if (number >= 1e9) return (number / 1e9).toFixed(2) + 'B';
        if (number >= 1e6) return (number / 1e6).toFixed(2) + 'M';
        if (number >= 1e3) return (number / 1e3).toFixed(2) + 'K';
        return number.toFixed(2);
    }

    async logout() {
        try {
            const response = await fetch('/api/logout', {
                method: 'POST',
                credentials: 'include'
            });
            
            if (response.ok) {
                window.location.href = '/';
            } else {
                console.error('Error al cerrar sesión');
            }
        } catch (error) {
            console.error('Error de conexión:', error);
        }
    }
}

// Inicializar dashboard cuando el DOM esté listo
document.addEventListener('DOMContentLoaded', function () {
    window.dashboard = new CryptoDashboard();
});