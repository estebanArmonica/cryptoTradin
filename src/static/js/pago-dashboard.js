// Función para mostrar/ocultar sección de pago
function showPaymentSection(type, coin, amount, price) {
    const section = document.getElementById('paymentSection');
    const description = document.getElementById('paymentDescription');

    if (type === 'buy') {
        description.innerHTML = `Comprar ${amount} ${coin.toUpperCase()} por $${(amount * price).toFixed(2)}`;
    } else {
        description.innerHTML = `Vender ${amount} ${coin.toUpperCase()} por $${(amount * price).toFixed(2)}`;
    }

    section.style.display = 'block';
    section.scrollIntoView({ behavior: 'smooth' });
}

function hidePaymentSection() {
    document.getElementById('paymentSection').style.display = 'none';
}

// Función para mostrar la sección de pago
function showPaymentSection(transactionType, coin, amount, price) {
    const paymentSection = document.getElementById('paymentSection');
    const paymentDescription = document.getElementById('paymentDescription');
    const cardForm = document.querySelector('#cardForm').parentElement.parentElement;
    const withdrawalForm = document.getElementById('withdrawalForm');

    if (transactionType === 'buy') {
        paymentDescription.textContent = `Estás a punto de comprar ${amount} ${coin.toUpperCase()} por $${(amount * price).toFixed(2)}`;
        cardForm.style.display = 'block';
        withdrawalForm.style.display = 'none';
    } else if (transactionType === 'withdraw') {
        paymentDescription.textContent = `Estás a punto de vender ${amount} ${coin.toUpperCase()} y transferir $${(amount * price).toFixed(2)} a tu cuenta bancaria`;
        cardForm.style.display = 'none';
        withdrawalForm.style.display = 'block';
        document.getElementById('withdrawalAmount').value = `$${(amount * price).toFixed(2)}`;
    }

    paymentSection.style.display = 'block';

    // Scroll to the payment section
    paymentSection.scrollIntoView({ behavior: 'smooth' });
}

// Función para ocultar la sección de pago
function hidePaymentSection() {
    document.getElementById('paymentSection').style.display = 'none';
}

// Función para procesar pago con tarjeta
async function processCardPayment(amount, coin, amountCrypto) {
    const statusDiv = document.getElementById('paymentStatus');
    statusDiv.innerHTML = '<div class="alert alert-info">Procesando pago...</div>';

    try {
        // Aquí iría la lógica real de procesamiento con Braintree
        // Simulamos un procesamiento exitoso
        setTimeout(() => {
            statusDiv.innerHTML = `
                        <div class="alert alert-success">
                            ✅ Pago procesado exitosamente<br>
                            ID de transacción: TX-${Math.random().toString(36).substr(2, 9).toUpperCase()}<br>
                            Has comprado ${amountCrypto} ${coin.toUpperCase()} por $${amount}
                        </div>
                    `;

            // Ocultar sección después de 3 segundos
            setTimeout(() => {
                hidePaymentSection();
            }, 3000);
        }, 2000);

    } catch (error) {
        statusDiv.innerHTML = `<div class="alert alert-danger">Error procesando el pago: ${error.message}</div>`;
    }
}

// Función para procesar retiro
async function processWithdrawal(amount, bankAccountId) {
    const statusDiv = document.getElementById('paymentStatus');
    statusDiv.innerHTML = '<div class="alert alert-info">Procesando transferencia...</div>';

    try {
        // Simulamos un procesamiento exitoso
        setTimeout(() => {
            statusDiv.innerHTML = `
                        <div class="alert alert-success">
                            ✅ Transferencia procesada exitosamente<br>
                            ID de transacción: TX-${Math.random().toString(36).substr(2, 9).toUpperCase()}<br>
                            Se transferirán $${amount} a tu cuenta bancaria
                        </div>
                    `;

            // Ocultar sección después de 3 segundos
            setTimeout(() => {
                hidePaymentSection();
            }, 3000);
        }, 2000);

    } catch (error) {
        statusDiv.innerHTML = `<div class="alert alert-danger">Error procesando la transferencia: ${error.message}</div>`;
    }
}

// Event listeners para los botones
document.addEventListener('DOMContentLoaded', function () {
    // Botón de pago con tarjeta
    document.getElementById('cardPaymentBtn')?.addEventListener('click', function () {
        const amount = 100; // Ejemplo: $100
        const coin = 'btc';
        const amountCrypto = 0.002; // Ejemplo: 0.002 BTC
        processCardPayment(amount, coin, amountCrypto);
    });

    // Botón de retiro
    document.getElementById('withdrawalBtn')?.addEventListener('click', function () {
        const bankAccountId = document.getElementById('bankAccountSelect').value;
        if (!bankAccountId) {
            alert('Por favor selecciona una cuenta bancaria');
            return;
        }
        const amount = 500; // Ejemplo: $500
        processWithdrawal(amount, bankAccountId);
    });
});