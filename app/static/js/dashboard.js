/* NetOps Desk Frontend Controller */

const state = {
    devices: [],
    incidents: [],
    dashboard: null,
    autoRefreshTimer: null,
    charts: {
        deviceHealth: null,
        incidentSeverity: null,
        latency: null,
    },
    pendingDelete: null,
};

// Bootstrap modal instances initialized on DOMContentLoaded
let deviceModal;
let incidentModal;
let confirmDeleteModal;

document.addEventListener("DOMContentLoaded", () => {
    deviceModal = new bootstrap.Modal(document.getElementById("deviceModal"));
    incidentModal = new bootstrap.Modal(document.getElementById("incidentModal"));
    confirmDeleteModal = new bootstrap.Modal(document.getElementById("confirmDeleteModal"));

    bindEvents();
    refreshAllData();
    configureAutoRefresh();
});

function bindEvents() {
    // Sidebar mobile toggle
    const sidebar = document.getElementById("sidebar");
    const backdrop = document.getElementById("sidebarBackdrop");
    document.getElementById("btnToggleSidebar").addEventListener("click", () => {
        sidebar.classList.toggle("open");
        backdrop.classList.toggle("show");
    });
    backdrop.addEventListener("click", () => {
        sidebar.classList.remove("open");
        backdrop.classList.remove("show");
    });

    // Sidebar smooth nav active state
    document.querySelectorAll(".sidebar-nav .nav-link").forEach((link) => {
        link.addEventListener("click", () => {
            document.querySelectorAll(".sidebar-nav .nav-link").forEach((el) => el.classList.remove("active"));
            link.classList.add("active");
            sidebar.classList.remove("open");
            backdrop.classList.remove("show");
        });
    });

    // Topbar & Sidebar action buttons
    document.getElementById("btnOpenDeviceModal").addEventListener("click", () => openDeviceModal());
    document.getElementById("btnSidebarAddDevice").addEventListener("click", () => openDeviceModal());
    document.getElementById("btnOpenIncidentModal").addEventListener("click", () => openIncidentModal());
    document.getElementById("btnSidebarAddIncident").addEventListener("click", () => openIncidentModal());
    document.getElementById("btnRunSimulation").addEventListener("click", runSimulatedCheck);
    document.getElementById("btnSidebarSeedDemo").addEventListener("click", seedDemoTopology);

    // Auto refresh switch
    document.getElementById("autoRefreshToggle").addEventListener("change", configureAutoRefresh);

    // Device filters
    document.getElementById("deviceSearchInput").addEventListener("input", debounce(fetchDevices, 250));
    document.getElementById("deviceStatusFilter").addEventListener("change", fetchDevices);
    document.getElementById("deviceTypeFilter").addEventListener("change", fetchDevices);

    // Incident filters
    document.getElementById("incidentStatusFilter").addEventListener("change", fetchIncidents);
    document.getElementById("incidentPriorityFilter").addEventListener("change", fetchIncidents);

    // Forms
    document.getElementById("deviceForm").addEventListener("submit", handleDeviceSubmit);
    document.getElementById("incidentForm").addEventListener("submit", handleIncidentSubmit);
    document.getElementById("confirmDeleteBtn").addEventListener("click", executePendingDelete);
}

function configureAutoRefresh() {
    if (state.autoRefreshTimer) {
        clearInterval(state.autoRefreshTimer);
        state.autoRefreshTimer = null;
    }
    const enabled = document.getElementById("autoRefreshToggle").checked;
    if (enabled) {
        state.autoRefreshTimer = setInterval(refreshAllData, 15000);
    }
}

async function refreshAllData() {
    await Promise.all([fetchDashboard(), fetchDevices(), fetchIncidents()]);
}

async function apiRequest(url, options = {}) {
    const response = await fetch(url, {
        headers: { "Content-Type": "application/json", ...(options.headers || {}) },
        ...options,
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
        const err = new Error(data.error || data.message || `HTTP ${response.status}`);
        err.details = data.details || null;
        err.status = response.status;
        throw err;
    }
    return data;
}

async function fetchDashboard() {
    try {
        const data = await apiRequest("/api/dashboard");
        state.dashboard = data;
        renderDashboardSummary(data);
        renderDashboardCharts(data);
    } catch (err) {
        showToast(`Failed to load dashboard metrics: ${err.message}`, "danger");
    }
}

async function fetchDevices() {
    try {
        const params = new URLSearchParams();
        const search = document.getElementById("deviceSearchInput").value.trim();
        const status = document.getElementById("deviceStatusFilter").value;
        const dtype = document.getElementById("deviceTypeFilter").value;

        if (search) params.set("search", search);
        if (status) params.set("status", status);
        if (dtype) params.set("device_type", dtype);

        const qs = params.toString() ? `?${params.toString()}` : "";
        const data = await apiRequest(`/api/devices${qs}`);
        state.devices = data.devices || [];
        renderDevicesTable(state.devices);
        renderLatencyChart(state.devices);
        populateIncidentDeviceSelect();
    } catch (err) {
        showToast(`Failed to load devices: ${err.message}`, "danger");
    }
}

async function fetchIncidents() {
    try {
        const params = new URLSearchParams();
        const status = document.getElementById("incidentStatusFilter").value;
        const priority = document.getElementById("incidentPriorityFilter").value;

        if (status) params.set("status", status);
        if (priority) params.set("priority", priority);

        const qs = params.toString() ? `?${params.toString()}` : "";
        const data = await apiRequest(`/api/incidents${qs}`);
        state.incidents = data.incidents || [];
        renderIncidentsTable(state.incidents);
    } catch (err) {
        showToast(`Failed to load incidents: ${err.message}`, "danger");
    }
}

function renderDashboardSummary(data) {
    const { devices, incidents, monitoring } = data;
    document.getElementById("kpiTotalDevices").textContent = devices.total;
    document.getElementById("kpiOnlineDevices").textContent = devices.online;
    document.getElementById("kpiWarningDevices").textContent = devices.warning;
    document.getElementById("kpiOfflineDevices").textContent = devices.offline;
    document.getElementById("kpiOpenIncidents").textContent = incidents.active_open_total;
    document.getElementById("kpiIncidentSubtext").textContent = `${incidents.resolved} resolved`;

    document.getElementById("kpiAvgLatency").textContent =
        devices.avg_simulated_latency_ms !== null ? `${devices.avg_simulated_latency_ms} ms` : "N/A";
    document.getElementById("kpiAvgUptime").textContent =
        `Avg Uptime: ${devices.avg_simulated_uptime_pct}% (sim)`;

    document.getElementById("sidebarDeviceCount").textContent = devices.total;
    document.getElementById("sidebarIncidentCount").textContent = incidents.active_open_total;
    document.getElementById("sidebarSimMeta").textContent =
        monitoring.enabled ? `Interval: ${monitoring.interval_seconds}s (Simulated)` : "Manual Simulation";
    document.getElementById("lastUpdatedLabel").textContent =
        `Last synced: ${new Date().toLocaleTimeString()}`;
}

function renderDashboardCharts(data) {
    const { devices, incidents } = data;

    // 1. Device Health Doughnut
    const healthCtx = document.getElementById("deviceHealthChart").getContext("2d");
    const healthValues = [devices.online, devices.warning, devices.offline];

    if (state.charts.deviceHealth) {
        state.charts.deviceHealth.data.datasets[0].data = healthValues;
        state.charts.deviceHealth.update();
    } else {
        state.charts.deviceHealth = new Chart(healthCtx, {
            type: "doughnut",
            data: {
                labels: ["ONLINE (Sim)", "WARNING (Sim)", "OFFLINE (Sim)"],
                datasets: [{
                    data: healthValues,
                    backgroundColor: ["#16A34A", "#F59E0B", "#DC2626"],
                    borderWidth: 2,
                    borderColor: "#FFFFFF",
                }],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: "65%",
                plugins: {
                    legend: { position: "bottom", labels: { boxWidth: 12, font: { size: 12 } } },
                },
            },
        });
    }

    // 2. Incident Severity Bar Chart
    const sevCtx = document.getElementById("incidentSeverityChart").getContext("2d");
    const sevOrder = ["LOW", "MEDIUM", "HIGH", "CRITICAL"];
    const sevValues = sevOrder.map((level) => incidents.by_priority[level] || 0);

    if (state.charts.incidentSeverity) {
        state.charts.incidentSeverity.data.datasets[0].data = sevValues;
        state.charts.incidentSeverity.update();
    } else {
        state.charts.incidentSeverity = new Chart(sevCtx, {
            type: "bar",
            data: {
                labels: sevOrder,
                datasets: [{
                    label: "Incidents",
                    data: sevValues,
                    backgroundColor: ["#64748B", "#3B82F6", "#F59E0B", "#DC2626"],
                    borderRadius: 6,
                }],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    y: { beginAtZero: true, ticks: { precision: 0 } },
                },
            },
        });
    }
}

function renderLatencyChart(devices) {
    const ctx = document.getElementById("latencyChart").getContext("2d");
    const topDevices = devices.slice(0, 8);
    const labels = topDevices.map((d) => d.name);
    const values = topDevices.map((d) => d.simulated_latency_ms ?? 0);
    const colors = topDevices.map((d) =>
        d.status === "OFFLINE" ? "#DC2626" : d.status === "WARNING" ? "#F59E0B" : "#2563EB"
    );

    if (state.charts.latency) {
        state.charts.latency.data.labels = labels;
        state.charts.latency.data.datasets[0].data = values;
        state.charts.latency.data.datasets[0].backgroundColor = colors;
        state.charts.latency.update();
    } else {
        state.charts.latency = new Chart(ctx, {
            type: "bar",
            data: {
                labels,
                datasets: [{
                    label: "Simulated Latency (ms)",
                    data: values,
                    backgroundColor: colors,
                    borderRadius: 6,
                }],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    y: { beginAtZero: true, title: { display: true, text: "ms (Simulated)" } },
                },
            },
        });
    }
}

function renderDevicesTable(devices) {
    const tbody = document.getElementById("devicesTableBody");
    if (!devices.length) {
        tbody.innerHTML = `
            <tr>
                <td colspan="9" class="text-center py-4 text-muted">
                    No devices found. Click <strong>Add Device</strong> or <strong>Seed Demo Topology</strong> to begin.
                </td>
            </tr>`;
        return;
    }

    tbody.innerHTML = devices.map((d) => {
        const latencyText = d.simulated_latency_ms !== null ? `${d.simulated_latency_ms} ms` : "Timeout";
        const checkedText = d.last_checked ? formatTimestamp(d.last_checked) : "--";
        return `
            <tr>
                <td>
                    <div class="fw-semibold text-navy">${escapeHtml(d.name)}</div>
                    ${d.open_incidents_count > 0 ? `<span class="badge bg-danger-subtle text-danger small">${d.open_incidents_count} open incident(s)</span>` : ""}
                </td>
                <td class="font-monospace">${escapeHtml(d.ip_address)}</td>
                <td><span class="badge bg-subtle-blue text-navy">${escapeHtml(d.device_type)}</span></td>
                <td>${escapeHtml(d.location)}</td>
                <td><span class="status-badge status-${d.status}">${d.status}</span></td>
                <td>${latencyText}</td>
                <td>${d.simulated_uptime_pct}%</td>
                <td class="small text-muted">${checkedText}</td>
                <td class="text-end text-nowrap">
                    <button class="btn btn-sm btn-outline-primary me-1" title="Log Incident" onclick="openIncidentModalForDevice(${d.id})">
                        <i class="bi bi-exclamation-triangle"></i>
                    </button>
                    <button class="btn btn-sm btn-outline-secondary me-1" title="Edit Device" onclick="openEditDevice(${d.id})">
                        <i class="bi bi-pencil"></i>
                    </button>
                    <button class="btn btn-sm btn-outline-danger" title="Delete Device" onclick="confirmDelete('device', ${d.id}, '${escapeAttr(d.name)}')">
                        <i class="bi bi-trash"></i>
                    </button>
                </td>
            </tr>`;
    }).join("");
}

function renderIncidentsTable(incidents) {
    const tbody = document.getElementById("incidentsTableBody");
    if (!incidents.length) {
        tbody.innerHTML = `
            <tr>
                <td colspan="7" class="text-center py-4 text-muted">
                    No incidents match the current filters.
                </td>
            </tr>`;
        return;
    }

    tbody.innerHTML = incidents.map((inc) => {
        const resolveBtn = inc.status !== "RESOLVED"
            ? `<button class="btn btn-sm btn-outline-success me-1" title="Resolve Incident" onclick="quickResolveIncident(${inc.id})">
                   <i class="bi bi-check2-circle"></i>
               </button>`
            : "";
        return `
            <tr>
                <td class="font-monospace text-muted">#${inc.id}</td>
                <td>
                    <div class="fw-semibold text-navy">${escapeHtml(inc.title)}</div>
                    ${inc.description ? `<div class="small text-muted text-truncate" style="max-width: 340px;">${escapeHtml(inc.description)}</div>` : ""}
                </td>
                <td>
                    <div class="fw-medium">${escapeHtml(inc.device_name || "Unknown")}</div>
                    <div class="small font-monospace text-muted">${escapeHtml(inc.device_ip || "")}</div>
                </td>
                <td><span class="priority-badge priority-${inc.priority}">${inc.priority}</span></td>
                <td><span class="status-badge status-${inc.status}">${inc.status}</span></td>
                <td class="small text-muted">${formatTimestamp(inc.created_at)}</td>
                <td class="text-end text-nowrap">
                    ${resolveBtn}
                    <button class="btn btn-sm btn-outline-secondary me-1" title="Edit Incident" onclick="openEditIncident(${inc.id})">
                        <i class="bi bi-pencil"></i>
                    </button>
                    <button class="btn btn-sm btn-outline-danger" title="Delete Incident" onclick="confirmDelete('incident', ${inc.id}, '${escapeAttr(inc.title)}')">
                        <i class="bi bi-trash"></i>
                    </button>
                </td>
            </tr>`;
    }).join("");
}

function populateIncidentDeviceSelect(selectedId = null) {
    const select = document.getElementById("incidentDeviceField");
    if (!state.devices.length) {
        select.innerHTML = `<option value="">No registered devices available</option>`;
        return;
    }
    select.innerHTML = state.devices.map((d) =>
        `<option value="${d.id}" ${Number(selectedId) === d.id ? "selected" : ""}>${escapeHtml(d.name)} (${escapeHtml(d.ip_address)})</option>`
    ).join("");
}

function openDeviceModal(device = null) {
    const errBox = document.getElementById("deviceFormError");
    errBox.classList.add("d-none");
    document.getElementById("deviceForm").reset();

    if (device) {
        document.getElementById("deviceModalTitle").textContent = `Edit Device: ${device.name}`;
        document.getElementById("deviceIdField").value = device.id;
        document.getElementById("deviceNameField").value = device.name;
        document.getElementById("deviceIpField").value = device.ip_address;
        document.getElementById("deviceTypeField").value = device.device_type;
        document.getElementById("deviceLocationField").value = device.location;
        document.getElementById("deviceStatusField").value = device.status;
    } else {
        document.getElementById("deviceModalTitle").textContent = "Register Network Device";
        document.getElementById("deviceIdField").value = "";
        document.getElementById("deviceStatusField").value = "ONLINE";
    }
    deviceModal.show();
}

window.openEditDevice = function (deviceId) {
    const device = state.devices.find((d) => d.id === deviceId);
    if (device) openDeviceModal(device);
};

async function handleDeviceSubmit(event) {
    event.preventDefault();
    const errBox = document.getElementById("deviceFormError");
    errBox.classList.add("d-none");

    const deviceId = document.getElementById("deviceIdField").value;
    const payload = {
        name: document.getElementById("deviceNameField").value.trim(),
        ip_address: document.getElementById("deviceIpField").value.trim(),
        device_type: document.getElementById("deviceTypeField").value,
        location: document.getElementById("deviceLocationField").value.trim(),
        status: document.getElementById("deviceStatusField").value,
    };

    try {
        if (deviceId) {
            await apiRequest(`/api/devices/${deviceId}`, { method: "PUT", body: JSON.stringify(payload) });
            showToast("Device updated successfully.", "success");
        } else {
            await apiRequest("/api/devices", { method: "POST", body: JSON.stringify(payload) });
            showToast("Device registered successfully.", "success");
        }
        deviceModal.hide();
        await refreshAllData();
    } catch (err) {
        const detailText = err.details ? Object.values(err.details).join(" ") : "";
        errBox.textContent = `${err.message} ${detailText}`.trim();
        errBox.classList.remove("d-none");
    }
}

function openIncidentModal(incident = null, presetDeviceId = null) {
    const errBox = document.getElementById("incidentFormError");
    errBox.classList.add("d-none");
    document.getElementById("incidentForm").reset();
    populateIncidentDeviceSelect(incident ? incident.device_id : presetDeviceId);

    if (incident) {
        document.getElementById("incidentModalTitle").textContent = `Edit Incident #${incident.id}`;
        document.getElementById("incidentIdField").value = incident.id;
        document.getElementById("incidentTitleField").value = incident.title;
        document.getElementById("incidentDescField").value = incident.description || "";
        document.getElementById("incidentPriorityField").value = incident.priority;
        document.getElementById("incidentStatusField").value = incident.status;
    } else {
        document.getElementById("incidentModalTitle").textContent = "Log Network Incident";
        document.getElementById("incidentIdField").value = "";
        document.getElementById("incidentPriorityField").value = "MEDIUM";
        document.getElementById("incidentStatusField").value = "OPEN";
    }
    incidentModal.show();
}

window.openIncidentModalForDevice = function (deviceId) {
    openIncidentModal(null, deviceId);
};

window.openEditIncident = function (incidentId) {
    const inc = state.incidents.find((i) => i.id === incidentId);
    if (inc) openIncidentModal(inc);
};

async function handleIncidentSubmit(event) {
    event.preventDefault();
    const errBox = document.getElementById("incidentFormError");
    errBox.classList.add("d-none");

    const deviceVal = document.getElementById("incidentDeviceField").value;
    if (!deviceVal) {
        errBox.textContent = "Please register a device before logging an incident.";
        errBox.classList.remove("d-none");
        return;
    }

    const incidentId = document.getElementById("incidentIdField").value;
    const payload = {
        device_id: Number(deviceVal),
        title: document.getElementById("incidentTitleField").value.trim(),
        description: document.getElementById("incidentDescField").value.trim(),
        priority: document.getElementById("incidentPriorityField").value,
        status: document.getElementById("incidentStatusField").value,
    };

    try {
        if (incidentId) {
            await apiRequest(`/api/incidents/${incidentId}`, { method: "PUT", body: JSON.stringify(payload) });
            showToast("Incident updated successfully.", "success");
        } else {
            await apiRequest("/api/incidents", { method: "POST", body: JSON.stringify(payload) });
            showToast("Incident created successfully.", "success");
        }
        incidentModal.hide();
        await refreshAllData();
    } catch (err) {
        const detailText = err.details ? Object.values(err.details).join(" ") : "";
        errBox.textContent = `${err.message} ${detailText}`.trim();
        errBox.classList.remove("d-none");
    }
}

window.quickResolveIncident = async function (incidentId) {
    try {
        await apiRequest(`/api/incidents/${incidentId}/resolve`, { method: "POST" });
        showToast(`Incident #${incidentId} resolved.`, "success");
        await refreshAllData();
    } catch (err) {
        showToast(`Failed to resolve incident: ${err.message}`, "danger");
    }
};

window.confirmDelete = function (type, id, label) {
    state.pendingDelete = { type, id };
    const warning = type === "device"
        ? `Delete device <strong>${escapeHtml(label)}</strong>? Any linked incidents will also be removed.`
        : `Delete incident <strong>${escapeHtml(label)}</strong>?`;
    document.getElementById("confirmDeleteBody").innerHTML = warning;
    confirmDeleteModal.show();
};

async function executePendingDelete() {
    if (!state.pendingDelete) return;
    const { type, id } = state.pendingDelete;
    const endpoint = type === "device" ? `/api/devices/${id}` : `/api/incidents/${id}`;
    try {
        await apiRequest(endpoint, { method: "DELETE" });
        confirmDeleteModal.hide();
        showToast(`${type === "device" ? "Device" : "Incident"} deleted.`, "success");
        state.pendingDelete = null;
        await refreshAllData();
    } catch (err) {
        showToast(`Delete failed: ${err.message}`, "danger");
    }
}

async function runSimulatedCheck() {
    const btn = document.getElementById("btnRunSimulation");
    btn.disabled = true;
    try {
        const result = await apiRequest("/api/monitoring/run", {
            method: "POST",
            body: JSON.stringify({ auto_create_incidents: true }),
        });
        showToast(
            `Simulated check complete: ${result.devices_checked} device(s) checked, ${result.status_changes.length} status change(s).`,
            "info"
        );
        await refreshAllData();
    } catch (err) {
        showToast(`Simulation error: ${err.message}`, "danger");
    } finally {
        btn.disabled = false;
    }
}

async function seedDemoTopology() {
    try {
        const result = await apiRequest("/api/monitoring/seed", { method: "POST" });
        showToast(result.message, "info");
        await refreshAllData();
    } catch (err) {
        showToast(`Seed failed: ${err.message}`, "danger");
    }
}

function showToast(message, variant = "primary") {
    const container = document.getElementById("toastContainer");
    const toastEl = document.createElement("div");
    toastEl.className = `toast align-items-center text-bg-${variant} border-0`;
    toastEl.setAttribute("role", "alert");
    toastEl.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">${escapeHtml(message)}</div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
        </div>`;
    container.appendChild(toastEl);
    const toast = new bootstrap.Toast(toastEl, { delay: 3500 });
    toastEl.addEventListener("hidden.bs.toast", () => toastEl.remove());
    toast.show();
}

function formatTimestamp(isoString) {
    if (!isoString) return "--";
    const dt = new Date(isoString);
    return Number.isNaN(dt.getTime()) ? isoString : dt.toLocaleString();
}

function escapeHtml(text) {
    return String(text ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#39;");
}

function escapeAttr(text) {
    return escapeHtml(text).replaceAll("\\", "\\\\");
}

function debounce(fn, waitMs) {
    let timer;
    return (...args) => {
        clearTimeout(timer);
        timer = setTimeout(() => fn(...args), waitMs);
    };
}
