// ===== COINBASE WALLET MANAGER =====
class CoinbaseWalletManager {
    constructor() {
        this.baseUrl = '/api/coinbase';
        this.connectedAccount = null;
        this.accountBalances = {};
        this.supportedChains = ['EVM', 'Solana'];
        this.isConnected = false;
        this.sessionToken = localStorage.getItem('session_token');
        this.currentLoadingModal = null; // ✅ Nueva propiedad
        this.loadingTimeout = null; // ✅ Timeout de seguridad

        this.initializeEventListeners();
        this.checkExistingConnection();
    }

    // ===== INITIALIZATION =====
    initializeEventListeners() {
        // Conectar wallet
        document.getElementById('connectCoinbaseBtn')?.addEventListener('click', () => {
            this.connectWallet();
        });

        // Desconectar wallet
        document.getElementById('disconnectCoinbaseBtn')?.addEventListener('click', () => {
            this.disconnectWallet();
        });

        // Crear cuenta EVM
        document.getElementById('createEVMAccountBtn')?.addEventListener('click', () => {
            this.createEVMAccount();
        });

        // Crear cuenta Solana
        document.getElementById('createSolanaAccountBtn')?.addEventListener('click', () => {
            this.createSolanaAccount();
        });

        // Importar cuenta
        document.getElementById('importAccountBtn')?.addEventListener('click', () => {
            this.importAccount();
        });

        // Actualizar balances
        document.getElementById('refreshBalancesBtn')?.addEventListener('click', () => {
            this.loadAccountBalances();
        });

        // Formulario de transferencia
        document.getElementById('transferForm')?.addEventListener('submit', (e) => {
            e.preventDefault();
            this.handleTransfer();
        });
    }

    checkExistingConnection() {
        const savedAccount = localStorage.getItem('coinbase_connected_account');
        if (savedAccount) {
            this.connectedAccount = JSON.parse(savedAccount);
            this.updateConnectionStatus(true);
            this.loadAccountBalances();
        }
    }

    // ===== AUTHENTICATION HELPERS (FIXED) =====
    async fetchWithAuth(url, options = {}) {
        const defaultOptions = {
            headers: {
                'Content-Type': 'application/json',
            },
            credentials: 'include'
        };

        try {
            const response = await fetch(url, { ...defaultOptions, ...options });

            // Manejar específicamente errores 401
            if (response.status === 401) {
                // Para endpoints de Coinbase, no redirigir inmediatamente
                if (url.includes('/api/coinbase')) {
                    this.showError('Sesión expirada. Por favor, recarga la página.');
                    return null;
                }

                // Para otros endpoints, redirigir después de mostrar un mensaje
                this.showError('Sesión expirada. Redirigiendo al login...');
                setTimeout(() => {
                    window.location.href = '/';
                }, 2000);
                return null;
            }

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            return await response.json();
        } catch (error) {
            console.error('API request failed:', error);

            // No redirigir por errores de red
            if (error.name === 'TypeError') {
                this.showError('Error de conexión. Verifica tu conexión a internet.');
                return null;
            }

            this.showError(`Error: ${error.message}`);
            return null;
        }
    }

    // En las funciones como connectWallet, crear cuenta, etc.:
    async connectWallet() {
        const accountName = document.getElementById('accountNameInput')?.value.trim();

        this.showLoading('Conectando con Coinbase...');

        try {
            // Primero probamos la conexión
            const connectionTest = await this.fetchWithAuth(`${this.baseUrl}/test-connection`);

            if (!connectionTest) {
                this.hideLoading();
                return;
            }

            if (!connectionTest.success) {
                throw new Error('No se pudo establecer conexión con Coinbase CDP');
            }

            // Obtenemos o creamos una cuenta
            const accountData = await this.fetchWithAuth(`${this.baseUrl}/evm/get-or-create`);

            if (!accountData) {
                this.hideLoading();
                return;
            }

            if (accountData.success) {
                this.connectedAccount = accountData.account;
                this.saveConnection();
                this.updateConnectionStatus(true);

                // ocultamos loading antes de mostrar éxito
                this.hideLoading();
                this.showSuccess('Wallet de Coinbase conectado exitosamente');

                // Cargar balances
                await this.loadAccountBalances();
            } else {
                throw new Error(accountData.error || 'Error al obtener la cuenta');
            }

        } catch (error) {
            this.hideLoading();
            // Solo mostrar error si no es un error de autenticación (ya manejado)
            if (!error.message.includes('Sesión expirada')) {
                this.showError(`Error conectando wallet: ${error.message}`);
            }
        } finally {
            this.hideLoading();
        }
    }

    disconnectWallet() {
        localStorage.removeItem('coinbase_connected_account');
        this.connectedAccount = null;
        this.accountBalances = {};
        this.updateConnectionStatus(false);
        this.clearAccountInfo();
        this.showSuccess('Wallet desconectado exitosamente');
    }

    // ===== MODAL MANAGEMENT =====
    closeAnyOpenModals() {
        try {
            // Cerrar todos los modales de manera segura
            const openModals = document.querySelectorAll('.modal.show');
            openModals.forEach(modal => {
                const modalId = modal.id;
                if (modalId) {
                    this.closeModalSafely(modalId);
                } else {
                    this.closeModalManually(modal);
                }
            });

            // Limpieza final
            setTimeout(() => {
                this.cleanupModalBackdrops();
            }, 100);
        } catch (error) {
            console.error('Error closing open modals:', error);
            this.cleanupModalBackdrops();
        }
    }

    // ===== ACCOUNT MANAGEMENT =====
    async createEVMAccount() {
        const accountName = prompt('Ingresa un nombre para la cuenta EVM (opcional):');

        this.showLoading('Creando cuenta EVM...');

        try {
            const response = await this.handleApiResponse(
                async () => {
                    const requestBody = accountName ? { name: accountName } : {};
                    return await this.fetchWithAuth(`${this.baseUrl}/evm/create`, {
                        method: 'POST',
                        body: JSON.stringify(requestBody)
                    });
                },
                `Cuenta EVM creada exitosamente`,
                'Creando cuenta EVM...'
            );

            if (response) {
                // ✅ Actualizar la cuenta conectada
                this.connectedAccount = response.account;
                this.saveConnection();
                this.updateAccountInfo(response.account);

                // ✅ Actualizar la lista de balances
                await this.loadAccountBalances();

                // ✅ Cerrar cualquier modal abierto
                this.closeAnyOpenModals();
            } else {
                throw new Error(response?.error || 'Error desconocido');
            }

        } catch (error) {
            this.hideLoading();
            this.showError(`Error creando cuenta EVM: ${error.message}`);
        }
    }

    async createSolanaAccount() {
        const accountName = prompt('Ingresa un nombre para la cuenta Solana (opcional):');

        this.showLoading('Creando cuenta Solana...');

        try {
            const response = await this.handleApiResponse(
                async () => {
                    const requestBody = accountName ? { name: accountName } : {};
                    return await this.fetchWithAuth(`${this.baseUrl}/solana/create`, {
                        method: 'POST',
                        body: JSON.stringify(requestBody)
                    });
                },
                `Cuenta Solana creada exitosamente`,
                'Creando cuenta Solana...'
            );


            if (response) {
                this.connectedAccount = response.account;
                this.saveConnection();
                this.updateAccountInfo(response.account);
                await this.loadAccountBalances();
                this.closeAnyOpenModals();
            } else {
                throw new Error(response?.error || 'Error desconocido');
            }

        } catch (error) {
            console.error('Error creating Solana account:', error);
            this.hideLoading();
            this.showError(`Error creando cuenta Solana: ${error.message}`);
        }
    }

    async importAccount() {
        const chain = prompt('Selecciona la blockchain (EVM o Solana):');
        const privateKey = prompt('Ingresa la clave privada:');
        const accountName = prompt('Ingresa un nombre para la cuenta (opcional):');

        if (!chain || !privateKey) {
            this.showError('Chain y clave privada son requeridos');
            return;
        }

        this.showLoading('Importando cuenta...');

        try {
            const endpoint = chain.toLowerCase() === 'solana' ? 'solana/import' : 'evm/import';
            const response = await this.fetchWithAuth(`${this.baseUrl}/${endpoint}`, {
                method: 'POST',
                body: JSON.stringify({
                    private_key: privateKey,
                    name: accountName
                })
            });

            if (response && response.success) {
                // ✅ Cerrar el modal de loading primero
                this.hideLoading();

                // ✅ Mostrar mensaje de éxito
                this.showSuccess(`Cuenta importada: ${response.account.address}`);

                // ✅ Actualizar la cuenta conectada
                this.connectedAccount = response.account;
                this.saveConnection();
                this.updateAccountInfo(response.account);

                // ✅ Actualizar la lista de balances
                await this.loadAccountBalances();

                // ✅ Cerrar cualquier modal abierto
                this.closeAnyOpenModals();

            } else {
                throw new Error(response?.error || 'Error desconocido');
            }

        } catch (error) {
            this.hideLoading();
            this.showError(`Error importando cuenta: ${error.message}`);
        }
    }

    // ===== BALANCE MANAGEMENT =====
    async loadAccountBalances() {
        if (!this.connectedAccount) return;

        this.showLoading('Cargando balances...');

        try {
            // Aquí implementarías la lógica para obtener balances reales
            // Por ahora usamos datos de ejemplo
            this.accountBalances = {
                'EVM': {
                    'ETH': { balance: '0.5', valueUSD: '1500.00' },
                    'USDC': { balance: '1000.0', valueUSD: '1000.00' },
                    'WBTC': { balance: '0.01', valueUSD: '500.00' }
                },
                'Solana': {
                    'SOL': { balance: '10.5', valueUSD: '1050.00' },
                    'USDT': { balance: '500.0', valueUSD: '500.00' }
                }
            };

            this.renderBalances();
            this.calculateTotalPortfolio();
            this.showSuccess('Balances actualizados');

        } catch (error) {
            this.showError(`Error cargando balances: ${error.message}`);
        } finally {
            this.hideLoading();
        }
    }

    renderBalances() {
        const container = document.getElementById('tokensList');
        if (!container) return;

        let html = '';

        Object.keys(this.accountBalances).forEach(chain => {
            html += `<div class="chain-section mb-4">
                        <h6 class="text-muted mb-3"><i class="fas fa-link me-2"></i>${chain}</h6>`;

            Object.keys(this.accountBalances[chain]).forEach(token => {
                const balance = this.accountBalances[chain][token];
                html += this.createTokenCard(token, balance, chain);
            });

            html += `</div>`;
        });

        container.innerHTML = html || `
            <div class="text-center py-4">
                <i class="fas fa-coins fa-3x text-muted mb-3"></i>
                <p class="text-muted">No se encontraron balances</p>
            </div>
        `;
    }

    createTokenCard(token, balance, chain) {
        const icons = {
            'ETH': 'fab fa-ethereum',
            'BTC': 'fab fa-bitcoin',
            'SOL': 'fas fa-sun',
            'USDC': 'fas fa-dollar-sign',
            'USDT': 'fas fa-coins',
            'WBTC': 'fab fa-btc'
        };

        return `
            <div class="token-card">
                <div class="d-flex align-items-center">
                    <div class="token-icon me-3">
                        <i class="${icons[token] || 'fas fa-coins'}"></i>
                    </div>
                    <div class="flex-grow-1">
                        <div class="d-flex justify-content-between align-items-center">
                            <div>
                                <h6 class="mb-1">${token}</h6>
                                <small class="text-muted">${chain}</small>
                            </div>
                            <div class="text-end">
                                <div class="fw-bold">${balance.balance}</div>
                                <small class="text-success">$${balance.valueUSD}</small>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    calculateTotalPortfolio() {
        let total = 0;

        Object.keys(this.accountBalances).forEach(chain => {
            Object.keys(this.accountBalances[chain]).forEach(token => {
                total += parseFloat(this.accountBalances[chain][token].valueUSD);
            });
        });

        document.getElementById('totalPortfolioValue').textContent =
            `$${total.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} USD`;
    }

    // ===== TRANSFER FUNCTIONS =====
    async handleTransfer() {
        const formData = new FormData(document.getElementById('transferForm'));
        const transferData = {
            fromAccount: formData.get('fromAccount'),
            toAccount: formData.get('toAccount'),
            amount: formData.get('amount'),
            token: formData.get('token'),
            chain: formData.get('chain'),
            memo: formData.get('memo')
        };

        if (!this.validateTransfer(transferData)) return;

        this.showLoading('Procesando transferencia...');

        try {
            // Aquí implementarías la lógica real de transferencia
            // Por ahora simulamos una transferencia exitosa
            await this.simulateTransfer(transferData);

            this.showSuccess(`Transferencia de ${transferData.amount} ${transferData.token} enviada exitosamente`);
            document.getElementById('transferForm').reset();

            // Actualizar balances
            setTimeout(() => this.loadAccountBalances(), 2000);

        } catch (error) {
            this.showError(`Error en transferencia: ${error.message}`);
        } finally {
            this.hideLoading();
        }
    }

    validateTransfer(transferData) {
        if (!transferData.fromAccount || !transferData.toAccount) {
            this.showError('Las cuentas de origen y destino son requeridas');
            return false;
        }

        if (!transferData.amount || parseFloat(transferData.amount) <= 0) {
            this.showError('El monto debe ser mayor a 0');
            return false;
        }

        if (!transferData.token) {
            this.showError('Selecciona un token');
            return false;
        }

        return true;
    }

    async simulateTransfer(transferData) {
        // Simular delay de red
        await new Promise(resolve => setTimeout(resolve, 2000));

        // Simular transacción exitosa
        return {
            success: true,
            transactionHash: '0x' + Math.random().toString(16).substr(2, 64),
            timestamp: new Date().toISOString()
        };
    }

    // ===== UI UPDATES =====
    updateConnectionStatus(connected) {
        this.isConnected = connected;
        const statusElement = document.getElementById('connectionStatus');
        const accountInfo = document.getElementById('accountInfo');

        if (statusElement) {
            statusElement.style.display = connected ? 'inline-block' : 'none';
        }

        if (accountInfo) {
            accountInfo.style.display = connected ? 'block' : 'none';
        }

        // Mostrar/ocultar botones según conexión
        document.getElementById('connectCoinbaseBtn').style.display = connected ? 'none' : 'block';
        document.getElementById('disconnectCoinbaseBtn').style.display = connected ? 'block' : 'none';
    }

    updateAccountInfo(account) {
        document.getElementById('accountName').textContent = account.name || account.address;
        document.getElementById('accountAddress').textContent = account.address;
        document.getElementById('accountType').textContent = account.type;
        document.getElementById('lastUpdate').textContent = new Date().toLocaleString();
    }

    clearAccountInfo() {
        document.getElementById('accountName').textContent = '-';
        document.getElementById('accountAddress').textContent = '-';
        document.getElementById('accountType').textContent = '-';
        document.getElementById('lastUpdate').textContent = '-';
        document.getElementById('tokensList').innerHTML = `
            <div class="text-center py-4">
                <i class="fas fa-coins fa-3x text-muted mb-3"></i>
                <p class="text-muted">Conecta tu wallet de Coinbase para ver tus tokens</p>
            </div>
        `;
        document.getElementById('totalPortfolioValue').textContent = '$0.00 USD';
    }

    saveConnection() {
        if (this.connectedAccount) {
            localStorage.setItem('coinbase_connected_account', JSON.stringify(this.connectedAccount));
        }
    }

    // ===== UI HELPERS =====
    showLoading(message = 'Procesando...', timeoutMs = 5000) {
        try {
            // Limpiar el timeout anterior
            if (this.loadingTimeout) {
                clearTimeout(this.loadingTimeout);
            }

            // Cerrar cualquier modal existente primero
            this.closeAnyOpenModals();

            const modalElement = document.getElementById('loadingModal');
            const messageElement = document.getElementById('loadingMessage');

            if (!modalElement) {
                console.warn('Modal de loading no encontrado');
                this.showAlert(message, 'info');
                return;
            }

            if (messageElement) {
                messageElement.textContent = message;
            }

            // Configurar el modal correctamente antes de mostrarlo
            modalElement.removeAttribute('aria-hidden');
            modalElement.setAttribute('aria-modal', 'true');
            modalElement.setAttribute('aria-labelledby', 'loadingModalLabel');

            // Crear nueva instancia y mostrar
            const modal = new bootstrap.Modal(modalElement, {
                backdrop: 'static',
                keyboard: false,
                focus: true
            });

            // Usar eventos de Bootstrap para manejar correctamente el foco
            modalElement.addEventListener('shown.bs.modal', () => {
                // Enfocar un elemento seguro dentro del modal
                const closeButton = modalElement.querySelector('.btn-close') || modalElement.querySelector('button');
                if (closeButton) {
                    closeButton.focus();
                }
            });

            modal.show();

            // Guardar referencia al modal actual
            this.currentLoadingModal = modal;

            // Timeout de seguridad
            this.loadingTimeout = setTimeout(() => {
                console.warn('Loading timeout alcanzado, cerrando modal');
                this.hideLoading();
                this.showError('La operación está tomando más tiempo de lo esperado. Por favor, intenta nuevamente.');
            }, timeoutMs);

        } catch (error) {
            console.error('Error mostrando loading:', error);
            this.showAlert(message, 'info');
        }
    }

    hideLoading() {
        try {
            // Limpiar timeout
            if (this.loadingTimeout) {
                clearTimeout(this.loadingTimeout);
                this.loadingTimeout = null;
            }

            /// Cerrar modal de loading correctamente
            this.closeModalSafely('loadingModal');


            /// Limpiar referencia
            this.currentLoadingModal = null;

        } catch (error) {
            console.error('Error ocultando loading:', error);
            this.cleanupModalBackdrops(); // Limpieza de emergencia
        }
    }

    closeModalSafely(modalId) {
        try {
            const modalElement = document.getElementById(modalId);
            if (!modalElement) return;

            // 1. Remover foco de cualquier elemento dentro del modal primero
            const focusedElement = document.activeElement;
            if (focusedElement && modalElement.contains(focusedElement)) {
                focusedElement.blur();
            }

            // 2. Obtener instancia de Bootstrap modal
            const modal = bootstrap.Modal.getInstance(modalElement);
            if (modal) {
                // Usar el método hide() de Bootstrap que maneja la accesibilidad correctamente
                modal.hide();
            } else {
                // Fallback: cerrar manualmente pero correctamente
                this.closeModalManually(modalElement);
            }
        } catch (error) {
            console.error(`Error closing modal ${modalId}:`, error);
            this.cleanupModalBackdrops();
        }
    }

    closeModalManually(modalElement) {
        // Remover clases de show
        modalElement.classList.remove('show');
        modalElement.style.display = 'none';

        // Remover atributos de accesibilidad problemáticos
        modalElement.removeAttribute('aria-hidden');
        modalElement.setAttribute('aria-modal', 'false');

        // Remover el backdrop específico de este modal
        const modalBackdrop = document.querySelector('.modal-backdrop');
        if (modalBackdrop) {
            modalBackdrop.remove();
        }

        // Restaurar el body
        document.body.classList.remove('modal-open');
        document.body.style.overflow = '';
        document.body.style.paddingRight = '';
    }

    cleanupModalBackdrops() {
        // Limpiar todos los backdrops
        const backdrops = document.querySelectorAll('.modal-backdrop');
        backdrops.forEach(backdrop => backdrop.remove());

        // Restaurar estado del body
        document.body.classList.remove('modal-open');
        document.body.style.overflow = '';
        document.body.style.paddingRight = '';

        // Asegurar que todos los modales estén cerrados
        const modals = document.querySelectorAll('.modal');
        modals.forEach(modal => {
            modal.classList.remove('show');
            modal.style.display = 'none';
            modal.removeAttribute('aria-hidden');
            modal.setAttribute('aria-modal', 'false');
        });
    }

    showSuccess(message) {
        this.showAlert(message, 'success');
    }

    showError(message) {
        this.showAlert(message, 'danger');
    }

    showAlert(message, type) {
        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
        alertDiv.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;

        // Insertar al inicio del container principal
        const container = document.querySelector('.container');
        if (container) {
            container.insertBefore(alertDiv, container.firstChild);
        }

        // Auto-remover después de 5 segundos
        setTimeout(() => {
            if (alertDiv.parentNode) {
                alertDiv.remove();
            }
        }, 5000);
    }

    // ===== RESPONSE HANDLER =====
    async handleApiResponse(apiCall, successMessage, loadingMessage = 'Procesando...') {
        this.showLoading(loadingMessage);

        try {
            const response = await apiCall();

            if (response && response.success) {
                // ✅ Cerrar el modal de loading correctamente
                this.hideLoading();

                // ✅ Mostrar mensaje de éxito
                if (successMessage) {
                    this.showSuccess(successMessage);
                }

                return response;
            } else {
                throw new Error(response?.error || 'Error desconocido');
            }

        } catch (error) {
            this.hideLoading();

            // No mostrar error si es de autenticación (ya se maneja en fetchWithAuth)
            if (!error.message.includes('Sesión expirada')) {
                this.showError(error.message);
            }

            return null;
        }
    }

    // ===== PUBLIC METHODS =====
    getAccount() {
        return this.connectedAccount;
    }

    getBalances() {
        return this.accountBalances;
    }

    isWalletConnected() {
        return this.isConnected;
    }

    // ===== TRANSACTION HISTORY =====
    async loadTransactionHistory() {
        if (!this.connectedAccount) return;

        try {
            // Implementar lógica para cargar historial de transacciones
            const transactions = await this.fetchTransactionHistory();
            this.renderTransactionHistory(transactions);
        } catch (error) {
            console.error('Error loading transaction history:', error);
        }
    }

    async fetchTransactionHistory() {
        // Simular datos de transacciones
        return [
            {
                hash: '0x123...abc',
                type: 'transfer',
                amount: '0.1',
                token: 'ETH',
                from: this.connectedAccount.address,
                to: '0x456...def',
                timestamp: new Date(Date.now() - 3600000).toISOString(),
                status: 'confirmed'
            },
            {
                hash: '0x789...ghi',
                type: 'receive',
                amount: '50.0',
                token: 'USDC',
                from: '0xdef...123',
                to: this.connectedAccount.address,
                timestamp: new Date(Date.now() - 7200000).toISOString(),
                status: 'confirmed'
            }
        ];
    }

    renderTransactionHistory(transactions) {
        const container = document.getElementById('transactionHistory');
        if (!container) return;

        if (!transactions || transactions.length === 0) {
            container.innerHTML = `
                <div class="text-center py-4">
                    <i class="fas fa-receipt fa-3x text-muted mb-3"></i>
                    <p class="text-muted">No hay transacciones recientes</p>
                </div>
            `;
            return;
        }

        let html = transactions.map(tx => `
            <div class="transaction-item d-flex justify-content-between align-items-center p-3 border-bottom">
                <div>
                    <div class="d-flex align-items-center">
                        <i class="fas fa-${tx.type === 'receive' ? 'arrow-down text-success' : 'arrow-up text-danger'} me-2"></i>
                        <div>
                            <strong>${tx.type === 'receive' ? 'Recibido' : 'Enviado'}</strong>
                            <div class="text-muted small">${tx.amount} ${tx.token}</div>
                        </div>
                    </div>
                </div>
                <div class="text-end">
                    <div class="small text-muted">${new Date(tx.timestamp).toLocaleDateString()}</div>
                    <span class="badge bg-${tx.status === 'confirmed' ? 'success' : 'warning'}">${tx.status}</span>
                </div>
            </div>
        `).join('');

        container.innerHTML = html;
    }
}

// ===== GLOBAL INSTANCE =====
let coinbaseWallet = null;

// ===== INITIALIZATION =====
document.addEventListener('DOMContentLoaded', function () {
    // Inicializar manager de Coinbase
    coinbaseWallet = new CoinbaseWalletManager();

    // Configurar event listeners adicionales
    setupAdditionalEventListeners();

    // Cargar historial de transacciones si está conectado
    if (coinbaseWallet.isWalletConnected()) {
        coinbaseWallet.loadTransactionHistory();
    }
});

function setupAdditionalEventListeners() {
    // Auto-completar cuenta conectada en formularios
    document.getElementById('accountNameInput')?.addEventListener('input', function () {
        const fromAccount = document.getElementById('fromAccount');
        if (fromAccount) {
            fromAccount.value = this.value;
        }
    });

    // Actualizar símbolo del token en transferencia
    document.getElementById('transferToken')?.addEventListener('change', function () {
        const symbolDisplay = document.getElementById('tokenSymbolDisplay');
        if (symbolDisplay) {
            symbolDisplay.textContent = this.value;
        }
    });

    // Quick actions
    document.getElementById('refreshAllBtn')?.addEventListener('click', function () {
        if (coinbaseWallet) {
            coinbaseWallet.loadAccountBalances();
            coinbaseWallet.loadTransactionHistory();
        }
    });

    document.getElementById('viewTokensBtn')?.addEventListener('click', function () {
        if (coinbaseWallet) {
            coinbaseWallet.loadAccountBalances();
        }
    });
}

// ===== GLOBAL FUNCTIONS FOR HTML =====
function connectCoinbaseWallet() {
    if (coinbaseWallet) {
        coinbaseWallet.connectWallet();
    }
}

function disconnectCoinbaseWallet() {
    if (coinbaseWallet) {
        coinbaseWallet.disconnectWallet();
    }
}

function loadCoinbaseTokens() {
    if (coinbaseWallet) {
        coinbaseWallet.loadAccountBalances();
    }
}

function showCoinbaseAccountInfo() {
    if (coinbaseWallet && coinbaseWallet.connectedAccount) {
        const account = coinbaseWallet.connectedAccount;
        const modalBody = document.getElementById('accountInfoModalBody');

        if (modalBody) {
            modalBody.innerHTML = `
                <div class="row">
                    <div class="col-md-6">
                        <p><strong>Nombre:</strong> ${account.name || 'No especificado'}</p>
                        <p><strong>Dirección:</strong> <code>${account.address}</code></p>
                        <p><strong>Tipo:</strong> ${account.type}</p>
                    </div>
                    <div class="col-md-6">
                        <p><strong>Creado:</strong> ${account.created_at ? new Date(account.created_at).toLocaleString() : 'N/A'}</p>
                        <p><strong>Importado:</strong> ${account.imported ? 'Sí' : 'No'}</p>
                        <p><strong>Smart Account:</strong> ${account.is_smart_account ? 'Sí' : 'No'}</p>
                    </div>
                </div>
                <div class="mt-3">
                    <button class="btn btn-outline-primary btn-sm" onclick="copyToClipboard('${account.address}')">
                        <i class="fas fa-copy"></i> Copiar Dirección
                    </button>
                </div>
            `;
        }

        new bootstrap.Modal(document.getElementById('accountInfoModal')).show();
    }
}

function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(() => {
        const originalText = event.target.innerHTML;
        event.target.innerHTML = '<i class="fas fa-check"></i> Copiado!';

        setTimeout(() => {
            event.target.innerHTML = originalText;
        }, 2000);
    });
}

// Exportar para uso global
window.coinbaseWallet = coinbaseWallet;
window.connectCoinbaseWallet = connectCoinbaseWallet;
window.disconnectCoinbaseWallet = disconnectCoinbaseWallet;
window.loadCoinbaseTokens = loadCoinbaseTokens;
window.showCoinbaseAccountInfo = showCoinbaseAccountInfo;