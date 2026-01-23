/**
 * SafeTrace Analysis Module
 * Enterprise-grade KYT transaction analysis with graph visualization
 */

let currentAnalysis = null;

/**
 * Handle analysis form submission
 */
async function handleAnalysis(event) {
    event.preventDefault();
    
    // Check if user is logged in
    if (!isLoggedIn()) {
        openAuthModal('login');
        showToast('Please login to run analysis', 'warning');
        return;
    }
    
    const txHash = document.getElementById('tx-hash').value.trim();
    const chain = document.getElementById('chain').value;
    const depth = parseInt(document.getElementById('depth').value);
    
    // Validate
    if (!txHash) {
        showToast('Please enter a transaction hash', 'error');
        return;
    }
    
    // Show loading state
    setAnalyzeLoading(true);
    showLoadingSection();
    hideResults();
    hideError();
    
    try {
        const response = await apiRequest('/api/v1/compliance/trace', {
            method: 'POST',
            body: JSON.stringify({
                tx_hash: txHash,
                chain: chain,
                depth: depth
            })
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.detail || data.message || 'Analysis failed');
        }
        
        if (data.success) {
            currentAnalysis = data;
            displayResults(data);
            
            // Save to history (localStorage for now, could be backend later)
            saveToHistory(data);
        } else {
            throw new Error(data.message || 'Analysis failed');
        }
        
    } catch (error) {
        showAnalysisError(error.message);
    } finally {
        setAnalyzeLoading(false);
        hideLoadingSection();
    }
}

/**
 * Set loading state for analyze button
 */
function setAnalyzeLoading(loading) {
    const btn = document.getElementById('analyze-btn');
    const text = document.getElementById('analyze-btn-text');
    const spinner = document.getElementById('analyze-spinner');
    const icon = document.getElementById('analyze-icon');
    
    if (loading) {
        btn.disabled = true;
        btn.classList.add('opacity-70');
        text.textContent = 'Analyzing...';
        spinner.classList.remove('hidden');
        if (icon) icon.classList.add('hidden');
    } else {
        btn.disabled = false;
        btn.classList.remove('opacity-70');
        text.textContent = 'Analyze Transaction';
        spinner.classList.add('hidden');
        if (icon) icon.classList.remove('hidden');
    }
}

/**
 * Show loading section
 */
function showLoadingSection() {
    const loadingSection = document.getElementById('loading-section');
    if (loadingSection) loadingSection.classList.remove('hidden');
}

/**
 * Hide loading section
 */
function hideLoadingSection() {
    const loadingSection = document.getElementById('loading-section');
    if (loadingSection) loadingSection.classList.add('hidden');
}

/**
 * Show analysis error
 */
function showAnalysisError(message) {
    const errorSection = document.getElementById('error-section');
    const errorMessage = document.getElementById('error-message');
    
    // Check if it's a "transaction not found" error
    if (message.includes('not found')) {
        errorMessage.innerHTML = `
            <p class="mb-2">${message}</p>
            <p class="text-sm mt-4">
                💡 <strong>Tip:</strong> Make sure you're using a real transaction hash from the selected blockchain.
            </p>
        `;
    } else {
        errorMessage.textContent = message;
    }
    
    errorSection.classList.remove('hidden');
    errorSection.scrollIntoView({ behavior: 'smooth' });
    hideResults();
}

/**
 * Hide error section
 */
function hideError() {
    const errorSection = document.getElementById('error-section');
    errorSection.classList.add('hidden');
}

/**
 * Hide results section
 */
function hideResults() {
    const resultsSection = document.getElementById('results-section');
    resultsSection.classList.add('hidden');
}

/**
 * Start new analysis
 */
function newAnalysis() {
    hideResults();
    hideError();
    document.getElementById('tx-hash').value = '';
    document.getElementById('tx-hash').focus();
}

/**
 * Save analysis to history (localStorage)
 */
function saveToHistory(data) {
    try {
        const history = JSON.parse(localStorage.getItem('safetrace_history') || '[]');
        history.unshift({
            ...data,
            timestamp: new Date().toISOString()
        });
        // Keep only last 10
        if (history.length > 10) history.pop();
        localStorage.setItem('safetrace_history', JSON.stringify(history));
    } catch (e) {
        console.error('Failed to save to history:', e);
    }
}

/**
 * Display analysis results with new forensic design
 */
function displayResults(data) {
    const resultsSection = document.getElementById('results-section');
    const report = data.report;
    const riskScore = report.risk_score;
    
    // Risk Score
    const score = riskScore.score;
    const level = riskScore.level;
    
    // Emit analysis complete event for investigation snapshot
    const analysisEvent = new CustomEvent('analysisComplete', {
        detail: {
            tx_hash: report.tx_hash,
            chain: report.chain,
            risk_score: score,
            risk_level: level,
            depth: report.depth || 1
        }
    });
    document.dispatchEvent(analysisEvent);
    
    // Update risk score display with animation
    const scoreDisplay = document.getElementById('risk-score-display');
    if (scoreDisplay) {
        animateNumber(scoreDisplay, 0, score, 1000);
    }
    
    // Update risk bar with gradient
    const riskBar = document.getElementById('risk-bar');
    if (riskBar) {
        riskBar.style.width = `${score}%`;
        riskBar.className = `h-full transition-all duration-1000 ${getRiskGradient(score)}`;
    }
    
    // Update risk badge with new classes
    const badge = document.getElementById('risk-level-badge');
    if (badge) {
        badge.textContent = level;
        badge.className = getRiskBadgeClass(score);
    }
    
    // Update transaction hash
    const txHashEl = document.getElementById('result-tx-hash');
    if (txHashEl) txHashEl.textContent = report.tx_hash;
    
    // Risk factors
    displayRiskFactors(riskScore.reasons || []);
    
    // Flagged entities
    displayFlaggedEntities(report.flagged_entities || []);
    
    // Stats
    const statAddresses = document.getElementById('stat-addresses');
    const statHops = document.getElementById('stat-hops');
    const statTransactions = document.getElementById('stat-transactions');
    const statApiCalls = document.getElementById('stat-api-calls');
    
    if (statAddresses) statAddresses.textContent = report.total_addresses_analyzed || 0;
    if (statHops) statHops.textContent = report.depth || 0;
    if (statTransactions) statTransactions.textContent = report.transactions_traced || 0;
    if (statApiCalls) statApiCalls.textContent = report.api_calls_used || 0;
    
    // PDF download
    if (data.pdf_url) {
        const pdfBtn = document.getElementById('download-pdf-btn');
        if (pdfBtn) pdfBtn.href = data.pdf_url;
    }
    
    // Generate and render graph
    const graphData = generateGraphFromResult(report);
    if (graphData && graphData.nodes.length > 0) {
        renderGraph(graphData);
    }
    
    // Show results
    resultsSection.classList.remove('hidden');
    resultsSection.scrollIntoView({ behavior: 'smooth' });
}

/**
 * Display risk factors with icons
 */
function displayRiskFactors(reasons) {
    const container = document.getElementById('risk-factors');
    if (!container) return;
    
    if (!reasons || reasons.length === 0) {
        container.innerHTML = `
            <div class="flex items-center gap-3 text-risk-safe bg-risk-safe/10 border border-risk-safe/20 rounded-lg p-3">
                <svg class="w-5 h-5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                    <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
                </svg>
                <span>No significant risk factors detected</span>
            </div>
        `;
        return;
    }
    
    container.innerHTML = reasons.map(reason => `
        <div class="flex items-start gap-3 bg-forensic-800 rounded-lg p-3">
            <svg class="w-5 h-5 text-risk-medium flex-shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clip-rule="evenodd"/>
            </svg>
            <span class="text-gray-300">${reason}</span>
        </div>
    `).join('');
}

/**
 * Display flagged entities
 */
function displayFlaggedEntities(entities) {
    const section = document.getElementById('flagged-entities-section');
    const container = document.getElementById('flagged-entities');
    
    if (!section || !container) return;
    
    if (!entities || entities.length === 0) {
        section.classList.add('hidden');
        return;
    }
    
    section.classList.remove('hidden');
    
    container.innerHTML = entities.map(entity => `
        <div class="flex items-center justify-between bg-risk-critical/10 border border-risk-critical/30 rounded-lg p-3">
            <div class="flex items-center gap-3">
                <div class="w-8 h-8 rounded-full bg-risk-critical/20 flex items-center justify-center">
                    <svg class="w-4 h-4 text-risk-critical" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/>
                    </svg>
                </div>
                <div>
                    <code class="font-mono text-sm text-white">${formatTxHash(entity.address || entity, 10)}</code>
                    <p class="text-xs text-gray-500">${entity.type || entity.tag || 'Flagged Entity'}</p>
                </div>
            </div>
            <span class="entity-badge-sanctioned">${entity.category || 'Sanctioned'}</span>
        </div>
    `).join('');
}

/**
 * Animate number counting
 */
function animateNumber(element, start, end, duration) {
    const startTime = performance.now();
    
    function update(currentTime) {
        const elapsed = currentTime - startTime;
        const progress = Math.min(elapsed / duration, 1);
        const current = Math.floor(start + (end - start) * easeOutQuad(progress));
        element.textContent = current;
        
        if (progress < 1) {
            requestAnimationFrame(update);
        }
    }
    
    requestAnimationFrame(update);
}

function easeOutQuad(t) {
    return t * (2 - t);
}

/**
 * Get risk gradient class based on score
 */
function getRiskGradient(score) {
    if (score >= 80) return 'bg-gradient-to-r from-risk-high to-risk-critical';
    if (score >= 60) return 'bg-gradient-to-r from-risk-medium to-risk-high';
    if (score >= 40) return 'bg-gradient-to-r from-risk-low to-risk-medium';
    if (score >= 20) return 'bg-gradient-to-r from-risk-safe to-risk-low';
    return 'bg-gradient-to-r from-risk-safe to-risk-safe';
}

/**
 * Get risk badge class based on score
 */
function getRiskBadgeClass(score) {
    if (score >= 80) return 'risk-badge-critical text-lg px-4 py-2';
    if (score >= 60) return 'risk-badge-high text-lg px-4 py-2';
    if (score >= 40) return 'risk-badge-medium text-lg px-4 py-2';
    if (score >= 20) return 'risk-badge-low text-lg px-4 py-2';
    return 'risk-badge-safe text-lg px-4 py-2';
}

/**
 * Get analysis history
 */
function getHistory() {
    try {
        return JSON.parse(localStorage.getItem('safetrace_history') || '[]');
    } catch (e) {
        return [];
    }
}

// Check auth state on page load
document.addEventListener('DOMContentLoaded', () => {
    const authNotice = document.getElementById('auth-notice');
    const freeNotice = document.getElementById('free-notice');
    
    if (isLoggedIn()) {
        if (authNotice) authNotice.classList.add('hidden');
        if (freeNotice) freeNotice.classList.add('hidden');
    } else {
        if (authNotice) authNotice.classList.remove('hidden');
    }
});
