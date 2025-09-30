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
        this.autoRefreshTime = 60000; // Reducido a 60 segundos

        // CACHÉ MEJORADO con expiración
        this.dataCache = new Map();
        this.chartCache = new Map();
        this.cacheExpiration = 120000; // 2 minutos de caché

        // Estados de carga y throttling
        this.isLoading = false;
        this.lastRequestTime = 0;
        this.requestDelay = 500; // 500ms

        // Precarga de datos esenciales
        this.essentialCoins = ['bitcoin', 'ethereum', 'binancecoin', 'solana', 'cardano'];

        this.init();
    }

    debugDataFlow() {
        console.log('🔧 Debug activado');

        // Verificar elementos del DOM
        const elements = ['quickStats', 'tradingSignals', 'candleChart'];
        elements.forEach(id => {
            const el = document.getElementById(id);
            console.log(`Elemento ${id}:`, el ? '✅ Encontrado' : '❌ No encontrado');
        });
    }

    // En init, manejar mejor la inicialización
    async init() {
        console.log("🚀 Inicializando dashboard...");
        this.updateLastUpdatedTime();

        try {
            // Cargar primero datos globales (más rápido)
            await this.loadGlobalMetrics();

            // Luego cargar datos de la moneda actual con timeout
            await Promise.race([
                this.loadCoinDataOptimized(this.currentCoin, 30),
                new Promise((_, reject) =>
                    setTimeout(() => reject(new Error('Timeout carga inicial')), 20000)
                )
            ]);

            console.log("✅ Dashboard inicializado correctamente");

        } catch (error) {
            console.error('❌ Error en inicialización:', error);
            // Cargar datos demo como fallback
            this.showDemoGlobalMetrics();
            this.showDemoCoinData(this.currentCoin);
            console.log("🔧 Modo demo activado debido a errores de inicialización");
        }

        this.setupEventListeners();
        this.startAutoRefresh();
        this.handleVisibilityChange();
        this.loadNotificationSettings();

        // Precargar después de un delay
        setTimeout(() => {
            this.preloadPopularCoins();
        }, 10000);
    }

    async loadCriticalDataSequentially() {
        try {
            // 1. Primero cargar datos globales (más rápido)
            await this.loadGlobalMetrics();

            // 2. Luego cargar datos de la moneda actual
            await this.loadCoinDataOptimized(this.currentCoin, 30);

            // 3. Finalmente cargar oportunidades en segundo plano
            setTimeout(() => this.loadOpportunities(), 2000);

        } catch (error) {
            console.error('Error en carga secuencial:', error);
        }
    }

    setupEventListeners() {
        // Selector de moneda
        const coinSelector = document.getElementById('coinSelector');
        if (coinSelector) {
            coinSelector.addEventListener('change', (e) => {
                this.currentCoin = e.target.value;
                this.loadCoinDataOptimized(this.currentCoin, 30);
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
                dashboard.loadCoinDataOptimized(dashboard.currentCoin, timeframe);
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
        await this.loadCoinDataOptimized(this.currentCoin, 30);
        this.updateLastUpdatedTime();
    }

    async loadGlobalMetrics() {
        // Verificar caché primero
        const cacheKey = 'global_metrics';
        const cached = this.getCachedData(cacheKey);

        if (cached) {
            this.renderGlobalMetrics(cached);
            return;
        }

        try {
            console.log("📊 Cargando métricas globales...");

            const response = await this.fetchWithTimeout('/api/v1/global', 5000); // 5s timeout

            if (response.ok) {
                const data = await response.json();
                this.setCachedData(cacheKey, data, 180000); // 3 minutos de caché
                this.renderGlobalMetrics(data);
            } else {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

        } catch (error) {
            console.warn('Error loading global metrics, using cache or demo:', error);
            this.showDemoGlobalMetrics();
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

    async loadCoinDataOptimized(coinId, days = 30) {
        // Mejor control de requests simultáneos
        if (this.isLoading) {
            console.log("⏳ Request en curso, esperando...");
            return;
        }

        // Cancelar request anterior si existe
        if (this.currentRequestController) {
            this.currentRequestController.abort();
        }

        this.isLoading = true;
        this.currentRequestController = new AbortController();

        try {
            console.log(`⚡ Cargando datos OPTIMIZADOS de ${coinId}...`);

            // Verificar caché primero
            const cacheKey = `coin_${coinId}_${days}`;
            const cachedData = this.getCachedData(cacheKey);

            if (cachedData) {
                console.log(`📦 Usando datos en CACHÉ para ${coinId}`);
                this.processCachedData(cachedData);
                return;
            }

            // Mostrar estados de carga solo si no hay caché
            this.showLoadingState('tradingSignals', 'predictions');

            // Cargar datos frescos con el nuevo controller
            const freshData = await this.fetchCoinDataOptimized(coinId, days);

            if (freshData) {
                this.currentData = freshData;
                this.setCachedData(cacheKey, freshData, this.cacheExpiration);
                this.processAndRenderData(freshData);
                console.log(`✅ Datos FRESCOS cargados para ${coinId}`);
            }

            this.useDemoMode = false;

        } catch (error) {
            if (error.name !== 'AbortError') {
                console.error('Error loading coin data:', error);
                this.handleDataLoadError(coinId);
            } else {
                console.log('🔄 Request cancelado intencionalmente');
            }
        } finally {
            this.isLoading = false;
            this.currentRequestController = null;
        }
    }

    processCachedData(cachedData) {
        this.currentData = cachedData;
        this.renderQuickStats(cachedData);
        this.prepareChartData(cachedData);
        this.calculateEMA();
        this.renderCandleChart();
        this.renderTradingSignals(cachedData);
        this.renderPredictions(cachedData);
    }

    processAndRenderData(data) {
        this.renderQuickStats(data);
        this.prepareChartData(data);
        this.calculateEMA();
        this.renderCandleChart();
        this.renderTradingSignals(data);
        this.renderPredictions(data);
    }

    handleDataLoadError(coinId) {
        // Si hay error pero tenemos caché, mantener los datos cacheados
        const cacheKey = `coin_${coinId}_30`;
        const cachedData = this.getCachedData(cacheKey);

        if (cachedData) {
            console.log(`🔄 Usando caché debido a error para ${coinId}`);
            this.processCachedData(cachedData);
        } else {
            this.showDemoCoinData(coinId);
            this.useDemoMode = true;
        }
    }

    // SISTEMA DE CACHÉ MEJORADO
    getCachedData(key) {
        const item = this.dataCache.get(key);
        if (!item) return null;

        const { data, timestamp } = item;
        if (Date.now() - timestamp > this.cacheExpiration) {
            this.dataCache.delete(key);
            return null;
        }

        return data;
    }

    setCachedData(key, data, expiration = this.cacheExpiration) {
        this.dataCache.set(key, {
            data,
            timestamp: Date.now(),
            expiration
        });
    }

    clearExpiredCache() {
        const now = Date.now();
        for (const [key, item] of this.dataCache.entries()) {
            if (now - item.timestamp > item.expiration) {
                this.dataCache.delete(key);
            }
        }
    }

    // OPTIMIZACIÓN DEL GRÁFICO
    renderCandleChart() {
        const chartDiv = document.getElementById('candleChart');
        if (!chartDiv) return;

        if (!this.ohlcData || this.ohlcData.length === 0) {
            chartDiv.innerHTML = this.getChartPlaceholder();
            return;
        }

        try {
            // Usar requestAnimationFrame para mejor rendimiento
            requestAnimationFrame(() => {
                this.createOptimizedChart();
            });
        } catch (error) {
            console.error('Error rendering candle chart:', error);
            chartDiv.innerHTML = this.getChartErrorTemplate(error);
        }
    }

    createOptimizedChart() {
        // Limitar datos para mejor rendimiento
        const displayData = this.ohlcData.slice(-50); // Mostrar solo últimos 50 puntos

        const dates = displayData.map(item => item.timestamp);
        const closes = displayData.map(item => item.close);

        const trace1 = {
            x: dates,
            y: closes,
            type: 'scatter',
            mode: 'lines',
            name: 'Precio',
            line: { color: '#28a745', width: 2 }
        };

        const data = [trace1];

        // Agregar EMA si está activado
        const emaToggle = document.getElementById('emaToggle');
        if (emaToggle && emaToggle.checked && this.emaData.length > 0) {
            const emaDisplayData = this.emaData.slice(-50);
            data.push({
                x: emaDisplayData.map(item => item.timestamp),
                y: emaDisplayData.map(item => item.value),
                type: 'scatter',
                mode: 'lines',
                name: `EMA (${this.emaPeriod})`,
                line: { color: '#667eea', width: 2 }
            });
        }

        const layout = {
            title: {
                text: `${this.currentCoin.toUpperCase()} - Precio en Tiempo Real`,
                font: { size: 14 }
            },
            xaxis: {
                title: 'Fecha',
                type: 'date',
                tickformat: '%d %b',
                tickangle: -45
            },
            yaxis: {
                title: 'Precio (USD)',
                tickprefix: '$'
            },
            showlegend: true,
            legend: {
                x: 0,
                y: 1.1,
                orientation: 'h'
            },
            margin: {
                l: 60,
                r: 40,
                t: 60,
                b: 60
            },
            hovermode: 'x unified'
        };

        const config = {
            responsive: true,
            displayModeBar: true,
            displaylogo: false,
            modeBarButtonsToRemove: ['lasso2d', 'select2d', 'autoScale2d'],
            scrollZoom: true
        };

        Plotly.newPlot('candleChart', data, layout, config);
    }

    getChartPlaceholder() {
        return `
            <div class="alert alert-info text-center">
                <p>📊 Cargando gráfico...</p>
                <small>Optimizando datos para mejor rendimiento</small>
            </div>
        `;
    }

    getChartErrorTemplate(error) {
        return `
            <div class="alert alert-warning text-center">
                <p>⚠️ Gráfico no disponible</p>
                <small>${error.message}</small>
                <button onclick="dashboard.loadCoinDataOptimized('${this.currentCoin}')" 
                        class="btn btn-sm btn-outline-warning mt-2">
                    Reintentar
                </button>
            </div>
        `;
    }



    async fetchCoinDataOptimized(coinId, days) {
        try {
            console.log(`🔍 Intentando cargar datos para ${coinId}...`);

            // Usar endpoints que SÍ existen en tu API
            const [marketData, historicalData] = await Promise.allSettled([
                this.fetchWithRetry(`/api/v1/coins/markets?vs_currency=usd&ids=${coinId}&per_page=1&page=1`, 10000),
                this.fetchWithRetry(`/api/v1/coins/${coinId}/market_chart/last_days?vs_currency=usd&days=${Math.min(days, 30)}`, 15000)
            ]);

            let marketJson = null;
            let historicalJson = null;

            // Procesar marketData
            if (marketData.status === 'fulfilled' && marketData.value.ok) {
                marketJson = await marketData.value.json();
                console.log(`✅ Market data obtenido para ${coinId}`);
            } else {
                console.warn(`❌ Falló market data para ${coinId}`);
            }

            // Procesar historicalData
            if (historicalData.status === 'fulfilled' && historicalData.value.ok) {
                historicalJson = await historicalData.value.json();
                console.log(`✅ Historical data obtenido para ${coinId}`);
            } else {
                console.warn(`❌ Falló historical data para ${coinId}`);
            }

            // Si ambos fallan, usar datos demo
            if (!marketJson && !historicalJson) {
                throw new Error('Todos los endpoints fallaron');
            }

            // Extraer datos de marketData (si está disponible)
            const coinData = marketJson && Array.isArray(marketJson) && marketJson.length > 0
                ? marketJson[0]
                : null;

            return {
                coin_id: coinId,
                current_price: coinData?.current_price || 0,
                price_change_24h: coinData?.price_change_percentage_24h || 0,
                market_cap: coinData?.market_cap || 0,
                volume_24h: coinData?.total_volume || 0,
                historical_data: this.processOptimizedHistoricalData(historicalJson)
            };

        } catch (error) {
            console.error('Error en fetchCoinDataOptimized:', error);
            // Fallback a datos demo
            return this.generateDemoCoinData(coinId);
        }
    }

    // Función auxiliar para generar datos demo
    generateDemoCoinData(coinId) {
        const basePrice = coinId === 'bitcoin' ? 45000 :
            coinId === 'ethereum' ? 3000 :
                coinId === 'binancecoin' ? 350 : 100;

        return {
            coin_id: coinId,
            current_price: basePrice,
            price_change_24h: (Math.random() * 10 - 5),
            market_cap: basePrice * (coinId === 'bitcoin' ? 19000000 : 100000000),
            volume_24h: basePrice * (coinId === 'bitcoin' ? 500000 : 2000000),
            historical_data: this.generateDemoHistoricalData(coinId, basePrice)
        };
    }

    processOptimizedHistoricalData(chartData) {
        if (!chartData || !chartData.prices) {
            console.warn('📊 No hay datos históricos, generando demo...');
            return this.generateDemoHistoricalData(this.currentCoin);
        }

        try {
            const prices = chartData.prices;
            console.log(`📈 Procesando ${prices.length} puntos históricos`);

            // Limitar a máximo 100 puntos para mejor rendimiento
            const maxPoints = 100;
            let processedData = [];

            if (prices.length > maxPoints) {
                const step = Math.ceil(prices.length / maxPoints);
                processedData = prices
                    .filter((_, index) => index % step === 0)
                    .map(([timestamp, price]) => this.createOHLCEntry(timestamp, price));
            } else {
                processedData = prices.map(([timestamp, price]) =>
                    this.createOHLCEntry(timestamp, price)
                );
            }

            console.log(`✅ Datos procesados: ${processedData.length} puntos`);
            return processedData;

        } catch (error) {
            console.error('Error procesando datos históricos:', error);
            return this.generateDemoHistoricalData(this.currentCoin);
        }
    }

    createOHLCEntry(timestamp, price) {
        const volatility = 0.02; // 2% de volatilidad
        const basePrice = price;

        return {
            timestamp: new Date(timestamp).toISOString(),
            open: basePrice,
            high: basePrice * (1 + Math.random() * volatility),
            low: basePrice * (1 - Math.random() * volatility),
            close: basePrice,
            volume: Math.random() * 1000000
        };
    }

    async fetchCoinDataTraditional(coinId, days) {
        try {
            const marketResponse = await this.fetchWithTimeout(
                `/api/v1/coins/markets?vs_currency=usd&ids=${coinId}&per_page=1&page=1`,
                8000
            );

            if (!marketResponse.ok) throw new Error(`HTTP error! status: ${marketResponse.status}`);

            const marketData = await marketResponse.json();
            if (!Array.isArray(marketData) || marketData.length === 0) {
                throw new Error(`No data found for ${coinId}`);
            }

            const coinData = marketData[0];

            return {
                coin_id: coinId,
                current_price: coinData.current_price || 0,
                price_change_24h: coinData.price_change_percentage_24h || 0,
                market_cap: coinData.market_cap || 0,
                volume_24h: coinData.total_volume || 0,
                historical_data: this.generateDemoHistoricalData(coinId, coinData.current_price)
            };

        } catch (error) {
            console.error('Error en fetchCoinDataTraditional:', error);
            throw error;
        }
    }

    async fetchWithTimeout(url, timeout = 15000) {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), timeout);

        try {
            const response = await fetch(url, {
                credentials: 'include',
                signal: controller.signal,
                headers: {
                    'Cache-Control': 'no-cache',
                    'Pragma': 'no-cache'
                }
            });

            clearTimeout(timeoutId);

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            return response;
        } catch (error) {
            clearTimeout(timeoutId);
            if (error.name === 'AbortError') {
                console.warn(`⏰ Timeout después de ${timeout}ms: ${url}`);
                throw new Error(`Timeout: No se pudo cargar ${url} en ${timeout}ms`);
            }
            throw error;
        }
    }

    async fetchHistoricalData(coinId, days) {
        let endpoint;

        if (days <= 90) {
            endpoint = `/api/v1/coins/${coinId}/market_chart/last_days?vs_currency=usd&days=${days}`;
        } else {
            endpoint = `/api/v1/coins/${coinId}/market_chart/range?vs_currency=usd`;
        }

        const response = await fetch(endpoint, {
            credentials: 'include'
        });

        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);

        return await response.json();
    }



    // Al final de loadCoinData, después de calcular EMA
    debugEMAData() {
        console.log('🔍 DEBUG EMA DATA:');
        console.log('OHLC Data length:', this.ohlcData.length);
        console.log('EMA Data length:', this.emaData.length);

        if (this.ohlcData.length > 0 && this.emaData.length > 0) {
            const lastPrice = this.ohlcData[this.ohlcData.length - 1].close;
            const lastEMA = this.emaData[this.emaData.length - 1].value;
            console.log('Último precio:', lastPrice);
            console.log('Última EMA:', lastEMA);
            console.log('Diferencia:', ((lastPrice - lastEMA) / lastEMA * 100).toFixed(2) + '%');
        }
    }

    processChartData(apiData, currentData) {
        // Procesar datos según la estructura de la API
        if (apiData.prices && Array.isArray(apiData.prices)) {
            return apiData.prices.map(([timestamp, price], index) => {
                // Para datos básicos de precio, crear datos OHLC simulados
                // En una implementación real, sería mejor usar el endpoint OHLC
                const volatility = 0.02; // 2% de volatilidad diaria
                const basePrice = price;
                const randomFactor = 1 + (Math.random() - 0.5) * volatility;

                return {
                    timestamp: new Date(timestamp).toISOString(),
                    open: index === 0 ? basePrice : apiData.prices[index - 1][1],
                    high: basePrice * (1 + Math.random() * volatility),
                    low: basePrice * (1 - Math.random() * volatility),
                    close: basePrice,
                    volume: apiData.total_volumes ? apiData.total_volumes[index][1] : 0
                };
            });
        } else if (Array.isArray(apiData)) {
            // Si son datos OHLC directos
            return apiData.map(item => ({
                timestamp: new Date(item[0]).toISOString(),
                open: item[1],
                high: item[2],
                low: item[3],
                close: item[4]
            }));
        } else {
            // Fallback a datos demo
            return this.generateDemoHistoricalData(this.currentCoin);
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
            // Verificar si tenemos un gráfico existente para actualizar en lugar de recrear
            const existingChart = chartDiv.data;

            if (existingChart && this.chartCache.has(this.currentCoin)) {
                // ACTUALIZACIÓN RÁPIDA del gráfico existente
                this.updateExistingChart(chartDiv);
            } else {
                // CREAR NUEVO GRÁFICO
                this.createNewChart(chartDiv);
                this.chartCache.set(this.currentCoin, true);
            }
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

    updateExistingChart(chartDiv) {
        const dates = this.ohlcData.map(item => item.timestamp);
        const closes = this.ohlcData.map(item => item.close);

        const update = {
            'x': [dates],
            'y': [closes]
        };

        // Si hay EMA, agregar actualización
        const emaToggle = document.getElementById('emaToggle');
        if (emaToggle && emaToggle.checked && this.emaData.length > 0) {
            update.x.push(this.emaData.map(item => item.timestamp));
            update.y.push(this.emaData.map(item => item.value));

            if (this.futureEmaData.length > 0) {
                update.x.push(this.futureEmaData.map(item => item.timestamp));
                update.y.push(this.futureEmaData.map(item => item.value));
            }
        }

        Plotly.react('candleChart', update);
        console.log("⚡ Gráfico actualizado (modo rápido)");
    }

    createNewChart(chartDiv) {
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
            increasing: { line: { color: '#28a745' }, fillcolor: '#28a745' },
            decreasing: { line: { color: '#dc3545' }, fillcolor: '#dc3545' }
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
                line: { color: '#667eea', width: 3 },
                yaxis: 'y2'
            });

            // Agregar predicción futura de EMA
            if (this.futureEmaData.length > 0) {
                candleData.push({
                    x: this.futureEmaData.map(item => item.timestamp),
                    y: this.futureEmaData.map(item => item.value),
                    type: 'scatter',
                    mode: 'lines',
                    name: `Predicción EMA (${this.futurePeriods}d)`,
                    line: { color: '#ff9900', width: 2, dash: 'dot' },
                    yaxis: 'y2'
                });
            }
        }

        const layout = {
            title: {
                text: `Gráfico de Velas - ${this.currentCoin.toUpperCase()} con EMA ${this.emaPeriod}`,
                font: { size: 16, family: 'Arial', color: '#2c3e50' },
                x: 0.05,
                y: 0.95
            },
            xaxis: {
                title: 'Fecha',
                type: 'date',
                rangeslider: {
                    visible: false
                },
                tickformat: '%d %b',
                tickangle: -45,
                tickmode: 'auto',
                nticks: 10, // Reducir número de ticks para más espacio
                showgrid: true,
                gridcolor: '#f1f3f4',
                zeroline: false
            },
            yaxis: {
                title: 'Volumen',
                side: 'left',
                showgrid: false,
                showticklabels: false // Ocultar labels del volumen para más espacio
            },
            yaxis2: {
                title: 'Precio (USD)',
                side: 'right',
                overlaying: 'y',
                showgrid: true,
                gridcolor: '#f1f3f4',
                tickprefix: '$',
                tickformat: '$,.0f',
                zeroline: false
            },
            showlegend: true,
            legend: {
                x: 0,
                y: 1.1,
                orientation: 'h',
                bgcolor: 'rgba(255,255,255,0.8)'
            },
            plot_bgcolor: 'rgba(255,255,255,1)',
            paper_bgcolor: 'rgba(255,255,255,1)',
            margin: {
                l: 10,   // Reducir márgenes izquierdos
                r: 60,
                t: 80,   // Más espacio arriba para título
                b: 80    // Más espacio abajo para labels
            },
            font: {
                family: 'Arial',
                size: 12,
                color: '#2c3e50'
            },
            hovermode: 'x unified',
            dragmode: 'zoom'
        };

        const config = {
            responsive: true,
            displayModeBar: true,
            displaylogo: false,
            modeBarButtonsToAdd: ['drawline', 'drawopenpath', 'drawclosedpath', 'drawcircle', 'drawrect', 'eraseshape'],
            modeBarButtonsToRemove: ['lasso2d', 'select2d'],
            scrollZoom: true,
            doubleClick: 'reset'
        };

        Plotly.newPlot('candleChart', candleData, layout, config);
        console.log("📊 Nuevo gráfico creado");
    }

    renderQuickStats(data) {
        const quickStats = document.getElementById('quickStats');
        if (!quickStats || !data) return;

        console.log('📊 Renderizando quickStats con datos:', {
            moneda: this.currentCoin,
            precio: data.current_price,
            cambio: data.price_change_24h,
            marketCap: data.market_cap,
            volumen: data.volume_24h
        });

        requestAnimationFrame(() => {
            // Asegurar que los valores sean números y tengan valores por defecto
            const currentPrice = parseFloat(data.current_price) || 0;
            const priceChange = parseFloat(data.price_change_24h) || 0;
            const marketCap = parseFloat(data.market_cap) || 0;
            const volume24h = parseFloat(data.volume_24h) || 0;

            const statsHtml = `
                <div class="stat-item">
                    <small class="text-muted">Precio Actual</small>
                    <h4 class="mb-0 text-primary">$${currentPrice.toLocaleString('en-US', {
                minimumFractionDigits: 2,
                maximumFractionDigits: currentPrice < 1 ? 6 : 2
            })}</h4>
                    <small class="text-muted">${this.currentCoin.toUpperCase()}</small>
                </div>
                <div class="stat-item">
                    <small class="text-muted">Cambio 24h</small>
                    <h4 class="mb-0 ${priceChange >= 0 ? 'text-success' : 'text-danger'}">
                        ${priceChange >= 0 ? '+' : ''}${priceChange.toFixed(2)}%
                    </h4>
                </div>
                <div class="stat-item">
                    <small class="text-muted">Market Cap</small>
                    <h4 class="mb-0">$${this.formatNumber(marketCap)}</h4>
                </div>
                <div class="stat-item">
                    <small class="text-muted">Volumen 24h</small>
                    <h4 class="mb-0">$${this.formatNumber(volume24h)}</h4>
                </div>
            `;
            quickStats.innerHTML = statsHtml;
        });
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

        // Generar señales inmediatamente con datos disponibles
        const signals = this.generateEMASignals();

        requestAnimationFrame(() => {
            let signalsHtml = `
                <div class="d-flex justify-content-between align-items-center mb-3">
                    <h6 class="mb-0">Señales de Trading:</h6>
                    <small class="text-muted">EMA${this.emaPeriod}</small>
                </div>
            `;

            if (signals.length === 0) {
                signalsHtml += `
                    <div class="alert alert-warning">
                        <div class="d-flex align-items-center">
                            <i class="bi bi-info-circle me-2"></i>
                            <div>
                                <p class="mb-1">No hay señales claras</p>
                                <small class="text-muted">Precio cerca de la EMA</small>
                            </div>
                        </div>
                    </div>
                `;
            } else {
                signals.forEach(signal => {
                    const alertClass = signal.type === 'BUY' ? 'alert-success' :
                        signal.type === 'SELL' ? 'alert-danger' : 'alert-warning';

                    const icon = signal.type === 'BUY' ? 'bi-arrow-up-circle' :
                        signal.type === 'SELL' ? 'bi-arrow-down-circle' : 'bi-pause-circle';

                    signalsHtml += `
                        <div class="alert ${alertClass}">
                            <div class="d-flex justify-content-between align-items-start">
                                <div class="flex-grow-1">
                                    <div class="d-flex align-items-center mb-2">
                                        <i class="bi ${icon} me-2"></i>
                                        <h6 class="mb-0">${signal.type}</h6>
                                        <span class="badge bg-${signal.confidence === 'high' ? 'success' : signal.confidence === 'medium' ? 'warning' : 'secondary'} ms-2">
                                            ${signal.confidence.toUpperCase()}
                                        </span>
                                    </div>
                                    <p class="mb-2 small">${signal.reason}</p>
                                    <div class="d-flex justify-content-between align-items-center">
                                        <small class="text-muted">
                                            <i class="bi bi-clock me-1"></i>
                                            ${new Date(signal.timestamp).toLocaleTimeString()}
                                        </small>
                                        <small class="text-muted">
                                            Precio: $${signal.price.toFixed(2)}
                                        </small>
                                    </div>
                                </div>
                            </div>
                        </div>
                    `;

                    // Botones de acción
                    if (signal.type === 'BUY' && signal.confidence === 'high') {
                        tradeActionsDiv.innerHTML = `
                            <div class="text-center">
                                <button class="btn btn-success btn-lg" id="buyBtn" 
                                    onclick="dashboard.executeTrade('buy')">
                                    <i class="bi bi-arrow-up-circle me-2"></i>
                                    Comprar ${this.currentCoin.toUpperCase()}
                                </button>
                            </div>
                        `;
                    } else if (signal.type === 'SELL' && signal.confidence === 'high') {
                        tradeActionsDiv.innerHTML = `
                            <div class="text-center">
                                <button class="btn btn-danger btn-lg" id="sellBtn" 
                                    onclick="dashboard.executeTrade('sell')">
                                    <i class="bi bi-arrow-down-circle me-2"></i>
                                    Vender ${this.currentCoin.toUpperCase()}
                                </button>
                            </div>
                        `;
                    }
                });
            }

            signalsDiv.innerHTML = signalsHtml;
        });
    }

    // OPTIMIZACIÓN DE SEÑALES
    generateEMASignals() {
        if (!this.emaData || this.emaData.length < 2 || !this.ohlcData || this.ohlcData.length < 2) {
            return [{
                type: 'HOLD',
                confidence: 'low',
                reason: 'Esperando datos suficientes para análisis...',
                price: 0,
                emaValue: 0,
                timestamp: new Date().toISOString()
            }];
        }

        const currentPrice = this.ohlcData[this.ohlcData.length - 1].close;
        const currentEma = this.emaData[this.emaData.length - 1].value;
        const priceVsEma = ((currentPrice - currentEma) / currentEma) * 100;

        // Señales simplificadas para mejor rendimiento
        if (priceVsEma > 1) {
            return [{
                type: 'BUY',
                confidence: 'medium',
                reason: `Precio ${priceVsEma.toFixed(2)}% por encima de la EMA${this.emaPeriod}. Posible tendencia alcista.`,
                price: currentPrice,
                emaValue: currentEma,
                timestamp: new Date().toISOString()
            }];
        } else if (priceVsEma < -1) {
            return [{
                type: 'SELL',
                confidence: 'medium',
                reason: `Precio ${Math.abs(priceVsEma).toFixed(2)}% por debajo de la EMA${this.emaPeriod}. Posible tendencia bajista.`,
                price: currentPrice,
                emaValue: currentEma,
                timestamp: new Date().toISOString()
            }];
        } else {
            return [{
                type: 'HOLD',
                confidence: 'medium',
                reason: `Precio cerca de la EMA${this.emaPeriod} (${priceVsEma.toFixed(2)}%). Esperando señal más clara.`,
                price: currentPrice,
                emaValue: currentEma,
                timestamp: new Date().toISOString()
            }];
        }
    }

    // AUTO-REFRESH OPTIMIZADO
    startAutoRefresh() {
        if (this.autoRefreshInterval) {
            clearInterval(this.autoRefreshInterval);
        }

        this.autoRefreshInterval = setInterval(() => {
            this.optimizedRefresh();
        }, this.autoRefreshTime);

        console.log("🔄 Auto-actualización OPTIMIZADA iniciada");
    }

    async optimizedRefresh() {
        if (this.isLoading) {
            console.log("⏳ Saltando actualización - ya hay una en curso");
            return;
        }

        try {
            console.log("🔄 Ejecutando actualización automática...");

            // Actualizar solo datos esenciales, de forma secuencial para evitar conflictos
            await this.loadGlobalMetrics();

            // Pequeña pausa entre requests
            await new Promise(resolve => setTimeout(resolve, 1000));

            await this.loadCoinDataOptimized(this.currentCoin, 30);

            this.updateLastUpdatedTime();
            console.log("✅ Actualización automática completada");

        } catch (error) {
            console.warn('⚠️ Error en actualización automática:', error.message);
            // No detener el auto-refresh por errores individuales
        }
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

        requestAnimationFrame(() => {
            if (this.futureEmaData && this.futureEmaData.length > 0) {
                const currentPrice = this.ohlcData[this.ohlcData.length - 1].close;
                const lastPrediction = this.futureEmaData[this.futureEmaData.length - 1].value;
                const changePercentage = ((lastPrediction - currentPrice) / currentPrice) * 100;
                const trend = changePercentage >= 0 ? 'alcista' : 'bajista';

                predictionsDiv.innerHTML = `
                    <h6>Predicción ${this.futurePeriods}d:</h6>
                    <div class="card mb-3">
                        <div class="card-body">
                            <h5 class="card-title ${changePercentage >= 0 ? 'text-success' : 'text-danger'}">
                                ${changePercentage >= 0 ? '📈' : '📉'} ${Math.abs(changePercentage).toFixed(2)}%
                            </h5>
                            <p class="card-text">
                                Tendencia ${trend} (EMA${this.emaPeriod})
                            </p>
                            <div class="row">
                                <div class="col-6">
                                    <small>Actual:</small>
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
            } else {
                predictionsDiv.innerHTML = `
                    <div class="alert alert-info">
                        <h6>🔮 Predicciones</h6>
                        <p>Calculando...</p>
                    </div>
                `;
            }
        });
    }

    // LIMPIAR CACHÉ cuando sea necesario
    clearCache() {
        this.dataCache.clear();
        this.chartCache.clear();
        console.log("🗑️ Caché limpiado");
    }

    // PRECARGA OPTIMIZADA
    async preloadPopularCoins() {
        console.log("🔮 Precargando datos esenciales...");

        const preloadPromises = this.essentialCoins
            .filter(coin => coin !== this.currentCoin)
            .map(async (coin, index) => {
                // Espaciar requests para evitar sobrecarga
                await new Promise(resolve => setTimeout(resolve, index * 2000));

                try {
                    console.log(`🔍 Precargando: ${coin}`);
                    const response = await this.fetchWithRetry(
                        `/api/v1/coins/markets?vs_currency=usd&ids=${coin}&per_page=1&page=1`,
                        8000,
                        2 // Solo 2 reintentos para precarga
                    );

                    if (response.ok) {
                        const data = await response.json();
                        if (Array.isArray(data) && data.length > 0) {
                            this.setCachedData(`coin_${coin}_simple`, data[0], 300000);
                            console.log(`✅ Precargado: ${coin}`);
                        }
                    }
                } catch (error) {
                    console.log(`❌ Error precargando ${coin}:`, error.message);
                    // No hacer nada, solo continuar con la siguiente
                }
            });

        await Promise.allSettled(preloadPromises);
        console.log("🎯 Precarga completada");
    }

    async fetchWithRetry(url, timeout = 15000, retries = 3) {
        for (let attempt = 1; attempt <= retries; attempt++) {
            try {
                console.log(`🔄 Intento ${attempt}/${retries} para: ${url}`);
                const response = await this.fetchWithTimeout(url, timeout);

                if (response.ok) {
                    return response;
                } else {
                    console.warn(`❌ HTTP ${response.status} en intento ${attempt}`);
                }
            } catch (error) {
                console.warn(`❌ Error en intento ${attempt}:`, error.message);

                if (attempt === retries) {
                    throw error;
                }

                // Esperar antes del siguiente intento (backoff exponencial)
                const delay = 1000 * Math.pow(2, attempt - 1);
                console.log(`⏳ Esperando ${delay}ms antes del reintento...`);
                await new Promise(resolve => setTimeout(resolve, delay));
            }
        }
    }

    // MANEJO DE CAMBIO DE MONEDA OPTIMIZADO
    changeCrypto() {
        const select = document.getElementById('coinSelector');
        const newCoin = select.value;

        if (newCoin === this.currentCoin) return;

        // Cancelar request anterior si existe
        if (this.currentRequestController) {
            this.currentRequestController.abort();
        }

        this.currentCoin = newCoin;
        this.showQuickChangeFeedback();
        this.loadCoinDataOptimized(this.currentCoin, 30);
    }

    // LIMPIEZA PERIÓDICA
    startCacheCleanup() {
        setInterval(() => {
            this.clearExpiredCache();
            console.log("🧹 Limpieza de caché ejecutada");
        }, 300000); // Cada 5 minutos
    }

    showQuickChangeFeedback() {
        const quickStats = document.getElementById('quickStats');
        if (quickStats) {
            quickStats.innerHTML = `
                <div class="text-center w-100 py-3">
                    <div class="spinner-border spinner-border-sm"></div>
                    <p class="mt-2 mb-0">Cambiando a ${this.currentCoin.toUpperCase()}...</p>
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
                    <button onclick="dashboard.loadCoinDataRobust('${coinId}')" class="btn btn-sm btn-outline-warning ms-2">
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
                    <div class="card opportunity-card" onclick="dashboard.loadCoinDataRobust('${coin.id || 'bitcoin'}')">
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

// Inicialización optimizada
document.addEventListener('DOMContentLoaded', function () {
    window.dashboard = new CryptoDashboard();

    // Iniciar limpieza de caché
    window.dashboard.startCacheCleanup();

    // Precargar después de que todo esté listo
    setTimeout(() => {
        window.dashboard.preloadPopularCoins();
    }, 5000);
});