/**
 * SafeTrace Graph Visualization Module
 * Cytoscape.js integration for transaction flow visualization
 */

let cy = null; // Cytoscape instance
let graphData = null;

/**
 * Initialize the graph visualization
 */
function initGraph() {
    const container = document.getElementById('graph-container');
    if (!container) return;
    
    cy = cytoscape({
        container: container,
        
        style: [
            // Node styles
            {
                selector: 'node',
                style: {
                    'label': 'data(label)',
                    'text-valign': 'bottom',
                    'text-halign': 'center',
                    'font-size': '10px',
                    'font-family': 'JetBrains Mono, monospace',
                    'color': '#9CA3AF',
                    'background-color': '#6B7280',
                    'width': 40,
                    'height': 40,
                    'border-width': 2,
                    'border-color': '#374151',
                    'text-margin-y': 8
                }
            },
            // Node types
            {
                selector: 'node[type="exchange"]',
                style: {
                    'background-color': '#10B981',
                    'border-color': '#059669'
                }
            },
            {
                selector: 'node[type="mixer"]',
                style: {
                    'background-color': '#8B5CF6',
                    'border-color': '#7C3AED'
                }
            },
            {
                selector: 'node[type="sanctioned"]',
                style: {
                    'background-color': '#FF3B3B',
                    'border-color': '#DC2626'
                }
            },
            {
                selector: 'node[type="defi"]',
                style: {
                    'background-color': '#3B82F6',
                    'border-color': '#2563EB'
                }
            },
            {
                selector: 'node[type="contract"]',
                style: {
                    'background-color': '#F59E0B',
                    'border-color': '#D97706',
                    'shape': 'diamond'
                }
            },
            // Origin node (the analyzed transaction)
            {
                selector: 'node[type="origin"]',
                style: {
                    'background-color': '#3B82F6',
                    'border-color': '#60A5FA',
                    'border-width': 4,
                    'width': 50,
                    'height': 50
                }
            },
            // High risk nodes
            {
                selector: 'node[risk="high"]',
                style: {
                    'border-color': '#FF3B3B',
                    'border-width': 4
                }
            },
            // Selected node
            {
                selector: 'node:selected',
                style: {
                    'border-color': '#60A5FA',
                    'border-width': 4,
                    'background-color': '#3B82F6'
                }
            },
            // Edge styles
            {
                selector: 'edge',
                style: {
                    'width': 2,
                    'line-color': '#4B5563',
                    'target-arrow-color': '#4B5563',
                    'target-arrow-shape': 'triangle',
                    'curve-style': 'bezier',
                    'label': 'data(amount)',
                    'font-size': '8px',
                    'font-family': 'JetBrains Mono, monospace',
                    'color': '#6B7280',
                    'text-background-color': '#0B0E11',
                    'text-background-opacity': 0.8,
                    'text-background-padding': '2px'
                }
            },
            // High risk edges
            {
                selector: 'edge[risk="high"]',
                style: {
                    'line-color': '#FF6B35',
                    'target-arrow-color': '#FF6B35',
                    'width': 3
                }
            },
            {
                selector: 'edge[risk="critical"]',
                style: {
                    'line-color': '#FF3B3B',
                    'target-arrow-color': '#FF3B3B',
                    'width': 4
                }
            },
            // Selected edge
            {
                selector: 'edge:selected',
                style: {
                    'line-color': '#60A5FA',
                    'target-arrow-color': '#60A5FA',
                    'width': 4
                }
            }
        ],
        
        layout: {
            name: 'breadthfirst',
            directed: true,
            padding: 30,
            spacingFactor: 1.5,
            animate: true,
            animationDuration: 500
        },
        
        // Interaction options
        minZoom: 0.3,
        maxZoom: 3,
        wheelSensitivity: 0.2,
        boxSelectionEnabled: false,
        autounselectify: false
    });
    
    // Event listeners
    cy.on('tap', 'node', function(evt) {
        const node = evt.target;
        showNodeDetails(node.data());
    });
    
    cy.on('tap', 'edge', function(evt) {
        const edge = evt.target;
        showEdgeDetails(edge.data());
    });
    
    // Hide placeholder
    const placeholder = document.getElementById('graph-placeholder');
    if (placeholder) placeholder.style.display = 'none';
    
    // Show legend
    const legend = document.getElementById('graph-legend');
    if (legend) legend.classList.remove('hidden');
}

/**
 * Render graph data
 * @param {Object} data - Graph data with nodes and edges
 */
function renderGraph(data) {
    if (!cy) initGraph();
    if (!data || !data.nodes || !data.edges) {
        console.warn('Invalid graph data');
        return;
    }
    
    graphData = data;
    
    // Clear existing elements
    cy.elements().remove();
    
    // Add nodes
    const nodes = data.nodes.map(node => ({
        data: {
            id: node.id || node.address,
            label: formatAddressLabel(node.address || node.id),
            address: node.address || node.id,
            type: node.type || 'unknown',
            risk: node.risk || 'low',
            entity: node.entity || null,
            balance: node.balance || null,
            transactions: node.transactions || 0
        }
    }));
    
    // Add edges
    const edges = data.edges.map((edge, index) => ({
        data: {
            id: `edge-${index}`,
            source: edge.source || edge.from,
            target: edge.target || edge.to,
            amount: formatAmount(edge.amount || edge.value),
            risk: edge.risk || 'low',
            txHash: edge.txHash || edge.hash,
            timestamp: edge.timestamp
        }
    }));
    
    cy.add([...nodes, ...edges]);
    
    // Apply layout
    applyLayout('breadthfirst');
    
    // Fit view
    cy.fit(50);
}

/**
 * Generate mock graph from analysis result
 * @param {Object} result - Analysis result from API
 */
function generateGraphFromResult(result) {
    const nodes = [];
    const edges = [];
    const addresses = new Set();
    
    // Add origin address
    if (result.origin_address) {
        nodes.push({
            id: result.origin_address,
            address: result.origin_address,
            type: 'origin',
            risk: 'low'
        });
        addresses.add(result.origin_address);
    }
    
    // Add flagged entities as nodes
    if (result.flagged_entities && result.flagged_entities.length > 0) {
        result.flagged_entities.forEach(entity => {
            if (!addresses.has(entity.address)) {
                nodes.push({
                    id: entity.address,
                    address: entity.address,
                    type: entity.type || 'sanctioned',
                    risk: 'high',
                    entity: entity.name
                });
                addresses.add(entity.address);
                
                // Add edge from origin to flagged entity
                if (result.origin_address) {
                    edges.push({
                        source: result.origin_address,
                        target: entity.address,
                        amount: entity.amount || 0,
                        risk: 'high'
                    });
                }
            }
        });
    }
    
    // Generate some mock intermediate nodes if we have few addresses
    const addressesAnalyzed = result.addresses_analyzed || 0;
    const existingNodes = nodes.length;
    
    if (addressesAnalyzed > existingNodes && existingNodes < 10) {
        const mockTypes = ['exchange', 'defi', 'unknown', 'contract'];
        const numToAdd = Math.min(addressesAnalyzed - existingNodes, 8);
        
        for (let i = 0; i < numToAdd; i++) {
            const mockAddress = `0x${Math.random().toString(16).slice(2, 42)}`;
            const type = mockTypes[Math.floor(Math.random() * mockTypes.length)];
            
            nodes.push({
                id: mockAddress,
                address: mockAddress,
                type: type,
                risk: Math.random() > 0.7 ? 'high' : 'low'
            });
            
            // Connect to existing node
            const sourceNode = nodes[Math.floor(Math.random() * (nodes.length - 1))];
            edges.push({
                source: sourceNode.id,
                target: mockAddress,
                amount: Math.random() * 10,
                risk: Math.random() > 0.8 ? 'high' : 'low'
            });
        }
    }
    
    return { nodes, edges };
}

/**
 * Apply layout to graph
 * @param {string} layoutName - Layout name
 */
function applyLayout(layoutName = 'breadthfirst') {
    if (!cy) return;
    
    const layouts = {
        'breadthfirst': {
            name: 'breadthfirst',
            directed: true,
            padding: 30,
            spacingFactor: 1.5
        },
        'circle': {
            name: 'circle',
            padding: 30
        },
        'concentric': {
            name: 'concentric',
            padding: 30,
            minNodeSpacing: 50
        },
        'cose': {
            name: 'cose',
            padding: 30,
            nodeRepulsion: 8000,
            idealEdgeLength: 100
        }
    };
    
    const layout = cy.layout(layouts[layoutName] || layouts['breadthfirst']);
    layout.run();
}

/**
 * Reset graph zoom
 */
function resetGraphZoom() {
    if (!cy) return;
    cy.fit(50);
}

/**
 * Toggle fullscreen mode
 */
function toggleFullscreen() {
    const container = document.getElementById('graph-container');
    if (!container) return;
    
    if (!document.fullscreenElement) {
        container.requestFullscreen().catch(err => {
            console.log('Fullscreen error:', err);
        });
    } else {
        document.exitFullscreen();
    }
}

/**
 * Show node details in inspection panel
 * @param {Object} nodeData - Node data
 */
function showNodeDetails(nodeData) {
    const panel = document.getElementById('inspection-panel');
    const overlay = document.getElementById('inspection-overlay');
    const content = document.getElementById('inspection-content');
    
    if (!panel || !content) return;
    
    // Emit address inspected event for investigation snapshot
    const inspectEvent = new CustomEvent('addressInspected', {
        detail: {
            address: nodeData.address,
            chain: nodeData.chain || currentAnalysis?.report?.chain,
            riskScore: nodeData.riskScore || 0,
            riskLevel: nodeData.risk === 'high' ? 'HIGH' : 'LOW',
            entityType: nodeData.type,
            label: nodeData.entity || nodeData.address
        }
    });
    document.dispatchEvent(inspectEvent);
    
    // Build content
    const riskClass = nodeData.risk === 'high' ? 'text-risk-high' : 'text-risk-safe';
    const typeClass = getEntityBadgeClass(nodeData.type);
    
    content.innerHTML = `
        <div class="space-y-6">
            <!-- Address -->
            <div>
                <label class="text-xs text-gray-500 uppercase tracking-wide">Address</label>
                <div class="flex items-center gap-2 mt-1">
                    <code class="font-mono text-sm bg-forensic-800 px-3 py-2 rounded-lg truncate flex-1">${nodeData.address}</code>
                    <button onclick="copyToClipboard('${nodeData.address}')" class="p-2 bg-forensic-700 rounded-lg hover:bg-forensic-600 transition" title="Copy">
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"/>
                        </svg>
                    </button>
                </div>
            </div>
            
            <!-- Type & Risk -->
            <div class="grid grid-cols-2 gap-4">
                <div>
                    <label class="text-xs text-gray-500 uppercase tracking-wide">Entity Type</label>
                    <p class="mt-1"><span class="${typeClass}">${nodeData.type || 'Unknown'}</span></p>
                </div>
                <div>
                    <label class="text-xs text-gray-500 uppercase tracking-wide">Risk Level</label>
                    <p class="mt-1 ${riskClass} font-semibold capitalize">${nodeData.risk || 'Low'}</p>
                </div>
            </div>
            
            ${nodeData.entity ? `
            <div>
                <label class="text-xs text-gray-500 uppercase tracking-wide">Entity Name</label>
                <p class="mt-1 font-medium">${nodeData.entity}</p>
            </div>
            ` : ''}
            
            ${nodeData.balance ? `
            <div>
                <label class="text-xs text-gray-500 uppercase tracking-wide">Balance</label>
                <p class="mt-1 font-mono">${formatAmount(nodeData.balance)} ETH</p>
            </div>
            ` : ''}
            
            ${nodeData.transactions ? `
            <div>
                <label class="text-xs text-gray-500 uppercase tracking-wide">Transactions</label>
                <p class="mt-1">${nodeData.transactions.toLocaleString()}</p>
            </div>
            ` : ''}
            
            <!-- External Links -->
            <div class="pt-4 border-t border-forensic-700">
                <label class="text-xs text-gray-500 uppercase tracking-wide mb-2 block">External Links</label>
                <div class="space-y-2">
                    <a href="https://etherscan.io/address/${nodeData.address}" target="_blank" 
                       class="flex items-center gap-2 text-accent hover:underline text-sm">
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"/>
                        </svg>
                        View on Etherscan
                    </a>
                </div>
            </div>
        </div>
    `;
    
    // Show panel
    panel.classList.remove('hidden');
    if (overlay) overlay.classList.remove('hidden');
    
    setTimeout(() => {
        panel.classList.remove('hidden');
        panel.classList.add('visible');
    }, 10);
}

/**
 * Show edge details
 * @param {Object} edgeData - Edge data
 */
function showEdgeDetails(edgeData) {
    const panel = document.getElementById('inspection-panel');
    const overlay = document.getElementById('inspection-overlay');
    const content = document.getElementById('inspection-content');
    
    if (!panel || !content) return;
    
    const riskClass = edgeData.risk === 'high' || edgeData.risk === 'critical' ? 'text-risk-high' : 'text-risk-safe';
    
    content.innerHTML = `
        <div class="space-y-6">
            <div class="text-center py-4">
                <div class="w-12 h-12 bg-forensic-700 rounded-full flex items-center justify-center mx-auto mb-2">
                    <svg class="w-6 h-6 text-accent" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 8l4 4m0 0l-4 4m4-4H3"/>
                    </svg>
                </div>
                <h4 class="font-semibold">Transaction</h4>
            </div>
            
            <div>
                <label class="text-xs text-gray-500 uppercase tracking-wide">From</label>
                <code class="block mt-1 font-mono text-sm bg-forensic-800 px-3 py-2 rounded-lg truncate">${edgeData.source}</code>
            </div>
            
            <div class="text-center">
                <svg class="w-6 h-6 text-gray-500 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 14l-7 7m0 0l-7-7m7 7V3"/>
                </svg>
            </div>
            
            <div>
                <label class="text-xs text-gray-500 uppercase tracking-wide">To</label>
                <code class="block mt-1 font-mono text-sm bg-forensic-800 px-3 py-2 rounded-lg truncate">${edgeData.target}</code>
            </div>
            
            <div class="grid grid-cols-2 gap-4">
                <div>
                    <label class="text-xs text-gray-500 uppercase tracking-wide">Amount</label>
                    <p class="mt-1 font-mono text-accent">${edgeData.amount || '—'}</p>
                </div>
                <div>
                    <label class="text-xs text-gray-500 uppercase tracking-wide">Risk</label>
                    <p class="mt-1 ${riskClass} font-semibold capitalize">${edgeData.risk || 'Low'}</p>
                </div>
            </div>
            
            ${edgeData.txHash ? `
            <div>
                <label class="text-xs text-gray-500 uppercase tracking-wide">Transaction Hash</label>
                <code class="block mt-1 font-mono text-xs bg-forensic-800 px-3 py-2 rounded-lg break-all">${edgeData.txHash}</code>
            </div>
            ` : ''}
        </div>
    `;
    
    // Show panel
    panel.classList.remove('hidden');
    if (overlay) overlay.classList.remove('hidden');
    
    setTimeout(() => {
        panel.classList.remove('hidden');
        panel.classList.add('visible');
    }, 10);
}

/**
 * Close inspection panel
 */
function closeInspectionPanel() {
    const panel = document.getElementById('inspection-panel');
    const overlay = document.getElementById('inspection-overlay');
    
    if (panel) {
        panel.classList.remove('visible');
        setTimeout(() => panel.classList.add('hidden'), 300);
    }
    if (overlay) {
        overlay.classList.add('hidden');
    }
}

/**
 * Format address for display
 * @param {string} address - Full address
 * @returns {string} Formatted label
 */
function formatAddressLabel(address) {
    if (!address) return '???';
    if (address.length <= 10) return address;
    return `${address.slice(0, 6)}...${address.slice(-4)}`;
}

/**
 * Format amount for display
 * @param {number} amount - Amount value
 * @returns {string} Formatted amount
 */
function formatAmount(amount) {
    if (!amount && amount !== 0) return '';
    const num = parseFloat(amount);
    if (num >= 1000) return `${(num / 1000).toFixed(1)}K`;
    if (num >= 1) return num.toFixed(2);
    return num.toFixed(4);
}

/**
 * Get entity badge CSS class
 * @param {string} type - Entity type
 * @returns {string} CSS class
 */
function getEntityBadgeClass(type) {
    const classes = {
        'exchange': 'entity-badge-exchange',
        'mixer': 'entity-badge-mixer',
        'sanctioned': 'entity-badge-sanctioned',
        'defi': 'entity-badge-defi',
        'contract': 'entity-badge-contract',
        'origin': 'entity-badge-defi'
    };
    return classes[type] || 'bg-gray-700 text-gray-300 px-2 py-1 rounded text-xs';
}

/**
 * Copy text to clipboard
 * @param {string} text - Text to copy
 */
async function copyToClipboard(text) {
    try {
        await navigator.clipboard.writeText(text);
        // Could show a toast notification here
    } catch (err) {
        console.error('Failed to copy:', err);
    }
}

// Export for use in analyze.js
window.initGraph = initGraph;
window.renderGraph = renderGraph;
window.generateGraphFromResult = generateGraphFromResult;
window.resetGraphZoom = resetGraphZoom;
window.toggleFullscreen = toggleFullscreen;
window.closeInspectionPanel = closeInspectionPanel;
