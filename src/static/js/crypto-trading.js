function saveState() {
    localStorage.setItem('tradingState', JSON.stringify(appState));
    console.log("Estado guardado correctamente");
}

function loadState() {
    const savedState = localStorage.getItem('tradingState');
    if (savedState) {
        appState = JSON.parse(savedState);
        return true;
    }
    return false;
}

// Al cargar la página, verificar si hay una transferencia pendiente
document.addEventListener('DOMContentLoaded', function () {
    // Verificar si hay una transferencia pendiente
    const pendingWithdrawal = localStorage.getItem('pendingWithdrawal');

    if (pendingWithdrawal) {
        const withdrawalData = JSON.parse(pendingWithdrawal);

        // Cargar el estado guardado
        const savedState = localStorage.getItem('tradingState');
        if (savedState) {
            appState = JSON.parse(savedState);

            // Procesar la retirada
            const amount = parseFloat(withdrawalData.amount);
            const fee = amount * 0.015; // 1.5% de comisión

            // Actualizar el estado
            appState.withdrawableProfit -= amount;
            appState.totalFees += fee;

            // Registrar la transacción
            appState.transactions.push({
                type: 'WITHDRAWAL',
                amount: amount,
                fee: fee,
                total: -amount,
                method: 'PAYPAL',
                email: withdrawalData.email,
                timestamp: new Date(withdrawalData.timestamp)
            });

            // Mostrar mensaje de confirmación
            alert(`Retiro procesado: $${amount.toFixed(2)} enviados a ${withdrawalData.email}`);

            // Limpiar los datos de transferencia pendiente
            localStorage.removeItem('pendingWithdrawal');
            localStorage.removeItem('tradingState');

            // Actualizar la UI
            updateUI();
        }
    }

    // Iniciar la aplicación normalmente
    initApp();

    // Inicializar PayPal para el modal
    initializeModalPayPal();
});

// ===== VARIABLES GLOBALES =====
const initialState = {
    balanceUSDT: 10000,
    balanceBTC: 0,
    balanceETH: 0,
    balanceSOL: 0,
    balanceBNB: 0,
    balanceADA: 0,
    currentPrice: 50000,
    positions: [],
    transactions: [],
    priceHistory: [],
    priceChange24h: 2.18,
    buyOrders: [],
    sellOrders: [],
    tradeFees: 0.001, // 0.1% de comisión
    initialInvestment: 10000,
    totalFees: 0,
    totalProfit: 0,
    totalLoss: 0,
    realizedProfit: 0,    // Ganancias realizadas (de ventas)
    realizedLoss: 0,      // Pérdidas realizadas (de ventas)
    unrealizedProfit: 0,  // Ganancias no realizadas (de posiciones abiertas)
    unrealizedLoss: 0,    // Pérdidas no realizadas (de posiciones abiertas)
    withdrawableProfit: 0, // Ganancias retirables

    // Precios de criptomonedas (se actualizarán con datos reales)
    cryptoPrices: {
        bitcoin: 50000,
        ethereum: 2345.67,
        solana: 98.76,
        binancecoin: 315.42,
        cardano: 0.52
    },
    // Símbolos de criptomonedas
    cryptoSymbols: {
        bitcoin: "BTC",
        ethereum: "ETH",
        solana: "SOL",
        binancecoin: "BNB",
        cardano: "ADA"
    },
    // Cambios porcentuales de las criptomonedas
    cryptoChanges: {
        bitcoin: 2.18,
        ethereum: 1.25,
        solana: -0.87,
        binancecoin: 0.42,
        cardano: -0.15
    },
    // Criptomoneda actualmente seleccionada
    currentCrypto: 'bitcoin',
    // Puntos de compra/venta en el gráfico
    tradePoints: []
};

let appState = { ...initialState };
let chart = null;
let updateInterval = null;
let currentTransactionType = '';
let paypalButtons = null;
let isPaypalInputFocused = false;
let userModifiedWithdrawal = false;
let sessionToken = localStorage.getItem('session_token');

// Variables para el modal de compra
let modalCryptoAmount = 0;
let modalTotalAmount = 0;
let modalCommission = 0;
let modalFinalAmount = 0;

// Configuración con credenciales REALES
const PAYPAL_CLIENT_ID = 'AQQemAMRExJZZv9AukiyD9eozPk-mL51cwmVyKGujHpKraHNW3wdVARfCrGJuXzOu6TECqb260DZEVpp';
const WITHDRAWAL_FEE_PERCENT = 1.5;
const MIN_WITHDRAWAL = 10;
const MAX_WITHDRAWAL = 5000;
let currentPaypalAmount = 100;

// ===== FUNCIONES DE API =====
async function fetchWithAuth(url, options = {}) {
    if (!sessionToken) {
        console.error('No session token available');
        return null;
    }

    const defaultOptions = {
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${sessionToken}`
        },
        credentials: 'include'
    };

    try {
        const response = await fetch(url, { ...defaultOptions, ...options });
        
        if (response.status === 401) {
            // Token expired or invalid
            localStorage.removeItem('session_token');
            window.location.href = '/';
            return null;
        }

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        return await response.json();
    } catch (error) {
        console.error('API request failed:', error);
        return null;
    }
}

async function fetchCryptoPrices() {
    try {
        const response = await fetch('/api/v1/coins/markets?vs_currency=usd&per_page=50&page=1');
        if (!response.ok) throw new Error('Failed to fetch prices');
        
        const data = await response.json();
        const prices = {};
        const changes = {};
        
        data.forEach(coin => {
            const coinId = coin.id;
            prices[coinId] = coin.current_price;
            changes[coinId] = coin.price_change_percentage_24h;
        });
        
        return { prices, changes };
    } catch (error) {
        console.error('Error fetching crypto prices:', error);
        return null;
    }
}

async function fetchCurrentPrice(coinId) {
    try {
        const response = await fetch(`/api/v1/trading/${coinId}/price`);
        if (!response.ok) throw new Error('Failed to fetch price');
        
        const data = await response.json();
        return data.price_usd;
    } catch (error) {
        console.error('Error fetching current price:', error);
        return null;
    }
}

async function fetchHistoricalData(coinId, days = 7) {
    try {
        const response = await fetch(`/api/v1/trading/${coinId}/metrics?days=${days}`);
        if (!response.ok) throw new Error('Failed to fetch historical data');
        
        const data = await response.json();
        return data;
    } catch (error) {
        console.error('Error fetching historical data:', error);
        return null;
    }
}

async function fetchTradingSignals(coinId, timeframe = '24h') {
    try {
        const response = await fetch(`/api/v1/trading/${coinId}/signals?time_frame=${timeframe}`);
        if (!response.ok) throw new Error('Failed to fetch signals');
        
        const data = await response.json();
        return data;
    } catch (error) {
        console.error('Error fetching trading signals:', error);
        return null;
    }
}

async function fetchUserBalance() {
    try {
        const response = await fetchWithAuth('/api/user/balance');
        return response;
    } catch (error) {
        console.error('Error fetching user balance:', error);
        return null;
    }
}

async function fetchCryptoBalances() {
    try {
        const response = await fetchWithAuth('/api/user/crypto-balances');
        return response;
    } catch (error) {
        console.error('Error fetching crypto balances:', error);
        return null;
    }
}

async function fetchMarketData() {
    try {
        const response = await fetch('/api/v1/market/performance');
        if (!response.ok) throw new Error('Failed to fetch market data');
        
        return await response.json();
    } catch (error) {
        console.error('Error fetching market data:', error);
        return null;
    }
}

// ===== FUNCIÓN AÑADIDA: CALCULAR GANANCIAS/PÉRDIDAS NO REALIZADAS =====
function calculateUnrealizedPnL() {
    appState.unrealizedProfit = 0;
    appState.unrealizedLoss = 0;

    appState.positions.forEach(position => {
        const crypto = position.crypto;
        const currentPrice = appState.cryptoPrices[crypto];
        const positionValue = position.amount * currentPrice;
        const initialValue = position.amount * position.entryPrice;
        const pnl = positionValue - initialValue;

        if (pnl >= 0) {
            appState.unrealizedProfit += pnl;
        } else {
            appState.unrealizedLoss += Math.abs(pnl);
        }
    });
}

// ===== INICIALIZACIÓN =====
async function initApp() {
    if (!loadState()) {
        appState = { ...initialState };
    }

    // Cargar datos reales
    await loadRealData();
    
    updateUI();
    generatePriceHistory();
    generateOrders();
    initChart();
    setupEventListeners();
    initializePayPal();
    setupModalEventListeners();

    // Iniciar actualizaciones en tiempo real cada minuto
    updateInterval = setInterval(updateRealData, 60000); // Actualizar cada 60 segundos (1 minuto)
}

async function loadRealData() {
    try {
        // Cargar precios de criptomonedas
        const priceData = await fetchCryptoPrices();
        if (priceData) {
            appState.cryptoPrices = priceData.prices;
            appState.cryptoChanges = priceData.changes;
        }

        // Cargar balance del usuario
        const balanceData = await fetchUserBalance();
        if (balanceData && balanceData.success) {
            appState.balanceUSDT = balanceData.balance;
        }

        // Cargar balances de criptomonedas
        const cryptoBalances = await fetchCryptoBalances();
        if (cryptoBalances && cryptoBalances.success) {
            cryptoBalances.balances.forEach(balance => {
                const symbol = balance.coin_id.toUpperCase();
                appState[`balance${symbol}`] = balance.balance;
            });
        }

        // Cargar datos de mercado
        const marketData = await fetchMarketData();
        if (marketData) {
            // Actualizar métricas globales si es necesario
        }

    } catch (error) {
        console.error('Error loading real data:', error);
    }
}

async function updateRealData() {
    try {
        const priceData = await fetchCryptoPrices();
        if (priceData) {
            appState.cryptoPrices = priceData.prices;
            appState.cryptoChanges = priceData.changes;
        }

        // Actualizar precio histórico para la criptomoneda actual
        const historicalData = await fetchHistoricalData(appState.currentCrypto, 1);
        if (historicalData && historicalData.metrics) {
            updatePriceHistory(historicalData.metrics);
        }

        updateUI();
        updateChart();

    } catch (error) {
        console.error('Error updating real data:', error);
    }
}

function updatePriceHistory(metrics) {
    if (!metrics || !metrics.timestamps || !metrics.prices) return;

    const newHistory = [];
    for (let i = 0; i < metrics.timestamps.length; i++) {
        newHistory.push({
            time: new Date(metrics.timestamps[i]),
            value: metrics.prices[i]
        });
    }

    appState.priceHistory = newHistory;
}

// ===== FUNCIÓN PARA REDIRIGIR AL FORMULARIO DE TRANSFERENCIA PAYPAL =====
function redirectToPaypalTransfer() {
    localStorage.setItem('withdrawableProfit', appState.withdrawableProfit);
    localStorage.setItem('tradingState', JSON.stringify(appState));
    window.location.href = 'paypal-transacc';
}

// ===== FUNCIONES NUEVAS PARA EL MODAL SIMPLIFICADO =====
function updatePaypalSummaryModal() {
    const crypto = appState.currentCrypto;
    const symbol = appState.cryptoSymbols[crypto];
    const price = parseFloat(document.getElementById('price').value) || appState.cryptoPrices[crypto];
    const amount = parseFloat(document.getElementById('amount').value) || 0;
    const total = price * amount;
    const commission = total * 0.01;
    const finalTotal = total + commission;

    document.getElementById('summary-crypto-name').textContent =
        `${crypto.charAt(0).toUpperCase() + crypto.slice(1)} (${symbol})`;
    document.getElementById('summary-current-price').textContent =
        `$${appState.cryptoPrices[crypto].toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
    document.getElementById('summary-crypto-amount').textContent =
        `${amount.toFixed(6)} ${symbol}`;
    document.getElementById('summary-unit-price').textContent =
        `$${price.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
    document.getElementById('summary-subtotal').textContent =
        `$${total.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
    document.getElementById('summary-fee').textContent =
        `$${commission.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
    document.getElementById('summary-total').textContent =
        `$${finalTotal.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

    setSummaryCryptoIcon(crypto);
    initSummaryPayPal(finalTotal, amount, crypto);
}

function setSummaryCryptoIcon(cryptoType) {
    const iconElement = document.getElementById('summary-crypto-icon');
    iconElement.className = '';

    switch (cryptoType) {
        case 'bitcoin':
            iconElement.classList.add('fab', 'fa-bitcoin');
            break;
        case 'ethereum':
            iconElement.classList.add('fab', 'fa-ethereum');
            break;
        case 'solana':
            iconElement.classList.add('fas', 'fa-chart-line');
            break;
        case 'binancecoin':
            iconElement.classList.add('fas', 'fa-coins');
            break;
        case 'cardano':
            iconElement.classList.add('fas', 'fa-square');
            break;
        default:
            iconElement.classList.add('fas', 'fa-coins');
    }
}

function initSummaryPayPal(amount, cryptoAmount, crypto) {
    const symbol = appState.cryptoSymbols[crypto];
    document.getElementById('summary-paypal-button-container').innerHTML = '';

    try {
        paypal.Buttons({
            style: {
                shape: 'pill',
                color: 'blue',
                layout: 'vertical',
                label: 'paypal'
            },

            createOrder: function (data, actions) {
                if (cryptoAmount <= 0) {
                    alert('Por favor, ingrese una cantidad válida de criptomoneda');
                    return false;
                }

                if (amount < 10) {
                    alert('El monto mínimo de compra es $10.00');
                    return false;
                }

                return actions.order.create({
                    purchase_units: [{
                        amount: {
                            value: amount.toFixed(2),
                            currency_code: 'USD',
                            breakdown: {
                                item_total: {
                                    value: (amount * 0.99).toFixed(2),
                                    currency_code: 'USD'
                                },
                                tax_total: {
                                    value: (amount * 0.01).toFixed(2),
                                    currency_code: 'USD'
                                }
                            }
                        },
                        items: [{
                            name: `Compra de ${cryptoAmount} ${symbol}`,
                            description: `Compra de ${crypto} a través de Crypto Trading Platform`,
                            quantity: '1',
                            unit_amount: {
                                value: (amount * 0.99).toFixed(2),
                                currency_code: 'USD'
                            },
                            category: 'DIGITAL_GOODS'
                        }]
                    }],
                    application_context: {
                        shipping_preference: 'NO_SHIPPING',
                        user_action: 'PAY_NOW'
                    }
                });
            },

            onApprove: function (data, actions) {
                return actions.order.capture().then(function (details) {
                    processPaypalPurchase(details, amount, cryptoAmount, crypto);
                });
            },

            onError: function (err) {
                console.error('Error en PayPal:', err);
                alert('Error en el procesamiento del pago. Por favor, intente nuevamente.');
            }

        }).render('#summary-paypal-button-container');

    } catch (error) {
        console.error('Error inicializando PayPal en modal de resumen:', error);
    }
}

async function processPaypalPurchase(details, amount, cryptoAmount, crypto) {
    try {
        const symbol = appState.cryptoSymbols[crypto];
        const price = amount / cryptoAmount;

        // Enviar transacción al backend
        const response = await fetchWithAuth('/api/paypal/buy-crypto', {
            method: 'POST',
            body: JSON.stringify({
                paymentID: details.id,
                payerID: details.payerID,
                amount: amount,
                coin_id: crypto,
                coin_amount: cryptoAmount,
                price_per_coin: price
            })
        });

        if (response && response.success) {
            // Actualizar estado local
            appState[`balance${symbol}`] = (appState[`balance${symbol}`] || 0) + cryptoAmount;
            
            appState.transactions.push({
                type: 'BUY',
                amount: cryptoAmount,
                price: price,
                total: amount * 0.99,
                fee: amount * 0.01,
                crypto: crypto,
                timestamp: new Date(),
                paymentMethod: 'PAYPAL',
                paymentId: details.id
            });

            // Añadir punto de compra en el gráfico
            addTradePoint('BUY', new Date(), price);

            if (cryptoAmount > 0.001) {
                appState.positions.push({
                    pair: `${symbol}/USDT`,
                    type: 'LONG',
                    entryPrice: price,
                    amount: cryptoAmount,
                    crypto: crypto,
                    timestamp: new Date()
                });
            }

            alert(`¡Compra exitosa! Has comprado ${cryptoAmount.toFixed(6)} ${symbol} por $${amount.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`);

            const modal = bootstrap.Modal.getInstance(document.getElementById('paypalSummaryModal'));
            if (modal) modal.hide();

            updateUI();
            saveState();
        } else {
            throw new Error('Error processing purchase');
        }

    } catch (error) {
        console.error('Error processing PayPal purchase:', error);
        alert('Error procesando la compra. Por favor, intente nuevamente.');
    }
}

// ===== ACTUALIZACIÓN DE LA INTERFAZ =====
function updateUI() {
    const crypto = appState.currentCrypto;
    const symbol = appState.cryptoSymbols[crypto];
    const price = appState.cryptoPrices[crypto];
    const change = appState.cryptoChanges[crypto];
    const balance = appState[`balance${symbol}`] || 0;

    // Actualizar información del par
    document.getElementById('pair-name').textContent = `${symbol}/USDT`;
    document.getElementById('current-price').textContent = `$${price.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

    const changeElement = document.getElementById('price-change');
    changeElement.textContent = `${change >= 0 ? '+' : ''}${change.toFixed(2)}%`;
    changeElement.className = `pair-change ${change >= 0 ? 'change-positive' : 'change-negative'}`;

    // Actualizar balances
    document.getElementById('balance-usdt').textContent = `$${appState.balanceUSDT.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
    document.getElementById('balance-crypto').textContent = `${balance.toFixed(6)} ${symbol}`;

    // Calcular valores totales
    const cryptoValue = balance * price;
    const totalValue = appState.balanceUSDT + cryptoValue;
    const netResult = totalValue - appState.initialInvestment;

    // Actualizar ganancias/pérdidas
    updateProfitLossUI();

    // Resto del código de updateUI()...
    document.getElementById('available-usdt').textContent = `${appState.balanceUSDT.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} USDT`;
    document.getElementById('available-crypto').textContent = `${balance.toFixed(6)} ${symbol}`;
    document.getElementById('max-buy').textContent = `${(appState.balanceUSDT / price).toFixed(6)} ${symbol}`;
    document.getElementById('max-sell').textContent = `${balance.toFixed(6)} ${symbol}`;
    document.getElementById('last-price').textContent = `$${price.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

    // Actualizar botones de compra/venta
    document.getElementById('buy-btn').textContent = `Comprar ${symbol}`;
    document.getElementById('sell-btn').textContent = `Vender ${symbol}`;

    // Actualizar resumen
    document.getElementById('total-value').textContent = `$${totalValue.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
    document.getElementById('net-result').textContent = `$${netResult.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
    document.getElementById('net-result').className = `summary-value ${netResult >= 0 ? 'positive' : 'negative'}`;
    document.getElementById('total-fees').textContent = `$${appState.totalFees.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

    // Actualizar ganancias retirables
    updateWithdrawableSections();

    // Actualizar posiciones
    renderPositions();

    // Actualizar historial de transacciones
    renderTransactions();
}

// Función para actualizar todas las secciones de ganancias retirables
function updateWithdrawableSections() {
    const withdrawableProfit = appState.withdrawableProfit;
    const paypalInput = document.getElementById('paypalWithdrawAmount');

    if (!userModifiedWithdrawal && !isPaypalInputFocused) {
        const maxWithdrawal = Math.min(MAX_WITHDRAWAL, withdrawableProfit);
        const defaultValue = Math.min(100, maxWithdrawal);
        paypalInput.value = maxWithdrawal > 0 ? defaultValue.toFixed(2) : '0.00';
        currentPaypalAmount = parseFloat(paypalInput.value);
    }

    document.getElementById('withdrawable-profit').textContent =
        `$${withdrawableProfit.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

    document.getElementById('withdrawable-amount').textContent =
        `$${withdrawableProfit.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

    document.getElementById('paypal-withdrawable-amount').textContent =
        `$${withdrawableProfit.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

    const maxWithdrawal = Math.min(MAX_WITHDRAWAL, withdrawableProfit);
    paypalInput.max = maxWithdrawal;

    calculatePayPalWithdrawal();
}

// Función para actualizar la UI con ganancias y pérdidas
function updateProfitLossUI() {
    calculateUnrealizedPnL();

    const totalProfit = appState.realizedProfit + appState.unrealizedProfit;
    const totalLoss = appState.realizedLoss + appState.unrealizedLoss;

    const profitPercent = appState.initialInvestment > 0 ?
        (totalProfit / appState.initialInvestment) * 100 : 0;
    const lossPercent = appState.initialInvestment > 0 ?
        (totalLoss / appState.initialInvestment) * 100 : 0;

    document.getElementById('total-profit').textContent =
        `+$${totalProfit.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
    document.getElementById('total-loss').textContent =
        `-$${totalLoss.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
    document.getElementById('profit-percent').textContent =
        `+${profitPercent.toFixed(2)}%`;
    document.getElementById('loss-percent').textContent =
        `-${lossPercent.toFixed(2)}%`;

    document.getElementById('total-profit').title =
        `Realizadas: $${appState.realizedProfit.toFixed(2)} | No realizadas: $${appState.unrealizedProfit.toFixed(2)}`;
    document.getElementById('total-loss').title =
        `Realizadas: $${appState.realizedLoss.toFixed(2)} | No realizadas: $${appState.unrealizedLoss.toFixed(2)}`;
}

// ===== SELECCIÓN DE CRIPTOMONEDA =====
function changeCrypto() {
    const select = document.getElementById('crypto-select');
    appState.currentCrypto = select.value;

    updateUI();
    generatePriceHistory();
    generateOrders();
    updateChart();
    updateModalCryptoInfo();
}

// ===== PAYPAL =====
function initializePayPal() {
    try {
        paypal.Buttons({
            style: {
                shape: 'pill',
                color: 'blue',
                layout: 'vertical',
                label: 'paypal'
            },

            createOrder: function (data, actions) {
                return actions.order.create({
                    purchase_units: [{
                        amount: {
                            value: currentPaypalAmount.toFixed(2),
                            currency_code: 'USD'
                        },
                        description: `Retiro de ganancias - ${new Date().toLocaleDateString()}`
                    }],
                    application_context: {
                        shipping_preference: 'NO_SHIPPING'
                    }
                });
            },

            onApprove: function (data, actions) {
                return actions.order.capture().then(function (details) {
                    processPayPalWithdrawal(details);
                });
            },

            onError: function (err) {
                console.error('Error en PayPal:', err);
                updatePayPalConnectionStatus('Error en la conexión con PayPal', 'danger');
            },

            onClick: function () {
                if (!validatePayPalWithdrawal()) {
                    return false;
                }
            }

        }).render('#paypal-button-container');

        updatePayPalConnectionStatus('Conectado a PayPal correctamente', 'success');

    } catch (error) {
        console.error('Error inicializando PayPal:', error);
        updatePayPalConnectionStatus('Error al conectar con PayPal', 'danger');
    }
}

// Validar retiro PayPal
function validatePayPalWithdrawal() {
    const amountInput = document.getElementById('paypalWithdrawAmount');
    const amount = parseFloat(amountInput.value) || 0;

    if (amount < MIN_WITHDRAWAL || amount > MAX_WITHDRAWAL) {
        alert(`El monto debe estar entre $${MIN_WITHDRAWAL} y $${MAX_WITHDRAWAL}`);
        amountInput.focus();
        return false;
    }

    if (amount > appState.withdrawableProfit) {
        alert('Ganancias retirables insuficientes para realizar este retiro');
        amountInput.focus();
        return false;
    }

    currentPaypalAmount = amount;
    return true;
}

// Procesar retiro con los datos de PayPal
async function processPayPalWithdrawal(paypalDetails) {
    try {
        updatePayPalConnectionStatus('Procesando retiro...', 'warning');

        const fee = (currentPaypalAmount * WITHDRAWAL_FEE_PERCENT) / 100;
        const totalReceived = currentPaypalAmount - fee;

        const response = await fetchWithAuth('/api/braintree/withdraw', {
            method: 'POST',
            body: JSON.stringify({
                amount: currentPaypalAmount,
                bank_account_token: 'paypal_account', // Token simulado para PayPal
                paypal_details: paypalDetails
            })
        });

        if (response && response.success) {
            showPayPalSuccess(response.transaction.id, totalReceived);
            updatePayPalConnectionStatus('Retiro procesado exitosamente', 'success');

            appState.withdrawableProfit -= currentPaypalAmount;
            saveState();
            updateUI();
        } else {
            throw new Error(response?.message || 'Error en el servidor');
        }

    } catch (error) {
        console.error('Error procesando retiro:', error);
        alert('Error procesando el retiro: ' + error.message);
        updatePayPalConnectionStatus('Error en el procesamiento', 'danger');
    }
}

// Mostrar éxito en retiro PayPal
function showPayPalSuccess(transactionId, amount) {
    const successHtml = `
        <div class="alert alert-success">
            <h5><i class="fas fa-check-circle me-2"></i>¡Retiro Exitoso!</h5>
            <p class="mb-1">ID de Transacción: <strong>${transactionId}</strong></p>
            <p class="mb-1">Monto recibido: <strong>$${amount.toFixed(2)}</strong></p>
            <p class="mb-0">Estado: <span class="badge bg-success">Completado</span></p>
        </div>
    `;

    document.querySelector('.paypal-withdrawal-section').insertAdjacentHTML('afterbegin', successHtml);
}

// Actualizar estado de conexión PayPal
function updatePayPalConnectionStatus(message, type) {
    const statusElement = document.getElementById('paypalConnectionStatus');
    statusElement.textContent = message;
    statusElement.className = 'mb-0';

    if (type === 'success') {
        statusElement.classList.add('text-success');
    } else if (type === 'danger') {
        statusElement.classList.add('text-danger');
    } else if (type === 'warning') {
        statusElement.classList.add('text-warning');
    }
}

// Calcular tarifas PayPal
function calculatePayPalWithdrawal() {
    const amountInput = document.getElementById('paypalWithdrawAmount');
    const amount = parseFloat(amountInput.value) || 0;
    const fee = (amount * WITHDRAWAL_FEE_PERCENT) / 100;
    const total = amount - Math.min(fee, 10);

    document.getElementById('paypalSummaryAmount').textContent = amount.toFixed(2);
    document.getElementById('paypalSummaryFee').textContent = Math.min(fee, 10).toFixed(2);
    document.getElementById('paypalSummaryTotal').textContent = total.toFixed(2);
}

// ===== FUNCIONES DEL MODAL DE COMPRA =====
function updateModalCryptoInfo() {
    const crypto = appState.currentCrypto;
    const symbol = appState.cryptoSymbols[crypto];
    const price = appState.cryptoPrices[crypto];

    document.getElementById('modal-crypto-name').textContent = `${crypto.charAt(0).toUpperCase() + crypto.slice(1)} (${symbol})`;
    document.getElementById('modal-crypto-symbol').textContent = symbol;
    document.getElementById('modal-current-price').textContent = `$${price.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
    document.getElementById('modal-unit-price').value = price.toFixed(2);

    setModalCryptoIcon(crypto);
    resetModalCalculations();
}

function setModalCryptoIcon(cryptoType) {
    const iconElement = document.getElementById('modal-crypto-icon');
    iconElement.className = '';

    switch (cryptoType) {
        case 'bitcoin':
            iconElement.classList.add('fab', 'fa-bitcoin');
            break;
        case 'ethereum':
            iconElement.classList.add('fab', 'fa-ethereum');
            break;
        case 'solana':
            iconElement.classList.add('fas', 'fa-chart-line');
            break;
        case 'binancecoin':
            iconElement.classList.add('fas', 'fa-coins');
            break;
        case 'cardano':
            iconElement.classList.add('fas', 'fa-square');
            break;
        default:
            iconElement.classList.add('fas', 'fa-coins');
    }
}

function calculateModalTotal() {
    modalCryptoAmount = parseFloat(document.getElementById('modal-crypto-amount').value) || 0;
    const price = appState.cryptoPrices[appState.currentCrypto];

    if (modalCryptoAmount <= 0) {
        resetModalCalculations();
        return;
    }

    modalTotalAmount = modalCryptoAmount * price;
    modalCommission = modalTotalAmount * 0.01;
    modalFinalAmount = modalTotalAmount + modalCommission;

    document.getElementById('modal-total-amount').value = modalTotalAmount.toFixed(2);
    document.getElementById('modal-summary-subtotal').textContent =
        `$${modalTotalAmount.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
    document.getElementById('modal-summary-fee').textContent =
        `$${modalCommission.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
    document.getElementById('modal-summary-total').textContent =
        `$${modalFinalAmount.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function resetModalCalculations() {
    document.getElementById('modal-total-amount').value = '0.00';
    document.getElementById('modal-summary-subtotal').textContent = '$0.00';
    document.getElementById('modal-summary-fee').textContent = '$0.00';
    document.getElementById('modal-summary-total').textContent = '$0.00';

    modalCryptoAmount = 0;
    modalTotalAmount = 0;
    modalCommission = 0;
    modalFinalAmount = 0;
}

function initializeModalPayPal() {
    try {
        paypal.Buttons({
            style: {
                shape: 'pill',
                color: 'blue',
                layout: 'vertical',
                label: 'paypal'
            },

            createOrder: function (data, actions) {
                if (modalCryptoAmount <= 0) {
                    alert('Por favor, ingrese una cantidad válida de criptomoneda');
                    return false;
                }

                if (modalFinalAmount < 10) {
                    alert('El monto mínimo de compra es $10.00');
                    return false;
                }

                return actions.order.create({
                    purchase_units: [{
                        amount: {
                            value: modalFinalAmount.toFixed(2),
                            currency_code: 'USD',
                            breakdown: {
                                item_total: {
                                    value: modalTotalAmount.toFixed(2),
                                    currency_code: 'USD'
                                },
                                tax_total: {
                                    value: modalCommission.toFixed(2),
                                    currency_code: 'USD'
                                }
                            }
                        },
                        items: [{
                            name: `Compra de ${modalCryptoAmount} ${appState.cryptoSymbols[appState.currentCrypto]}`,
                            description: `Compra de ${appState.currentCrypto} a través de Crypto Trading Platform`,
                            quantity: '1',
                            unit_amount: {
                                value: modalTotalAmount.toFixed(2),
                                currency_code: 'USD'
                            },
                            category: 'DIGITAL_GOODS'
                        }]
                    }],
                    application_context: {
                        shipping_preference: 'NO_SHIPPING',
                        user_action: 'PAY_NOW'
                    }
                });
            },

            onApprove: function (data, actions) {
                return actions.order.capture().then(function (details) {
                    processModalPurchase(details);
                });
            },

            onError: function (err) {
                console.error('Error en PayPal:', err);
                alert('Error en el procesamiento del pago. Por favor, intente nuevamente.');
            },

            onClick: function () {
                if (modalCryptoAmount <= 0) {
                    alert('Por favor, ingrese una cantidad válida de criptomoneda');
                    return false;
                }

                if (modalFinalAmount < 10) {
                    alert('El monto mínimo de compra es $10.00');
                    return false;
                }
            }

        }).render('#modal-paypal-button-container');

    } catch (error) {
        console.error('Error inicializando PayPal en modal:', error);
    }
}

async function processModalPurchase(details) {
    try {
        const crypto = appState.currentCrypto;
        const symbol = appState.cryptoSymbols[crypto];

        const response = await fetchWithAuth('/api/paypal/buy-crypto', {
            method: 'POST',
            body: JSON.stringify({
                paymentID: details.id,
                payerID: details.payerID,
                amount: modalFinalAmount,
                coin_id: crypto,
                coin_amount: modalCryptoAmount,
                price_per_coin: appState.cryptoPrices[crypto]
            })
        });

        if (response && response.success) {
            appState[`balance${symbol}`] = (appState[`balance${symbol}`] || 0) + modalCryptoAmount;
            
            appState.transactions.push({
                type: 'BUY',
                amount: modalCryptoAmount,
                price: appState.cryptoPrices[crypto],
                total: modalTotalAmount,
                fee: modalCommission,
                crypto: crypto,
                timestamp: new Date(),
                paymentMethod: 'PAYPAL',
                paymentId: details.id
            });

            // Añadir punto de compra en el gráfico
            addTradePoint('BUY', new Date(), appState.cryptoPrices[crypto]);

            if (modalCryptoAmount > 0.001) {
                appState.positions.push({
                    pair: `${symbol}/USDT`,
                    type: 'LONG',
                    entryPrice: appState.cryptoPrices[crypto],
                    amount: modalCryptoAmount,
                    crypto: crypto,
                    timestamp: new Date()
                });
            }

            alert(`¡Compra exitosa! Has comprado ${modalCryptoAmount.toFixed(6)} ${symbol} por $${modalTotalAmount.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`);

            const modal = bootstrap.Modal.getInstance(document.getElementById('buyCryptoModal'));
            if (modal) modal.hide();

            saveState();
            updateUI();
        } else {
            throw new Error('Error processing purchase');
        }

    } catch (error) {
        console.error('Error processing modal purchase:', error);
        alert('Error procesando la compra. Por favor, intente nuevamente.');
    }
}

function setupModalEventListeners() {
    document.getElementById('modal-crypto-amount').addEventListener('input', calculateModalTotal);
    document.getElementById('buyCryptoModal').addEventListener('show.bs.modal', function () {
        updateModalCryptoInfo();
    });
}

// ===== FUNCIONES DEL SIMULADOR =====
function generatePriceHistory() {
    const now = Date.now();
    appState.priceHistory = [];
    const crypto = appState.currentCrypto;
    const price = appState.cryptoPrices[crypto];
    const change = appState.cryptoChanges[crypto];

    for (let i = 100; i > 0; i--) {
        const time = new Date(now - i * 60000);
        const baseChange = (change / 100) / 1440;
        const randomChange = (Math.random() - 0.5) * 0.002;

        const previousPrice = i === 100 ? price * 0.98 : appState.priceHistory[appState.priceHistory.length - 1].value;
        const newPrice = previousPrice * (1 + baseChange + randomChange);

        appState.priceHistory.push({
            time: time,
            value: newPrice
        });
    }

    appState.priceHistory.push({
        time: new Date(now),
        value: price
    });
}

function generateOrders() {
    const crypto = appState.currentCrypto;
    const price = appState.cryptoPrices[crypto];

    appState.buyOrders = [];
    for (let i = 10; i >= 1; i--) {
        const orderPrice = price * (1 - i * 0.001);
        const amount = (0.1 * i * (0.8 + Math.random() * 0.4));
        const total = orderPrice * amount;

        appState.buyOrders.push({
            price: orderPrice,
            amount: amount,
            total: total
        });
    }

    appState.sellOrders = [];
    for (let i = 1; i <= 10; i++) {
        const orderPrice = price * (1 + i * 0.001);
        const amount = (0.1 * i * (0.8 + Math.random() * 0.4));
        const total = orderPrice * amount;

        appState.sellOrders.push({
            price: orderPrice,
            amount: amount,
            total: total
        });
    }

    renderOrders();
}

function renderOrders() {
    const buyOrdersContainer = document.getElementById('buy-orders');
    const sellOrdersContainer = document.getElementById('sell-orders');

    buyOrdersContainer.innerHTML = '';
    sellOrdersContainer.innerHTML = '';

    appState.buyOrders.forEach(order => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td class="buy-price">${order.price.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 5 })}</td>
            <td>${order.amount.toFixed(5)}</td>
            <td>${order.total.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
        `;
        buyOrdersContainer.appendChild(row);
    });

    appState.sellOrders.forEach(order => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td class="sell-price">${order.price.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 5 })}</td>
            <td>${order.amount.toFixed(5)}</td>
            <td>${order.total.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
        `;
        sellOrdersContainer.appendChild(row);
    });
}

function renderPositions() {
    const positionsContainer = document.getElementById('positions-container');
    const crypto = appState.currentCrypto;
    const symbol = appState.cryptoSymbols[crypto];

    const currentPositions = appState.positions.filter(pos => pos.crypto === crypto);

    if (currentPositions.length === 0) {
        positionsContainer.innerHTML = `
            <div style="text-align: center; padding: 40px 20px; color: var(--text-secondary);">
                <div style="font-size: 48px; margin-bottom: 10px;">📊</div>
                <div>No hay posiciones abiertas</div>
                <div style="font-size: 13px; margin-top: 5px;">Realiza tu primera operación para comenzar</div>
            </div>
        `;
        return;
    }

    positionsContainer.innerHTML = '';

    currentPositions.forEach((position, index) => {
        const currentValue = position.amount * appState.cryptoPrices[crypto];
        const initialValue = position.amount * position.entryPrice;
        const profit = currentValue - initialValue;
        const profitPercent = (profit / initialValue) * 100;

        const positionEl = document.createElement('div');
        positionEl.className = 'position-card';
        positionEl.innerHTML = `
            <div class="position-info">
                <div class="position-pair">${position.pair}</div>
                <div class="position-details">
                    ${position.type} • ${position.amount.toFixed(6)} ${symbol} • Entrada: $${position.entryPrice.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                </div>
            </div>
            <div class="position-profit ${profit >= 0 ? 'positive' : 'negative'}">
                ${profit >= 0 ? '+' : ''}$${profit.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                <div class="profit-badge ${profit >= 0 ? 'positive' : 'negative'}">
                    ${profit >= 0 ? '+' : ''}${profitPercent.toFixed(2)}%
                </div>
            </div>
            <button class="close-btn" onclick="closePosition(${index}, '${crypto}')">×</button>
        `;

        positionsContainer.appendChild(positionEl);
    });
}

function renderTransactions() {
    const transactionHistory = document.getElementById('transaction-history');
    const crypto = appState.currentCrypto;

    const currentTransactions = appState.transactions.filter(trans => trans.crypto === crypto);

    if (currentTransactions.length === 0) {
        transactionHistory.innerHTML = '<div class="loading">No hay transacciones</div>';
        return;
    }

    transactionHistory.innerHTML = '';

    const recentTransactions = currentTransactions.slice(-10).reverse();

    recentTransactions.forEach(transaction => {
        const symbol = appState.cryptoSymbols[transaction.crypto];
        const transactionEl = document.createElement('div');
        transactionEl.className = 'transaction-item';

        transactionEl.innerHTML = `
            <div>
                <div class="transaction-type ${transaction.type.toLowerCase()}">${transaction.type}</div>
                <div class="transaction-details">${transaction.amount.toFixed(6)} ${symbol} @ $${transaction.price.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</div>
            </div>
            <div class="transaction-amount ${transaction.type === 'BUY' ? 'negative' : 'positive'}">
                ${transaction.type === 'BUY' ? '-' : '+'}$${Math.abs(transaction.total).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </div>
        `;

        transactionHistory.appendChild(transactionEl);
    });
}

// Función para añadir puntos de compra/venta en el gráfico
function addTradePoint(type, time, price) {
    appState.tradePoints.push({
        type: type,
        time: time,
        price: price
    });
    
    // Mantener solo los puntos de las últimas 24 horas
    const oneDayAgo = new Date();
    oneDayAgo.setHours(oneDayAgo.getHours() - 24);
    appState.tradePoints = appState.tradePoints.filter(point => new Date(point.time) > oneDayAgo);
    
    updateChart();
}

function initChart() {
    const ctx = document.getElementById('priceChart').getContext('2d');
    const symbol = appState.cryptoSymbols[appState.currentCrypto];

    // Preparar datos para el gráfico
    const priceData = appState.priceHistory.map(d => d.value);
    const timeLabels = appState.priceHistory.map(d => d.time.toLocaleTimeString());
    
    // Preparar datos para los puntos de compra/venta
    const buyPoints = appState.tradePoints.filter(point => point.type === 'BUY');
    const sellPoints = appState.tradePoints.filter(point => point.type === 'SELL');

    chart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: timeLabels,
            datasets: [
                {
                    label: `${symbol}/USDT`,
                    data: priceData,
                    borderColor: '#0ecb81',
                    backgroundColor: 'rgba(14, 203, 129, 0.1)',
                    borderWidth: 2,
                    fill: true,
                    tension: 0.1,
                    pointRadius: 0
                },
                {
                    label: 'Compras',
                    data: buyPoints.map(point => {
                        const timeIndex = appState.priceHistory.findIndex(
                            d => d.time.getTime() === new Date(point.time).getTime()
                        );
                        return timeIndex !== -1 ? {x: timeIndex, y: point.price} : null;
                    }).filter(point => point !== null),
                    pointStyle: 'circle',
                    pointRadius: 8,
                    pointBackgroundColor: 'green',
                    showLine: false
                },
                {
                    label: 'Ventas',
                    data: sellPoints.map(point => {
                        const timeIndex = appState.priceHistory.findIndex(
                            d => d.time.getTime() === new Date(point.time).getTime()
                        );
                        return timeIndex !== -1 ? {x: timeIndex, y: point.price} : null;
                    }).filter(point => point !== null),
                    pointStyle: 'circle',
                    pointRadius: 8,
                    pointBackgroundColor: 'red',
                    showLine: false
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    mode: 'index',
                    intersect: false,
                    callbacks: {
                        label: function (context) {
                            if (context.datasetIndex === 0) {
                                return `$${context.parsed.y.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
                            } else if (context.datasetIndex === 1) {
                                return `Compra: $${context.parsed.y.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
                            } else if (context.datasetIndex === 2) {
                                return `Venta: $${context.parsed.y.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
                            }
                        }
                    }
                }
            },
            scales: {
                x: {
                    grid: {
                        color: 'rgba(42, 54, 83, 0.5)'
                    },
                    ticks: {
                        color: '#94a3b8',
                        maxTicksLimit: 8
                    }
                },
                y: {
                    grid: {
                        color: 'rgba(42, 54, 83, 0.5)'
                    },
                    ticks: {
                        color: '#94a3b8',
                        callback: function (value) {
                            return '$' + value.toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 0 });
                        }
                    }
                }
            },
            interaction: {
                intersect: false,
                mode: 'index'
            }
        }
    });
}

function calculateAverageBuyPrice(crypto) {
    const buyTransactions = appState.transactions.filter(trans =>
        trans.type === 'BUY' && trans.crypto === crypto
    );

    if (buyTransactions.length === 0) return 0;

    let totalSpent = 0;
    let totalBought = 0;

    buyTransactions.forEach(transaction => {
        totalSpent += transaction.total;
        totalBought += transaction.amount;
    });

    return totalBought > 0 ? totalSpent / totalBought : 0;
}

function closePosition(index, crypto) {
    const globalIndex = appState.positions.findIndex(pos =>
        pos.crypto === crypto &&
        appState.positions.indexOf(pos) === index
    );

    if (globalIndex >= 0 && globalIndex < appState.positions.length) {
        const position = appState.positions[globalIndex];
        const symbol = appState.cryptoSymbols[position.crypto];
        const currentPrice = appState.cryptoPrices[position.crypto];
        const currentValue = position.amount * currentPrice;
        const initialValue = position.amount * position.entryPrice;
        const fee = currentValue * appState.tradeFees;
        const profit = currentValue - initialValue - fee;

        appState.balanceUSDT += currentValue - fee;
        appState[`balance${symbol}`] = (appState[`balance${symbol}`] || 0) - position.amount;
        appState.totalFees += fee;

        if (profit > 0) {
            appState.withdrawableProfit += profit;
            appState.realizedProfit += profit;
        } else {
            appState.realizedLoss += Math.abs(profit);
        }

        appState.transactions.push({
            type: 'SELL',
            amount: position.amount,
            price: currentPrice,
            total: currentValue,
            fee: fee,
            profitLoss: profit,
            crypto: position.crypto,
            timestamp: new Date()
        });

        // Añadir punto de venta en el gráfico
        addTradePoint('SELL', new Date(), currentPrice);

        appState.positions.splice(globalIndex, 1);

        updateProfitLossUI();
        updateWithdrawableSections();
        saveState();

        alert(`Posición cerrada: ${position.amount.toFixed(6)} ${symbol}\nGanancia/Pérdida: ${profit >= 0 ? '+' : '-'}$${Math.abs(profit).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`);
    }
}

function updateSimulation() {
    Object.keys(appState.cryptoPrices).forEach(crypto => {
        const changePercent = (Math.random() - 0.5) * 0.004;
        appState.cryptoPrices[crypto] = appState.cryptoPrices[crypto] * (1 + changePercent);
        appState.cryptoChanges[crypto] += (Math.random() - 0.5) * 0.1;
    });

    const crypto = appState.currentCrypto;
    const price = appState.cryptoPrices[crypto];

    appState.priceHistory.push({
        time: new Date(),
        value: price
    });

    if (appState.priceHistory.length > 100) {
        appState.priceHistory.shift();
    }

    updateOrders();
    updateUI();
    updateChart();
}

function updateOrders() {
    appState.buyOrders.forEach(order => {
        const amountChange = 1 + (Math.random() - 0.5) * 0.1;
        order.amount = order.amount * amountChange;
        order.total = order.price * order.amount;
    });

    appState.sellOrders.forEach(order => {
        const amountChange = 1 + (Math.random() - 0.5) * 0.1;
        order.amount = order.amount * amountChange;
        order.total = order.price * order.amount;
    });

    renderOrders();
}

function updateChart() {
    if (!chart) return;

    const symbol = appState.cryptoSymbols[appState.currentCrypto];

    chart.data.labels = appState.priceHistory.map(d => d.time.toLocaleTimeString());
    chart.data.datasets[0].data = appState.priceHistory.map(d => d.value);
    chart.data.datasets[0].label = `${symbol}/USDT`;

    // Actualizar puntos de compra/venta
    const buyPoints = appState.tradePoints.filter(point => point.type === 'BUY');
    const sellPoints = appState.tradePoints.filter(point => point.type === 'SELL');

    chart.data.datasets[1].data = buyPoints.map(point => {
        const timeIndex = appState.priceHistory.findIndex(
            d => d.time.getTime() === new Date(point.time).getTime()
        );
        return timeIndex !== -1 ? {x: timeIndex, y: point.price} : null;
    }).filter(point => point !== null);

    chart.data.datasets[2].data = sellPoints.map(point => {
        const timeIndex = appState.priceHistory.findIndex(
            d => d.time.getTime() === new Date(point.time).getTime()
        );
        return timeIndex !== -1 ? {x: timeIndex, y: point.price} : null;
    }).filter(point => point !== null);

    chart.update('none');
}

function calculateTotal() {
    const price = parseFloat(document.getElementById('price').value) || 0;
    const amount = parseFloat(document.getElementById('amount').value) || 0;
    const total = price * amount;

    document.getElementById('total').value = total.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

// ===== EVENT LISTENERS =====
function setupEventListeners() {
    document.getElementById('crypto-select').addEventListener('change', changeCrypto);

    const paypalInput = document.getElementById('paypalWithdrawAmount');

    document.getElementById('paypalSummaryModal').addEventListener('show.bs.modal', function () {
        updatePaypalSummaryModal();
    });

    document.getElementById('price').addEventListener('input', function () {
        calculateTotal();
        if (document.getElementById('paypalSummaryModal').classList.contains('show')) {
            updatePaypalSummaryModal();
        }
    });

    document.getElementById('amount').addEventListener('input', function () {
        calculateTotal();
        if (document.getElementById('paypalSummaryModal').classList.contains('show')) {
            updatePaypalSummaryModal();
        }
    });

    paypalInput.addEventListener('focus', function () {
        isPaypalInputFocused = true;
    });

    paypalInput.addEventListener('blur', function () {
        isPaypalInputFocused = false;

        const amount = parseFloat(this.value) || 0;
        const maxWithdrawal = Math.min(MAX_WITHDRAWAL, appState.withdrawableProfit);

        if (amount > maxWithdrawal) {
            this.value = maxWithdrawal.toFixed(2);
            currentPaypalAmount = maxWithdrawal;
        } else if (amount < MIN_WITHDRAWAL) {
            this.value = MIN_WITHDRAWAL.toFixed(2);
            currentPaypalAmount = MIN_WITHDRAWAL;
        } else {
            currentPaypalAmount = amount;
            userModifiedWithdrawal = true;
        }

        calculatePayPalWithdrawal();
    });

    paypalInput.addEventListener('input', function (e) {
        const amount = parseFloat(e.target.value) || 0;
        currentPaypalAmount = amount;
        userModifiedWithdrawal = true;
        calculatePayPalWithdrawal();
    });

    document.getElementById('price').addEventListener('input', calculateTotal);
    document.getElementById('amount').addEventListener('input', calculateTotal);

    document.getElementById('buy-btn').addEventListener('click', function () {
        const amount = parseFloat(document.getElementById('amount').value) || 0;
        const price = parseFloat(document.getElementById('price').value) || appState.cryptoPrices[appState.currentCrypto];
        const total = amount * price;
        const fee = total * appState.tradeFees;
        const crypto = appState.currentCrypto;
        const symbol = appState.cryptoSymbols[crypto];

        if (amount <= 0) {
            alert('Por favor ingresa una cantidad válida');
            return;
        }

        if (total > appState.balanceUSDT) {
            alert('Saldo insuficiente en USDT');
            return;
        }

        appState.balanceUSDT -= total + fee;
        appState[`balance${symbol}`] = (appState[`balance${symbol}`] || 0) + amount;
        appState.totalFees += fee;

        appState.transactions.push({
            type: 'BUY',
            amount: amount,
            price: price,
            total: total,
            fee: fee,
            crypto: crypto,
            timestamp: new Date()
        });

        // Añadir punto de compra en el gráfico
        addTradePoint('BUY', new Date(), price);

        if (amount > 0.001) {
            appState.positions.push({
                pair: `${symbol}/USDT`,
                type: 'LONG',
                entryPrice: price,
                amount: amount,
                crypto: crypto,
                timestamp: new Date()
            });
        }

        alert(`¡Compra exitosa! Has comprado ${amount.toFixed(6)} ${symbol} por $${total.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`);

        saveState();
        updateUI();
    });

    document.getElementById('sell-btn').addEventListener('click', function () {
        const amount = parseFloat(document.getElementById('amount').value) || 0;
        const price = parseFloat(document.getElementById('price').value) || appState.cryptoPrices[appState.currentCrypto];
        const total = amount * price;
        const fee = total * appState.tradeFees;
        const crypto = appState.currentCrypto;
        const symbol = appState.cryptoSymbols[crypto];
        const balance = appState[`balance${symbol}`] || 0

        const averageBuyPrice = calculateAverageBuyPrice(crypto);
        const profitLoss = (price - averageBuyPrice) * amount - fee;

        if (amount <= 0) {
            alert('Por favor ingresa una cantidad válida');
            return;
        }

        if (amount > balance) {
            alert(`Saldo insuficiente en ${symbol}`);
            return;
        }

        appState.balanceUSDT += total - fee;
        appState[`balance${symbol}`] = (appState[`balance${symbol}`] || 0) - amount;
        appState.totalFees += fee;

        if (profitLoss > 0) {
            appState.withdrawableProfit += profitLoss;
            appState.realizedProfit += profitLoss;
        } else {
            appState.realizedLoss += Math.abs(profitLoss);
        }

        appState.transactions.push({
            type: 'SELL',
            amount: amount,
            price: price,
            total: total,
            fee: fee,
            profitLoss: profitLoss,
            crypto: crypto,
            timestamp: new Date()
        });

        // Añadir punto de venta en el gráfico
        addTradePoint('SELL', new Date(), price);

        let amountToClose = amount;

        for (let i = 0; i < appState.positions.length && amountToClose > 0; i++) {
            const position = appState.positions[i];

            if (position.crypto === crypto) {
                const closeAmount = Math.min(amountToClose, position.amount);

                if (closeAmount === position.amount) {
                    appState.positions.splice(i, 1);
                    i--;
                } else {
                    position.amount -= closeAmount;
                }

                amountToClose -= closeAmount;
            }
        }

        alert(`¡Venda exitosa! Has vendido ${amount.toFixed(6)} ${symbol} por $${total.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`);

        updateProfitLossUI();
        updateWithdrawableSections();
        saveState();
        updateUI();
    });

    document.querySelectorAll('.tab').forEach(tab => {
        tab.addEventListener('click', function () {
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            this.classList.add('active');

            const isHistoryTab = this.textContent === 'Historial';
            document.getElementById('positions-container').style.display = isHistoryTab ? 'none' : 'block';
            document.getElementById('transaction-history').style.display = isHistoryTab ? 'block' : 'none';
        });
    });

    document.querySelectorAll('.control-btn').forEach(btn => {
        btn.addEventListener('click', function () {
            document.querySelectorAll('.control-btn').forEach(b => b.classList.remove('active'));
            this.classList.add('active');
        });
    });

    document.getElementById('paypalWithdrawAmount').addEventListener('input', function (e) {
        const amount = parseFloat(e.target.value) || 0;
        currentPaypalAmount = amount;
        userModifiedWithdrawal = true;
        calculatePayPalWithdrawal();
    });
}

// ===== INICIAR LA APLICACIÓN =====
document.addEventListener('DOMContentLoaded', function () {
    initApp();

    setTimeout(() => {
        const tooltipTriggerList = [].slice.call(document.querySelectorAll('[title]'));
        tooltipTriggerList.map(function (tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });
    }, 1000);
});