// Elementos del DOM
const loginForm = document.getElementById("login-form");
const verifyForm = document.getElementById("verify-form");
const step1 = document.getElementById("step-1");
const step2 = document.getElementById("step-2");
const step1Indicator = document.getElementById("step-1-indicator");
const step2Indicator = document.getElementById("step-2-indicator");
const togglePasswordBtn = document.getElementById("toggle-password");
const passwordInput = document.getElementById("password");
const loginBtn = document.getElementById("login-btn");
const verifyBtn = document.getElementById("verify-btn");

let userEmail = "";

// Alternar visibilidad de contraseña
togglePasswordBtn.addEventListener("click", () => {
    const type = passwordInput.getAttribute("type") === "password" ? "text" : "password";
    passwordInput.setAttribute("type", type);

    // Cambiar icono
    const icon = togglePasswordBtn.querySelector("i");
    icon.classList.toggle("fa-eye");
    icon.classList.toggle("fa-eye-slash");
});

// Envío del formulario de login
loginForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const correo = document.getElementById("correo").value;
    const password = document.getElementById("password").value;

    // Validación básica
    if (!correo || !password) {
        Swal.fire({
            icon: 'warning',
            title: 'Campos incompletos',
            text: 'Por favor, completa todos los campos',
            confirmButtonColor: '#2563eb'
        });
        return;
    }

    // Mostrar estado de carga
    loginBtn.classList.add("btn-loading");

    const formData = new FormData();
    formData.append("correo", correo);
    formData.append("password", password);

    try {
        const response = await fetch("/api/login", {
            method: "POST",
            body: formData
        });

        const data = await response.json();

        if (response.ok) {
            // Mostrar éxito con SweetAlert
            await Swal.fire({
                icon: 'success',
                title: 'Código enviado',
                text: 'Hemos enviado un código de verificación a tu correo electrónico',
                confirmButtonColor: '#2563eb'
            });

            // Cambiar al paso 2
            userEmail = correo;
            step1.classList.add("hidden");
            step2.classList.remove("hidden");
            step1Indicator.classList.remove("active");
            step2Indicator.classList.add("active");

        } else {
            // Mostrar error
            Swal.fire({
                icon: 'error',
                title: 'Error al iniciar sesión',
                text: data.error || data.detail || 'Ocurrió un error inesperado',
                confirmButtonColor: '#2563eb'
            });
        }
    } catch (error) {
        Swal.fire({
            icon: 'error',
            title: 'Error de conexión',
            text: 'No se pudo conectar con el servidor. Intenta nuevamente.',
            confirmButtonColor: '#2563eb'
        });
    } finally {
        loginBtn.classList.remove("btn-loading");
    }
});

// Envío del formulario de verificación
verifyForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const code = document.getElementById("code").value;

    // Validación básica
    if (!code || code.length !== 6) {
        Swal.fire({
            icon: 'warning',
            title: 'Código inválido',
            text: 'Por favor, ingresa un código de 6 dígitos',
            confirmButtonColor: '#2563eb'
        });
        return;
    }

    // Mostrar estado de carga
    verifyBtn.classList.add("btn-loading");

    const formData = new FormData();
    formData.append("correo", userEmail);
    formData.append("code", code);

    try {
        const response = await fetch("/api/verify-code", {
            method: "POST",
            body: formData
        });

        const data = await response.json();

        if (response.ok) {
            // Mostrar éxito con SweetAlert
            await Swal.fire({
                icon: 'success',
                title: '¡Verificación exitosa!',
                text: 'Serás redirigido al dashboard en unos momentos',
                confirmButtonColor: '#2563eb',
                timer: 2000,
                showConfirmButton: false
            });

            // Redirigir al dashboard
            setTimeout(() => {
                window.location.href = "/dashboard";
            }, 2000);

        } else {
            // Mostrar error
            Swal.fire({
                icon: 'error',
                title: 'Código incorrecto',
                text: data.error || data.detail || 'El código ingresado no es válido',
                confirmButtonColor: '#2563eb'
            });
        }
    } catch (error) {
        Swal.fire({
            icon: 'error',
            title: 'Error de conexión',
            text: 'No se pudo verificar el código. Intenta nuevamente.',
            confirmButtonColor: '#2563eb'
        });
    } finally {
        verifyBtn.classList.remove("btn-loading");
    }
});

// Efecto de aparición para los elementos
document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('.form-group, .btn, .links').forEach((element, index) => {
        element.style.opacity = 0;
        element.style.transform = 'translateY(10px)';
        element.style.transition = `opacity 0.5s ease ${index * 0.1}s, transform 0.5s ease ${index * 0.1}s`;

        setTimeout(() => {
            element.style.opacity = 1;
            element.style.transform = 'translateY(0)';
        }, 100);
    });
});