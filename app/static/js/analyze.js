/**
 * SafeTrace Analysis Module
 * Handles KYT transaction analysis
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
    }
}

/**
 * Set loading state for analyze button
 */
function setAnalyzeLoading(loading) {
    const btn = document.getElementById('analyze-btn');
    const text = document.getElementById('analyze-btn-text');
    const spinner = document.getElementById('analyze-spinner');
    
    if (loading) {
        btn.disabled = true;
        text.textContent = 'Analyzing...';
        spinner.classList.remove('hidden');
    } else {
        btn.disabled = false;
        text.textContent = 'Analyze Transaction';
        spinner.classList.add('hidden');
    }
}

/**
 * Display analysis results
 */
function displayResults(data) {
    const resultsSection = document.getElementById('results-section');
    const report = data.report;
    const riskScore = report.risk_score;
    
    // Risk Score
    const score = riskScore.score;
    const level = riskScore.level;
    
    // Update risk bar
    const riskBar = document.getElementById('risk-bar');
    riskBar.style.width = `${score}%`;
    riskBar.className = `absolute h-full transition-all duration-500 ${getRiskBgColor(score)}`;
    
    // Update risk badge
    const badge = document.getElementById('risk-level-badge');
    badge.textContent = level;
    badge.className = `px-3 py-1 rounded-full text-sm font-semibold ${getRiskBgColor(score)} text-white`;
    
    // Update score value
    document.getElementById('risk-score-value').textContent = `${score}/100`;
    document.getElementById('risk-score-value').className = `text-center text-3xl font-bold mt-4 ${getRiskColor(score)}`;
    
    // Risk reasons
    const reasonsList = document.getElementById('reasons-list');
    reasonsList.innerHTML = '';
    
    if (riskScore.reasons && riskScore.reasons.length > 0) {
        riskScore.reasons.forEach(reason => {
            const li = document.createElement('li');
            li.className = 'flex items-start space-x-2 text-gray-300';
            li.innerHTML = `
                <svg class="w-5 h-5 ${score > 50 ? 'text-yellow-400' : 'text-green-400'} flex-shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                    <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clip-rule="evenodd"/>
                </svg>
                <span>${reason}</span>
            `;
            reasonsList.appendChild(li);
        });
    }
    
    // Flagged entities
    const flaggedSection = document.getElementById('flagged-entities');
    const entitiesList = document.getElementById('entities-list');
    
    if (report.flagged_entities && report.flagged_entities.length > 0) {
        flaggedSection.classList.remove('hidden');
        entitiesList.innerHTML = '';
        
        report.flagged_entities.forEach(entity => {
            const div = document.createElement('div');
            div.className = 'bg-red-500/10 border border-red-500/30 rounded-lg p-3';
            div.innerHTML = `
                <p class="font-mono text-sm">${formatTxHash(entity.address || entity, 12)}</p>
                <p class="text-sm text-gray-400">${entity.type || entity.tag || 'Flagged'}</p>
            `;
            entitiesList.appendChild(div);
        });
    } else {
        flaggedSection.classList.add('hidden');
    }
    
    // Transaction details
    document.getElementById('result-tx-hash').textContent = report.tx_hash;
    document.getElementById('result-chain').textContent = getChainName(report.chain);
    document.getElementById('result-addresses').textContent = report.total_addresses_analyzed || 'N/A';
    document.getElementById('result-api-calls').textContent = report.api_calls_used || 'N/A';
    
    // PDF download
    if (data.pdf_url) {
        const pdfBtn = document.getElementById('download-pdf-btn');
        pdfBtn.href = data.pdf_url;
        pdfBtn.classList.remove('hidden');
    }
    
    // Show results
    resultsSection.classList.remove('hidden');
    resultsSection.scrollIntoView({ behavior: 'smooth' });
}

/**
 * Hide results section
 */
function hideResults() {
    document.getElementById('results-section').classList.add('hidden');
}

/**
 * Show analysis error
 */
function showAnalysisError(message) {
    const errorSection = document.getElementById('error-section');
    document.getElementById('error-message').textContent = message;
    errorSection.classList.remove('hidden');
    errorSection.scrollIntoView({ behavior: 'smooth' });
}

/**
 * Hide error section
 */
function hideError() {
    document.getElementById('error-section').classList.add('hidden');
}

/**
 * Start new analysis
 */
function newAnalysis() {
    currentAnalysis = null;
    document.getElementById('analyze-form').reset();
    document.getElementById('depth-value').textContent = '3';
    hideResults();
    hideError();
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

/**
 * Save analysis to local history
 */
function saveToHistory(data) {
    try {
        const history = JSON.parse(localStorage.getItem('safetrace_history') || '[]');
        
        const entry = {
            id: Date.now(),
            timestamp: new Date().toISOString(),
            tx_hash: data.report.tx_hash,
            chain: data.report.chain,
            risk_score: data.report.risk_score.score,
            risk_level: data.report.risk_score.level,
            pdf_url: data.pdf_url
        };
        
        // Add to beginning, keep last 50
        history.unshift(entry);
        if (history.length > 50) {
            history.pop();
        }
        
        localStorage.setItem('safetrace_history', JSON.stringify(history));
    } catch (e) {
        console.warn('Could not save to history:', e);
    }
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
