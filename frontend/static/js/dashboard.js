/**
 * SafeTrace Dashboard Module
 * Handles dashboard functionality, API keys, and history
 */

let dashboardData = {
    apiKeys: [],
    history: [],
    usage: {
        today: 0,
        limit: 100,
        total: 0,
        highRisk: 0
    }
};

/**
 * Initialize dashboard
 */
async function initDashboard() {
    // Check if logged in
    if (!isLoggedIn()) {
        window.location.href = '/';
        return;
    }
    
    const user = getCurrentUser();
    
    // Update user info in UI
    updateUserInfo(user);
    
    // Load data
    await Promise.all([
        loadApiKeys(),
        loadUsageStats(),
        loadHistory()
    ]);
}

/**
 * Update user information in UI
 */
function updateUserInfo(user) {
    if (!user) return;
    
    const nameEl = document.getElementById('user-name');
    const emailEl = document.getElementById('user-email');
    const planEl = document.getElementById('user-plan');
    const accountTypeEl = document.getElementById('stat-account-type');
    const upgradeLink = document.getElementById('upgrade-link');
    
    if (nameEl) nameEl.textContent = user.full_name || user.email.split('@')[0];
    if (emailEl) emailEl.textContent = user.email;
    
    const isPremium = user.is_premium;
    
    if (planEl) {
        planEl.innerHTML = isPremium 
            ? '<span class="inline-block px-2 py-1 bg-primary-500 rounded text-sm">Premium</span>'
            : '<span class="inline-block px-2 py-1 bg-gray-700 rounded text-sm">Free</span>';
    }
    
    if (accountTypeEl) {
        accountTypeEl.textContent = isPremium ? 'Premium' : 'Free';
    }
    
    if (upgradeLink) {
        upgradeLink.style.display = isPremium ? 'none' : 'inline';
    }
    
    // Update limit based on plan
    const limitEl = document.getElementById('stat-limit');
    if (limitEl) {
        limitEl.textContent = isPremium ? '1000' : '100';
        dashboardData.usage.limit = isPremium ? 1000 : 100;
    }
}

/**
 * Load API keys from server
 */
async function loadApiKeys() {
    try {
        const response = await apiRequest('/auth/api-keys');
        
        if (response.ok) {
            const keys = await response.json();
            dashboardData.apiKeys = keys;
            renderApiKeys(keys);
        }
    } catch (e) {
        console.warn('Could not load API keys:', e);
    }
}

/**
 * Render API keys in the UI
 */
function renderApiKeys(keys) {
    const container = document.getElementById('api-keys-list');
    const noKeysMsg = document.getElementById('no-keys-message');
    
    if (!keys || keys.length === 0) {
        if (noKeysMsg) noKeysMsg.style.display = 'block';
        return;
    }
    
    if (noKeysMsg) noKeysMsg.style.display = 'none';
    
    container.innerHTML = keys.map(key => `
        <div class="bg-dark-800 rounded-lg p-4 flex items-center justify-between">
            <div class="flex-1">
                <div class="flex items-center space-x-3">
                    <span class="font-semibold">${escapeHtml(key.name)}</span>
                    ${key.is_active 
                        ? '<span class="px-2 py-0.5 bg-green-500/20 text-green-400 text-xs rounded">Active</span>'
                        : '<span class="px-2 py-0.5 bg-red-500/20 text-red-400 text-xs rounded">Inactive</span>'}
                </div>
                <p class="text-sm text-gray-400 mt-1">
                    <code class="bg-dark-900 px-2 py-0.5 rounded">${key.key_prefix}...</code>
                    ${key.description ? ` • ${escapeHtml(key.description)}` : ''}
                </p>
                <p class="text-xs text-gray-500 mt-1">
                    Created ${formatDate(key.created_at)}
                    ${key.last_used_at ? ` • Last used ${formatDate(key.last_used_at)}` : ''}
                </p>
            </div>
            <div class="flex items-center space-x-2">
                ${key.is_active ? `
                    <button onclick="revokeApiKey('${key.id}')" 
                        class="p-2 text-red-400 hover:bg-red-500/10 rounded transition" 
                        title="Revoke key">
                        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/>
                        </svg>
                    </button>
                ` : ''}
            </div>
        </div>
    `).join('');
}

/**
 * Load usage statistics
 */
async function loadUsageStats() {
    try {
        const response = await apiRequest('/auth/usage');
        
        if (response.ok) {
            const usage = await response.json();
            updateUsageStats(usage);
        }
    } catch (e) {
        // Fall back to history-based stats
        updateUsageFromHistory();
    }
}

/**
 * Update usage stats in UI
 */
function updateUsageStats(usage) {
    const requestsTodayEl = document.getElementById('stat-requests-today');
    const usageBarEl = document.getElementById('usage-bar');
    const totalEl = document.getElementById('stat-total-analyses');
    const highRiskEl = document.getElementById('stat-high-risk');
    
    if (requestsTodayEl) requestsTodayEl.textContent = usage.requests_today || 0;
    if (usageBarEl) {
        const percentage = Math.min((usage.requests_today / dashboardData.usage.limit) * 100, 100);
        usageBarEl.style.width = `${percentage}%`;
    }
    if (totalEl) totalEl.textContent = usage.total_requests || 0;
    if (highRiskEl) highRiskEl.textContent = usage.high_risk_count || 0;
}

/**
 * Update usage from local history (fallback)
 */
function updateUsageFromHistory() {
    const history = getHistory();
    const today = new Date().toDateString();
    
    const todayCount = history.filter(h => 
        new Date(h.timestamp).toDateString() === today
    ).length;
    
    const highRiskCount = history.filter(h => h.risk_score > 50).length;
    
    updateUsageStats({
        requests_today: todayCount,
        total_requests: history.length,
        high_risk_count: highRiskCount
    });
}

/**
 * Load analysis history
 */
async function loadHistory() {
    // First try server
    try {
        const response = await apiRequest('/auth/history');
        if (response.ok) {
            const history = await response.json();
            dashboardData.history = history;
            renderHistory(history.slice(0, 5));
            return;
        }
    } catch (e) {
        // Fall back to local storage
    }
    
    // Use local storage
    const localHistory = getHistory();
    dashboardData.history = localHistory;
    renderHistory(localHistory.slice(0, 5));
}

/**
 * Render history in the UI
 */
function renderHistory(history) {
    const container = document.getElementById('history-list');
    const noHistoryMsg = document.getElementById('no-history-message');
    
    if (!history || history.length === 0) {
        if (noHistoryMsg) noHistoryMsg.style.display = 'block';
        return;
    }
    
    if (noHistoryMsg) noHistoryMsg.style.display = 'none';
    
    container.innerHTML = history.map(item => `
        <div class="bg-dark-800 rounded-lg p-4">
            <div class="flex items-center justify-between mb-2">
                <code class="text-sm font-mono">${formatTxHash(item.tx_hash)}</code>
                <span class="px-2 py-0.5 rounded text-xs font-semibold ${getRiskBgColor(item.risk_score)} text-white">
                    ${item.risk_level || getRiskLabel(item.risk_score)}
                </span>
            </div>
            <div class="flex items-center justify-between text-sm text-gray-400">
                <span>${getChainName(item.chain)}</span>
                <span>${formatDateTime(item.timestamp)}</span>
            </div>
            ${item.pdf_url ? `
                <a href="${item.pdf_url}" target="_blank" 
                    class="inline-block mt-2 text-xs text-primary-400 hover:underline">
                    Download PDF
                </a>
            ` : ''}
        </div>
    `).join('');
}

/**
 * Open create API key modal
 */
function createApiKey() {
    document.getElementById('create-key-modal').classList.remove('hidden');
    document.body.style.overflow = 'hidden';
}

/**
 * Close create API key modal
 */
function closeKeyModal() {
    document.getElementById('create-key-modal').classList.add('hidden');
    document.body.style.overflow = '';
    document.getElementById('create-key-form').reset();
    hideError('create-key-error');
}

/**
 * Handle create API key form
 */
async function handleCreateKey(event) {
    event.preventDefault();
    
    const name = document.getElementById('key-name').value.trim();
    const description = document.getElementById('key-description').value.trim();
    
    try {
        const response = await apiRequest('/auth/api-keys', {
            method: 'POST',
            body: JSON.stringify({
                name: name,
                description: description || null
            })
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to create API key');
        }
        
        const data = await response.json();
        
        // Close create modal
        closeKeyModal();
        
        // Show new key modal
        showNewKey(data.key);
        
        // Reload keys
        await loadApiKeys();
        
    } catch (error) {
        showError('create-key-error', error.message);
    }
}

/**
 * Show new API key modal
 */
function showNewKey(key) {
    document.getElementById('new-key-value').textContent = key;
    document.getElementById('new-key-modal').classList.remove('hidden');
    document.body.style.overflow = 'hidden';
}

/**
 * Close new key modal
 */
function closeNewKeyModal() {
    document.getElementById('new-key-modal').classList.add('hidden');
    document.body.style.overflow = '';
}

/**
 * Copy API key to clipboard
 */
function copyApiKey() {
    const key = document.getElementById('new-key-value').textContent;
    copyToClipboard(key);
}

/**
 * Revoke API key
 */
async function revokeApiKey(keyId) {
    if (!confirm('Are you sure you want to revoke this API key? This action cannot be undone.')) {
        return;
    }
    
    try {
        const response = await apiRequest(`/auth/api-keys/${keyId}`, {
            method: 'DELETE'
        });
        
        if (response.ok) {
            showToast('API key revoked', 'success');
            await loadApiKeys();
        } else {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to revoke key');
        }
    } catch (error) {
        showToast(error.message, 'error');
    }
}

/**
 * Escape HTML to prevent XSS
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Initialize dashboard on page load
document.addEventListener('DOMContentLoaded', initDashboard);
