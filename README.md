# Synapse SDLC — Enterprise Observability & Telemetry Hub

A production-grade, zero-dependency telemetry monitoring platform and interactive analytics dashboard built for enterprise multi-agent software development lifecycles.

---

## 🌟 Key Features
- **Interactive Web Dashboard:** Modern Dark/Light theme UI with live KPI counters and real-time SVG charts.
- **High-Performance REST Server:** Built on native Python standard library with zero external pip dependencies.
- **Thread-Safe Telemetry Store:** In-memory sliding-window circular buffer with dynamic filtering and aggregation.
- **Data Export Engine:** Instant export to CSV (with formula injection sanitization) and structured JSON.
- **RBAC Mock Authentication:** Role-based access control with permissions for `admin`, `operator`, and `viewer`.
- **Security Hardening:** Path traversal protection, body size clamping (1MB max), and input sanitization.

---

## 🚀 Quickstart

### 1. Launch the Application Server
```bash
python src/server.py 8080
```
Open your browser at `http://127.0.0.1:8080` to access the interactive dashboard.

### 2. Run Automated Test Suite
```bash
python -m unittest discover tests
```

### 3. Docker Deployment
```bash
docker build -t synapse-platform:latest .
docker run -p 8080:8080 synapse-platform:latest
```

---

## 📡 REST API Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/health` | Service health, uptime, and system version |
| `GET` | `/api/stats` | Aggregated telemetry KPIs and model breakdowns |
| `GET` | `/api/metrics` | Filtered list of agent turn execution metrics |
| `POST` | `/api/metrics` | Records a new agent execution metric |
| `GET` | `/api/export` | Downloads metrics as `csv` or `json` |
| `GET` | `/api/auth/me` | Returns current user role and permissions |
| `POST` | `/api/admin/purge` | Purges metrics database (Admin role required) |
