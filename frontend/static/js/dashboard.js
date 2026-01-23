/**
 * SafeTrace Dashboard Module
 * Enterprise-grade dashboard with forensic analytics
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
    
    // Hide loading state
    const loadingEl = document.getElementById('history-loading');
    if (loadingEl) loadingEl.style.display = 'none';
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
    const createdEl = document.getElementById('user-created');
    
    if (nameEl) nameEl.textContent = user.full_name || user.email.split('@')[0];
    if (emailEl) emailEl.textContent = user.email;
    
    const isPremium = user.is_premium || false;
    
    if (planEl) {
        planEl.innerHTML = isPremium 
            ? '<span class="inline-block px-2 py-1 bg-accent rounded text-sm font-medium">Pro</span>'
            : '<span class="inline-block px-2 py-1 bg-forensic-700 rounded text-sm">Free</span>';
    }
    
    if (accountTypeEl) {
        accountTypeEl.textContent = isPremium ? 'Pro' : 'Free';
    }
    
    if (upgradeLink) {
        upgradeLink.style.display = isPremium ? 'none' : 'inline';
    }
    
    if (createdEl && user.created_at) {
        const date = new Date(user.created_at);
        createdEl.textContent = date.toLocaleDateString('en-US', { month: 'long', year: 'numeric' });
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
    renderHistory(localHistory.slice(0, 8));
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
 * Get risk badge class based on score
 */
function getRiskBadgeClass(score) {
    if (score >= 80) return 'risk-badge-critical';
    if (score >= 60) return 'risk-badge-high';
    if (score >= 40) return 'risk-badge-medium';
    if (score >= 20) return 'risk-badge-low';
    return 'risk-badge-safe';
}

/**
 * Render history in the UI with new forensic styling
 */
function renderHistory(history) {
    const loadingEl = document.getElementById('history-loading');
    const noHistoryMsg = document.getElementById('no-history-message');
    const itemsContainer = document.getElementById('history-items');
    
    if (loadingEl) loadingEl.style.display = 'none';
    
    if (!history || history.length === 0) {
        if (noHistoryMsg) noHistoryMsg.classList.remove('hidden');
        return;
    }
    
    if (noHistoryMsg) noHistoryMsg.classList.add('hidden');
    
    if (itemsContainer) {
        itemsContainer.innerHTML = history.map(item => `
            <div class="glass-card rounded-lg p-4 hover:border-accent/30 transition-all cursor-pointer group" 
                 onclick="viewAnalysis('${escapeHtml(item.tx_hash)}', '${item.chain}')">
                <div class="flex items-center justify-between mb-3">
                    <div class="flex items-center gap-3">
                        <div class="w-8 h-8 rounded-lg ${getChainBgColor(item.chain)} flex items-center justify-center">
                            <span class="text-xs font-bold">${getChainShortName(item.chain)}</span>
                        </div>
                        <div>
                            <code class="text-sm font-mono text-white group-hover:text-accent transition">${formatTxHash(item.tx_hash)}</code>
                            <p class="text-xs text-gray-500">${getChainName(item.chain)}</p>
                        </div>
                    </div>
                    <span class="${getRiskBadgeClass(item.risk_score)}">
                        ${item.risk_level || getRiskLabel(item.risk_score)}
                    </span>
                </div>
                <div class="flex items-center justify-between text-sm">
                    <span class="text-gray-500">${formatDateTime(item.timestamp)}</span>
                    <div class="flex items-center gap-2 opacity-0 group-hover:opacity-100 transition">
                        ${item.pdf_url ? `
                            <a href="${item.pdf_url}" target="_blank" 
                               class="text-xs text-accent hover:underline"
                               onclick="event.stopPropagation()">
                                PDF Report
                            </a>
                        ` : ''}
                        <span class="text-xs text-gray-400">View →</span>
                    </div>
                </div>
            </div>
        `).join('');
    }
}

/**
 * Get chain background color
 */
function getChainBgColor(chain) {
    const colors = {
        'bitcoin': 'bg-orange-500/20',
        'ethereum': 'bg-purple-500/20',
        'bsc': 'bg-yellow-500/20',
        'polygon': 'bg-purple-500/20',
        'arbitrum': 'bg-blue-500/20',
        'optimism': 'bg-red-500/20',
        'avalanche': 'bg-red-500/20',
        'fantom': 'bg-blue-500/20',
        'base': 'bg-blue-500/20'
    };
    return colors[chain?.toLowerCase()] || 'bg-gray-500/20';
}

/**
 * Get chain short name
 */
function getChainShortName(chain) {
    const names = {
        'bitcoin': 'BTC',
        'ethereum': 'ETH',
        'bsc': 'BSC',
        'polygon': 'POL',
        'arbitrum': 'ARB',
        'optimism': 'OP',
        'avalanche': 'AVAX',
        'fantom': 'FTM',
        'base': 'BASE',
        'litecoin': 'LTC',
        'dogecoin': 'DOGE'
    };
    return names[chain?.toLowerCase()] || chain?.substring(0, 3).toUpperCase() || '???';
}

/**
 * View analysis details
 */
function viewAnalysis(txHash, chain) {
    window.location.href = `/analyze?tx=${encodeURIComponent(txHash)}&chain=${chain}`;
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
