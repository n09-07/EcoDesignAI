// ─────────────────────────────────────────────────────────────
// studio.js  —  EcoDesignAI Studio
// Communicates with the chatbot iframe via postMessage
// ─────────────────────────────────────────────────────────────

const MATERIALS = {
    bamboo:     { carbonPct: 10, carbonLabel: "Low",     recyclable: "Yes",     cost: "Low",    durability: "Medium", sub: "Fast growing, renewable, low carbon footprint." },
    plastic:    { carbonPct: 80, carbonLabel: "High",    recyclable: "Partial", cost: "Low",    durability: "High",   sub: "Lightweight and versatile, but high carbon output." },
    steel:      { carbonPct: 60, carbonLabel: "Medium",  recyclable: "Yes",     cost: "Medium", durability: "High",   sub: "Strong and fully recyclable structural material." },
    aluminum:   { carbonPct: 30, carbonLabel: "Low-Med", recyclable: "Yes",     cost: "Medium", durability: "High",   sub: "Lightweight, durable and highly recyclable metal." },
    mycelium:   { carbonPct: 5,  carbonLabel: "Low",     recyclable: "Yes",     cost: "Medium", durability: "Low",    sub: "Fungi-based biomaterial, fully compostable and carbon-negative." },
    bioplastic: { carbonPct: 20, carbonLabel: "Low",     recyclable: "Partial", cost: "Medium", durability: "Medium", sub: "Plant-derived plastic alternative with lower carbon emissions." }
};

const CARBON_COLORS = { Low: "#4ade80", "Low-Med": "#a3e635", Medium: "#facc15", High: "#f87171" };

let currentMaterial = "bamboo";

// ── Update detail card ──────────────────────────────────────
function selectMaterial(name) {
    const d = MATERIALS[name];
    if (!d) return;
    currentMaterial = name;

    // Tabs
    document.querySelectorAll('.material-card').forEach(c =>
        c.classList.toggle('active', c.dataset.material === name)
    );

    // Spotlight
    document.getElementById('spotlight-name').textContent =
        name.charAt(0).toUpperCase() + name.slice(1);
    document.getElementById('spotlight-sub').textContent = d.sub;

    // Detail card
    document.getElementById('impact-name').textContent = name.toUpperCase();
    document.getElementById('detail-recyclable').textContent = d.recyclable;
    document.getElementById('detail-cost').textContent       = d.cost;
    document.getElementById('detail-durability').textContent = d.durability;
    document.getElementById('carbon-label').textContent      = d.carbonLabel;

    const fill = document.getElementById('carbon-fill');
    fill.style.width      = d.carbonPct + '%';
    fill.style.background = CARBON_COLORS[d.carbonLabel] || '#4ade80';
}

// ── Build compare grid ──────────────────────────────────────
function buildCompareGrid() {
    const grid = document.getElementById('compare-grid');
    grid.innerHTML = '';
    Object.entries(MATERIALS).forEach(([name, d]) => {
        const ecoScore = Math.round(100 - d.carbonPct * 0.7);
        const col      = CARBON_COLORS[d.carbonLabel] || '#4ade80';
        const card     = document.createElement('div');
        card.className = 'compare-card';
        card.innerHTML = `
            <div class="cc-name">${name}</div>
            <div class="cc-bars">
                <div class="cc-row">
                    <span>Carbon</span>
                    <div class="cc-track"><div class="cc-fill" style="width:${d.carbonPct}%;background:${col}"></div></div>
                    <span>${d.carbonPct}</span>
                </div>
                <div class="cc-row">
                    <span>Eco</span>
                    <div class="cc-track"><div class="cc-fill" style="width:${ecoScore}%;background:#4ade80"></div></div>
                    <span>${ecoScore}</span>
                </div>
            </div>
            <div class="cc-dur">${d.durability} durability · ${d.cost} cost</div>
        `;
        card.addEventListener('click', () => selectMaterial(name));
        grid.appendChild(card);
    });
}

// ── "Design with this material" button ─────────────────────
document.getElementById('design-with-btn').addEventListener('click', () => {
    const d        = MATERIALS[currentMaterial];
    const sentence = `I want to design a product using ${currentMaterial}. My budget is ${d.cost.toLowerCase()}.`;

    const frame = document.getElementById('chat-frame');

    // postMessage lets us talk to the iframe even on the same origin
    frame.contentWindow.postMessage(
        { type: 'INJECT_MESSAGE', text: sentence },
        window.location.origin          // same-origin only — safe
    );

    // Visually pulse the right panel to draw the user's eye
    const panel = document.querySelector('.right-panel');
    panel.classList.remove('pulse');
    void panel.offsetWidth;
    panel.classList.add('pulse');
    setTimeout(() => panel.classList.remove('pulse'), 700);
});

// ── Tab clicks ──────────────────────────────────────────────
document.querySelectorAll('.material-card').forEach(card => {
    card.addEventListener('click', () => selectMaterial(card.dataset.material));
});

// ── Init ────────────────────────────────────────────────────
buildCompareGrid();
selectMaterial('bamboo');