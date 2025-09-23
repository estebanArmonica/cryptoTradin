// Verificar autenticación al cargar la página
document.addEventListener('DOMContentLoaded', function() {
    checkAuthentication();
    setupAuthHandlers();
});

// Configurar manejadores de autenticación
function setupAuthHandlers() {
    // Manejar cierre de sesión
    const logoutBtn = document.getElementById('logoutBtn');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', function(e) {
            e.preventDefault();
            logout();
        });
    }

    // Verificar sesión periódicamente
    setInterval(checkSession, 300000); // Cada 5 minutos
}

// Verificar si el usuario está autenticado
async function checkAuthentication() {
    try {
        const response = await fetch('/api/user/balance', {
            method: 'GET',
            credentials: 'include',
            headers: {
                'Accept': 'application/json'
            }
        });
        
        if (response.status === 401) {
            // No autenticado, redirigir al login
            handleAuthError();
            return false;
        }
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        // Usuario autenticado, continuar
        const data = await response.json();
        updateUserUI(data);
        return true;
        
    } catch (error) {
        console.error('Error checking authentication:', error);
        
        // Solo redirigir si es error de red o servidor
        if (error.name === 'TypeError' || error.message.includes('Failed to fetch')) {
            console.warn('Error de conexión, pero manteniendo sesión local');
            return true; // Mantener UI como si estuviera autenticado
        }
        
        handleAuthError();
        return false;
    }
}

// Verificar sesión sin redirección
async function checkSession() {
    try {
        const response = await fetch('/api/user/balance', {
            method: 'GET',
            credentials: 'include',
            headers: {
                'Accept': 'application/json'
            }
        });
        
        if (response.status === 401) {
            console.warn('Sesión expirada');
            showSessionExpiredWarning();
            return false;
        }
        
        return response.ok;
        
    } catch (error) {
        console.warn('Error verificando sesión:', error);
        return true; // Asumir que la sesión sigue activa en caso de error de red
    }
}

// Actualizar UI con información del usuario
function updateUserUI(userData) {
    // Actualizar balance en navbar si existe
    const balanceElement = document.getElementById('userBalance');
    if (balanceElement && userData.balance !== undefined) {
        balanceElement.textContent = `$${parseFloat(userData.balance).toFixed(2)}`;
    }

    // Actualizar nombre de usuario si existe
    const userMenu = document.getElementById('userMenu');
    if (userMenu) {
        const userNameElements = userMenu.querySelectorAll('.user-name');
        userNameElements.forEach(el => {
            if (userData.user_id) {
                el.textContent = `Usuario #${userData.user_id}`;
            }
        });
    }

    // Mostrar elementos protegidos
    const protectedElements = document.querySelectorAll('.protected-content');
    protectedElements.forEach(el => {
        el.style.display = 'block';
    });

    // Ocultar elementos de login
    const loginElements = document.querySelectorAll('.login-content');
    loginElements.forEach(el => {
        el.style.display = 'none';
    });
}

// Manejar errores de autenticación
function handleAuthError() {
    // Guardar la URL actual para redirigir después del login
    const currentPath = window.location.pathname;
    if (currentPath !== '/' && currentPath !== '/register') {
        sessionStorage.setItem('redirectAfterLogin', currentPath);
    }
    
    // Redirigir al login
    window.location.href = '/';
}

// Mostrar advertencia de sesión expirada
function showSessionExpiredWarning() {
    // Crear o mostrar modal de sesión expirada
    let expiredModal = document.getElementById('sessionExpiredModal');
    
    if (!expiredModal) {
        expiredModal = document.createElement('div');
        expiredModal.id = 'sessionExpiredModal';
        expiredModal.className = 'modal fade';
        expiredModal.innerHTML = `
            <div class="modal-dialog modal-dialog-centered">
                <div class="modal-content">
                    <div class="modal-header bg-warning">
                        <h5 class="modal-title">Sesión Expirada</h5>
                    </div>
                    <div class="modal-body">
                        <p>Tu sesión ha expirado por inactividad. Por favor inicia sesión nuevamente.</p>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-primary" onclick="logout()">
                            Ir al Login
                        </button>
                    </div>
                </div>
            </div>
        `;
        document.body.appendChild(expiredModal);
    }
    
    const modal = new bootstrap.Modal(expiredModal);
    modal.show();
}

// Logout function
async function logout() {
    try {
        showLoading('Cerrando sesión...');
        
        const response = await fetch('/api/logout', {
            method: 'POST',
            credentials: 'include',
            headers: {
                'Accept': 'application/json'
            }
        });
        
        if (response.ok) {
            // Limpiar cualquier dato local
            sessionStorage.clear();
            localStorage.removeItem('protonWallet');
            
            // Redirigir al login
            window.location.href = '/';
        } else {
            throw new Error('Error en el logout');
        }
        
    } catch (error) {
        console.error('Error during logout:', error);
        // Redirigir de todas formas
        window.location.href = '/';
    } finally {
        hideLoading();
    }
}

// Proteger rutas específicas
function protectRoute() {
    const protectedRoutes = ['/dashboard', '/wallet', '/trading', '/profile', '/simulacion'];
    const currentPath = window.location.pathname;
    
    if (protectedRoutes.includes(currentPath)) {
        checkAuthentication().then(isAuthenticated => {
            if (!isAuthenticated) {
                handleAuthError();
            }
        });
    }
}

// Interceptar requests para manejar errores de autenticación
function setupAuthInterceptor() {
    const originalFetch = window.fetch;
    
    window.fetch = async function(...args) {
        try {
            const response = await originalFetch(...args);
            
            if (response.status === 401) {
                // Sesión expirada
                showSessionExpiredWarning();
                throw new Error('Unauthorized');
            }
            
            return response;
        } catch (error) {
            if (error.message === 'Unauthorized') {
                // Ya manejado por el interceptor
                throw error;
            }
            throw error;
        }
    };
}

// Inicializar interceptor de autenticación
setupAuthInterceptor();

// Exportar funciones para uso global
window.checkAuthentication = checkAuthentication;
window.logout = logout;
window.protectRoute = protectRoute;