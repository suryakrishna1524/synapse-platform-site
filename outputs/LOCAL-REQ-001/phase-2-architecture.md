# Phase 2: System Architecture & API Specification — `LOCAL-REQ-001`

## 1. System Architecture Diagram

```
+-------------------------------------------------------------+
|                     Client Browser                          |
|  (HTML5 + Vanilla Modern JS + SVG Charts + CSS Variables)   |
+------------------------------+------------------------------+
                               | HTTP / REST (Fetch API)
                               v
+-------------------------------------------------------------+
|               Python Platform Server (src/server.py)        |
|  - Router & Dispatcher      - Static Asset Pipeline         |
|  - CORS & Header Security   - Error Boundary Handlers       |
+------------------------------+------------------------------+
                               | In-Memory Data Access
                               v
+-------------------------------------------------------------+
|               Telemetry Data Store (src/store.py)           |
|  - Thread-Safe Metric Index - Filter & Aggregation Engine   |
|  - JSON & CSV Serializer    - Mock RBAC Session Authority   |
+-------------------------------------------------------------+
```

---

## 2. REST API Contract

### Endpoints
1. `GET /api/health`
   - Returns server health status, uptime, version, and memory profile.
   - Response: `{"status": "ok", "uptime_seconds": 120.5, "version": "1.0.0", "active_threads": 2}`

2. `GET /api/stats`
   - Returns high-level KPI metrics.
   - Response: `{"total_runs": 142, "total_tokens": 1245000, "total_spend_usd": 7.4520, "active_plan": "Enterprise", "success_rate_pct": 98.6}`

3. `GET /api/metrics`
   - Parameters: `agent` (optional), `status` (optional), `limit` (default: 50).
   - Response: `{"count": 50, "items": [{"id": 1, "agent": "AC-ORCH", "model": "Claude Sonnet 5", "tokens": 3200, "cost_usd": 0.0211, "duration_s": 2.4, "status": "success", "timestamp": "2026-10-02T12:00:00Z"}]}`

4. `POST /api/metrics`
   - Adds a new metric record.
   - Payload: `{"agent": "AC-003B", "model": "GPT-5.3-Codex", "tokens": 4500, "duration_s": 3.1, "status": "success"}`
   - Response: `{"status": "created", "id": 143}`

5. `GET /api/export`
   - Parameters: `format` (`csv` or `json`).
   - Content-Type: `text/csv` or `application/json`.
   - Downloads complete historical dataset with `Content-Disposition: attachment; filename=synapse_telemetry.csv`.

6. `GET /api/auth/me`
   - Returns active user profile and permissions based on `X-User-Role` or `Authorization` header.
   - Response: `{"user": "dev-lead@synapse-sdlc.dev", "role": "admin", "permissions": ["read", "write", "purge", "export"]}`
