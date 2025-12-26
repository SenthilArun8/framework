// --- SERVER SENT EVENTS (Optimization Phase 24) ---
function startSSE() {
    const statusSpan = document.getElementById('conn-status');

    console.log("Starting EventSource connection...");
    const evtSource = new EventSource('/events');

    evtSource.onopen = function () {
        statusSpan.innerText = "LIVE (STREAM)";
        statusSpan.classList.add('connected');
    };

    evtSource.onmessage = function (event) {
        try {
            const state = JSON.parse(event.data);
            console.log("SSE State Received:", state); // Debug Log
            if (state) updateUI(state);
        } catch (e) {
            console.error("Error parsing SSE data:", e);
        }
    };

    evtSource.onerror = function (err) {
        console.error("EventSource failed:", err);
        statusSpan.innerText = "RECONNECTING";
        statusSpan.classList.remove('connected');
    };
}

function updateUI(state) {
    if (!state) return;



    // 1. Psyche
    document.getElementById('mood-val').innerText = state.profile.current_mood;

    const goalsList = document.getElementById('goals-list');
    goalsList.innerHTML = state.profile.goals.map(g => `<li>${g}</li>`).join('');

    const valuesContainer = document.getElementById('values-list');
    valuesContainer.innerHTML = '';
    for (const [key, val] of Object.entries(state.profile.values)) {
        const percent = Math.round(val.score * 100);
        valuesContainer.innerHTML += `
            <div class="bar-item">
                <div style="display:flex; justify-content:space-between;">
                    <span>${val.name}</span>
                    <span>${percent}%</span>
                </div>
                <div class="bar-outer">
                    <div class="bar-inner" style="width: ${percent}%"></div>
                </div>
            </div>
        `;
    }

    // 2. Chat
    const chatBox = document.getElementById('chat-history');
    const msgsHTML = state.chat_log.map(msg => `
        <div class="msg ${msg.role === 'human' ? 'user' : 'ai'}">
            <b>${msg.role === 'human' ? 'You' : 'Elias'}:</b> ${msg.content}
        </div>
    `).join('');

    if (chatBox.innerHTML !== msgsHTML) {
        chatBox.innerHTML = msgsHTML;
        chatBox.scrollTop = chatBox.scrollHeight;
    }

    // 3. Relationships (Robust Lookup)
    console.log("Relationships:", state.profile.relationships);
    let rel = state.profile.relationships['User_123'];
    if (!rel) {
        const keys = Object.keys(state.profile.relationships);
        if (keys.length > 0) rel = state.profile.relationships[keys[0]];
    }
    console.log("Selected Relationship:", rel);

    if (rel) {
        setMeter('trust', rel.trust_level);
        setMeter('respect', rel.respect_level);
    } else {
        // Debug fallback
        console.warn("No relationship found");
    }

    // 4. Memory Feed (Inside Graph Card Overlay)
    const memContainer = document.getElementById('memory-feed');
    let memHTML = '';

    // Recent Memories (Vector)
    if (state.last_turn && state.last_turn.memories) {
        state.last_turn.memories.forEach(m => {
            memHTML += `<div class="mem-chip">📂 ${m.description}</div>`;
        });
    }

    // Graph Connections
    if (state.last_turn && state.last_turn.graph_connections) {
        state.last_turn.graph_connections.forEach(g => {
            memHTML += `<div class="mem-chip graph">🕷️ ${g}</div>`;
        });
    }

    memContainer.innerHTML = memHTML || '<span style="color:#555; align-self:center;">No recent triggers.</span>';

    // 5. Subconscious
    if (state.last_turn && state.last_turn.subconscious) {
        document.getElementById('inner-thought').innerText = state.last_turn.subconscious;
    }

    // 6. Graph Visualization
    if (state.knowledge_graph) {
        updateGraph(state.knowledge_graph);
    }

    // 7. Strategy Chart (Phase 12)
    if (state.motivational && state.motivational.active_strategy) {
        updateStrategyChart(state.motivational.active_strategy);
    }
}

function setMeter(type, val) {
    const circle = document.getElementById(`${type}-circle`);
    const text = document.getElementById(`${type}-text`);
    const circumference = 100; // pathLength 100 technically
    const offset = circumference - val;

    circle.style.strokeDasharray = `${val}, 100`;
    text.innerText = Math.round(val) + "%";
}

// Initialize SSE
startSSE();

// --- CHAT INTERACTION ---
const inputField = document.getElementById('user-input');
const sendBtn = document.getElementById('send-btn');

async function sendMessage() {
    const text = inputField.value.trim();
    if (!text) return;

    // UI Update immediately (Optimistic)
    const chatBox = document.getElementById('chat-history');
    chatBox.innerHTML += `
        <div class="msg user"><b>You:</b> ${text}</div>
    `;
    chatBox.scrollTop = chatBox.scrollHeight;

    inputField.value = '';
    inputField.disabled = true;
    sendBtn.disabled = true;

    try {
        const response = await fetch('/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: text })
        });
        const data = await response.json();

        // State updates via SSE automatically

    } catch (e) {
        console.error("Chat Error:", e);
        chatBox.innerHTML += `<div class="msg system">Error sending message.</div>`;
    } finally {
        inputField.disabled = false;
        sendBtn.disabled = false;
        inputField.focus();
    }
}

if (sendBtn) sendBtn.addEventListener('click', sendMessage);
if (inputField) inputField.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') sendMessage();
});

// --- GRAPH VISUALIZATION ---
let network = null;
let nodes = new vis.DataSet([]);
let edges = new vis.DataSet([]);

function initGraph() {
    const container = document.getElementById('kg-network');
    const data = { nodes: nodes, edges: edges };
    const options = {
        nodes: {
            shape: 'dot',
            size: 15,
            font: { size: 12, color: '#ffffff' },
            borderWidth: 2,
            color: { background: '#1a1a20', border: '#00bcd4', highlight: '#9c27b0' }
        },
        edges: {
            width: 1,
            color: { color: '#444', highlight: '#9c27b0' },
            arrows: 'to',
            smooth: { type: 'continuous' }
        },
        physics: {
            stabilization: false,
            barnesHut: { gravitationalConstant: -2000, springConstant: 0.04, springLength: 95 }
        },
        interaction: { hover: true, tooltipDelay: 200 }
    };
    network = new vis.Network(container, data, options);
}

function updateGraph(vizData) {
    if (!vizData) return;

    // Initialize if first time
    if (!network && document.getElementById('kg-network')) initGraph();

    // Update DataSets (Vis.js handles diffing if IDs match)
    const hasNodes = vizData.nodes && vizData.nodes.length > 0;

    // VISUAL FEEDBACK FOR EMPTY STATE (Phase 15)
    const container = document.getElementById('kg-network');
    if (!hasNodes) {
        if (!container.innerHTML.includes("Graph Offline")) {
            container.innerHTML = `
                <div style="display:flex; flex-direction:column; align-items:center; justify-content:center; height:100%; color:#555;">
                    <span style="font-size:2rem;">🕸️</span>
                    <p>Graph Offline / No Data</p>
                    <small>Enable Neo4j to visualize knowledge.</small>
                </div>
            `;
            network = null; // Reset network instance
        }
    } else {
        if (!network) initGraph();
        nodes.update(vizData.nodes);
        edges.update(vizData.edges);
    }

    const status = document.getElementById('graph-status');
    if (status) status.innerText = hasNodes ? `${vizData.nodes.length} nodes, ${vizData.edges.length} edges` : "Offline";
}

// --- RESET LOGIC (Phase 15) ---
document.getElementById('reset-btn').addEventListener('click', async () => {
    if (!confirm("⚠️ ARE YOU SURE?\nThis will wipe all memories, relationship progress, and chat history.\nThis cannot be undone.")) return;

    try {
        const btn = document.getElementById('reset-btn');
        btn.disabled = true;
        btn.innerText = "RESETTING...";

        const res = await fetch('/reset_character', { method: 'POST' });
        const data = await res.json();

        alert("✅ " + data.message);
        window.location.reload();

    } catch (e) {
        alert("❌ Reset Failed: " + e);
        document.getElementById('reset-btn').innerText = "⚠️ RESET";
        document.getElementById('reset-btn').disabled = false;
    }
});

// --- STRATEGY CHART (Phase 12) ---
let strategyChart = null;
const allStrategies = [
    "neutral",
    "defensive_curt", "fragmented_thoughts", "over_explaining_clingy",
    "shutdown_withdrawal", "spaced_out_drifting", "mixed_signals_hesitant",
    "argumentative_assertive", "vulnerable_seeking", "hyper_vigilant", "needy_demanding"
];

function initStrategyChart() {
    const canvas = document.getElementById('strategyChart');
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    // Radar Chart
    strategyChart = new Chart(ctx, {
        type: 'radar',
        data: {
            labels: allStrategies.map(s => s.split('_')[0].toUpperCase()), // Short labels
            datasets: [{
                label: 'Behavioral Weight',
                data: new Array(allStrategies.length).fill(0),
                backgroundColor: 'rgba(156, 39, 176, 0.2)', // Purple tint
                borderColor: '#00bcd4', // Blue border
                pointBackgroundColor: '#fff',
                borderWidth: 2
            }]
        },
        options: {
            scales: {
                r: {
                    angleLines: { color: '#333' },
                    grid: { color: '#333' },
                    pointLabels: { color: '#aaa', font: { size: 9 } },
                    suggestedMin: 0,
                    suggestedMax: 1,
                    ticks: { display: false, backdropColor: 'transparent' }
                }
            },
            plugins: { legend: { display: false } },
            maintainAspectRatio: false
        }
    });
}

function updateStrategyChart(activeStrategy) {
    if (!strategyChart) initStrategyChart();
    if (!strategyChart) return;

    let map = {};
    if (typeof activeStrategy === 'string') {
        map[activeStrategy.toLowerCase()] = 1.0;
    } else if (activeStrategy) {
        map = activeStrategy;
    }

    const values = allStrategies.map(key => map[key] || 0);
    strategyChart.data.datasets[0].data = values;
    strategyChart.update();
}
