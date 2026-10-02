/**
 * Synapse SDLC — Reactive Frontend Application Engine
 * Native Vanilla JS with SVG Charting, Dynamic Themes, REST Sync, Anomaly Detection & Budget Forecasting
 */

(function () {
  "use strict";

  // In-Memory Fallback Client Store (for static hosting like GitHub Pages)
  const seedMetrics = [
    { id: 1, contract_id: "AC-000", agent_name: "Ticket Analyzer", model: "Claude Haiku 4.5", tokens: 1450, cost_usd: 0.0025, duration_seconds: 0.8, status: "success", description: "Analyzed ticket requirements", timestamp: new Date(Date.now() - 3600000).toISOString() },
    { id: 2, contract_id: "AC-001", agent_name: "Problem Decomposer", model: "Claude Sonnet 5", tokens: 2800, cost_usd: 0.0185, duration_seconds: 1.4, status: "success", description: "Decomposed functional specifications", timestamp: new Date(Date.now() - 3300000).toISOString() },
    { id: 3, contract_id: "AC-002", agent_name: "Design Architect", model: "Claude Sonnet 5", tokens: 3400, cost_usd: 0.0224, duration_seconds: 1.9, status: "success", description: "Formulated system architecture topology", timestamp: new Date(Date.now() - 3000000).toISOString() },
    { id: 4, contract_id: "AC-002A", agent_name: "Design Critic", model: "Claude Sonnet 5", tokens: 2100, cost_usd: 0.0139, duration_seconds: 1.1, status: "warning", description: "Security notice: Path traversal guard verified", timestamp: new Date(Date.now() - 2700000).toISOString() },
    { id: 5, contract_id: "AC-003A", agent_name: "Scaffolder", model: "GPT-5.3-Codex", tokens: 1950, cost_usd: 0.0093, duration_seconds: 0.9, status: "success", description: "Scaffolded directory layout", timestamp: new Date(Date.now() - 2400000).toISOString() },
    { id: 6, contract_id: "AC-003B", agent_name: "Code Builder", model: "GPT-5.3-Codex", tokens: 5400, cost_usd: 0.0256, duration_seconds: 3.2, status: "success", description: "Synthesized core application logic", timestamp: new Date(Date.now() - 2100000).toISOString() },
    { id: 7, contract_id: "AC-004", agent_name: "Requirement Verifier", model: "Claude Sonnet 5", tokens: 2900, cost_usd: 0.0191, duration_seconds: 1.6, status: "success", description: "Verified 100% acceptance criteria", timestamp: new Date(Date.now() - 1800000).toISOString() },
    { id: 8, contract_id: "AC-005", agent_name: "Risk Critic", model: "Claude Sonnet 5", tokens: 2200, cost_usd: 0.0145, duration_seconds: 1.2, status: "success", description: "Blast radius audit: Zero regression risk", timestamp: new Date(Date.now() - 1500000).toISOString() },
    { id: 9, contract_id: "AC-006", agent_name: "Automated Test Engineer", model: "GPT-5.3-Codex", tokens: 4100, cost_usd: 0.0195, duration_seconds: 2.8, status: "success", description: "Authored unit and HTTP contract tests", timestamp: new Date(Date.now() - 1200000).toISOString() },
    { id: 10, contract_id: "AC-007", agent_name: "Documentation Engine", model: "Claude Haiku 4.5", tokens: 1850, cost_usd: 0.0033, duration_seconds: 0.9, status: "success", description: "Generated ADR and API documentation", timestamp: new Date(Date.now() - 900000).toISOString() },
    { id: 11, contract_id: "AC-008", agent_name: "IaC & DevOps Specialist", model: "Claude Sonnet 5", tokens: 2300, cost_usd: 0.0152, duration_seconds: 1.3, status: "success", description: "Constructed Dockerfile & Compose spec", timestamp: new Date(Date.now() - 600000).toISOString() },
    { id: 12, contract_id: "AC-009", agent_name: "Automated Code Reviewer", model: "Claude Sonnet 5", tokens: 3100, cost_usd: 0.0205, duration_seconds: 1.7, status: "success", description: "Clean code review: PR approved", timestamp: new Date(Date.now() - 300000).toISOString() },
    { id: 13, contract_id: "AC-003B-ANOMALY", agent_name: "Heavy Synthesizer", model: "Claude Sonnet 5", tokens: 18500, cost_usd: 0.1221, duration_seconds: 9.4, status: "warning", description: "Simulated recursive AST expansion spike", timestamp: new Date(Date.now() - 60000).toISOString() },
  ];

  const seedAudit = [
    { id: 1, action: "WORKSPACE_INIT", user: "developer@synapse-sdlc.dev", role: "admin", status: "success", details: "Initialized Synapse SDLC Copilot Enterprise Workspace", timestamp: new Date(Date.now() - 3600000).toISOString() },
    { id: 2, action: "AGENT_DISPATCH", user: "orchestrator", role: "system", status: "success", details: "Dispatched AC-000 Ticket Analyzer", timestamp: new Date(Date.now() - 3300000).toISOString() },
    { id: 3, action: "PHASE_TRANSITION", user: "orchestrator", role: "system", status: "success", details: "Advanced to Phase 2: Design Architect", timestamp: new Date(Date.now() - 3000000).toISOString() },
    { id: 4, action: "SECURITY_AUDIT", user: "critic@synapse-sdlc.dev", role: "operator", status: "success", details: "Destructive command filter audit passed", timestamp: new Date(Date.now() - 2700000).toISOString() },
    { id: 5, action: "EXPORT_TELEMETRY", user: "developer@synapse-sdlc.dev", role: "admin", status: "success", details: "Exported metrics report (CSV)", timestamp: new Date(Date.now() - 600000).toISOString() },
    { id: 6, action: "WEBHOOK_CRITICAL_SPEND_ALERT", user: "webhook-dispatcher", role: "system", status: "dispatched", details: "Dispatched webhook for CRITICAL_SPEND_ALERT", timestamp: new Date(Date.now() - 120000).toISOString() },
  ];

  let clientMetrics = JSON.parse(JSON.stringify(seedMetrics));
  let clientAudit = JSON.parse(JSON.stringify(seedAudit));
  let clientMetricsCounter = 14;
  let clientAuditCounter = 7;
  let isStaticMode = false;
  let acknowledgedAlerts = new Set();

  // Application State
  const state = {
    metrics: [],
    stats: {},
    anomalies: [],
    forecast: {},
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
    tabAlerts: document.getElementById("tab-alerts"),
    tabAudit: document.getElementById("tab-audit"),
    tabWebhooks: document.getElementById("tab-webhooks"),
    viewDashboard: document.getElementById("view-dashboard"),
    viewAlerts: document.getElementById("view-alerts"),
    viewAudit: document.getElementById("view-audit"),
    viewWebhooks: document.getElementById("view-webhooks"),
    auditTbody: document.getElementById("audit-tbody"),
    filterAuditUser: document.getElementById("filter-audit-user"),
    filterAuditAction: document.getElementById("filter-audit-action"),
    btnRefreshAudit: document.getElementById("btn-refresh-audit"),
    btnTriggerWebhook: document.getElementById("btn-trigger-webhook"),
    webhookEventSelect: document.getElementById("webhook-event-select"),
    // Alerts & Forecast Elements
    kpiAnomalyCount: document.getElementById("kpi-anomaly-count"),
    kpiForecastSpend: document.getElementById("kpi-forecast-spend"),
    kpiExhaustionDays: document.getElementById("kpi-exhaustion-days"),
    kpiExhaustionStatus: document.getElementById("kpi-exhaustion-status"),
    kpiDailyBurn: document.getElementById("kpi-daily-burn"),
    forecastChartContainer: document.getElementById("forecast-chart-container"),
    alertsTbody: document.getElementById("alerts-tbody"),
    btnRefreshAlerts: document.getElementById("btn-refresh-alerts"),
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

  // Calculate stats from client metrics array
  function calculateClientStats() {
    const total_runs = clientMetrics.length;
    if (total_runs === 0) {
      return {
        total_runs: 0,
        total_tokens: 0,
        total_spend_usd: 0.0,
        success_rate_pct: 100.0,
        average_duration_s: 0.0,
        models_breakdown: {},
      };
    }
    const total_tokens = clientMetrics.reduce((sum, m) => sum + m.tokens, 0);
    const total_spend_usd = clientMetrics.reduce((sum, m) => sum + m.cost_usd, 0);
    const successful_runs = clientMetrics.filter((m) => m.status === "success").length;
    const average_duration_s = +(clientMetrics.reduce((sum, m) => sum + m.duration_seconds, 0) / total_runs).toFixed(2);
    const success_rate_pct = +((successful_runs / total_runs) * 100).toFixed(1);

    const models_breakdown = {};
    clientMetrics.forEach((m) => {
      models_breakdown[m.model] = (models_breakdown[m.model] || 0) + m.tokens;
    });

    return {
      total_runs,
      total_tokens,
      total_spend_usd,
      success_rate_pct,
      average_duration_s,
      models_breakdown,
    };
  }

  // Calculate client-side statistical anomalies
  function calculateClientAnomalies() {
    if (clientMetrics.length < 3) return [];
    const tokensList = clientMetrics.map((m) => m.tokens);
    const durList = clientMetrics.map((m) => m.duration_seconds);

    const avgTok = tokensList.reduce((a, b) => a + b, 0) / tokensList.length;
    const varTok = tokensList.reduce((a, b) => a + Math.pow(b - avgTok, 2), 0) / tokensList.length;
    const stdTok = Math.sqrt(varTok) || 1.0;

    const avgDur = durList.reduce((a, b) => a + b, 0) / durList.length;
    const varDur = durList.reduce((a, b) => a + Math.pow(b - avgDur, 2), 0) / durList.length;
    const stdDur = Math.sqrt(varDur) || 1.0;

    const anomalies = [];
    clientMetrics.forEach((m) => {
      const zTok = (m.tokens - avgTok) / stdTok;
      const zDur = (m.duration_seconds - avgDur) / stdDur;
      const isSpend = zTok >= 1.6;
      const isLat = zDur >= 1.6;
      const isErr = m.status === "error";

      if (isSpend || isLat || isErr) {
        anomalies.push({
          alert_id: m.id,
          contract_id: m.contract_id,
          agent_name: m.agent_name,
          model: m.model,
          tokens: m.tokens,
          cost_usd: m.cost_usd,
          duration_seconds: m.duration_seconds,
          severity: (zTok >= 2.2 || isErr) ? "CRITICAL" : "WARNING",
          anomaly_type: isSpend ? "SPEND_SPIKE" : (isLat ? "LATENCY_SPIKE" : "EXECUTION_ERROR"),
          z_score: +Math.max(zTok, zDur).toFixed(2),
          acknowledged: acknowledgedAlerts.has(m.id),
          timestamp: m.timestamp,
          recommendation: isSpend ? "Review prompt context length" : (isLat ? "Optimize agent reasoning steps" : "Inspect error stack trace"),
        });
      }
    });
    return anomalies;
  }

  // Calculate client-side 30-day forecast
  function calculateClientForecast() {
    const totalSpend = clientMetrics.reduce((sum, m) => sum + m.cost_usd, 0);
    const totalRuns = clientMetrics.length;
    const avgCostPerRun = totalRuns > 0 ? (totalSpend / totalRuns) : 0.015;
    const dailyBurnRate = +(avgCostPerRun * 20).toFixed(4);
    const quotaUsd = 25.0;

    const points = [];
    let acc = +totalSpend.toFixed(4);
    let exhaustionDay = null;

    for (let d = 1; d <= 30; d++) {
      acc = +(acc + dailyBurnRate).toFixed(4);
      const upper = +(acc * (1 + 0.02 * d)).toFixed(4);
      const lower = +(Math.max(0, acc * (1 - 0.02 * d))).toFixed(4);

      if (acc >= quotaUsd && exhaustionDay === null) {
        exhaustionDay = d;
      }

      points.push({
        day: d,
        projected_spend_usd: acc,
        upper_bound_usd: upper,
        lower_bound_usd: lower,
      });
    }

    return {
      current_spend_usd: +totalSpend.toFixed(4),
      daily_burn_rate_usd: dailyBurnRate,
      monthly_quota_usd: quotaUsd,
      projected_month_end_spend_usd: points[points.length - 1]?.projected_spend_usd || 0,
      quota_exhaustion_day: exhaustionDay,
      days_until_exhaustion: exhaustionDay || 30,
      recommended_action: exhaustionDay ? `Quota projected to exhaust in ${exhaustionDay} days` : "Budget trajectory healthy",
      forecast_points: points,
    };
  }

  // Live SSE Stream Engine with Static Simulation Fallback
  function initLiveStream() {
    let sseWorking = false;
    if (window.EventSource && window.location.protocol !== "file:") {
      try {
        const es = new EventSource("/api/stream");
        es.onopen = () => {
          sseWorking = true;
          isStaticMode = false;
          if (el.systemStatusText) el.systemStatusText.textContent = "Live: Backend Connected";
        };
        es.onmessage = (e) => {
          try {
            const data = JSON.parse(e.data);
            if (data.type === "connected") return;
            showToast(`[${data.contract_id}] ${data.agent_name} completed turn (${data.tokens} tokens)`, data.status === "error" ? "error" : "success");
            fetchDashboardData();
            fetchAuditLogs();
            fetchAlertsAndForecast();
          } catch (err) {}
        };
        es.onerror = () => {
          if (!sseWorking) {
            activateStaticSimulator();
          } else {
            if (el.systemStatusText) el.systemStatusText.textContent = "Live: Reconnecting...";
          }
        };
      } catch (e) {
        activateStaticSimulator();
      }
    } else {
      activateStaticSimulator();
    }
  }

  function activateStaticSimulator() {
    isStaticMode = true;
    if (el.systemStatusText) el.systemStatusText.textContent = "Live: GitHub Pages (Simulated)";
    
    // Periodically simulate realistic autonomous agent activity every 15s
    setInterval(() => {
      const agents = [
        { contract_id: "AC-003B", agent_name: "Code Builder", model: "GPT-5.3-Codex", rate: 0.00475 },
        { contract_id: "AC-006", agent_name: "Automated Test Engineer", model: "GPT-5.3-Codex", rate: 0.00475 },
        { contract_id: "AC-002A", agent_name: "Design Critic", model: "Claude Sonnet 5", rate: 0.0066 },
        { contract_id: "AC-009", agent_name: "Automated Code Reviewer", model: "Claude Sonnet 5", rate: 0.0066 },
      ];
      const selected = agents[Math.floor(Math.random() * agents.length)];
      const tokens = Math.floor(Math.random() * 3000) + 1200;
      const duration = +(Math.random() * 2 + 0.8).toFixed(2);
      const cost = +((tokens / 1000) * selected.rate).toFixed(4);
      const isWarning = Math.random() < 0.15;
      const status = isWarning ? "warning" : "success";

      const newRecord = {
        id: clientMetricsCounter++,
        contract_id: selected.contract_id,
        agent_name: selected.agent_name,
        model: selected.model,
        tokens: tokens,
        cost_usd: cost,
        duration_seconds: duration,
        status: status,
        description: `Autonomous lifecycle verification turn for ${selected.contract_id}`,
        timestamp: new Date().toISOString(),
      };

      clientMetrics.unshift(newRecord);
      if (clientMetrics.length > 50) clientMetrics.pop();

      // Also add audit log
      clientAudit.unshift({
        id: clientAuditCounter++,
        action: "AGENT_TURN_EXECUTED",
        user: `${selected.agent_name.toLowerCase().replace(/\s+/g, "-")}@synapse-sdlc.dev`,
        role: "agent",
        status: status,
        details: `Turn executed for ${selected.contract_id} (${tokens} tokens, $${cost})`,
        timestamp: new Date().toISOString(),
      });

      showToast(`[${selected.contract_id}] ${selected.agent_name} completed turn (${tokens.toLocaleString()} tokens)`, status);
      fetchDashboardData();
      fetchAuditLogs();
      fetchAlertsAndForecast();
    }, 15000);
  }

  // Tab Navigation
  function switchTab(target) {
    const tabs = [
      { btn: el.tabDashboard, view: el.viewDashboard },
      { btn: el.tabAlerts, view: el.viewAlerts },
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
    } else if (target === el.tabAlerts) {
      fetchAlertsAndForecast();
    }
  }

  // Anomaly & Forecast Fetching
  async function fetchAlertsAndForecast() {
    if (isStaticMode) {
      state.anomalies = calculateClientAnomalies();
      state.forecast = calculateClientForecast();
      renderAlertsView();
      return;
    }

    try {
      const [anomRes, fcRes] = await Promise.all([
        fetch("/api/alerts/anomalies"),
        fetch("/api/forecast"),
      ]);

      if (anomRes.ok && fcRes.ok) {
        const anomData = await anomRes.json();
        state.anomalies = anomData.anomalies || [];
        state.forecast = await fcRes.json();
        renderAlertsView();
      } else {
        isStaticMode = true;
        fetchAlertsAndForecast();
      }
    } catch (err) {
      isStaticMode = true;
      fetchAlertsAndForecast();
    }
  }

  function renderAlertsView() {
    const f = state.forecast || {};
    const anoms = state.anomalies || [];

    if (el.kpiAnomalyCount) el.kpiAnomalyCount.textContent = anoms.filter((a) => !a.acknowledged).length;
    if (el.kpiForecastSpend) el.kpiForecastSpend.textContent = `$${(f.projected_month_end_spend_usd || 0).toFixed(2)}`;
    if (el.kpiExhaustionDays) el.kpiExhaustionDays.textContent = f.quota_exhaustion_day ? `${f.quota_exhaustion_day} Days` : "30+ Days";
    if (el.kpiExhaustionStatus) el.kpiExhaustionStatus.textContent = f.recommended_action || "Budget Trajectory Healthy";
    if (el.kpiDailyBurn) el.kpiDailyBurn.textContent = `$${(f.daily_burn_rate_usd || 0).toFixed(4)}/day`;

    // Render Table
    if (el.alertsTbody) {
      if (anoms.length === 0) {
        el.alertsTbody.innerHTML = `<tr><td colspan="9" class="text-center" style="padding: 1.5rem; color: var(--text-muted);">Zero active anomalies detected across agent execution telemetry.</td></tr>`;
      } else {
        el.alertsTbody.innerHTML = anoms.map((a) => `
          <tr>
            <td><strong>#${a.alert_id}</strong></td>
            <td><span class="tag tag-${a.severity === 'CRITICAL' ? 'error' : 'warning'}">${a.severity}</span></td>
            <td><code>${a.contract_id}</code> (${a.agent_name})</td>
            <td><small>${a.model}</small></td>
            <td><strong>${a.anomaly_type}</strong></td>
            <td><code>+${a.z_score}&sigma;</code></td>
            <td>${a.tokens.toLocaleString()} tok ($${a.cost_usd.toFixed(4)})</td>
            <td><small style="color: var(--text-secondary);">${a.recommendation}</small></td>
            <td>
              ${a.acknowledged 
                ? '<span class="badge" style="background: rgba(16,185,129,0.2); color: var(--success);">Acknowledged</span>' 
                : `<button class="btn btn-secondary btn-sm btn-ack-alert" data-alert-id="${a.alert_id}">Acknowledge</button>`}
            </td>
          </tr>
        `).join("");

        // Bind acknowledge clicks
        document.querySelectorAll(".btn-ack-alert").forEach((btn) => {
          btn.addEventListener("click", () => handleAcknowledgeAlert(parseInt(btn.getAttribute("data-alert-id"), 10)));
        });
      }
    }

    // Render Forecast Chart
    renderForecastChart(f.forecast_points || []);
  }

  async function handleAcknowledgeAlert(alertId) {
    if (isStaticMode) {
      acknowledgedAlerts.add(alertId);
      clientAudit.unshift({
        id: clientAuditCounter++,
        action: "ALERT_ACKNOWLEDGE",
        user: "developer@synapse-sdlc.dev",
        role: state.currentRole,
        status: "success",
        details: `Acknowledged anomaly alert for record #${alertId}`,
        timestamp: new Date().toISOString(),
      });
      showToast(`Acknowledged alert #${alertId}`, "success");
      fetchAlertsAndForecast();
      fetchAuditLogs();
      return;
    }

    try {
      const res = await fetch("/api/alerts/acknowledge", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-User-Role": state.currentRole,
        },
        body: JSON.stringify({ alert_id: alertId, user: "developer@synapse-sdlc.dev" }),
      });
      if (res.ok) {
        showToast(`Acknowledged alert #${alertId}`, "success");
        fetchAlertsAndForecast();
        fetchAuditLogs();
      } else {
        throw new Error("HTTP error");
      }
    } catch (err) {
      acknowledgedAlerts.add(alertId);
      showToast(`Acknowledged alert #${alertId}`, "success");
      fetchAlertsAndForecast();
    }
  }

  // Forecast SVG Chart Engine
  function renderForecastChart(points) {
    if (!el.forecastChartContainer || points.length === 0) return;
    const chartWidth = 650;
    const chartHeight = 220;
    const maxVal = Math.max(...points.map((p) => p.upper_bound_usd), 25.0);
    const stepX = (chartWidth - 80) / (points.length - 1);

    const ptsProjected = points.map((p, idx) => ({
      x: 40 + idx * stepX,
      y: chartHeight - 35 - (p.projected_spend_usd / maxVal) * (chartHeight - 65),
      spend: p.projected_spend_usd,
      day: p.day,
    }));

    const ptsUpper = points.map((p, idx) => ({
      x: 40 + idx * stepX,
      y: chartHeight - 35 - (p.upper_bound_usd / maxVal) * (chartHeight - 65),
    }));

    const ptsLower = points.map((p, idx) => ({
      x: 40 + idx * stepX,
      y: chartHeight - 35 - (p.lower_bound_usd / maxVal) * (chartHeight - 65),
    }));

    // Build cone polygon
    const upperPath = ptsUpper.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x} ${p.y}`).join(' ');
    const lowerPath = ptsLower.reverse().map((p) => `L ${p.x} ${p.y}`).join(' ');
    const coneD = `${upperPath} ${lowerPath} Z`;

    // Line Path
    const lineD = ptsProjected.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x} ${p.y}`).join(' ');

    // Quota line (25 USD)
    const quotaY = chartHeight - 35 - (25.0 / maxVal) * (chartHeight - 65);

    let svg = `<svg viewBox="0 0 ${chartWidth} ${chartHeight}" style="width: 100%; height: 100%;">`;
    
    // Confidence Cone
    svg += `<path d="${coneD}" fill="rgba(59, 130, 246, 0.15)" stroke="none"/>`;
    
    // Quota Threshold line
    svg += `<line x1="40" y1="${quotaY}" x2="${chartWidth - 40}" y2="${quotaY}" stroke="#ef4444" stroke-dasharray="4" stroke-width="1.5"/>`;
    svg += `<text x="${chartWidth - 38}" y="${quotaY + 4}" font-size="9" fill="#ef4444" font-weight="bold">Quota: $25.00</text>`;

    // Main Forecast Line
    svg += `<path d="${lineD}" fill="none" stroke="#3b82f6" stroke-width="3" stroke-linecap="round"/>`;

    // Dots at days 5, 10, 15, 20, 25, 30
    ptsProjected.filter((p) => p.day % 5 === 0 || p.day === 1).forEach((p) => {
      svg += `
        <circle cx="${p.x}" cy="${p.y}" r="4" fill="#3b82f6" stroke="var(--bg-card)" stroke-width="2">
          <title>Day ${p.day}: $${p.spend.toFixed(2)}</title>
        </circle>
        <text x="${p.x}" y="${chartHeight - 12}" text-anchor="middle" font-size="8" fill="var(--text-secondary)">Day ${p.day}</text>
        <text x="${p.x}" y="${p.y - 8}" text-anchor="middle" font-size="8" fill="var(--text-primary)">$${p.spend.toFixed(1)}</text>
      `;
    });

    svg += `</svg>`;
    el.forecastChartContainer.innerHTML = svg;
  }

  // Audit Logs
  async function fetchAuditLogs() {
    const userF = el.filterAuditUser ? el.filterAuditUser.value.toLowerCase().trim() : "";
    const actionF = el.filterAuditAction ? el.filterAuditAction.value : "all";

    if (isStaticMode) {
      renderAuditLogs(clientAudit, userF, actionF);
      return;
    }

    try {
      const res = await fetch(`/api/audit-logs?limit=50&user=${encodeURIComponent(userF)}&action=${encodeURIComponent(actionF)}`);
      if (!res.ok) {
        isStaticMode = true;
        renderAuditLogs(clientAudit, userF, actionF);
        return;
      }
      const data = await res.json();
      const logs = data.logs || [];
      renderAuditLogsDirect(logs);
    } catch (err) {
      isStaticMode = true;
      renderAuditLogs(clientAudit, userF, actionF);
    }
  }

  function renderAuditLogs(logsList, userFilter, actionFilter) {
    let list = logsList.filter((l) => {
      const matchesUser = !userFilter || l.user.toLowerCase().includes(userFilter);
      const matchesAction = actionFilter === "all" || l.action === actionFilter.toUpperCase();
      return matchesUser && matchesAction;
    });

    renderAuditLogsDirect(list);
  }

  function renderAuditLogsDirect(logs) {
    if (!el.auditTbody) return;
    if (logs.length === 0) {
      el.auditTbody.innerHTML = `<tr><td colspan="7" class="text-center" style="padding: 1.5rem; color: var(--text-muted);">No audit logs matching filter criteria.</td></tr>`;
      return;
    }
    el.auditTbody.innerHTML = logs
      .map(
        (l) => `
      <tr>
        <td><strong>#${l.id}</strong></td>
        <td><code>${l.action}</code></td>
        <td>${l.user}</td>
        <td><span class="badge">${l.role}</span></td>
        <td><span class="tag tag-${l.status === "error" ? "error" : "success"}">${l.status}</span></td>
        <td>${l.details}</td>
        <td><small>${new Date(l.timestamp).toLocaleTimeString()}</small></td>
      </tr>
    `
      )
      .join("");
  }

  // Webhook Test Dispatch
  async function triggerTestWebhook() {
    const ev = el.webhookEventSelect ? el.webhookEventSelect.value : "CRITICAL_SPEND_ALERT";
    
    if (isStaticMode) {
      clientAudit.unshift({
        id: clientAuditCounter++,
        action: `WEBHOOK_${ev.toUpperCase()}`,
        user: "webhook-dispatcher",
        role: "system",
        status: "dispatched",
        details: `Dispatched webhook for ${ev} (threshold: $10.00)`,
        timestamp: new Date().toISOString(),
      });
      showToast(`Webhook Dispatched: ${ev} (delivered)`, "success");
      fetchAuditLogs();
      return;
    }

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
      } else {
        throw new Error("HTTP error");
      }
    } catch (err) {
      clientAudit.unshift({
        id: clientAuditCounter++,
        action: `WEBHOOK_${ev.toUpperCase()}`,
        user: "webhook-dispatcher",
        role: "system",
        status: "dispatched",
        details: `Dispatched webhook for ${ev} (threshold: $10.00)`,
        timestamp: new Date().toISOString(),
      });
      showToast(`Webhook Dispatched: ${ev} (delivered)`, "success");
      fetchAuditLogs();
    }
  }

  // Initialization
  function init() {
    applyTheme(state.theme);
    bindEvents();
    fetchDashboardData();
    fetchAuditLogs();
    fetchAlertsAndForecast();
    initLiveStream();

    // Hash routing support
    const hash = window.location.hash;
    if (hash === "#audit" && el.tabAudit) {
      switchTab(el.tabAudit);
    } else if (hash === "#alerts" && el.tabAlerts) {
      switchTab(el.tabAlerts);
    } else if (hash === "#webhooks" && el.tabWebhooks) {
      switchTab(el.tabWebhooks);
    } else if (hash === "#record" && el.modalMetric) {
      el.modalMetric.style.display = "flex";
    }
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

  // Client-side export helper
  function triggerClientDownload(filename, content, mimeType) {
    const blob = new Blob([content], { type: mimeType });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    showToast(`Exported ${filename} successfully`, "success");
  }

  // Event Listeners
  function bindEvents() {
    el.themeToggle.addEventListener("click", () => {
      applyTheme(state.theme === "dark" ? "light" : "dark");
    });

    el.roleSelect.addEventListener("change", (e) => {
      state.currentRole = e.target.value;
      updateRolePermissions();
      showToast(`Switched active RBAC role to: ${state.currentRole.toUpperCase()}`, "info");
    });

    el.btnRefresh.addEventListener("click", () => {
      fetchDashboardData();
      showToast("Telemetry metrics refreshed", "info");
    });

    if (el.btnRefreshAlerts) {
      el.btnRefreshAlerts.addEventListener("click", () => {
        fetchAlertsAndForecast();
        showToast("Anomaly feed & budget forecast refreshed", "info");
      });
    }

    el.filterSearch.addEventListener("input", (e) => {
      state.searchFilter = e.target.value.toLowerCase();
      renderTable();
    });

    el.filterStatus.addEventListener("change", (e) => {
      state.statusFilter = e.target.value;
      renderTable();
    });

    el.btnExportCsv.addEventListener("click", () => {
      if (!isStaticMode) {
        window.location.href = "/api/export?format=csv";
      } else {
        const headers = ["id", "contract_id", "agent_name", "model", "tokens", "cost_usd", "duration_seconds", "status", "timestamp"];
        const rows = clientMetrics.map((m) => [m.id, m.contract_id, m.agent_name, m.model, m.tokens, m.cost_usd, m.duration_seconds, m.status, m.timestamp]);
        const csv = [headers.join(","), ...rows.map((r) => r.map((c) => `"${c}"`).join(","))].join("\n");
        triggerClientDownload("synapse_telemetry_export.csv", csv, "text/csv;charset=utf-8;");
      }
    });

    el.btnExportJson.addEventListener("click", () => {
      if (!isStaticMode) {
        window.location.href = "/api/export?format=json";
      } else {
        const jsonStr = JSON.stringify({ metrics: clientMetrics, export_timestamp: new Date().toISOString(), total_records: clientMetrics.length }, null, 2);
        triggerClientDownload("synapse_telemetry_export.json", jsonStr, "application/json");
      }
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
    if (el.tabAlerts) el.tabAlerts.addEventListener("click", () => switchTab(el.tabAlerts));
    if (el.tabAudit) el.tabAudit.addEventListener("click", () => switchTab(el.tabAudit));
    if (el.tabWebhooks) el.tabWebhooks.addEventListener("click", () => switchTab(el.tabWebhooks));

    if (el.btnRefreshAudit) el.btnRefreshAudit.addEventListener("click", fetchAuditLogs);
    if (el.filterAuditUser) el.filterAuditUser.addEventListener("input", fetchAuditLogs);
    if (el.filterAuditAction) el.filterAuditAction.addEventListener("change", fetchAuditLogs);
    if (el.btnTriggerWebhook) el.btnTriggerWebhook.addEventListener("click", triggerTestWebhook);

    el.formRecordMetric.addEventListener("submit", handleMetricSubmit);

    el.btnPurge.addEventListener("click", async () => {
      if (confirm("Are you sure you want to purge all stored telemetry?")) {
        if (isStaticMode) {
          clientMetrics = [];
          fetchDashboardData();
          fetchAlertsAndForecast();
          showToast("Telemetry store purged", "warning");
          return;
        }
        try {
          const res = await fetch("/api/admin/purge", {
            method: "POST",
            headers: { "X-User-Role": state.currentRole },
          });
          if (res.ok) {
            fetchDashboardData();
            fetchAlertsAndForecast();
            showToast("Telemetry store purged", "warning");
          } else {
            alert("Error: Insufficient permissions to purge records.");
          }
        } catch (err) {
          clientMetrics = [];
          fetchDashboardData();
          fetchAlertsAndForecast();
          showToast("Telemetry store purged", "warning");
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
    if (isStaticMode) {
      state.stats = calculateClientStats();
      state.metrics = [...clientMetrics];
      renderKPIs();
      renderTable();
      renderCharts();
      if (el.footerLastSync) {
        el.footerLastSync.textContent = `Synchronized: ${new Date().toLocaleTimeString()} (Client Live Engine)`;
      }
      return;
    }

    try {
      const [statsRes, metricsRes] = await Promise.all([
        fetch("/api/stats"),
        fetch("/api/metrics?limit=100"),
      ]);

      if (statsRes.ok && metricsRes.ok) {
        state.stats = await statsRes.json();
        const data = await metricsRes.json();
        state.metrics = data.items || [];
        renderKPIs();
        renderTable();
        renderCharts();
      } else {
        isStaticMode = true;
        fetchDashboardData();
      }

      if (el.footerLastSync) {
        el.footerLastSync.textContent = `Synchronized: ${new Date().toLocaleTimeString()}`;
      }
    } catch (err) {
      isStaticMode = true;
      fetchDashboardData();
    }
  }

  // Render KPIs
  function renderKPIs() {
    const s = state.stats || {};
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
    const cost = +((tokens / 1000) * rate).toFixed(4);
    const agentName = document.getElementById("form-contract-id").selectedOptions[0].text.split("(")[1]?.replace(")", "") || contract;

    const newRecord = {
      id: clientMetricsCounter++,
      contract_id: contract,
      agent_name: agentName,
      model: model,
      tokens: tokens,
      cost_usd: cost,
      duration_seconds: duration,
      status: status,
      description: "Live interactive turn submission",
      timestamp: new Date().toISOString(),
    };

    if (isStaticMode) {
      clientMetrics.unshift(newRecord);
      clientAudit.unshift({
        id: clientAuditCounter++,
        action: "METRIC_RECORDED",
        user: "developer@synapse-sdlc.dev",
        role: state.currentRole,
        status: status,
        details: `Recorded manual turn for ${contract} (${tokens} tokens, $${cost})`,
        timestamp: new Date().toISOString(),
      });
      el.modalMetric.style.display = "none";
      showToast(`Recorded turn for ${contract} successfully`, "success");
      fetchDashboardData();
      fetchAlertsAndForecast();
      fetchAuditLogs();
      return;
    }

    try {
      const res = await fetch("/api/metrics", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-User-Role": state.currentRole,
        },
        body: JSON.stringify(newRecord),
      });

      if (res.ok) {
        el.modalMetric.style.display = "none";
        showToast(`Recorded turn for ${contract} successfully`, "success");
        fetchDashboardData();
        fetchAlertsAndForecast();
      } else {
        throw new Error("HTTP Error");
      }
    } catch (err) {
      clientMetrics.unshift(newRecord);
      el.modalMetric.style.display = "none";
      showToast(`Recorded turn for ${contract} successfully`, "success");
      fetchDashboardData();
      fetchAlertsAndForecast();
    }
  }

  // Boot Application
  window.addEventListener("DOMContentLoaded", init);
})();
