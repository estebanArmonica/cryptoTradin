// Proton Wallet Integration
class ProtonWallet {
    constructor() {
        this.connected = false;
        this.accountName = null;
        this.balances = [];
        this.tokens = [];
        this.totalValueUSD = 0;
    }

    // Conectar a Proton Wallet
    async connect(accountName, permission = 'active') {
        try {
            showLoading('Conectando con Proton Wallet...');

            const response = await fetch('/api/proton/connect', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    account_name: accountName,
                    permission: permission
                })
            });

            const result = await response.json();

            if (result.success) {
                this.connected = true;
                this.accountName = result.account;
                this.balances = result.balances || [];
                this.totalValueUSD = result.total_value || 0;

                this.updateUI();
                this.updateBalanceUI();
                this.updateTokensUI();

                showSuccess('Wallet conectada exitosamente!');
                return true;
            } else {
                throw new Error(result.message || result.error || 'Error al conectar');
            }
        } catch (error) {
            console.error('Error connecting to Proton Wallet:', error);
            showError('Error al conectar: ' + error.message);
            return false;
        } finally {
            hideLoading();
        }
    }

    // Cargar datos de la cuenta
    async loadAccountData() {
        if (!this.connected || !this.accountName) return;

        try {
            showLoading('Cargando datos de la cuenta...');

            // Cargar balance completo
            const balanceResponse = await fetch(`/api/proton/balance/${this.accountName}`);
            const balanceData = await balanceResponse.json();

            if (balanceData.success) {
                this.balances = balanceData.tokens || [];
                this.totalValueUSD = balanceData.total_value_usd || 0;
                this.updateBalanceUI();
                this.updateTokensUI();
            } else {
                throw new Error(balanceData.message || 'Error al cargar balance');
            }

        } catch (error) {
            console.error('Error loading account data:', error);
            showError('Error al cargar datos: ' + error.message);
        } finally {
            hideLoading();
        }
    }

    // Cargar tokens
    async loadTokens() {
        if (!this.connected || !this.accountName) return;

        try {
            showLoading('Cargando tokens...');

            const response = await fetch(`/api/proton/tokens/${this.accountName}`);
            const result = await response.json();

            if (result.success) {
                this.tokens = result.tokens || [];
                this.totalValueUSD = result.total_value_usd || 0;
                this.updateTokensUI();
            } else {
                throw new Error(result.message || 'Error al cargar tokens');
            }
        } catch (error) {
            console.error('Error loading tokens:', error);
            showError('Error al cargar tokens: ' + error.message);
        } finally {
            hideLoading();
        }
    }

    // Obtener información de la cuenta
    async getAccountInfo() {
        if (!this.accountName) return null;

        try {
            const response = await fetch(`/api/proton/account-info/${this.accountName}`);
            const result = await response.json();

            if (result.success) {
                return result.account_info;
            } else {
                throw new Error(result.message || 'Error al obtener información');
            }
        } catch (error) {
            console.error('Error getting account info:', error);
            return null;
        }
    }

    // Función para probar la conexión con el backend
    async testBackendConnection() {
        try {
            const response = await fetch('/api/proton/test');
            const result = await response.json();
            console.log('Test backend:', result);
            return result.success;
        } catch (error) {
            console.error('Backend no disponible:', error);
            return false;
        }
    }

    // Llama a esta función antes de hacer transferencias
    async safeTransfer(fromAccount, toAccount, quantity, memo = '', contract = 'eosio.token') {
        const isBackendOk = await protonWallet.testBackendConnection();
        if (!isBackendOk) {
            showError('El servidor no está disponible. Verifica tu backend.');
            return null;
        }

        return await protonWallet.transfer(fromAccount, toAccount, quantity, memo, contract);
    }

    // Realizar transferencia
    async transfer(fromAccount, toAccount, quantity, memo = '', contract = 'eosio.token') {
    try {
        showLoading('Creando transacción...');

        console.log('Datos de transferencia: ', {
            from_account: fromAccount,
            to_account: toAccount,
            quantity: quantity,
            memo: memo,
            contract: contract
        });

        const response = await fetch('/api/proton/transfer', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                from_account: fromAccount,
                to_account: toAccount,
                quantity: quantity,
                memo: memo,
                contract: contract
            })
        });

        // Verificar el estado HTTP primero
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const result = await response.json();

        if (result.success) {
            showSuccess('Transacción creada exitosamente!');
            console.log('Transacción para firmar:', result.transaction);

            // Aquí deberías integrar con una wallet real para firmar
            // Por ahora mostramos la información
            this.showTransactionInfo(result);

            return result;
        } else {
            // Mejor manejo de errores del servidor
            const errorMessage = result.message || result.error || result.details || 'Error en la transferencia';
            throw new Error(errorMessage);
        }
    } catch (error) {
        console.error('Error transferring:', error);

        // Mensaje más específico según el tipo de error
        let userMessage = 'Error en transferencia: ';
        if (error.message.includes('HTTP error')) {
            userMessage += 'Error de conexión con el servidor';
        } else if (error.message.includes('account not found')) {
            userMessage += 'Cuenta de destino no encontrada';
        } else if (error.message.includes('insufficient balance')) {
            userMessage += 'Saldo insuficiente';
        } else {
            userMessage += error.message;
        }

        showError(userMessage);
        return null;
    } finally {
        hideLoading();
    }
}

// Mostrar información de transacción
showTransactionInfo(transactionData) {
    const modal = new bootstrap.Modal(document.getElementById('transactionModal'));
    const modalBody = document.getElementById('transactionModalBody');

    modalBody.innerHTML = `
            <div class="alert alert-info">
                <h6>Transacción Creada</h6>
                <p>La transacción ha sido creada exitosamente. Para completarla, debes firmarla con tu wallet de Proton.</p>
            </div>
            
            <div class="mb-3">
                <strong>Cadena:</strong> ${transactionData.chain_id?.substring(0, 20)}...
            </div>
            
            <div class="mb-3">
                <strong>Acciones:</strong>
                <pre class="bg-light p-2 mt-2" style="font-size: 12px">${JSON.stringify(transactionData.transaction?.actions, null, 2)}</pre>
            </div>
            
            <div class="alert alert-warning">
                <small>
                    <i class="fas fa-exclamation-triangle"></i>
                    Esta es una simulación. En una implementación real, la transacción se enviaría a tu wallet para firma.
                </small>
            </div>
        `;

    modal.show();
}

// Actualizar UI con estado de conexión
updateUI() {
    const statusElement = document.getElementById('connectionStatus');
    const accountInfo = document.getElementById('accountInfo');
    const connectButton = document.getElementById('connectProtonBtn');
    const fromAccountInput = document.getElementById('fromAccount');
    const accountNameInput = document.getElementById('accountNameInput');

    if (this.connected) {
        if (statusElement) statusElement.style.display = 'inline-block';
        if (accountInfo) accountInfo.style.display = 'block';
        if (connectButton) {
            connectButton.innerHTML = '<i class="fas fa-sync-alt"></i> Reconectar';
            connectButton.classList.remove('btn-primary');
            connectButton.classList.add('btn-outline-primary');
        }

        if (fromAccountInput) {
            fromAccountInput.value = this.accountName;
        }

        this.updateAccountInfo();

    } else {
        if (statusElement) statusElement.style.display = 'none';
        if (accountInfo) accountInfo.style.display = 'none';
        if (connectButton) {
            connectButton.innerHTML = '<i class="fas fa-plug"></i> Conectar Wallet';
            connectButton.classList.add('btn-primary');
            connectButton.classList.remove('btn-outline-primary');
        }
    }
}

// Actualizar información de la cuenta
updateAccountInfo() {
    const accountNameElement = document.getElementById('accountName');
    const lastUpdateElement = document.getElementById('lastUpdate');
    const totalValueElement = document.getElementById('totalValueUSD');

    if (accountNameElement) {
        accountNameElement.textContent = this.accountName;
    }

    if (lastUpdateElement) {
        lastUpdateElement.textContent = new Date().toLocaleString();
    }

    if (totalValueElement) {
        totalValueElement.textContent = `$${this.totalValueUSD.toFixed(2)} USD`;
    }
}

// Actualizar UI de balances
updateBalanceUI() {
    const totalBalanceElement = document.getElementById('totalBalance');
    if (totalBalanceElement && this.balances.length > 0) {
        const xprBalance = this.balances.find(b => b.symbol === 'XPR');
        if (xprBalance) {
            totalBalanceElement.textContent = `${parseFloat(xprBalance.amount).toFixed(4)} XPR`;
        }
    }
}

// Actualizar UI de tokens
updateTokensUI() {
    const tokensList = document.getElementById('tokensList');
    const totalValueElement = document.getElementById('totalPortfolioValue');

    if (totalValueElement) {
        totalValueElement.textContent = `$${this.totalValueUSD.toFixed(2)} USD`;
    }

    if (!tokensList) return;

    if (this.tokens && this.tokens.length > 0) {
        tokensList.innerHTML = this.tokens.map(token => `
                <div class="token-card card mb-2">
                    <div class="card-body py-2">
                        <div class="d-flex justify-content-between align-items-center">
                            <div class="d-flex align-items-center">
                                <div class="token-icon me-3">
                                    <i class="fas fa-coins fa-lg text-warning"></i>
                                </div>
                                <div>
                                    <h6 class="mb-1">${token.symbol || 'TOKEN'}</h6>
                                    <small class="text-muted">${token.contract || 'N/A'}</small>
                                </div>
                            </div>
                            <div class="text-end">
                                <strong>${parseFloat(token.amount || 0).toFixed(4)}</strong>
                                <div class="text-success small">$${(parseFloat(token.value_usd || 0)).toFixed(2)} USD</div>
                                ${token.price_usd ? `<div class="text-muted small">$${parseFloat(token.price_usd).toFixed(4)} c/u</div>` : ''}
                            </div>
                        </div>
                    </div>
                </div>
            `).join('');
    } else {
        tokensList.innerHTML = `
                <div class="text-center py-4">
                    <i class="fas fa-coins fa-3x text-muted mb-3"></i>
                    <p class="text-muted">No se encontraron tokens</p>
                    <button class="btn btn-sm btn-outline-primary" onclick="protonWallet.loadTokens()">
                        <i class="fas fa-refresh"></i> Recargar
                    </button>
                </div>
            `;
    }
}

// Desconectar wallet
disconnect() {
    this.connected = false;
    this.accountName = null;
    this.balances = [];
    this.tokens = [];
    this.totalValueUSD = 0;

    this.updateUI();
    this.updateTokensUI();

    // Limpiar formularios
    const accountNameInput = document.getElementById('accountNameInput');
    if (accountNameInput) accountNameInput.value = '';

    showSuccess('Wallet desconectada');
}
}

// Instancia global de Proton Wallet
const protonWallet = new ProtonWallet();

// Funciones globales para uso en HTML
function connectProtonWallet() {
    const accountNameInput = document.getElementById('accountNameInput');
    const accountName = accountNameInput ? accountNameInput.value.trim() : '';

    if (!accountName) {
        showError('Por favor ingresa un nombre de cuenta de Proton');
        return;
    }

    protonWallet.connect(accountName);
}

function disconnectProtonWallet() {
    protonWallet.disconnect();
}

function loadProtonTokens() {
    protonWallet.loadTokens();
}

function showProtonAccountInfo() {
    protonWallet.getAccountInfo().then(info => {
        if (info) {
            const modal = new bootstrap.Modal(document.getElementById('accountInfoModal'));
            const modalBody = document.getElementById('accountInfoModalBody');

            modalBody.innerHTML = `
                <div class="mb-3">
                    <strong>Nombre:</strong> ${info.account_name}
                </div>
                <div class="mb-3">
                    <strong>Balance RAM:</strong> ${info.ram_quota || 'N/A'}
                </div>
                <div class="mb-3">
                    <strong>CPU:</strong> ${info.cpu_limit || 'N/A'}
                </div>
                <div class="mb-3">
                    <strong>NET:</strong> ${info.net_limit || 'N/A'}
                </div>
                <div class="mb-3">
                    <strong>Permisos:</strong>
                    <pre class="bg-light p-2 mt-2" style="font-size: 12px">${JSON.stringify(info.permissions, null, 2)}</pre>
                </div>
            `;

            modal.show();
        }
    });
}

// Manejar formulario de transferencia
document.addEventListener('DOMContentLoaded', function () {
    const transferForm = document.getElementById('transferForm');
    if (transferForm) {
        transferForm.addEventListener('submit', async function (e) {
            e.preventDefault();

            const fromAccount = document.getElementById('fromAccount').value;
            const toAccount = document.getElementById('toAccount').value;
            const amount = document.getElementById('transferAmount').value;
            const symbol = document.getElementById('transferSymbol').value;
            const memo = document.getElementById('transferMemo').value;
            const contract = document.getElementById('transferContract').value;

            if (!fromAccount || !toAccount || !amount || !symbol) {
                showError('Por favor completa todos los campos requeridos');
                return;
            }

            const quantity = `${parseFloat(amount).toFixed(4)} ${symbol}`;
            await protonWallet.transfer(fromAccount, toAccount, quantity, memo, contract);
        });
    }

    // Cargar tokens soportados
    loadSupportedTokens();
});

// Cargar tokens soportados
async function loadSupportedTokens() {
    try {
        const response = await fetch('/api/proton/supported-tokens');
        const result = await response.json();

        if (result.success) {
            const symbolSelect = document.getElementById('transferSymbol');
            const contractSelect = document.getElementById('transferContract');

            if (symbolSelect && contractSelect) {
                // Limpiar selects
                symbolSelect.innerHTML = '';
                contractSelect.innerHTML = '';

                // Agregar opciones
                result.supported_tokens.forEach(token => {
                    const option = document.createElement('option');
                    option.value = token.symbol;
                    option.textContent = `${token.symbol} - ${token.display_name}`;
                    symbolSelect.appendChild(option);

                    const contractOption = document.createElement('option');
                    contractOption.value = token.contract;
                    contractOption.textContent = `${token.contract} (${token.symbol})`;
                    contractSelect.appendChild(contractOption);
                });
            }
        }
    } catch (error) {
        console.error('Error loading supported tokens:', error);
    }
}

// Utilidades de UI
function showLoading(message = 'Cargando...') {
    let loadingModal = document.getElementById('loadingModal');
    if (!loadingModal) {
        // Crear modal de loading si no existe
        loadingModal = document.createElement('div');
        loadingModal.id = 'loadingModal';
        loadingModal.className = 'modal fade';
        loadingModal.innerHTML = `
            <div class="modal-dialog modal-dialog-centered">
                <div class="modal-content">
                    <div class="modal-body text-center">
                        <div class="spinner-border text-primary mb-3" role="status">
                            <span class="visually-hidden">Cargando...</span>
                        </div>
                        <p id="loadingMessage">${message}</p>
                    </div>
                </div>
            </div>
        `;
        document.body.appendChild(loadingModal);
    }

    document.getElementById('loadingMessage').textContent = message;
    const modal = new bootstrap.Modal(loadingModal);
    modal.show();
}

function hideLoading() {
    const loadingModal = document.getElementById('loadingModal');
    if (loadingModal) {
        const modal = bootstrap.Modal.getInstance(loadingModal);
        if (modal) modal.hide();
    }
}

function showError(message) {
    // Usar Toast de Bootstrap si está disponible
    if (typeof bootstrap !== 'undefined' && bootstrap.Toast) {
        const toast = createToast('Error', message, 'danger');
        document.body.appendChild(toast);
        new bootstrap.Toast(toast).show();
    } else {
        alert('Error: ' + message);
    }
}

function showSuccess(message) {
    // Usar Toast de Bootstrap si está disponible
    if (typeof bootstrap !== 'undefined' && bootstrap.Toast) {
        const toast = createToast('Éxito', message, 'success');
        document.body.appendChild(toast);
        new bootstrap.Toast(toast).show();
    } else {
        alert('Éxito: ' + message);
    }
}

function createToast(title, message, type = 'info') {
    const toastId = 'toast-' + Date.now();
    const toast = document.createElement('div');
    toast.className = `toast align-items-center text-bg-${type} border-0`;
    toast.id = toastId;
    toast.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">
                <strong>${title}:</strong> ${message}
            </div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
        </div>
    `;

    // Auto-remover después de mostrar
    toast.addEventListener('hidden.bs.toast', function () {
        toast.remove();
    });

    return toast;
}