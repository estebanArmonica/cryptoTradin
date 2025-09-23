// Elementos del DOM
const registerForm = document.getElementById("register-form");
const togglePasswordBtn = document.getElementById("toggle-password");
const passwordInput = document.getElementById("password");
const passwordStrengthBar = document.getElementById("password-strength-bar");
const passwordStrengthText = document.getElementById("password-strength-text");
const registerBtn = document.getElementById("register-btn");

// Alternar visibilidad de contraseña
togglePasswordBtn.addEventListener("click", () => {
    const type = passwordInput.getAttribute("type") === "password" ? "text" : "password";
    passwordInput.setAttribute("type", type);

    // Cambiar icono
    const icon = togglePasswordBtn.querySelector("i");
    icon.classList.toggle("fa-eye");
    icon.classList.toggle("fa-eye-slash");
});

// Verificar fortaleza de la contraseña
passwordInput.addEventListener("input", checkPasswordStrength);

function checkPasswordStrength() {
    const password = passwordInput.value;
    let strength = 0;
    let message = "";
    let color = "";

    // Verificar longitud
    if (password.length > 5) strength += 20;
    if (password.length > 8) strength += 20;

    // Verificar caracteres diversos
    if (/[A-Z]/.test(password)) strength += 20;
    if (/[0-9]/.test(password)) strength += 20;
    if (/[^A-Za-z0-9]/.test(password)) strength += 20;

    // Asignar mensaje y color según la fortaleza
    if (password.length === 0) {
        message = "Seguridad de la contraseña";
        color = "transparent";
    } else if (password.length < 6) {
        message = "Muy corta (mínimo 6 caracteres)";
        color = "#ef4444";
    } else if (strength < 40) {
        message = "Débil";
        color = "#ef4444";
    } else if (strength < 60) {
        message = "Moderada";
        color = "#f59e0b";
    } else if (strength < 80) {
        message = "Fuerte";
        color = "#84cc16";
    } else {
        message = "Muy fuerte";
        color = "#10b981";
    }

    // Actualizar la barra y el texto
    passwordStrengthBar.style.width = strength + "%";
    passwordStrengthBar.style.backgroundColor = color;
    passwordStrengthText.textContent = message;
    passwordStrengthText.style.color = color;
}

// Envío del formulario de registro
registerForm.addEventListener("submit", async (e) => {
    e.preventDefault();

    const nombre = document.getElementById("nombre").value;
    const apellido = document.getElementById("apellido").value;
    const correo = document.getElementById("correo").value;
    const password = document.getElementById("password").value;
    const terms = document.getElementById("terms").checked;

    // Validación básica
    if (!nombre || !apellido || !correo || !password) {
        Swal.fire({
            icon: 'warning',
            title: 'Campos incompletos',
            text: 'Por favor, completa todos los campos',
            confirmButtonColor: '#16a34a'
        });
        return;
    }

    if (!terms) {
        Swal.fire({
            icon: 'warning',
            title: 'Términos y condiciones',
            text: 'Debes aceptar los términos y condiciones para continuar',
            confirmButtonColor: '#16a34a'
        });
        return;
    }

    if (password.length < 6) {
        Swal.fire({
            icon: 'warning',
            title: 'Contraseña demasiado corta',
            text: 'La contraseña debe tener al menos 6 caracteres',
            confirmButtonColor: '#16a34a'
        });
        return;
    }

    // Mostrar estado de carga
    registerBtn.classList.add("btn-loading");

    const formData = new FormData();
    formData.append("nombre", nombre);
    formData.append("apellido", apellido);
    formData.append("correo", correo);
    formData.append("password", password);

    try {
        const response = await fetch("/api/register", {
            method: "POST",
            body: formData
        });

        const data = await response.json();

        if (response.ok) {
            // Mostrar éxito con SweetAlert
            await Swal.fire({
                icon: 'success',
                title: '¡Registro exitoso!',
                html: `
                            <p>Tu cuenta ha sido creada correctamente.</p>
                            <p>Revisa tu correo electrónico para verificar tu cuenta.</p>
                        `,
                confirmButtonColor: '#16a34a'
            });

            // Redirigir al login después de 2 segundos
            setTimeout(() => {
                window.location.href = "/";
            }, 2000);

        } else {
            // Mostrar error
            Swal.fire({
                icon: 'error',
                title: 'Error en el registro',
                text: data.detail || "Error desconocido",
                confirmButtonColor: '#16a34a'
            });
        }
    } catch (error) {
        Swal.fire({
            icon: 'error',
            title: 'Error de conexión',
            text: 'No se pudo conectar con el servidor. Intenta nuevamente.',
            confirmButtonColor: '#16a34a'
        });
    } finally {
        registerBtn.classList.remove("btn-loading");
    }
});

// Efecto de aparición para los elementos
document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('.form-group, .btn, .links, .terms').forEach((element, index) => {
        element.style.opacity = 0;
        element.style.transform = 'translateY(10px)';
        element.style.transition = `opacity 0.5s ease ${index * 0.1}s, transform 0.5s ease ${index * 0.1}s`;

        setTimeout(() => {
            element.style.opacity = 1;
            element.style.transform = 'translateY(0)';
        }, 100);
    });
});