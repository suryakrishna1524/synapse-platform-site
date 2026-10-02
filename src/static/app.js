/**
 * Synapse SDLC — Reactive Frontend Application Engine
 * Native Vanilla JS with SVG Charting, Dynamic Themes & REST Sync
 */

(function () {
  "use strict";

  // Application State
  const state = {
    metrics: [],
    stats: {},
    currentRole: "admin",
    theme: localStorage.getItem("synapse_theme") || "dark",
    searchFilter: "",
    statusFilter: "all",
  };

  // DOM Elements
  const el = {
    themeToggle: document.getElementById("theme-toggle"),
    themeIcon: document.getElementById("theme-icon"),
    roleSelect: document.getElementById("role-select"),
    btnRefresh: document.getElementById("btn-refresh"),
    btnExportCsv: document.getElementById("btn-export-csv"),
    btnExportJson: document.getElementById("btn-export-json"),
    btnAddMetric: document.getElementById("btn-add-metric"),
    btnPurge: document.getElementById("btn-purge-data"),
    filterSearch: document.getElementById("filter-search"),
    filterStatus: document.getElementById("filter-status"),
    tableBody: document.getElementById("telemetry-tbody"),
    kpiRuns: document.getElementById("kpi-total-runs"),
    kpiTokens: document.getElementById("kpi-total-tokens"),
    kpiSpend: document.getElementById("kpi-total-spend"),
    kpiDuration: document.getElementById("kpi-avg-duration"),
    kpiSuccessRate: document.getElementById("kpi-success-rate"),
    modelChartContainer: document.getElementById("model-chart-container"),
    timelineChartContainer: document.getElementById("timeline-chart-container"),
    modalMetric: document.getElementById("modal-metric"),
    modalClose: document.getElementById("modal-close"),
    btnCancelModal: document.getElementById("btn-cancel-modal"),
    formRecordMetric: document.getElementById("form-record-metric"),
    footerLastSync: document.getElementById("footer-last-sync"),
    toastContainer: document.getElementById("toast-container"),
    systemStatusText: document.getElementById("system-status-text"),
    tabDashboard: document.getElementById("tab-dashboard"),
    tabAudit: document.getElementById("tab-audit"),
    tabWebhooks: document.getElementById("tab-webhooks"),
    viewDashboard: document.getElementById("view-dashboard"),
    viewAudit: document.getElementById("view-audit"),
    viewWebhooks: document.getElementById("view-webhooks"),
    auditTbody: document.getElementById("audit-tbody"),
    filterAuditUser: document.getElementById("filter-audit-user"),
    filterAuditAction: document.getElementById("filter-audit-action"),
    btnRefreshAudit: document.getElementById("btn-refresh-audit"),
    btnTriggerWebhook: document.getElementById("btn-trigger-webhook"),
    webhookEventSelect: document.getElementById("webhook-event-select"),
  };

  // Toast System
  function showToast(message, type = "info") {
    if (!el.toastContainer) return;
    const icons = { success: "✅", warning: "⚠️", error: "❌", info: "⚡" };
    const toast = document.createElement("div");
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `<span>${icons[type] || "⚡"}</span> <span>${message}</span>`;
    el.toastContainer.appendChild(toast);
    setTimeout(() => {
      toast.style.transition = "opacity 0.4s ease, transform 0.4s ease";
      toast.style.opacity = "0";
      toast.style.transform = "translateX(100%)";
      setTimeout(() => toast.remove(), 400);
    }, 4000);
  }

  // Live SSE Stream Engine
  function initLiveStream() {
    if (!window.EventSource) return;
    const es = new EventSource("/api/stream");

    es.onopen = () => {
      if (el.systemStatusText) el.systemStatusText.textContent = "Live: Connected";
    };

    es.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data);
        if (data.type === "connected") return;

        // Received new metric event
        showToast(`[${data.contract_id}] ${data.agent_name} completed turn (${data.tokens} tokens)`, data.status === "error" ? "error" : "success");
        fetchDashboardData();
        fetchAuditLogs();
      } catch (err) {
        // Ping or malformed
      }
    };

    es.onerror = () => {
      if (el.systemStatusText) el.systemStatusText.textContent = "Live: Reconnecting...";
    };
  }

  // Tab Navigation
  function switchTab(target) {
    const tabs = [
      { btn: el.tabDashboard, view: el.viewDashboard },
      { btn: el.tabAudit, view: el.viewAudit },
      { btn: el.tabWebhooks, view: el.viewWebhooks },
    ];
    tabs.forEach((t) => {
      if (!t.btn || !t.view) return;
      if (t.btn === target) {
        t.btn.classList.add("active");
        t.btn.style.borderColor = "var(--accent-primary)";
        t.view.style.display = "block";
      } else {
        t.btn.classList.remove("active");
        t.btn.style.borderColor = "var(--border-color)";
        t.view.style.display = "none";
      }
    });
    if (target === el.tabAudit) {
      fetchAuditLogs();
    }
  }

  // Audit Logs
  async function fetchAuditLogs() {
    try {
      const userF = el.filterAuditUser ? el.filterAuditUser.value : "";
      const actionF = el.filterAuditAction ? el.filterAuditAction.value : "all";
      const res = await fetch(`/api/audit-logs?limit=50&user=${encodeURIComponent(userF)}&action=${encodeURIComponent(actionF)}`);
      if (!res.ok) return;
      const data = await res.json();
      const logs = data.logs || [];
      if (!el.auditTbody) return;
      if (logs.length === 0) {
        el.auditTbody.innerHTML = `<tr><td colspan="7" class="text-center" style="padding: 1.5rem; color: var(--text-muted);">No audit logs matching filter criteria.</td></tr>`;
        return;
      }
      el.auditTbody.innerHTML = logs.map((l) => `
        <tr>
          <td><strong>#${l.id}</strong></td>
          <td><code>${l.action}</code></td>
          <td>${l.user}</td>
          <td><span class="badge">${l.role}</span></td>
          <td><span class="tag tag-${l.status === "error" ? "error" : "success"}">${l.status}</span></td>
          <td>${l.details}</td>
          <td><small>${new Date(l.timestamp).toLocaleTimeString()}</small></td>
        </tr>
      `).join("");
    } catch (err) {
      console.error("Failed to fetch audit logs:", err);
    }
  }

  // Webhook Test Dispatch
  async function triggerTestWebhook() {
    const ev = el.webhookEventSelect ? el.webhookEventSelect.value : "CRITICAL_SPEND_ALERT";
    try {
      const res = await fetch("/api/webhooks/test", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          event: ev,
          source: "Synapse SDLC Webhook Engine",
          timestamp: new Date().toISOString(),
          environment: "production",
          threshold_usd: 10.0,
        }),
      });
      if (res.ok) {
        const data = await res.json();
        showToast(`Webhook Dispatched: ${data.event_type} (${data.status})`, "success");
        fetchAuditLogs();
      }
    } catch (err) {
      showToast("Failed to dispatch webhook alert", "error");
    }
  }

  // Initialization
  function init() {
    applyTheme(state.theme);
    bindEvents();
    fetchDashboardData();
    fetchAuditLogs();
    initLiveStream();
  }

  // Theme Management
  function applyTheme(theme) {
    document.documentElement.setAttribute("data-theme", theme);
    state.theme = theme;
    localStorage.setItem("synapse_theme", theme);
    if (el.themeIcon) {
      el.themeIcon.textContent = theme === "dark" ? "☀️" : "🌙";
    }
    renderCharts();
  }

  // Event Listeners
  function bindEvents() {
    el.themeToggle.addEventListener("click", () => {
      applyTheme(state.theme === "dark" ? "light" : "dark");
    });

    el.roleSelect.addEventListener("change", (e) => {
      state.currentRole = e.target.value;
      updateRolePermissions();
    });

    el.btnRefresh.addEventListener("click", () => {
      fetchDashboardData();
    });

    el.filterSearch.addEventListener("input", (e) => {
      state.searchFilter = e.target.value.toLowerCase();
      renderTable();
    });

    el.filterStatus.addEventListener("change", (e) => {
      state.statusFilter = e.target.value;
      renderTable();
    });

    el.btnExportCsv.addEventListener("click", () => {
      window.location.href = "/api/export?format=csv";
    });

    el.btnExportJson.addEventListener("click", () => {
      window.location.href = "/api/export?format=json";
    });

    el.btnAddMetric.addEventListener("click", () => {
      el.modalMetric.style.display = "flex";
    });

    el.modalClose.addEventListener("click", () => {
      el.modalMetric.style.display = "none";
    });

    el.btnCancelModal.addEventListener("click", () => {
      el.modalMetric.style.display = "none";
    });

    if (el.tabDashboard) el.tabDashboard.addEventListener("click", () => switchTab(el.tabDashboard));
    if (el.tabAudit) el.tabAudit.addEventListener("click", () => switchTab(el.tabAudit));
    if (el.tabWebhooks) el.tabWebhooks.addEventListener("click", () => switchTab(el.tabWebhooks));

    if (el.btnRefreshAudit) el.btnRefreshAudit.addEventListener("click", fetchAuditLogs);
    if (el.filterAuditUser) el.filterAuditUser.addEventListener("input", fetchAuditLogs);
    if (el.filterAuditAction) el.filterAuditAction.addEventListener("change", fetchAuditLogs);
    if (el.btnTriggerWebhook) el.btnTriggerWebhook.addEventListener("click", triggerTestWebhook);

    el.formRecordMetric.addEventListener("submit", handleMetricSubmit);

    el.btnPurge.addEventListener("click", async () => {
      if (confirm("Are you sure you want to purge all stored telemetry?")) {
        try {
          const res = await fetch("/api/admin/purge", {
            method: "POST",
            headers: { "X-User-Role": state.currentRole },
          });
          if (res.ok) {
            fetchDashboardData();
          } else {
            alert("Error: Insufficient permissions to purge records.");
          }
        } catch (err) {
          console.error("Purge error:", err);
        }
      }
    });
  }

  function updateRolePermissions() {
    if (state.currentRole === "admin") {
      el.btnPurge.style.display = "inline-flex";
      el.btnAddMetric.style.display = "inline-flex";
    } else if (state.currentRole === "operator") {
      el.btnPurge.style.display = "none";
      el.btnAddMetric.style.display = "inline-flex";
    } else {
      // Viewer
      el.btnPurge.style.display = "none";
      el.btnAddMetric.style.display = "none";
    }
  }

  // Data Fetching
  async function fetchDashboardData() {
    try {
      const [statsRes, metricsRes] = await Promise.all([
        fetch("/api/stats"),
        fetch("/api/metrics?limit=100"),
      ]);

      if (statsRes.ok) {
        state.stats = await statsRes.json();
        renderKPIs();
      }

      if (metricsRes.ok) {
        const data = await metricsRes.json();
        state.metrics = data.items || [];
        renderTable();
        renderCharts();
      }

      if (el.footerLastSync) {
        el.footerLastSync.textContent = `Synchronized: ${new Date().toLocaleTimeString()}`;
      }
    } catch (err) {
      console.error("Failed to fetch dashboard data:", err);
    }
  }

  // Render KPIs
  function renderKPIs() {
    const s = state.stats;
    el.kpiRuns.textContent = s.total_runs ? s.total_runs.toLocaleString() : "0";
    el.kpiTokens.textContent = s.total_tokens ? s.total_tokens.toLocaleString() : "0";
    el.kpiSpend.textContent = `$${(s.total_spend_usd || 0).toFixed(4)}`;
    el.kpiDuration.textContent = `${s.average_duration_s || 0}s`;
    el.kpiSuccessRate.textContent = `${s.success_rate_pct || 100}%`;
  }

  // Render Table
  function renderTable() {
    let list = state.metrics.filter((item) => {
      const matchesSearch =
        !state.searchFilter ||
        item.contract_id.toLowerCase().includes(state.searchFilter) ||
        item.agent_name.toLowerCase().includes(state.searchFilter) ||
        item.model.toLowerCase().includes(state.searchFilter);

      const matchesStatus =
        state.statusFilter === "all" || item.status === state.statusFilter;

      return matchesSearch && matchesStatus;
    });

    if (list.length === 0) {
      el.tableBody.innerHTML = `<tr><td colspan="9" class="text-center" style="padding: 2rem; color: var(--text-muted);">No metrics matching current filter criteria.</td></tr>`;
      return;
    }

    el.tableBody.innerHTML = list
      .map(
        (m) => `
      <tr>
        <td><strong>#${m.id}</strong></td>
        <td><code>${m.contract_id}</code></td>
        <td>${m.agent_name}</td>
        <td><small>${m.model}</small></td>
        <td>${m.tokens.toLocaleString()}</td>
        <td>$${m.cost_usd.toFixed(4)}</td>
        <td>${m.duration_seconds}s</td>
        <td><span class="tag tag-${m.status}">${m.status}</span></td>
        <td><small>${new Date(m.timestamp).toLocaleTimeString()}</small></td>
      </tr>
    `
      )
      .join("");
  }

  // Native Interactive SVG Chart Engine
  function renderCharts() {
    renderModelBarChart();
    renderTimelineLineChart();
  }

  function renderModelBarChart() {
    const models = state.stats.models_breakdown || {};
    const entries = Object.entries(models);

    if (entries.length === 0) {
      el.modelChartContainer.innerHTML = `<span style="color: var(--text-muted);">No model data available</span>`;
      return;
    }

    const maxTokens = Math.max(...entries.map((e) => e[1]), 1000);
    const chartHeight = 180;
    const chartWidth = 400;
    const barWidth = 40;
    const gap = 35;
    const colors = ["#3b82f6", "#10b981", "#8b5cf6", "#f59e0b", "#ec4899"];

    let svg = `<svg viewBox="0 0 ${chartWidth} ${chartHeight}" style="width: 100%; height: 100%;">`;

    entries.forEach(([modelName, tokens], idx) => {
      const h = Math.round((tokens / maxTokens) * (chartHeight - 50));
      const x = 30 + idx * (barWidth + gap);
      const y = chartHeight - 30 - h;
      const col = colors[idx % colors.length];

      svg += `
        <rect x="${x}" y="${y}" width="${barWidth}" height="${h}" rx="4" fill="${col}" opacity="0.85">
          <title>${modelName}: ${tokens.toLocaleString()} tokens</title>
        </rect>
        <text x="${x + barWidth / 2}" y="${y - 6}" text-anchor="middle" font-size="10" fill="var(--text-secondary)">${(tokens / 1000).toFixed(0)}k</text>
        <text x="${x + barWidth / 2}" y="${chartHeight - 12}" text-anchor="middle" font-size="9" fill="var(--text-secondary)">${modelName.split(" ")[0]}</text>
      `;
    });

    svg += `</svg>`;
    el.modelChartContainer.innerHTML = svg;
  }

  function renderTimelineLineChart() {
    const items = [...state.metrics].slice(-10).reverse();
    if (items.length < 2) {
      el.timelineChartContainer.innerHTML = `<span style="color: var(--text-muted);">Recording more agent turns to generate trendline...</span>`;
      return;
    }

    const chartHeight = 180;
    const chartWidth = 400;
    const maxCost = Math.max(...items.map((i) => i.cost_usd), 0.01);
    const stepX = (chartWidth - 60) / (items.length - 1);

    const points = items.map((item, idx) => {
      const x = 30 + idx * stepX;
      const y = chartHeight - 30 - (item.cost_usd / maxCost) * (chartHeight - 60);
      return { x, y, cost: item.cost_usd, name: item.contract_id };
    });

    const pathD = points.reduce((acc, p, idx) => {
      return idx === 0 ? `M ${p.x} ${p.y}` : `${acc} L ${p.x} ${p.y}`;
    }, "");

    let svg = `<svg viewBox="0 0 ${chartWidth} ${chartHeight}" style="width: 100%; height: 100%;">`;
    // Line
    svg += `<path d="${pathD}" fill="none" stroke="var(--accent-primary)" stroke-width="3" stroke-linecap="round"/>`;

    // Dots
    points.forEach((p) => {
      svg += `
        <circle cx="${p.x}" cy="${p.y}" r="4" fill="var(--accent-primary)" stroke="var(--bg-card)" stroke-width="2">
          <title>${p.name}: $${p.cost.toFixed(4)}</title>
        </circle>
        <text x="${p.x}" y="${chartHeight - 12}" text-anchor="middle" font-size="8" fill="var(--text-secondary)">${p.name}</text>
      `;
    });

    svg += `</svg>`;
    el.timelineChartContainer.innerHTML = svg;
  }

  // Handle Manual Metric Submission
  async function handleMetricSubmit(e) {
    e.preventDefault();
    const contract = document.getElementById("form-contract-id").value;
    const model = document.getElementById("form-model").value;
    const tokens = parseInt(document.getElementById("form-tokens").value, 10);
    const duration = parseFloat(document.getElementById("form-duration").value);
    const status = document.getElementById("form-status").value;

    const rate = model.includes("Sonnet") ? 0.0066 : model.includes("Codex") ? 0.00475 : 0.00176;
    const cost = (tokens / 1000) * rate;

    try {
      const res = await fetch("/api/metrics", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-User-Role": state.currentRole,
        },
        body: json.stringify({
          contract_id: contract,
          agent_name: document.getElementById("form-contract-id").selectedOptions[0].text.split("(")[1]?.replace(")", "") || contract,
          model: model,
          tokens: tokens,
          cost_usd: cost,
          duration_seconds: duration,
          status: status,
          description: "Live interactive turn submission",
        }),
      });

      if (res.ok) {
        el.modalMetric.style.display = "none";
        fetchDashboardData();
      }
    } catch (err) {
      console.error("Failed to post metric:", err);
    }
  }

  // Boot Application
  window.addEventListener("DOMContentLoaded", init);
})();
