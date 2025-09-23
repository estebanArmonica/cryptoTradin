// Función para mostrar/ocultar contraseñas
function setupPasswordToggles() {
    const togglePassword = (buttonId, inputId) => {
        const button = document.getElementById(buttonId);
        const input = document.getElementById(inputId);
        
        button.addEventListener('click', function() {
            const type = input.getAttribute('type') === 'password' ? 'text' : 'password';
            input.setAttribute('type', type);
            
            // Cambiar icono
            const icon = button.querySelector('i');
            if (type === 'text') {
                icon.classList.remove('bi-eye');
                icon.classList.add('bi-eye-slash');
            } else {
                icon.classList.remove('bi-eye-slash');
                icon.classList.add('bi-eye');
            }
        });
    };
    
    togglePassword('toggleCurrentPassword', 'currentPassword');
    togglePassword('toggleNewPassword', 'newPassword');
    togglePassword('toggleConfirmPassword', 'confirmPassword');
}

// Llama a la función cuando el DOM esté cargado
document.addEventListener('DOMContentLoaded', function() {
    setupPasswordToggles();
    
    // El resto de tu código existente...
    // Navegación suave
    document.querySelectorAll('.list-group-item').forEach(item => {
        item.addEventListener('click', function (e) {
            e.preventDefault();
            const target = this.getAttribute('href').substring(1);
            document.getElementById(target).scrollIntoView({
                behavior: 'smooth'
            });

            // Actualizar active class
            document.querySelectorAll('.list-group-item').forEach(i => i.classList.remove('active'));
            this.classList.add('active');
        });
    });

    // Actualizar información personal
    document.getElementById('profileForm').addEventListener('submit', async function (e) {
        e.preventDefault();

        const formData = {
            nombre: document.getElementById('nombre').value,
            apellido: document.getElementById('apellido').value,
            correo: document.getElementById('correo').value
        };

        try {
            const response = await axios.post('/api/user/profile/update', formData, {
                withCredentials: true
            });

            if (response.data.success) {
                Swal.fire({
                    icon: 'success',
                    title: '¡Perfecto!',
                    text: response.data.message,
                    timer: 2000
                });
            }
        } catch (error) {
            Swal.fire({
                icon: 'error',
                title: 'Error',
                text: error.response?.data?.detail || 'Error al actualizar perfil'
            });
        }
    });

    // Cambiar contraseña
    document.getElementById('passwordForm').addEventListener('submit', async function (e) {
        e.preventDefault();

        const newPassword = document.getElementById('newPassword').value;
        const confirmPassword = document.getElementById('confirmPassword').value;

        if (newPassword !== confirmPassword) {
            Swal.fire({
                icon: 'error',
                title: 'Error',
                text: 'Las contraseñas no coinciden'
            });
            return;
        }

        const formData = {
            current_password: document.getElementById('currentPassword').value,
            new_password: newPassword
        };

        try {
            const response = await axios.post('/api/user/profile/update', formData, {
                withCredentials: true
            });

            if (response.data.success) {
                Swal.fire({
                    icon: 'success',
                    title: '¡Contraseña actualizada!',
                    text: response.data.message,
                    timer: 2000
                });

                // Limpiar formulario
                document.getElementById('passwordForm').reset();
            }
        } catch (error) {
            Swal.fire({
                icon: 'error',
                title: 'Error',
                text: error.response?.data?.detail || 'Error al cambiar contraseña'
            });
        }
    });

    // Validación en tiempo real
    document.getElementById('newPassword').addEventListener('input', function () {
        const confirmPassword = document.getElementById('confirmPassword');
        if (this.value !== confirmPassword.value && confirmPassword.value !== '') {
            confirmPassword.setCustomValidity('Las contraseñas no coinciden');
        } else {
            confirmPassword.setCustomValidity('');
        }
    });

    document.getElementById('confirmPassword').addEventListener('input', function () {
        const newPassword = document.getElementById('newPassword');
        if (this.value !== newPassword.value) {
            this.setCustomValidity('Las contraseñas no coinciden');
        } else {
            this.setCustomValidity('');
        }
    });
});