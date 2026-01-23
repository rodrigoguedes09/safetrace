/**
 * SafeTrace Authentication Module
 * Handles user login, registration, and session management
 */

const API_BASE = '';

// Session storage keys
const STORAGE_KEYS = {
    API_KEY: 'safetrace_api_key',
    USER: 'safetrace_user',
    TOKEN: 'safetrace_token'
};

/**
 * Check if user is logged in
 */
function isLoggedIn() {
    return localStorage.getItem(STORAGE_KEYS.API_KEY) !== null;
}

/**
 * Get current user data
 */
function getCurrentUser() {
    const userData = localStorage.getItem(STORAGE_KEYS.USER);
    return userData ? JSON.parse(userData) : null;
}

/**
 * Get API key
 */
function getApiKey() {
    return localStorage.getItem(STORAGE_KEYS.API_KEY);
}

/**
 * Save session data
 */
function saveSession(user, apiKey) {
    localStorage.setItem(STORAGE_KEYS.USER, JSON.stringify(user));
    localStorage.setItem(STORAGE_KEYS.API_KEY, apiKey);
}

/**
 * Clear session data
 */
function clearSession() {
    localStorage.removeItem(STORAGE_KEYS.USER);
    localStorage.removeItem(STORAGE_KEYS.API_KEY);
    localStorage.removeItem(STORAGE_KEYS.TOKEN);
}

/**
 * Update navigation based on login state
 */
function updateNavigation() {
    const loginBtn = document.getElementById('nav-login-btn');
    const ctaBtn = document.getElementById('nav-cta-btn');
    const userMenu = document.getElementById('nav-user-menu');
    const mobileAuthSection = document.getElementById('mobile-auth-section');
    const mobileUserSection = document.getElementById('mobile-user-section');
    
    if (isLoggedIn()) {
        // User is logged in - hide login button, show user menu
        if (loginBtn) loginBtn.classList.add('hidden');
        if (ctaBtn) {
            ctaBtn.textContent = 'Dashboard';
            ctaBtn.href = '/dashboard';
        }
        if (userMenu) {
            userMenu.classList.remove('hidden');
            userMenu.classList.add('flex');
        }
        // Mobile menu
        if (mobileAuthSection) mobileAuthSection.classList.add('hidden');
        if (mobileUserSection) mobileUserSection.classList.remove('hidden');
    } else {
        // User is not logged in - show login button, hide user menu
        if (loginBtn) loginBtn.classList.remove('hidden');
        if (ctaBtn) {
            ctaBtn.textContent = 'Start Analysis';
            ctaBtn.href = '/analyze';
        }
        if (userMenu) {
            userMenu.classList.add('hidden');
            userMenu.classList.remove('flex');
        }
        // Mobile menu
        if (mobileAuthSection) mobileAuthSection.classList.remove('hidden');
        if (mobileUserSection) mobileUserSection.classList.add('hidden');
    }
}

/**
 * Open authentication modal
 */
function openAuthModal(mode = 'login') {
    const modal = document.getElementById('auth-modal');
    const loginForm = document.getElementById('login-form');
    const registerForm = document.getElementById('register-form');
    
    modal.classList.remove('hidden');
    document.body.style.overflow = 'hidden';
    
    if (mode === 'login') {
        loginForm.classList.remove('hidden');
        registerForm.classList.add('hidden');
    } else {
        loginForm.classList.add('hidden');
        registerForm.classList.remove('hidden');
    }
    
    // Clear any previous errors
    hideError('login-error');
    hideError('register-error');
}

/**
 * Close authentication modal
 */
function closeAuthModal() {
    const modal = document.getElementById('auth-modal');
    modal.classList.add('hidden');
    document.body.style.overflow = '';
}

/**
 * Switch to register form
 */
function switchToRegister() {
    document.getElementById('login-form').classList.add('hidden');
    document.getElementById('register-form').classList.remove('hidden');
    hideError('login-error');
}

/**
 * Switch to login form
 */
function switchToLogin() {
    document.getElementById('register-form').classList.add('hidden');
    document.getElementById('login-form').classList.remove('hidden');
    hideError('register-error');
}

/**
 * Handle login form submission
 */
async function handleLogin(event) {
    event.preventDefault();
    
    const email = document.getElementById('login-email').value.trim();
    const password = document.getElementById('login-password').value;
    
    // Basic validation
    if (!email || !password) {
        showError('login-error', 'Please enter both email and password');
        return;
    }
    
    if (!email.includes('@')) {
        showError('login-error', 'Please enter a valid email address');
        return;
    }
    
    try {
        // First, we need to get an API key using email/password
        // Using the bootstrap endpoint
        const response = await fetch(`${API_BASE}/auth/bootstrap?email=${encodeURIComponent(email)}&password=${encodeURIComponent(password)}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                name: 'Web Session',
                description: 'Created via web login'
            })
        });
        
        if (!response.ok) {
            const error = await response.json();
            let errorMessage = 'Login failed';
            
            if (typeof error.detail === 'string') {
                errorMessage = error.detail;
            } else if (error.detail && typeof error.detail === 'object') {
                if (Array.isArray(error.detail)) {
                    errorMessage = error.detail.map(e => e.msg || e.message || e).join(', ');
                } else {
                    errorMessage = error.detail.message || JSON.stringify(error.detail);
                }
            } else if (error.message) {
                errorMessage = error.message;
            }
            
            throw new Error(errorMessage);
        }
        
        const data = await response.json();
        
        // Create user object from response
        const user = {
            id: data.user_id,
            email: email,
            is_premium: false // Will be updated when we fetch user details
        };
        
        // Save session
        saveSession(user, data.key);
        
        // Close modal and update UI
        closeAuthModal();
        updateNavigation();
        showToast('Login successful!', 'success');
        
        // Redirect to dashboard if on login page
        if (window.location.pathname === '/' || window.location.pathname === '/login') {
            window.location.href = '/dashboard';
        } else {
            // Reload current page to update auth state
            window.location.reload();
        }
        
    } catch (error) {
        showError('login-error', error.message);
    }
}

/**
 * Handle registration form submission
 */
async function handleRegister(event) {
    event.preventDefault();
    
    const fullName = document.getElementById('register-name').value.trim();
    const email = document.getElementById('register-email').value.trim();
    const password = document.getElementById('register-password').value;
    
    // Basic validation
    if (!fullName || fullName.length < 2) {
        showError('register-error', 'Full name must be at least 2 characters');
        return;
    }
    
    if (!email || !email.includes('@')) {
        showError('register-error', 'Please enter a valid email address');
        return;
    }
    
    if (!password || password.length < 8) {
        showError('register-error', 'Password must be at least 8 characters');
        return;
    }
    
    // Check password strength
    if (!/[A-Z]/.test(password)) {
        showError('register-error', 'Password must contain at least one uppercase letter');
        return;
    }
    
    if (!/[a-z]/.test(password)) {
        showError('register-error', 'Password must contain at least one lowercase letter');
        return;
    }
    
    if (!/[0-9]/.test(password)) {
        showError('register-error', 'Password must contain at least one digit');
        return;
    }
    
    // Check password byte length (bcrypt limit)
    if (new Blob([password]).size > 72) {
        showError('register-error', 'Password is too long (max 72 bytes)');
        return;
    }
    
    try {
        // Register user
        const registerResponse = await fetch(`${API_BASE}/auth/register`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                email: email,
                full_name: fullName,
                password: password
            })
        });
        
        if (!registerResponse.ok) {
            const error = await registerResponse.json();
            let errorMessage = 'Registration failed';
            
            if (typeof error.detail === 'string') {
                errorMessage = error.detail;
            } else if (error.detail && typeof error.detail === 'object') {
                if (Array.isArray(error.detail)) {
                    errorMessage = error.detail.map(e => e.msg || e.message || e).join(', ');
                } else {
                    errorMessage = error.detail.message || JSON.stringify(error.detail);
                }
            } else if (error.message) {
                errorMessage = error.message;
            }
            
            throw new Error(errorMessage);
        }
        
        const userData = await registerResponse.json();
        
        // Show success and switch to login
        showSuccess('register-success', 'Account created! Now logging you in...');
        
        // Auto-login by getting an API key
        setTimeout(async () => {
            try {
                const loginResponse = await fetch(`${API_BASE}/auth/bootstrap?email=${encodeURIComponent(email)}&password=${encodeURIComponent(password)}`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        name: 'Web Session',
                        description: 'Created during registration'
                    })
                });
                
                if (loginResponse.ok) {
                    const keyData = await loginResponse.json();
                    
                    const user = {
                        id: userData.id,
                        email: userData.email,
                        full_name: userData.full_name,
                        is_premium: userData.is_premium
                    };
                    
                    saveSession(user, keyData.key);
                    closeAuthModal();
                    updateNavigation();
                    showToast('Welcome to SafeTrace!', 'success');
                    
                    // Redirect to dashboard
                    window.location.href = '/dashboard';
                }
            } catch (e) {
                // If auto-login fails, just show success and let user login manually
                showSuccess('register-success', 'Account created! Please login.');
                setTimeout(switchToLogin, 1500);
            }
        }, 1000);
        
    } catch (error) {
        showError('register-error', error.message);
    }
}

/**
 * Logout user
 */
function logout() {
    clearSession();
    updateNavigation();
    showToast('Logged out successfully', 'info');
    window.location.href = '/';
}

/**
 * Show error message
 */
function showError(elementId, message) {
    const el = document.getElementById(elementId);
    if (el) {
        el.textContent = message;
        el.classList.remove('hidden');
    }
}

/**
 * Hide error message
 */
function hideError(elementId) {
    const el = document.getElementById(elementId);
    if (el) {
        el.classList.add('hidden');
    }
}

/**
 * Show success message
 */
function showSuccess(elementId, message) {
    const el = document.getElementById(elementId);
    if (el) {
        el.textContent = message;
        el.classList.remove('hidden');
    }
}

/**
 * Show toast notification
 */
function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    if (!container) return;
    
    const colors = {
        success: 'bg-green-500',
        error: 'bg-red-500',
        info: 'bg-primary-500',
        warning: 'bg-yellow-500'
    };
    
    const toast = document.createElement('div');
    toast.className = `${colors[type]} text-white px-6 py-3 rounded-lg shadow-lg animate-slide-up`;
    toast.textContent = message;
    
    container.appendChild(toast);
    
    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transition = 'opacity 0.3s';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

/**
 * Protected page check
 */
function requireAuth() {
    if (!isLoggedIn()) {
        openAuthModal('login');
        return false;
    }
    return true;
}

/**
 * Make authenticated API request
 */
async function apiRequest(url, options = {}) {
    const apiKey = getApiKey();
    
    const headers = {
        'Content-Type': 'application/json',
        ...options.headers
    };
    
    if (apiKey) {
        headers['X-API-Key'] = apiKey;
    }
    
    const response = await fetch(`${API_BASE}${url}`, {
        ...options,
        headers
    });
    
    // Handle 401 - session expired
    if (response.status === 401) {
        clearSession();
        updateNavigation();
        showToast('Session expired. Please login again.', 'warning');
        openAuthModal('login');
        throw new Error('Session expired');
    }
    
    return response;
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    updateNavigation();
});
