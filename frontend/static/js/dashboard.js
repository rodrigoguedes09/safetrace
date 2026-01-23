/**
 * SafeTrace Dashboard Module
 * Handles dashboard functionality and analysis history
 */

let dashboardData = {
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
    await loadHistory();
    updateUsageFromHistory();
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
    
    const isPremium = user.is_premium || false;
    
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
 * Load analysis history from localStorage
 */
async function loadHistory() {
    const localHistory = getHistory();
    dashboardData.history = localHistory;
    renderHistory(localHistory.slice(0, 10));
}

/**
 * Update usage stats from local history
 */
function updateUsageFromHistory() {
    const history = getHistory();
    const today = new Date().toDateString();
    
    const todayCount = history.filter(h => 
        new Date(h.timestamp).toDateString() === today
    ).length;
    
    const highRiskCount = history.filter(h => h.risk_score >= 67).length;
    
    updateUsageStats({
        requests_today: todayCount,
        total_requests: history.length,
        high_risk_count: highRiskCount
    });
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
 * Escape HTML to prevent XSS
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Initialize dashboard on page load
document.addEventListener('DOMContentLoaded', initDashboard);
