/**
 * SafeTrace Investigation Snapshot Module
 * Handles investigation breadcrumb trail, session persistence, and PDF export enhancements
 */

const InvestigationSnapshot = (function() {
    'use strict';

    const STORAGE_KEY = 'safetrace_investigation_trail';
    const MAX_TRAIL_LENGTH = 50;

    // Investigation trail data structure
    let trail = [];
    let currentIndex = -1;

    /**
     * Initialize the investigation snapshot module
     */
    function init() {
        loadTrail();
        renderBreadcrumb();
        setupEventListeners();
    }

    /**
     * Load investigation trail from localStorage
     */
    function loadTrail() {
        try {
            const stored = localStorage.getItem(STORAGE_KEY);
            if (stored) {
                const data = JSON.parse(stored);
                trail = data.trail || [];
                currentIndex = data.currentIndex >= 0 ? data.currentIndex : trail.length - 1;
            }
        } catch (e) {
            console.error('Error loading investigation trail:', e);
            trail = [];
            currentIndex = -1;
        }
    }

    /**
     * Save investigation trail to localStorage
     */
    function saveTrail() {
        try {
            localStorage.setItem(STORAGE_KEY, JSON.stringify({
                trail: trail,
                currentIndex: currentIndex
            }));
        } catch (e) {
            console.error('Error saving investigation trail:', e);
        }
    }

    /**
     * Add a new investigation step to the trail
     * @param {Object} step - Investigation step data
     */
    function addStep(step) {
        // Create step entry
        const entry = {
            id: generateId(),
            timestamp: new Date().toISOString(),
            type: step.type || 'analysis', // analysis, address, transaction
            chain: step.chain,
            hash: step.hash,
            address: step.address,
            riskScore: step.riskScore,
            riskLevel: step.riskLevel,
            label: step.label || formatHash(step.hash || step.address),
            depth: step.depth || 1,
            entityType: step.entityType,
            notes: step.notes || ''
        };

        // If we're not at the end, remove forward history
        if (currentIndex < trail.length - 1) {
            trail = trail.slice(0, currentIndex + 1);
        }

        // Add new step
        trail.push(entry);

        // Limit trail length
        if (trail.length > MAX_TRAIL_LENGTH) {
            trail = trail.slice(-MAX_TRAIL_LENGTH);
        }

        currentIndex = trail.length - 1;
        saveTrail();
        renderBreadcrumb();

        return entry;
    }

    /**
     * Navigate to a specific step in the trail
     * @param {number} index - Index in the trail to navigate to
     */
    function navigateToStep(index) {
        if (index >= 0 && index < trail.length) {
            currentIndex = index;
            saveTrail();
            
            const step = trail[index];
            
            // Emit navigation event for other modules to handle
            const event = new CustomEvent('investigationNavigate', {
                detail: step
            });
            document.dispatchEvent(event);
            
            renderBreadcrumb();
            return step;
        }
        return null;
    }

    /**
     * Navigate back in the investigation trail
     */
    function navigateBack() {
        if (currentIndex > 0) {
            return navigateToStep(currentIndex - 1);
        }
        return null;
    }

    /**
     * Navigate forward in the investigation trail
     */
    function navigateForward() {
        if (currentIndex < trail.length - 1) {
            return navigateToStep(currentIndex + 1);
        }
        return null;
    }

    /**
     * Clear the investigation trail
     */
    function clearTrail() {
        trail = [];
        currentIndex = -1;
        saveTrail();
        renderBreadcrumb();
    }

    /**
     * Get the current investigation trail
     */
    function getTrail() {
        return [...trail];
    }

    /**
     * Get the current step
     */
    function getCurrentStep() {
        return currentIndex >= 0 ? trail[currentIndex] : null;
    }

    /**
     * Render the breadcrumb UI
     */
    function renderBreadcrumb() {
        const container = document.getElementById('investigation-breadcrumb');
        if (!container) return;

        if (trail.length === 0) {
            container.classList.add('hidden');
            return;
        }

        container.classList.remove('hidden');

        // Build breadcrumb HTML
        let html = `
            <div class="flex items-center space-x-2 overflow-x-auto scrollbar-hide py-2">
                <!-- Navigation buttons -->
                <button id="trail-back-btn" class="p-1.5 rounded-md transition-colors ${currentIndex > 0 ? 'text-forensic-400 hover:text-white hover:bg-forensic-700' : 'text-forensic-600 cursor-not-allowed'}" ${currentIndex <= 0 ? 'disabled' : ''}>
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"/>
                    </svg>
                </button>
                <button id="trail-forward-btn" class="p-1.5 rounded-md transition-colors ${currentIndex < trail.length - 1 ? 'text-forensic-400 hover:text-white hover:bg-forensic-700' : 'text-forensic-600 cursor-not-allowed'}" ${currentIndex >= trail.length - 1 ? 'disabled' : ''}>
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"/>
                    </svg>
                </button>
                
                <div class="h-4 w-px bg-forensic-700"></div>
                
                <!-- Trail items -->
                <div class="flex items-center space-x-1 flex-nowrap">
        `;

        // Show limited breadcrumb items
        const maxVisible = 5;
        const startIndex = Math.max(0, currentIndex - Math.floor(maxVisible / 2));
        const endIndex = Math.min(trail.length, startIndex + maxVisible);
        const visibleTrail = trail.slice(startIndex, endIndex);

        // Show ellipsis at start if needed
        if (startIndex > 0) {
            html += `
                <span class="text-forensic-500 text-xs">...</span>
                <svg class="w-3 h-3 text-forensic-600 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"/>
                </svg>
            `;
        }

        visibleTrail.forEach((step, idx) => {
            const actualIndex = startIndex + idx;
            const isActive = actualIndex === currentIndex;
            const riskClass = getRiskClass(step.riskLevel);
            
            html += `
                <button 
                    class="trail-step flex items-center space-x-1.5 px-2 py-1 rounded-md text-xs font-mono transition-all ${
                        isActive 
                            ? 'bg-forensic-700 text-white ring-1 ring-accent' 
                            : 'text-forensic-400 hover:bg-forensic-800 hover:text-white'
                    }"
                    data-index="${actualIndex}"
                    title="${step.hash || step.address}&#10;Risk: ${step.riskLevel}&#10;${new Date(step.timestamp).toLocaleString()}"
                >
                    ${getStepIcon(step.type, step.entityType)}
                    <span class="max-w-[80px] truncate">${step.label}</span>
                    <span class="inline-block w-1.5 h-1.5 rounded-full ${riskClass}"></span>
                </button>
            `;

            // Add separator between items
            if (idx < visibleTrail.length - 1) {
                html += `
                    <svg class="w-3 h-3 text-forensic-600 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"/>
                    </svg>
                `;
            }
        });

        // Show ellipsis at end if needed
        if (endIndex < trail.length) {
            html += `
                <svg class="w-3 h-3 text-forensic-600 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"/>
                </svg>
                <span class="text-forensic-500 text-xs">...</span>
            `;
        }

        html += `
                </div>
                
                <div class="h-4 w-px bg-forensic-700 ml-auto"></div>
                
                <!-- Trail actions -->
                <div class="flex items-center space-x-1 flex-shrink-0">
                    <span class="text-forensic-500 text-xs">${trail.length} steps</span>
                    <button id="trail-export-btn" class="p-1.5 rounded-md text-forensic-400 hover:text-white hover:bg-forensic-700 transition-colors" title="Export investigation trail">
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
                        </svg>
                    </button>
                    <button id="trail-clear-btn" class="p-1.5 rounded-md text-forensic-400 hover:text-risk-critical hover:bg-forensic-700 transition-colors" title="Clear investigation trail">
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/>
                        </svg>
                    </button>
                </div>
            </div>
        `;

        container.innerHTML = html;

        // Re-attach event listeners
        attachBreadcrumbListeners();
    }

    /**
     * Setup event listeners
     */
    function setupEventListeners() {
        // Listen for new analysis results
        document.addEventListener('analysisComplete', (e) => {
            if (e.detail) {
                addStep({
                    type: 'analysis',
                    chain: e.detail.chain,
                    hash: e.detail.tx_hash,
                    riskScore: e.detail.risk_score,
                    riskLevel: e.detail.risk_level,
                    depth: e.detail.depth
                });
            }
        });

        // Listen for address clicks in graph
        document.addEventListener('addressInspected', (e) => {
            if (e.detail) {
                addStep({
                    type: 'address',
                    chain: e.detail.chain,
                    address: e.detail.address,
                    riskScore: e.detail.riskScore,
                    riskLevel: e.detail.riskLevel,
                    entityType: e.detail.entityType,
                    label: e.detail.label || formatHash(e.detail.address)
                });
            }
        });
    }

    /**
     * Attach breadcrumb button listeners
     */
    function attachBreadcrumbListeners() {
        // Back button
        const backBtn = document.getElementById('trail-back-btn');
        if (backBtn) {
            backBtn.addEventListener('click', () => navigateBack());
        }

        // Forward button
        const forwardBtn = document.getElementById('trail-forward-btn');
        if (forwardBtn) {
            forwardBtn.addEventListener('click', () => navigateForward());
        }

        // Trail step buttons
        document.querySelectorAll('.trail-step').forEach(btn => {
            btn.addEventListener('click', () => {
                const index = parseInt(btn.dataset.index, 10);
                navigateToStep(index);
            });
        });

        // Export button
        const exportBtn = document.getElementById('trail-export-btn');
        if (exportBtn) {
            exportBtn.addEventListener('click', () => exportTrail());
        }

        // Clear button
        const clearBtn = document.getElementById('trail-clear-btn');
        if (clearBtn) {
            clearBtn.addEventListener('click', () => {
                if (confirm('Clear all investigation history?')) {
                    clearTrail();
                }
            });
        }
    }

    /**
     * Export the investigation trail as JSON
     */
    function exportTrail() {
        const exportData = {
            exported_at: new Date().toISOString(),
            investigation_id: generateId(),
            total_steps: trail.length,
            trail: trail.map(step => ({
                timestamp: step.timestamp,
                type: step.type,
                chain: step.chain,
                hash: step.hash,
                address: step.address,
                risk_score: step.riskScore,
                risk_level: step.riskLevel,
                entity_type: step.entityType,
                notes: step.notes
            }))
        };

        const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `safetrace-investigation-${new Date().toISOString().split('T')[0]}.json`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);

        showToast('Investigation trail exported successfully', 'success');
    }

    /**
     * Import an investigation trail from JSON
     * @param {File} file - JSON file to import
     */
    function importTrail(file) {
        const reader = new FileReader();
        reader.onload = (e) => {
            try {
                const data = JSON.parse(e.target.result);
                if (data.trail && Array.isArray(data.trail)) {
                    trail = data.trail.map(step => ({
                        id: generateId(),
                        timestamp: step.timestamp,
                        type: step.type,
                        chain: step.chain,
                        hash: step.hash,
                        address: step.address,
                        riskScore: step.risk_score,
                        riskLevel: step.risk_level,
                        entityType: step.entity_type,
                        label: formatHash(step.hash || step.address),
                        notes: step.notes || ''
                    }));
                    currentIndex = trail.length - 1;
                    saveTrail();
                    renderBreadcrumb();
                    showToast(`Imported ${trail.length} investigation steps`, 'success');
                }
            } catch (err) {
                console.error('Error importing trail:', err);
                showToast('Error importing investigation trail', 'error');
            }
        };
        reader.readAsText(file);
    }

    /**
     * Generate investigation summary for PDF export
     */
    function generateSummary() {
        if (trail.length === 0) return null;

        // Calculate statistics
        const chains = [...new Set(trail.map(s => s.chain).filter(Boolean))];
        const avgRisk = trail.reduce((sum, s) => sum + (s.riskScore || 0), 0) / trail.length;
        const highRiskSteps = trail.filter(s => s.riskScore >= 60).length;
        const entityTypes = [...new Set(trail.map(s => s.entityType).filter(Boolean))];

        return {
            total_steps: trail.length,
            start_time: trail[0].timestamp,
            end_time: trail[trail.length - 1].timestamp,
            chains_analyzed: chains,
            average_risk_score: Math.round(avgRisk),
            high_risk_steps: highRiskSteps,
            entity_types_found: entityTypes,
            steps: trail.map(s => ({
                timestamp: s.timestamp,
                type: s.type,
                chain: s.chain,
                identifier: s.hash || s.address,
                risk_score: s.riskScore,
                risk_level: s.riskLevel,
                entity_type: s.entityType
            }))
        };
    }

    // Helper functions
    function generateId() {
        return 'inv_' + Date.now().toString(36) + Math.random().toString(36).substr(2, 9);
    }

    function formatHash(hash) {
        if (!hash) return '—';
        if (hash.length <= 12) return hash;
        return hash.slice(0, 6) + '...' + hash.slice(-4);
    }

    function getRiskClass(level) {
        const classes = {
            'CRITICAL': 'bg-risk-critical',
            'HIGH': 'bg-risk-high',
            'MEDIUM': 'bg-risk-medium',
            'LOW': 'bg-risk-low',
            'SAFE': 'bg-risk-safe'
        };
        return classes[level] || 'bg-forensic-500';
    }

    function getStepIcon(type, entityType) {
        if (type === 'address') {
            if (entityType === 'exchange') {
                return `<svg class="w-3 h-3 text-entity-exchange flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4"/>
                </svg>`;
            }
            if (entityType === 'mixer') {
                return `<svg class="w-3 h-3 text-entity-mixer flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
                </svg>`;
            }
            return `<svg class="w-3 h-3 text-forensic-400 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5.121 17.804A13.937 13.937 0 0112 16c2.5 0 4.847.655 6.879 1.804M15 10a3 3 0 11-6 0 3 3 0 016 0zm6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
            </svg>`;
        }
        
        // Transaction icon
        return `<svg class="w-3 h-3 text-accent flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/>
        </svg>`;
    }

    function showToast(message, type = 'info') {
        // Use global toast function if available
        if (typeof window.showToast === 'function') {
            window.showToast(message, type);
        } else {
            console.log(`[${type.toUpperCase()}] ${message}`);
        }
    }

    // Public API
    return {
        init,
        addStep,
        navigateBack,
        navigateForward,
        navigateToStep,
        clearTrail,
        getTrail,
        getCurrentStep,
        exportTrail,
        importTrail,
        generateSummary
    };
})();

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', () => {
    InvestigationSnapshot.init();
});

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = InvestigationSnapshot;
}
