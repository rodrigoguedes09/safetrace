/**
 * SafeTrace Core Application Module
 */

// Global app state
const AppState = {
    initialized: false,
    user: null
};

/**
 * Initialize application
 */
function initApp() {
    if (AppState.initialized) return;
    
    // Check auth state
    AppState.user = getCurrentUser();
    
    // Update UI based on auth
    updateNavigation();
    
    AppState.initialized = true;
}

/**
 * Format date for display
 */
function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
    });
}

/**
 * Format date with time
 */
function formatDateTime(dateString) {
    const date = new Date(dateString);
    return date.toLocaleString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

/**
 * Truncate text with ellipsis
 */
function truncate(text, length = 20) {
    if (!text) return '';
    if (text.length <= length) return text;
    return text.substring(0, length) + '...';
}

/**
 * Format transaction hash for display
 */
function formatTxHash(hash, chars = 8) {
    if (!hash) return '';
    if (hash.length <= chars * 2 + 3) return hash;
    return hash.substring(0, chars) + '...' + hash.substring(hash.length - chars);
}

/**
 * Copy text to clipboard
 */
async function copyToClipboard(text) {
    try {
        await navigator.clipboard.writeText(text);
        showToast('Copied to clipboard!', 'success');
    } catch (err) {
        // Fallback for older browsers
        const textArea = document.createElement('textarea');
        textArea.value = text;
        document.body.appendChild(textArea);
        textArea.select();
        document.execCommand('copy');
        document.body.removeChild(textArea);
        showToast('Copied to clipboard!', 'success');
    }
}

/**
 * Get risk level color class
 */
function getRiskColor(score) {
    if (score <= 25) return 'text-green-400';
    if (score <= 50) return 'text-yellow-400';
    if (score <= 75) return 'text-orange-400';
    return 'text-red-400';
}

/**
 * Get risk level background color
 */
function getRiskBgColor(score) {
    if (score <= 25) return 'bg-green-500';
    if (score <= 50) return 'bg-yellow-500';
    if (score <= 75) return 'bg-orange-500';
    return 'bg-red-500';
}

/**
 * Get risk level label
 */
function getRiskLabel(score) {
    if (score <= 25) return 'LOW';
    if (score <= 50) return 'MEDIUM';
    if (score <= 75) return 'HIGH';
    return 'CRITICAL';
}

/**
 * Chain display names
 */
const CHAIN_NAMES = {
    'ethereum': 'Ethereum',
    'bitcoin': 'Bitcoin',
    'binance-smart-chain': 'BNB Chain',
    'polygon': 'Polygon',
    'arbitrum': 'Arbitrum',
    'optimism': 'Optimism',
    'base': 'Base',
    'avalanche': 'Avalanche',
    'fantom': 'Fantom',
    'gnosis': 'Gnosis',
    'bitcoin-cash': 'Bitcoin Cash',
    'litecoin': 'Litecoin',
    'dogecoin': 'Dogecoin',
    'dash': 'Dash',
    'zcash': 'Zcash'
};

/**
 * Get chain display name
 */
function getChainName(chain) {
    return CHAIN_NAMES[chain] || chain.charAt(0).toUpperCase() + chain.slice(1).replace(/-/g, ' ');
}

/**
 * Debounce function
 */
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

/**
 * Loading state helpers
 */
function setLoading(buttonId, loading) {
    const btn = document.getElementById(buttonId);
    if (!btn) return;
    
    const text = btn.querySelector('[id$="-text"]') || btn;
    const spinner = btn.querySelector('[id$="-spinner"]');
    
    if (loading) {
        btn.disabled = true;
        btn.classList.add('opacity-75', 'cursor-not-allowed');
        if (spinner) spinner.classList.remove('hidden');
        if (text && text.id) text.textContent = 'Loading...';
    } else {
        btn.disabled = false;
        btn.classList.remove('opacity-75', 'cursor-not-allowed');
        if (spinner) spinner.classList.add('hidden');
    }
}

/**
 * Toggle user dropdown menu
 */
function toggleUserDropdown() {
    const dropdown = document.getElementById('user-dropdown');
    if (dropdown) {
        dropdown.classList.toggle('hidden');
    }
}

/**
 * Close dropdown when clicking outside
 */
document.addEventListener('click', function(event) {
    const dropdown = document.getElementById('user-dropdown');
    const userMenu = document.getElementById('nav-user-menu');
    
    if (dropdown && userMenu && !userMenu.contains(event.target)) {
        dropdown.classList.add('hidden');
    }
});

// Initialize on load
document.addEventListener('DOMContentLoaded', initApp);
