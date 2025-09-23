class PaymentProcessor {
    constructor() {
        this.braintreeClient = null;
        this.hostedFieldsInstance = null;
        this.paypalInstance = null;
        this.currentTransaction = null;
        this.init();
    }

    async init() {
        try {
            // Obtener cliente token desde tu backend
            const clientToken = await this.getClientToken();

            // Inicializar Braintree
            this.braintreeClient = await braintree.client.create({
                authorization: clientToken
            });

            const urlParams = this.getUrlParams();

            // Si hay parámetros en la URL, los usara
            if (urlParams.coin) {
                appState.currentCoin = urlParams.coin;
                document.getElementById('crypto-select').value = urlParams.coin;
            }

            // Configurar campos de pago
            this.setupHostedFields();

            // Configurar PayPal
            this.setupPayPal();

        } catch (error) {
            console.error('Error inicializando procesador de pagos:', error);
        }
    }

    async getClientToken() {
        // Llamar a tu backend para obtener un token de cliente
        const response = await fetch('/api/braintree/client-token', {
            method: 'GET',
            credentials: 'include'
        });

        if (!response.ok) {
            throw new Error('Error obteniendo token de cliente');
        }

        const data = await response.json();
        return data.clientToken;
    }

    async setupHostedFields() {
        try {
            // ESPERAR a que los elementos existan en el DOM
            await this.waitForElements(['#card-number', '#cvv', '#expiration-date']);

            // Configurar campos de tarjeta de crédito
            this.hostedFieldsInstance = await braintree.hostedFields.create({
                client: this.braintreeClient,
                styles: {
                    input: {
                        'font-size': '16px',
                        'color': '#3A3A3A'
                    },
                    '.invalid': {
                        'color': 'red'
                    }
                },
                fields: {
                    number: {
                        selector: '#card-number',
                        placeholder: '4111 1111 1111 1111'
                    },
                    cvv: {
                        selector: '#cvv',
                        placeholder: '123'
                    },
                    expirationDate: {
                        selector: '#expiration-date',
                        placeholder: 'MM/YY'
                    }
                }
            });

            console.log('Hosted Fields configurados correctamente');
        } catch (error) {
            console.error('Error configurando Hosted Fields:', error);
        }
    }

    // Función para esperar a que los elementos existan en el DOM
    waitForElements(selectors, timeout = 5000) {
        return new Promise((resolve, reject) => {
            const startTime = Date.now();

            const checkElements = () => {
                const allExist = selectors.every(selector => {
                    return document.querySelector(selector) !== null;
                });

                if (allExist) {
                    resolve();
                } else if (Date.now() - startTime >= timeout) {
                    reject(new Error(`Elementos no encontrados: ${selectors.join(', ')}`));
                } else {
                    setTimeout(checkElements, 100);
                }
            };

            checkElements();
        });
    }

    async setupPayPal() {
        // Configurar botón de PayPal
        this.paypalInstance = await braintree.paypal.create({
            client: this.braintreeClient
        });
    }

    async processCardPayment(amount, coin, amountCrypto) {
        try {
            // Tokenizar la tarjeta
            const { nonce } = await this.hostedFieldsInstance.tokenize();

            // Enviar el nonce al servidor para procesar el pago
            const response = await fetch('/api/braintree/process-payment', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    paymentMethodNonce: nonce,
                    amount: amount,
                    coin: coin,
                    amountCrypto: amountCrypto
                })
            });

            const result = await response.json();

            if (result.success) {
                return {
                    success: true,
                    transactionId: result.transaction.id,
                    message: 'Pago procesado exitosamente'
                };
            } else {
                return {
                    success: false,
                    message: result.message || 'Error procesando el pago'
                };
            }
        } catch (error) {
            console.error('Error procesando pago con tarjeta:', error);
            return {
                success: false,
                message: 'Error procesando el pago'
            };
        }
    }

    async initiateWithdrawal(amount, bankAccountId) {
        try {
            // Procesar retiro a cuenta bancaria
            const response = await fetch('/api/braintree/withdraw', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    amount: amount,
                    bankAccountId: bankAccountId
                })
            });

            const result = await response.json();

            if (result.success) {
                return {
                    success: true,
                    transactionId: result.transaction.id,
                    message: 'Retiro procesado exitosamente'
                };
            } else {
                return {
                    success: false,
                    message: result.message || 'Error procesando el retiro'
                };
            }
        } catch (error) {
            console.error('Error procesando retiro:', error);
            return {
                success: false,
                message: 'Error procesando el retiro'
            };
        }
    }
}

// Integración con el dashboard existente
class CryptoDashboardWithPayments extends CryptoDashboard {
    constructor() {
        super();
        this.paymentProcessor = new PaymentProcessor();
        this.setupPaymentEventListeners();
    }

    setupPaymentEventListeners() {
        // Modificar el evento de compra para usar pagos reales
        document.getElementById('buyBtn')?.addEventListener('click', () => {
            this.showPaymentOptions('buy');
        });

        document.getElementById('sellBtn')?.addEventListener('click', () => {
            this.showWithdrawalOptions();
        });
    }

    showPaymentOptions(action) {
        const currentPrice = this.ohlcData[this.ohlcData.length - 1].close;
        const amount = parseFloat(document.getElementById('amount').value) || 0;
        const total = currentPrice * amount;

        if (amount <= 0) {
            alert('Por favor ingresa una cantidad válida');
            return;
        }

        this.currentTransaction = {
            action: action,
            coin: this.currentCoin,
            amount: amount,
            total: total,
            currentPrice: currentPrice
        };

        // Mostrar modal de pago
        this.renderPaymentForm();
        $('#paymentModal').modal('show');
    }

    renderPaymentForm() {
        const formHtml = `
                    <div class="row">
                        <div class="col-md-12">
                            <div class="alert alert-info">
                                <p>Estás a punto de ${this.currentTransaction.action === 'buy' ? 'comprar' : 'vender'} 
                                ${this.currentTransaction.amount} ${this.currentTransaction.coin.toUpperCase()} 
                                por $${this.currentTransaction.total.toFixed(2)}</p>
                            </div>
                        </div>
                    </div>
                    
                    <div class="row mt-3">
                        <div class="col-md-6">
                            <div class="card">
                                <div class="card-header">
                                    <h6>Pago con Tarjeta</h6>
                                </div>
                                <div class="card-body">
                                    <form id="cardForm">
                                        <div class="form-group mb-3">
                                            <label for="card-number">Número de Tarjeta</label>
                                            <!-- AQUÍ ESTÁ EL ELEMENTO CORRECTO -->
                                            <div id="card-number" class="form-control braintree-field"></div>
                                        </div>
                                        
                                        <div class="row mb-3">
                                            <div class="col-md-6">
                                                <label for="expiration-date">Fecha de Expiración</label>
                                                <!-- AQUÍ ESTÁ EL ELEMENTO CORRECTO -->
                                                <div id="expiration-date" class="form-control braintree-field"></div>
                                            </div>
                                            <div class="col-md-6">
                                                <label for="cvv">CVV</label>
                                                <!-- AQUÍ ESTÁ EL ELEMENTO CORRECTO -->
                                                <div id="cvv" class="form-control braintree-field"></div>
                                            </div>
                                        </div>
                                        
                                        <button type="button" id="cardPaymentBtn" class="btn btn-primary w-100">
                                            Pagar con Tarjeta
                                        </button>
                                    </form>
                                </div>
                            </div>
                        </div>
                        
                        <div class="col-md-6">
                            <div class="card">
                                <div class="card-header">
                                    <h6>Pago con PayPal</h6>
                                </div>
                                <div class="card-body text-center">
                                    <div id="paypal-button" class="mt-3"></div>
                                </div>
                            </div>
                        </div>
                    </div>
                `;

        document.getElementById('paymentForm').innerHTML = formHtml;

        // Configurar evento para pago con tarjeta
        document.getElementById('cardPaymentBtn').addEventListener('click', () => {
            this.processCardPayment();
        });

        // Inicializar Hosted Fields DESPUÉS de renderizar el formulario
        this.setupHostedFields();

        // Configurar botón de PayPal
        this.setupPayPalButton();
    }

    async processCardPayment() {
        const statusDiv = document.getElementById('paymentStatus');
        statusDiv.innerHTML = '<div class="alert alert-info">Procesando pago...</div>';

        const result = await this.paymentProcessor.processCardPayment(
            this.currentTransaction.total,
            this.currentTransaction.coin,
            this.currentTransaction.amount
        );

        if (result.success) {
            statusDiv.innerHTML = `<div class="alert alert-success">${result.message}<br>ID de transacción: ${result.transactionId}</div>`;

            // Actualizar balances en el dashboard
            await this.updateBalancesAfterTransaction();

            // Cerrar modal después de 3 segundos
            setTimeout(() => {
                $('#paymentModal').modal('hide');
            }, 3000);
        } else {
            statusDiv.innerHTML = `<div class="alert alert-danger">${result.message}</div>`;
        }
    }

    setupPayPalButton() {
        // Crear botón de PayPal
        paypal.Buttons({
            createOrder: (data, actions) => {
                return actions.order.create({
                    purchase_units: [{
                        amount: {
                            value: this.currentTransaction.total.toFixed(2)
                        }
                    }]
                });
            },
            onApprove: async (data, actions) => {
                const statusDiv = document.getElementById('paymentStatus');
                statusDiv.innerHTML = '<div class="alert alert-info">Procesando pago con PayPal...</div>';

                const result = await this.paymentProcessor.processPayPalPayment(
                    this.currentTransaction.total,
                    this.currentTransaction.coin,
                    this.currentTransaction.amount
                );

                if (result.success) {
                    statusDiv.innerHTML = `<div class="alert alert-success">${result.message}<br>ID de transacción: ${result.transactionId}</div>`;

                    // Actualizar balances en el dashboard
                    await this.updateBalancesAfterTransaction();

                    // Cerrar modal después de 3 segundos
                    setTimeout(() => {
                        $('#paymentModal').modal('hide');
                    }, 3000);
                } else {
                    statusDiv.innerHTML = `<div class="alert alert-danger">${result.message}</div>`;
                }
            }
        }).render('#paypal-button');
    }

    async updateBalancesAfterTransaction() {
        // Actualizar los balances después de una transacción exitosa
        if (this.currentTransaction.action === 'buy') {
            // Restar el monto en USD y agregar las criptomonedas compradas
            this.balanceUSDT -= this.currentTransaction.total;
            this.balanceBTC += this.currentTransaction.amount;
        } else {
            // Restar las criptomonedas y agregar el monto en USD
            this.balanceBTC -= this.currentTransaction.amount;
            this.balanceUSDT += this.currentTransaction.total;
        }

        // Actualizar la interfaz
        this.updateUI();
    }

    showWithdrawalOptions() {
        // Mostrar opciones para retirar fondos a cuenta bancaria
        const currentPrice = this.ohlcData[this.ohlcData.length - 1].close;
        const amount = parseFloat(document.getElementById('amount').value) || 0;
        const total = currentPrice * amount;

        if (amount <= 0) {
            alert('Por favor ingresa una cantidad válida');
            return;
        }

        if (amount > this.balanceBTC) {
            alert('No tienes suficiente saldo en BTC');
            return;
        }

        this.currentTransaction = {
            action: 'withdraw',
            coin: this.currentCoin,
            amount: amount,
            total: total,
            currentPrice: currentPrice
        };

        this.renderWithdrawalForm();
        $('#paymentModal').modal('show');
    }

    renderWithdrawalForm() {
        const formHtml = `
                    <div class="row">
                        <div class="col-md-12">
                            <div class="alert alert-info">
                                <p>Estás a punto de vender ${this.currentTransaction.amount} ${this.currentTransaction.coin.toUpperCase()} 
                                por $${this.currentTransaction.total.toFixed(2)} y transferir los fondos a tu cuenta bancaria</p>
                            </div>
                        </div>
                    </div>
                    
                    <div class="row mt-3">
                        <div class="col-md-12">
                            <div class="card">
                                <div class="card-header">
                                    <h6>Transferencia Bancaria</h6>
                                </div>
                                <div class="card-body">
                                    <div class="form-group mb-3">
                                        <label>Seleccionar Cuenta Bancaria</label>
                                        <select id="bankAccountSelect" class="form-select">
                                            <option value="">Selecciona una cuenta bancaria</option>
                                            <option value="account_1">Cuenta Principal ****1234</option>
                                            <option value="account_2">Cuenta de Ahorros ****5678</option>
                                        </select>
                                    </div>
                                    
                                    <div class="form-group mb-3">
                                        <label>Monto a Transferir</label>
                                        <input type="text" class="form-control" value="$${this.currentTransaction.total.toFixed(2)}" readonly>
                                    </div>
                                    
                                    <button type="button" id="withdrawalBtn" class="btn btn-primary w-100">
                                        Solicitar Transferencia
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>
                `;

        document.getElementById('paymentForm').innerHTML = formHtml;

        // Configurar evento para retiro
        document.getElementById('withdrawalBtn').addEventListener('click', () => {
            this.processWithdrawal();
        });
    }

    async processWithdrawal() {
        const bankAccountId = document.getElementById('bankAccountSelect').value;

        if (!bankAccountId) {
            alert('Por favor selecciona una cuenta bancaria');
            return;
        }

        const statusDiv = document.getElementById('paymentStatus');
        statusDiv.innerHTML = '<div class="alert alert-info">Procesando transferencia...</div>';

        const result = await this.paymentProcessor.initiateWithdrawal(
            this.currentTransaction.total,
            bankAccountId
        );

        if (result.success) {
            statusDiv.innerHTML = `<div class="alert alert-success">${result.message}<br>ID de transacción: ${result.transactionId}</div>`;

            // Actualizar balances después del retiro
            this.balanceBTC -= this.currentTransaction.amount;
            this.updateUI();

            // Cerrar modal después de 3 segundos
            setTimeout(() => {
                $('#paymentModal').modal('hide');
            }, 3000);
        } else {
            statusDiv.innerHTML = `<div class="alert alert-danger">${result.message}</div>`;
        }
    }
}
// Solo he añadido la funcionalidad del tema oscuro/claro
document.addEventListener('DOMContentLoaded', function () {
    const themeSwitch = document.getElementById('themeSwitch');
    const themeIcon = themeSwitch.querySelector('i');

    // Comprobar si hay una preferencia guardada
    const savedTheme = localStorage.getItem('theme') || 'light';
    if (savedTheme === 'dark') {
        document.documentElement.setAttribute('data-theme', 'dark');
        themeIcon.classList.remove('bi-moon-stars');
        themeIcon.classList.add('bi-sun');
    }

    themeSwitch.addEventListener('click', function () {
        const currentTheme = document.documentElement.getAttribute('data-theme');
        if (currentTheme === 'dark') {
            document.documentElement.removeAttribute('data-theme');
            themeIcon.classList.remove('bi-sun');
            themeIcon.classList.add('bi-moon-stars');
            localStorage.setItem('theme', 'light');
        } else {
            document.documentElement.setAttribute('data-theme', 'dark');
            themeIcon.classList.remove('bi-moon-stars');
            themeIcon.classList.add('bi-sun');
            localStorage.setItem('theme', 'dark');
        }
    });

    // Inicializar el dashboard
    window.dashboard = new CryptoDashboard();
});

// Función para cerrar sesión
async function logoutUser() {
    try {
        // Mostrar confirmación con SweetAlert2
        const result = await Swal.fire({
            title: '¿Cerrar sesión?',
            text: '¿Estás seguro de que deseas salir de tu cuenta?',
            icon: 'question',
            showCancelButton: true,
            confirmButtonColor: '#3085d6',
            cancelButtonColor: '#d33',
            confirmButtonText: 'Sí, cerrar sesión',
            cancelButtonText: 'Cancelar'
        });

        if (result.isConfirmed) {
            const response = await fetch('/api/logout', {
                method: 'POST',
                credentials: 'include'
            });

            if (response.ok) {
                await Swal.fire({
                    title: 'Sesión cerrada',
                    text: 'Has cerrado sesión exitosamente.',
                    icon: 'success',
                    timer: 2000,
                    showConfirmButton: false
                });

                // Redirigir después de mostrar el mensaje
                setTimeout(() => {
                    window.location.href = '/';
                }, 2000);
            } else {
                throw new Error('Error al cerrar sesión');
            }
        }
    } catch (error) {
        await Swal.fire({
            title: 'Error',
            text: 'Error al cerrar sesión. Inténtalo de nuevo.',
            icon: 'error',
            confirmButtonText: 'Aceptar'
        });
    }
}

// Agregar evento al botón de logout
document.addEventListener('DOMContentLoaded', function () {
    const logoutBtn = document.getElementById('logoutBtn');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', logoutUser);
    }

    const themeSwitch = document.getElementById('themeSwitch');
    const themeIcon = themeSwitch.querySelector('i');

    // Comprobar si hay una preferencia guardada
    const savedTheme = localStorage.getItem('theme') || 'light';
    if (savedTheme === 'dark') {
        document.documentElement.setAttribute('data-theme', 'dark');
        themeIcon.classList.remove('bi-moon-stars');
        themeIcon.classList.add('bi-sun');
    }

    themeSwitch.addEventListener('click', function () {
        const currentTheme = document.documentElement.getAttribute('data-theme');
        if (currentTheme === 'dark') {
            document.documentElement.removeAttribute('data-theme');
            themeIcon.classList.remove('bi-sun');
            themeIcon.classList.add('bi-moon-stars');
            localStorage.setItem('theme', 'light');
        } else {
            document.documentElement.setAttribute('data-theme', 'dark');
            themeIcon.classList.remove('bi-moon-stars');
            themeIcon.classList.add('bi-sun');
            localStorage.setItem('theme', 'dark');
        }
    });

    // Inicializar el dashboard
    window.dashboard = new CryptoDashboard();
});