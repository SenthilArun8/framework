const map = L.map('map-container').setView([0, 0], 2);
L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png').addTo(map);

const evtSource = new EventSource("http://localhost:8001/stream");

evtSource.onmessage = function (event) {
    console.log("Update:", event.data);
    const data = event.data; // logic to parse json later
    // Placeholder logic
    addLog(data);
};

function addLog(msg) {
    const list = document.getElementById('feed-list');
    const item = document.createElement('li');
    item.textContent = msg;
    list.prepend(item);
    if (list.children.length > 20) list.lastChild.remove();
}

async function startSim() {
    await fetch("http://localhost:8001/start", { method: "POST" });
}

async function stopSim() {
    await fetch("http://localhost:8001/stop", { method: "POST" });
}
