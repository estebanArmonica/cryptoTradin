// Obtener las ganancias retirables del localStorage
document.addEventListener('DOMContentLoaded', function () {
    const withdrawableProfit = localStorage.getItem('withdrawableProfit');
    const withdrawableAmountElement = document.getElementById('withdrawable-amount');
    const amountInput = document.getElementById('amount');

    if (withdrawableProfit) {
        const amount = parseFloat(withdrawableProfit);
        withdrawableAmountElement.textContent = `$${amount.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

        // Establecer el máximo que se puede retirar
        const maxWithdrawal = Math.min(5000, amount);
        amountInput.max = maxWithdrawal;

        // Actualizar el texto de ayuda
        document.getElementById('amount-help').textContent =
            `Mínimo $10.00 - Máximo $${maxWithdrawal.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

        // Establecer el valor por defecto (el máximo o 100, lo que sea menor)
        const defaultValue = Math.min(100, maxWithdrawal);
        if (maxWithdrawal > 0) {
            amountInput.value = defaultValue.toFixed(2);
        }
    } else {
        withdrawableAmountElement.textContent = '$0.00';
        amountInput.disabled = true;
        document.getElementById('amount-help').textContent = 'No hay ganancias retirables disponibles';
    }
});

document.getElementById('transferForm').addEventListener('submit', function (e) {
    e.preventDefault();

    // Validar el monto
    const amount = parseFloat(document.getElementById('amount').value);
    const withdrawableProfit = parseFloat(localStorage.getItem('withdrawableProfit') || 0);

    if (amount > withdrawableProfit) {
        alert('El monto solicitado excede tus ganancias retirables disponibles.');
        return;
    }

    // Simulación de proceso de transferencia (sin delay largo)
    const email = document.getElementById('paypalEmail').value;

    // Guardar información de la transacción
    const transactionData = {
        amount: amount,
        email: email,
        timestamp: new Date().toISOString(),
        status: 'pending'
    };

    // Guardar en localStorage para procesar después
    localStorage.setItem('pendingWithdrawal', JSON.stringify(transactionData));

    // Mostrar mensaje de éxito
    alert(`¡Transferencia iniciada!\n$${amount.toFixed(2)} serán transferidos a ${email}\n\nEsta operación puede tardar hasta 48 horas.`);

    // Redirigir de vuelta a la plataforma de trading
    setTimeout(() => {
        window.location.href = 'trading';
    }, 1000);
});

// Simular cambios en la tasa de conversión
setInterval(() => {
    const rateElement = document.querySelector('.rate-value');
    const currentRate = parseFloat(rateElement.textContent.split('=')[1].trim().replace('$', '').replace(',', ''));
    const randomChange = (Math.random() * 1000) - 500; // Cambio aleatorio entre -500 y +500
    const newRate = currentRate + randomChange;

    rateElement.textContent = `1 BTC = $${newRate.toLocaleString('en-US', { maximumFractionDigits: 2 })} USD`;
}, 30000);