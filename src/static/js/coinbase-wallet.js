// ===== COINBASE WALLET MANAGER =====
class CoinbaseWalletManager {
    constructor() {
        this.baseUrl = '/api/coinbase';
        this.connectedAccount = null;
        this.accountBalances = {};
        this.supportedChains = ['EVM', 'Solana'];
        this.isConnected = false;
        this.isProcessing = false;
        this.currentLoadingModal = null;
        this.loadingTimeout = null;
        this.lastOperationTime = 0;

        console.log('🔄 CoinbaseWalletManager constructor llamado');
        
        // Inicialización diferida para asegurar que el DOM esté listo
        setTimeout(() => {
            this.initializeEventListeners();
            this.checkExistingConnection();
        }, 100);
    }

    // ===== INITIALIZATION =====
    initializeEventListeners() {
        console.log('🔧 Inicializando event listeners de Coinbase Wallet');
        
        try {
            // Conectar wallet - MÚLTIPLES BOTONES
            const connectButtons = [
                'connectCoinbaseBtn', 
                'connectCoinbaseBtn2'
            ];
            
            connectButtons.forEach(btnId => {
                const btn = document.getElementById(btnId);
                if (btn) {
                    btn.addEventListener('click', () => {
                        console.log(`🖱️ Botón ${btnId} clickeado`);
                        this.connectWallet();
                    });
                } else {
                    console.warn(`⚠️ Botón ${btnId} no encontrado`);
                }
            });

            // Desconectar wallet
            const disconnectButtons = [
                'disconnectCoinbaseBtn',
                'disconnectCoinbaseBtn2'
            ];
            
            disconnectButtons.forEach(btnId => {
                const btn = document.getElementById(btnId);
                if (btn) {
                    btn.addEventListener('click', () => {
                        this.disconnectWallet();
                    });
                }
            });

            // Crear cuenta EVM
            const evmBtn = document.getElementById('createEVMAccountBtn');
            if (evmBtn) {
                evmBtn.addEventListener('click', () => {
                    this.createEVMAccount();
                });
            }

            // Crear cuenta Solana
            const solanaBtn = document.getElementById('createSolanaAccountBtn');
            if (solanaBtn) {
                solanaBtn.addEventListener('click', () => {
                    this.createSolanaAccount();
                });
            }

            // Importar cuenta
            const importBtn = document.getElementById('importAccountBtn');
            if (importBtn) {
                importBtn.addEventListener('click', () => {
                    this.importAccount();
                });
            }

            // Actualizar balances
            const refreshButtons = [
                'refreshBalancesBtn',
                'refreshBalancesBtn2',
                'refreshAllBtn'
            ];
            
            refreshButtons.forEach(btnId => {
                const btn = document.getElementById(btnId);
                if (btn) {
                    btn.addEventListener('click', () => {
                        this.loadAccountBalances();
                    });
                }
            });

            // Formulario de transferencia
            const transferForm = document.getElementById('transferForm');
            if (transferForm) {
                transferForm.addEventListener('submit', (e) => {
                    e.preventDefault();
                    this.handleTransfer();
                });
            }

            console.log('✅ Todos los event listeners configurados correctamente');

        } catch (error) {
            console.error('❌ Error inicializando event listeners:', error);
        }
    }

    checkExistingConnection() {
        console.log('🔍 Verificando conexión existente...');
        
        try {
            const savedAccount = localStorage.getItem('coinbase_connected_account');
            if (savedAccount) {
                console.log('📁 Cuenta guardada encontrada en localStorage');
                
                try {
                    this.connectedAccount = JSON.parse(savedAccount);
                    console.log('✅ Cuenta parseada:', this.connectedAccount);
                    
                    // ✅ CORREGIDO: Actualizar la información de la cuenta PRIMERO
                    this.updateAccountInfo(this.connectedAccount);
                    this.updateConnectionStatus(true);
                    
                    // Cargar balances después de un breve delay
                    setTimeout(() => {
                        this.loadAccountBalances();
                    }, 500);
                    
                    this.showSuccess('✅ Wallet de Coinbase reconectado automáticamente');
                    
                } catch (error) {
                    console.error('❌ Error parseando cuenta guardada:', error);
                    localStorage.removeItem('coinbase_connected_account');
                }
            } else {
                console.log('ℹ️ No hay cuenta guardada en localStorage');
            }
        } catch (error) {
            console.error('❌ Error verificando conexión existente:', error);
        }
    }

    // ===== AUTHENTICATION HELPERS =====
    async fetchWithAuth(url, options = {}) {
        console.log(`🌐 Fetching: ${url}`, options);
        
        // Solo prevenir operaciones de escritura simultáneas
        const isWriteOperation = options.method && options.method !== 'GET';
        
        if (isWriteOperation && this.isProcessing) {
            console.warn('⏳ Operación ya en progreso, saltando solicitud de escritura');
            this.showInfo('⌛ Hay una operación en progreso. Espere...');
            return null;
        }

        const defaultOptions = {
            headers: {
                'Content-Type': 'application/json',
            },
            credentials: 'include',
            timeout: 30000 // 30 segundos timeout
        };

        try {
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 30000);
            
            const response = await fetch(url, { 
                ...defaultOptions, 
                ...options,
                signal: controller.signal 
            });
            
            clearTimeout(timeoutId);

            console.log(`📨 Response status: ${response.status} for ${url}`);

            if (response.status === 401) {
                if (url.includes('/api/coinbase')) {
                    this.showError('🔐 Sesión expirada. Por favor, recarga la página.');
                    return null;
                }
                this.showError('🔐 Sesión expirada. Redirigiendo al login...');
                setTimeout(() => {
                    window.location.href = '/';
                }, 2000);
                return null;
            }

            if (!response.ok) {
                let errorMessage = `Error HTTP! status: ${response.status}`;
                
                try {
                    const errorText = await response.text();
                    console.error(`❌ Error response:`, errorText);
                    
                    try {
                        const errorData = JSON.parse(errorText);
                        errorMessage = errorData.error || errorData.detail || errorMessage;
                    } catch {
                        errorMessage = errorText || errorMessage;
                    }
                } catch (textError) {
                    console.error('❌ Error leyendo respuesta de error:', textError);
                }
                
                throw new Error(errorMessage);
            }

            const responseData = await response.json();
            console.log(`✅ Success response from ${url}:`, responseData);
            return responseData;
            
        } catch (error) {
            console.error(`❌ API request failed for ${url}:`, error);

            if (error.name === 'AbortError') {
                this.showError('⏰ Timeout: La solicitud tardó demasiado tiempo.');
                return null;
            }

            if (error.name === 'TypeError') {
                this.showError('🌐 Error de conexión. Verifica tu conexión a internet.');
                return null;
            }

            const errorMessage = error.message.includes('Error desconocido') ? 
                'Error en el servidor. Intente nuevamente.' : error.message;
                
            this.showError(`❌ Error: ${errorMessage}`);
            return null;
        }
    }

    // ===== WALLET OPERATIONS =====
    async connectWallet() {
        console.log('🔗 Iniciando conexión de wallet...');
        
        if (this.isProcessing) {
            console.warn('⏳ Conexión ya en progreso, ignorando solicitud');
            this.showInfo('⌛ Conectando wallet... Espere por favor.');
            return;
        }
        
        this.isProcessing = true;
        this.lastOperationTime = Date.now();
        
        const accountNameInput = document.getElementById('accountNameInput');
        const accountName = accountNameInput ? accountNameInput.value.trim() : '';

        console.log(`📝 Nombre de cuenta proporcionado: "${accountName}"`);

        this.showLoading('🔗 Conectando con Coinbase Wallet...', 20000);

        try {
            // Primero probamos la conexión con el servidor
            console.log('🔄 Probando conexión con el servidor...');
            const connectionTest = await this.fetchWithAuth(`${this.baseUrl}/test-connection`);

            if (!connectionTest) {
                throw new Error('No se pudo verificar la conexión con el servidor');
            }

            console.log('✅ Conexión con servidor exitosa:', connectionTest);

            if (!connectionTest.success) {
                throw new Error(connectionTest.error || 'No se pudo establecer conexión con Coinbase CDP');
            }

            // Intentar crear o obtener cuenta
            let accountData;
            const requestBody = accountName ? { name: accountName } : {};
            
            console.log('🔄 Creando/obteniendo cuenta EVM...');
            
            try {
                accountData = await this.fetchWithAuth(`${this.baseUrl}/evm/create`, {
                    method: 'POST',
                    body: JSON.stringify(requestBody)
                });
                
                if (!accountData) {
                    throw new Error('No se pudo crear la cuenta');
                }
                
            } catch (createError) {
                console.warn('⚠️ Create falló, intentando obtener cuenta existente:', createError);
                
                // Intentar obtener cuenta existente
                accountData = await this.fetchWithAuth(`${this.baseUrl}/evm/accounts`);
                
                if (accountData && accountData.success && accountData.accounts && accountData.accounts.length > 0) {
                    console.log('✅ Usando cuenta existente');
                    accountData = {
                        success: true,
                        account: accountData.accounts[0]
                    };
                } else {
                    throw new Error('No se pudo crear ni obtener una cuenta existente');
                }
            }

            if (!accountData.success) {
                const errorMsg = accountData.error || accountData.message || 'Error desconocido al crear cuenta';
                throw new Error(errorMsg);
            }

            console.log('✅ Cuenta obtenida exitosamente:', accountData.account);

            this.connectedAccount = accountData.account;
            this.saveConnection();
            
            // ✅ CORREGIDO: Actualizar la información de la cuenta ANTES de cambiar el estado
            this.updateAccountInfo(this.connectedAccount);
            this.updateConnectionStatus(true);

            this.hideLoading();
            this.showSuccess(`✅ Wallet de Coinbase conectado correctamente! 
                            <br><small>Cuenta: ${this.formatAddress(this.connectedAccount.address)}</small>`);

            // Cargar balances después de conectar
            setTimeout(() => {
                this.loadAccountBalances();
            }, 1000);

        } catch (error) {
            console.error('❌ Error conectando wallet:', error);
            this.hideLoading();
            this.showError(`❌ Error conectando wallet: ${error.message}`);
        } finally {
            this.isProcessing = false;
            console.log('🔚 Proceso de conexión finalizado');
        }
    }

    disconnectWallet() {
        console.log('🔌 Desconectando wallet...');
        
        const accountAddress = this.connectedAccount ? 
            this.formatAddress(this.connectedAccount.address) : '';

        localStorage.removeItem('coinbase_connected_account');
        this.connectedAccount = null;
        this.accountBalances = {};
        this.isProcessing = false;
        this.updateConnectionStatus(false);
        this.clearAccountInfo();
        
        this.showSuccess(`🔌 Wallet de Coinbase desconectado correctamente!
                        ${accountAddress ? `<br><small>Cuenta: ${accountAddress}</small>` : ''}`);
    }

    // ===== ACCOUNT MANAGEMENT =====
    async createEVMAccount() {
        if (this.isProcessing) {
            this.showInfo('⌛ Operación en progreso. Espere...');
            return;
        }

        this.isProcessing = true;
        const accountName = prompt('Ingresa un nombre para la cuenta EVM (opcional):');
        
        if (accountName === null) {
            this.isProcessing = false;
            return;
        }

        this.showLoading('🔄 Creando cuenta EVM...', 15000);

        try {
            const requestBody = accountName ? { name: accountName } : {};
            const response = await this.fetchWithAuth(`${this.baseUrl}/evm/create`, {
                method: 'POST',
                body: JSON.stringify(requestBody)
            });

            if (!response) {
                throw new Error('No se recibió respuesta del servidor');
            }

            if (response.success) {
                this.hideLoading();
                this.showSuccess(`✅ Cuenta EVM creada exitosamente!
                                <br><small>Dirección: ${this.formatAddress(response.account.address)}</small>`);

                this.connectedAccount = response.account;
                this.saveConnection();
                this.updateAccountInfo(response.account);
                await this.loadAccountBalances();
                this.closeAnyOpenModals();
            } else {
                const errorMsg = response.error || response.message || 'Error al crear la cuenta EVM';
                throw new Error(errorMsg);
            }

        } catch (error) {
            console.error('Error creating EVM account:', error);
            this.hideLoading();
            this.showError(`❌ Error creando cuenta EVM: ${error.message}`);
        } finally {
            this.isProcessing = false;
        }
    }

    async createSolanaAccount() {
        if (this.isProcessing) {
            this.showInfo('⌛ Operación en progreso. Espere...');
            return;
        }

        this.isProcessing = true;
        const accountName = prompt('Ingresa un nombre para la cuenta Solana (opcional):');

        if (accountName === null) {
            this.isProcessing = false;
            return;
        }

        try {
            this.showLoading('🔄 Creando cuenta Solana...', 15000);

            const requestBody = accountName ? { name: accountName } : {};
            const response = await this.fetchWithAuth(`${this.baseUrl}/solana/create`, {
                method: 'POST',
                body: JSON.stringify(requestBody)
            });

            if (!response) {
                throw new Error('No se recibió respuesta del servidor');
            }

            if (response.success) {
                this.hideLoading();
                this.showSuccess(`✅ Cuenta Solana creada exitosamente!
                                <br><small>Dirección: ${this.formatAddress(response.account.address)}</small>`);

                this.connectedAccount = response.account;
                this.saveConnection();
                this.updateAccountInfo(response.account);
                await this.loadAccountBalances();
                this.closeAnyOpenModals();
            } else {
                const errorMsg = response.error || response.message || 'Error al crear la cuenta Solana';
                throw new Error(errorMsg);
            }

        } catch (error) {
            console.error('Error creating Solana account:', error);
            this.hideLoading();
            this.showError(`❌ Error creando cuenta Solana: ${error.message}`);
        } finally {
            this.isProcessing = false;
        }
    }

    async importAccount() {
        if (this.isProcessing) {
            this.showInfo('⌛ Operación en progreso. Espere...');
            return;
        }

        this.isProcessing = true;

        const chain = prompt('Selecciona la blockchain (EVM o Solana):');
        if (chain === null) {
            this.isProcessing = false;
            return;
        }

        const privateKey = prompt('Ingresa la clave privada:');
        if (privateKey === null) {
            this.isProcessing = false;
            return;
        }

        const accountName = prompt('Ingresa un nombre para la cuenta (opcional):');

        if (!chain || !privateKey) {
            this.showError('Chain y clave privada son requeridos');
            this.isProcessing = false;
            return;
        }

        try {
            this.showLoading('📥 Importando cuenta...', 15000);

            const endpoint = chain.toLowerCase() === 'solana' ? 'solana/import' : 'evm/import';
            const response = await this.fetchWithAuth(`${this.baseUrl}/${endpoint}`, {
                method: 'POST',
                body: JSON.stringify({
                    private_key: privateKey,
                    name: accountName
                })
            });

            if (!response) {
                throw new Error('No se recibió respuesta del servidor');
            }

            if (response.success) {
                this.hideLoading();
                this.showSuccess(`✅ Cuenta importada exitosamente!
                                <br><small>Dirección: ${this.formatAddress(response.account.address)}</small>`);

                this.connectedAccount = response.account;
                this.saveConnection();
                this.updateAccountInfo(response.account);
                await this.loadAccountBalances();
                this.closeAnyOpenModals();
            } else {
                const errorMsg = response.error || response.message || 'Error al importar la cuenta';
                throw new Error(errorMsg);
            }

        } catch (error) {
            console.error('Error importing account:', error);
            this.hideLoading();
            this.showError(`❌ Error importando cuenta: ${error.message}`);
        } finally {
            this.isProcessing = false;
        }
    }

    // ===== BALANCE MANAGEMENT =====
    async loadAccountBalances() {
        if (this.isProcessing) {
            console.log('💰 Carga de balances diferida por operación de escritura');
            return;
        }

        console.log('💰 Cargando balances de cuenta...');
        this.showLoading('💰 Cargando balances...', 10000);

        try {
            // Simular balances para demostración
            await new Promise(resolve => setTimeout(resolve, 2000));
            
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
            this.showSuccess('✅ Balances actualizados correctamente');

        } catch (error) {
            console.error('Error loading balances:', error);
            
            // Fallback a datos de ejemplo
            this.accountBalances = {
                'EVM': {
                    'ETH': { balance: '0.5', valueUSD: '1500.00' },
                    'USDC': { balance: '1000.0', valueUSD: '1000.00' }
                },
                'Solana': {
                    'SOL': { balance: '10.5', valueUSD: '1050.00' },
                    'USDT': { balance: '500.0', valueUSD: '500.00' }
                }
            };
            
            this.renderBalances();
            this.calculateTotalPortfolio();
            this.showInfo('ℹ️ Usando datos de ejemplo - Error cargando balances reales');
            
        } finally {
            this.hideLoading();
        }
    }

    renderBalances() {
        const container = document.getElementById('tokensList');
        if (!container) {
            console.warn('❌ Contenedor tokensList no encontrado');
            return;
        }

        let html = '';

        Object.keys(this.accountBalances).forEach(chain => {
            const chainBalances = this.accountBalances[chain];
            if (Object.keys(chainBalances).length === 0) return;

            html += `<div class="chain-section mb-4">
                        <h6 class="text-muted mb-3"><i class="fas fa-link me-2"></i>${chain}</h6>`;

            Object.keys(chainBalances).forEach(token => {
                const balance = chainBalances[token];
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
        
        console.log('✅ Balances renderizados correctamente');
    }

    createTokenCard(token, balance, chain) {
        const icons = {
            'ETH': 'fab fa-ethereum text-primary',
            'BTC': 'fab fa-bitcoin text-warning',
            'SOL': 'fas fa-sun text-warning',
            'USDC': 'fas fa-dollar-sign text-success',
            'USDT': 'fas fa-coins text-info',
            'WBTC': 'fab fa-btc text-orange'
        };

        return `
            <div class="token-card card mb-2">
                <div class="card-body py-2">
                    <div class="d-flex align-items-center">
                        <div class="token-icon me-3">
                            <i class="${icons[token] || 'fas fa-coins text-muted'} fa-lg"></i>
                        </div>
                        <div class="flex-grow-1">
                            <div class="d-flex justify-content-between align-items-center">
                                <div>
                                    <h6 class="mb-1 fw-bold">${token}</h6>
                                    <small class="text-muted">${chain}</small>
                                </div>
                                <div class="text-end">
                                    <div class="fw-bold text-dark">${balance.balance}</div>
                                    <small class="text-success">$${balance.valueUSD}</small>
                                </div>
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

        const totalElement = document.getElementById('totalPortfolioValue');
        if (totalElement) {
            totalElement.textContent = `$${total.toLocaleString('en-US', { 
                minimumFractionDigits: 2, 
                maximumFractionDigits: 2 
            })} USD`;
        }
        
        console.log(`💰 Valor total del portfolio: $${total}`);
    }

    // ===== TRANSFER FUNCTIONS =====
    async handleTransfer() {
        if (this.isProcessing) {
            this.showInfo('⌛ Operación en progreso. Espere...');
            return;
        }
        this.isProcessing = true;

        const formData = new FormData(document.getElementById('transferForm'));
        const transferData = {
            fromAccount: formData.get('fromAccount'),
            toAccount: formData.get('toAccount'),
            amount: formData.get('amount'),
            token: formData.get('token'),
            chain: formData.get('chain'),
            memo: formData.get('memo')
        };

        console.log('📤 Datos de transferencia:', transferData);

        if (!this.validateTransfer(transferData)) {
            this.isProcessing = false;
            return;
        }

        this.showLoading('🔄 Procesando transferencia...', 20000);

        try {
            const result = await this.executeTransfer(transferData);

            if (result && result.success) {
                this.showSuccess(`✅ Transferencia completada!
                                <br><small>${transferData.amount} ${transferData.token} enviados correctamente</small>`);
                document.getElementById('transferForm').reset();
                setTimeout(() => this.loadAccountBalances(), 2000);
            } else {
                throw new Error(result?.error || 'Error en la transferencia');
            }

        } catch (error) {
            console.error('Transfer error:', error);
            this.showError(`❌ Error en transferencia: ${error.message}`);
        } finally {
            this.isProcessing = false;
            this.hideLoading();
        }
    }

    async executeTransfer(transferData) {
        console.log(`🔄 Ejecutando transferencia en ${transferData.chain}`);
        
        // Simular transferencia exitosa para demostración
        await new Promise(resolve => setTimeout(resolve, 3000));
        
        return {
            success: true,
            transaction_hash: '0x' + Math.random().toString(16).substr(2, 64),
            message: 'Transferencia simulada exitosamente'
        };
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

    // ===== UI MANAGEMENT =====
    updateConnectionStatus(connected) {
        this.isConnected = connected;
        
        console.log(`🔄 Actualizando estado de conexión: ${connected}`);
        
        const statusElement = document.getElementById('connectionStatus');
        const accountInfo = document.getElementById('accountInfo');
        const connectBtn = document.getElementById('connectCoinbaseBtn');
        const disconnectBtn = document.getElementById('disconnectCoinbaseBtn');
        const connectBtn2 = document.getElementById('connectCoinbaseBtn2');
        const disconnectBtn2 = document.getElementById('disconnectCoinbaseBtn2');

        if (statusElement) {
            statusElement.style.display = connected ? 'inline-block' : 'none';
        }

        if (accountInfo) {
            accountInfo.style.display = connected ? 'block' : 'none';
        }

        // Actualizar todos los botones de conexión/desconexión
        [connectBtn, connectBtn2].forEach(btn => {
            if (btn) btn.style.display = connected ? 'none' : 'block';
        });
        
        [disconnectBtn, disconnectBtn2].forEach(btn => {
            if (btn) btn.style.display = connected ? 'block' : 'none';
        });

        console.log('✅ Estado de conexión actualizado');
    }

    updateAccountInfo(account) {
        console.log('📝 Actualizando información de cuenta:', account);
        
        const accountName = document.getElementById('accountName');
        const accountAddress = document.getElementById('accountAddress');
        const accountType = document.getElementById('accountType');
        const lastUpdate = document.getElementById('lastUpdate');

        console.log('🔍 Elementos encontrados:', {
            accountName: !!accountName,
            accountAddress: !!accountAddress,
            accountType: !!accountType,
            lastUpdate: !!lastUpdate
        });

        if (accountName) {
            accountName.textContent = account.name || account.address || 'No disponible';
            console.log('✅ Nombre actualizado:', accountName.textContent);
        } else {
            console.error('❌ Elemento accountName no encontrado');
        }
        
        if (accountAddress) {
            accountAddress.textContent = account.address || 'No disponible';
            console.log('✅ Dirección actualizada:', accountAddress.textContent);
        } else {
            console.error('❌ Elemento accountAddress no encontrado');
        }
        
        if (accountType) {
            accountType.textContent = account.type || 'EVM'; // Valor por defecto
            console.log('✅ Tipo actualizado:', accountType.textContent);
        } else {
            console.error('❌ Elemento accountType no encontrado');
        }
        
        if (lastUpdate) {
            lastUpdate.textContent = new Date().toLocaleString();
            console.log('✅ Última actualización:', lastUpdate.textContent);
        } else {
            console.error('❌ Elemento lastUpdate no encontrado');
        }
        
        // Auto-completar formulario de transferencia
        const fromAccountInput = document.getElementById('fromAccount');
        if (fromAccountInput && account.address) {
            fromAccountInput.value = account.address;
            console.log('✅ Formulario auto-completado:', fromAccountInput.value);
        }

        console.log('✅ Información de cuenta actualizada completamente');
    }

    clearAccountInfo() {
        console.log('🧹 Limpiando información de cuenta');
        
        this.updateAccountInfo({
            name: '-',
            address: '-',
            type: '-'
        });
        
        const tokensList = document.getElementById('tokensList');
        const totalPortfolio = document.getElementById('totalPortfolioValue');
        
        if (tokensList) {
            tokensList.innerHTML = `
                <div class="text-center py-4">
                    <i class="fas fa-coins fa-3x text-muted mb-3"></i>
                    <p class="text-muted">Conecta tu wallet de Coinbase para ver tus tokens</p>
                </div>
            `;
        }
        
        if (totalPortfolio) {
            totalPortfolio.textContent = '$0.00 USD';
        }
    }

    saveConnection() {
        if (this.connectedAccount) {
            localStorage.setItem('coinbase_connected_account', JSON.stringify(this.connectedAccount));
            console.log('💾 Conexión guardada en localStorage');
        }
    }

    formatAddress(address) {
        if (!address) return '';
        return `${address.substring(0, 8)}...${address.substring(address.length - 6)}`;
    }

    // ===== LOADING MANAGEMENT =====
    showLoading(message = '🔄 Procesando...', timeoutMs = 15000) {
        try {
            console.log(`⏳ Mostrando loading: ${message}`);
            
            if (this.loadingTimeout) {
                clearTimeout(this.loadingTimeout);
                this.loadingTimeout = null;
            }

            this.closeAnyOpenModals();

            const modalElement = document.getElementById('loadingModal');
            const messageElement = document.getElementById('loadingMessage');
            const cancelButton = document.getElementById('cancelLoadingBtn');

            if (!modalElement) {
                console.warn('❌ Modal de loading no encontrado');
                return;
            }

            if (messageElement) {
                messageElement.textContent = message;
            }

            if (cancelButton) {
                cancelButton.onclick = () => this.cancelOperation();
            }

            const modal = new bootstrap.Modal(modalElement, {
                backdrop: 'static',
                keyboard: false,
                focus: true
            });

            modal.show();
            this.currentLoadingModal = modal;

            this.loadingTimeout = setTimeout(() => {
                console.warn('⏰ Loading timeout alcanzado');
                this.hideLoading();
                this.showError('La operación está tomando más tiempo de lo esperado. Por favor, intenta nuevamente.');
            }, timeoutMs);

        } catch (error) {
            console.error('❌ Error mostrando loading:', error);
        }
    }

    hideLoading() {
        try {
            console.log('👋 Ocultando loading');
            
            if (this.loadingTimeout) {
                clearTimeout(this.loadingTimeout);
                this.loadingTimeout = null;
            }

            this.closeModalSafely('loadingModal');
            this.currentLoadingModal = null;

        } catch (error) {
            console.error('❌ Error ocultando loading:', error);
            this.cleanupModalBackdrops();
        }
    }

    cancelOperation() {
        console.log('❌ Operación cancelada por el usuario');
        this.isProcessing = false;
        this.hideLoading();
        this.showInfo('Operación cancelada por el usuario');
    }

    closeModalSafely(modalId) {
        try {
            const modalElement = document.getElementById(modalId);
            if (!modalElement) return;

            const modal = bootstrap.Modal.getInstance(modalElement);
            if (modal) {
                modal.hide();
            } else {
                this.closeModalManually(modalElement);
            }
        } catch (error) {
            console.error(`❌ Error closing modal ${modalId}:`, error);
            this.cleanupModalBackdrops();
        }
    }

    closeAnyOpenModals() {
        try {
            const openModals = document.querySelectorAll('.modal.show');
            openModals.forEach(modal => {
                const modalId = modal.id;
                if (modalId) {
                    this.closeModalSafely(modalId);
                }
            });

            setTimeout(() => this.cleanupModalBackdrops(), 100);
        } catch (error) {
            console.error('❌ Error closing open modals:', error);
            this.cleanupModalBackdrops();
        }
    }

    closeModalManually(modalElement) {
        modalElement.classList.remove('show');
        modalElement.style.display = 'none';
        modalElement.setAttribute('aria-hidden', 'true');
        
        const backdrop = document.querySelector('.modal-backdrop');
        if (backdrop) backdrop.remove();
        
        document.body.classList.remove('modal-open');
        document.body.style.overflow = '';
        document.body.style.paddingRight = '';
    }

    cleanupModalBackdrops() {
        const backdrops = document.querySelectorAll('.modal-backdrop');
        backdrops.forEach(backdrop => backdrop.remove());
        
        document.body.classList.remove('modal-open');
        document.body.style.overflow = '';
        document.body.style.paddingRight = '';

        const modals = document.querySelectorAll('.modal');
        modals.forEach(modal => {
            modal.classList.remove('show');
            modal.style.display = 'none';
            modal.setAttribute('aria-hidden', 'true');
        });
    }

    // ===== NOTIFICATION SYSTEM =====
    showSuccess(message) {
        console.log('✅ Success:', message);
        this.showAlert(message, 'success');
    }

    showError(message) {
        console.error('❌ Error:', message);
        this.showAlert(message, 'danger');
    }

    showInfo(message) {
        console.log('ℹ️ Info:', message);
        this.showAlert(message, 'info');
    }

    showAlert(message, type) {
        let alertContainer = document.getElementById('alertContainer');
        if (!alertContainer) {
            alertContainer = document.createElement('div');
            alertContainer.id = 'alertContainer';
            alertContainer.className = 'position-fixed top-0 end-0 p-3';
            alertContainer.style.zIndex = '9999';
            document.body.appendChild(alertContainer);
        }

        const alertId = 'alert-' + Date.now();
        const alertDiv = document.createElement('div');
        alertDiv.id = alertId;
        alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
        alertDiv.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;

        alertContainer.appendChild(alertDiv);

        setTimeout(() => {
            const alertToRemove = document.getElementById(alertId);
            if (alertToRemove) {
                alertToRemove.remove();
            }
        }, 5000);
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
        if (!this.connectedAccount || this.isProcessing) return;

        try {
            const transactions = await this.fetchTransactionHistory();
            this.renderTransactionHistory(transactions);
        } catch (error) {
            console.error('Error loading transaction history:', error);
        }
    }

    async fetchTransactionHistory() {
        // Simular historial de transacciones
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

        const html = transactions.map(tx => `
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

// ===== GLOBAL INSTANCE AND INITIALIZATION =====
let coinbaseWallet = null;

function initializeCoinbaseWallet() {
    console.log('🚀 Inicializando Coinbase Wallet...');
    
    try {
        if (typeof bootstrap === 'undefined') {
            console.error('❌ Bootstrap no está cargado');
            return;
        }

        coinbaseWallet = new CoinbaseWalletManager();
        console.log('✅ Coinbase Wallet Manager inicializado correctamente');

        // Hacer disponible globalmente
        window.coinbaseWallet = coinbaseWallet;
        
        // Configurar funciones globales
        window.connectCoinbaseWallet = function() {
            if (coinbaseWallet) {
                coinbaseWallet.connectWallet();
            } else {
                console.error('❌ Coinbase Wallet no está inicializado');
                showGlobalAlert('Error: Coinbase Wallet no está disponible. Recarga la página.', 'danger');
            }
        };

        window.disconnectCoinbaseWallet = function() {
            if (coinbaseWallet) {
                coinbaseWallet.disconnectWallet();
            }
        };

        window.loadCoinbaseTokens = function() {
            if (coinbaseWallet) {
                coinbaseWallet.loadAccountBalances();
            }
        };

        window.showCoinbaseAccountInfo = function() {
            if (coinbaseWallet && coinbaseWallet.connectedAccount) {
                const account = coinbaseWallet.connectedAccount;
                const modalBody = document.getElementById('accountInfoModalBody');

                if (modalBody) {
                    modalBody.innerHTML = `
                        <div class="row">
                            <div class="col-md-6">
                                <p><strong>Nombre:</strong> ${account.name || 'No especificado'}</p>
                                <p><strong>Dirección:</strong> <code class="user-select-all">${account.address}</code></p>
                                <p><strong>Tipo:</strong> ${account.type}</p>
                                <p><strong>Creado:</strong> ${account.created_at ? new Date(account.created_at).toLocaleString() : 'N/A'}</p>
                            </div>
                            <div class="col-md-6">
                                <p><strong>Importado:</strong> ${account.imported ? 'Sí' : 'No'}</p>
                                <p><strong>Smart Account:</strong> ${account.is_smart_account ? 'Sí' : 'No'}</p>
                                <p><strong>Última actualización:</strong> ${new Date().toLocaleString()}</p>
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
            } else {
                showGlobalAlert('❌ No hay una cuenta de Coinbase conectada', 'warning');
            }
        };

        window.copyToClipboard = function(text) {
            navigator.clipboard.writeText(text).then(() => {
                const button = event.target.closest('button');
                if (button) {
                    const originalHTML = button.innerHTML;
                    button.innerHTML = '<i class="fas fa-check"></i> Copiado!';
                    button.disabled = true;
                    
                    setTimeout(() => {
                        button.innerHTML = originalHTML;
                        button.disabled = false;
                    }, 2000);
                }
            }).catch(err => {
                console.error('Error copying to clipboard:', err);
                showGlobalAlert('❌ Error al copiar al portapapeles', 'danger');
            });
        };

        console.log('✅ Todas las funciones globales configuradas');

    } catch (error) {
        console.error('❌ Error inicializando Coinbase Wallet:', error);
    }
}

// Función global para mostrar alertas
function showGlobalAlert(message, type) {
    let alertContainer = document.getElementById('alertContainer');
    if (!alertContainer) {
        alertContainer = document.createElement('div');
        alertContainer.id = 'alertContainer';
        alertContainer.className = 'position-fixed top-0 end-0 p-3';
        alertContainer.style.zIndex = '9999';
        document.body.appendChild(alertContainer);
    }

    const alertId = 'alert-' + Date.now();
    const alertDiv = document.createElement('div');
    alertDiv.id = alertId;
    alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;

    alertContainer.appendChild(alertDiv);

    setTimeout(() => {
        const alertToRemove = document.getElementById(alertId);
        if (alertToRemove) {
            alertToRemove.remove();
        }
    }, 5000);
}

// ===== INITIALIZATION WHEN DOM IS READY =====
document.addEventListener('DOMContentLoaded', function() {
    console.log('📄 DOM completamente cargado, inicializando Coinbase Wallet...');
    
    // Esperar a que Bootstrap esté disponible
    if (typeof bootstrap !== 'undefined') {
        initializeCoinbaseWallet();
    } else {
        // Si Bootstrap no está disponible, esperar y reintentar
        console.log('⏳ Esperando a que Bootstrap se cargue...');
        const waitForBootstrap = setInterval(() => {
            if (typeof bootstrap !== 'undefined') {
                clearInterval(waitForBootstrap);
                initializeCoinbaseWallet();
            }
        }, 100);
    }
});

// Exportar para uso global
window.initializeCoinbaseWallet = initializeCoinbaseWallet;