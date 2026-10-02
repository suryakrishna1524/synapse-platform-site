"""Telemetry Data Store — In-Memory Thread-Safe Metrics, Filtering & Export Engine."""

import csv
import io
import json
import queue
import threading
import time
from typing import Dict, List, Any, Optional, Tuple


class TelemetryStore:
    """Thread-safe storage and querying of SDLC telemetry events and metrics."""

    MAX_RECORDS = 5000
    MAX_AUDIT_LOGS = 2000

    def __init__(self):
        self._lock = threading.Lock()
        self._records: List[Dict[str, Any]] = []
        self._audit_logs: List[Dict[str, Any]] = []
        self._rate_limits: Dict[str, List[float]] = {}
        self._subscribers: List[queue.Queue] = []
        self._id_counter = 1
        self._audit_id_counter = 1
        self._seed_initial_data()
        self._seed_initial_audit_logs()

    def _seed_initial_data(self) -> None:
        """Populates realistic seed telemetry to enable instant interactive visualization."""
        seed_events = [
            ("AC-000", "Ticket Analyzer", "Claude Haiku 4.5", 1450, 0.0025, 0.8, "success", "Analyzed ticket requirements"),
            ("AC-001", "Problem Decomposer", "Claude Sonnet 5", 2800, 0.0185, 1.4, "success", "Decomposed functional specifications"),
            ("AC-002", "Design Architect", "Claude Sonnet 5", 3400, 0.0224, 1.9, "success", "Formulated system architecture topology"),
            ("AC-002A", "Design Critic", "Claude Sonnet 5", 2100, 0.0139, 1.1, "warning", "Security notice: Path traversal guard verified"),
            ("AC-003A", "Scaffolder", "GPT-5.3-Codex", 1950, 0.0093, 0.9, "success", "Scaffolded directory layout"),
            ("AC-003B", "Code Builder", "GPT-5.3-Codex", 5400, 0.0256, 3.2, "success", "Synthesized core application logic"),
            ("AC-004", "Requirement Verifier", "Claude Sonnet 5", 2900, 0.0191, 1.6, "success", "Verified 100% acceptance criteria"),
            ("AC-005", "Risk Critic", "Claude Sonnet 5", 2200, 0.0145, 1.2, "success", "Blast radius audit: Zero regression risk"),
            ("AC-006", "Automated Test Engineer", "GPT-5.3-Codex", 4100, 0.0195, 2.8, "success", "Authored unit and HTTP contract tests"),
            ("AC-007", "Documentation Engine", "Claude Haiku 4.5", 1850, 0.0033, 0.9, "success", "Generated ADR and API documentation"),
            ("AC-008", "IaC & DevOps Specialist", "Claude Sonnet 5", 2300, 0.0152, 1.3, "success", "Constructed Dockerfile & Compose spec"),
            ("AC-009", "Automated Code Reviewer", "Claude Sonnet 5", 3100, 0.0205, 1.7, "success", "Clean code review: PR approved"),
        ]

        now = time.time()
        for idx, (contract, name, model, tokens, cost, dur, status, desc) in enumerate(seed_events):
            item_time = now - ((len(seed_events) - idx) * 300)
            self._records.append({
                "id": self._id_counter,
                "contract_id": contract,
                "agent_name": name,
                "model": model,
                "tokens": tokens,
                "cost_usd": cost,
                "duration_seconds": dur,
                "status": status,
                "description": desc,
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(item_time)),
            })
            self._id_counter += 1

    def add_metric(
        self,
        contract_id: str,
        agent_name: str,
        model: str,
        tokens: int,
        cost_usd: float,
        duration_seconds: float,
        status: str = "success",
        description: str = "",
    ) -> Dict[str, Any]:
        """Thread-safely adds a new metric record with sliding-window size bounding."""
        with self._lock:
            record = {
                "id": self._id_counter,
                "contract_id": str(contract_id).strip(),
                "agent_name": str(agent_name).strip() or "Anonymous Agent",
                "model": str(model).strip() or "Auto Model",
                "tokens": max(0, int(tokens)),
                "cost_usd": max(0.0, round(float(cost_usd), 4)),
                "duration_seconds": max(0.01, round(float(duration_seconds), 2)),
                "status": str(status).lower() if str(status).lower() in ("success", "warning", "error") else "success",
                "description": self._sanitize_text(description),
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            }
            self._id_counter += 1
            self._records.append(record)

            # Enforce max record ceiling
            if len(self._records) > self.MAX_RECORDS:
                self._records = self._records[-self.MAX_RECORDS:]

            # Broadcast to active SSE stream subscribers
            for q in list(self._subscribers):
                try:
                    q.put_nowait(record)
                except Exception:
                    pass

            return record

    def subscribe(self) -> queue.Queue:
        with self._lock:
            q: queue.Queue = queue.Queue(maxsize=100)
            self._subscribers.append(q)
            return q

    def unsubscribe(self, q: queue.Queue) -> None:
        with self._lock:
            if q in self._subscribers:
                self._subscribers.remove(q)

    def get_metrics(
        self,
        agent_filter: Optional[str] = None,
        status_filter: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Returns filtered list of metric items."""
        with self._lock:
            results = list(self._records)

        if agent_filter:
            af = agent_filter.lower().strip()
            results = [r for r in results if af in r["contract_id"].lower() or af in r["agent_name"].lower()]

        if status_filter and status_filter.lower() != "all":
            sf = status_filter.lower().strip()
            results = [r for r in results if r["status"] == sf]

        results.reverse()
        return results[:limit]

    def get_statistics(self) -> Dict[str, Any]:
        """Calculates aggregated performance statistics."""
        with self._lock:
            total_runs = len(self._records)
            if total_runs == 0:
                return {
                    "total_runs": 0,
                    "total_tokens": 0,
                    "total_spend_usd": 0.0,
                    "success_rate_pct": 100.0,
                    "average_duration_s": 0.0,
                    "models_breakdown": {},
                }

            total_tokens = sum(r["tokens"] for r in self._records)
            total_spend = sum(r["cost_usd"] for r in self._records)
            successful_runs = sum(1 for r in self._records if r["status"] == "success")
            avg_duration = sum(r["duration_seconds"] for r in self._records) / total_runs

            models: Dict[str, int] = {}
            for r in self._records:
                m = r["model"]
                models[m] = models.get(m, 0) + r["tokens"]

            return {
                "total_runs": total_runs,
                "total_tokens": total_tokens,
                "total_spend_usd": round(total_spend, 4),
                "success_rate_pct": round((successful_runs / total_runs) * 100.0, 1),
                "average_duration_s": round(avg_duration, 2),
                "models_breakdown": models,
            }

    def export_data(self, fmt: str = "json") -> Tuple[str, str]:
        """Exports data in CSV or JSON with CSV formula injection sanitization."""
        with self._lock:
            items = list(self._records)

        if fmt.lower() == "csv":
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(["ID", "Contract ID", "Agent Name", "Model", "Tokens", "Cost (USD)", "Duration (s)", "Status", "Timestamp", "Description"])
            for r in items:
                writer.writerow([
                    r["id"],
                    r["contract_id"],
                    r["agent_name"],
                    r["model"],
                    r["tokens"],
                    f"{r['cost_usd']:.4f}",
                    f"{r['duration_seconds']:.2f}",
                    r["status"],
                    r["timestamp"],
                    self._csv_sanitize(r["description"]),
                ])
            return output.getvalue(), "text/csv"
        else:
            return json.dumps({"exported_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "metrics": items}, indent=2), "application/json"

    def purge(self) -> int:
        """Purges stored metrics (Admin-restricted operation)."""
        with self._lock:
            count = len(self._records)
            self._records.clear()
            return count

    def _seed_initial_audit_logs(self) -> None:
        """Seeds initial audit events."""
        seed_audit = [
            ("WORKSPACE_INIT", "developer@synapse-sdlc.dev", "admin", "success", "Initialized Synapse SDLC Copilot Enterprise Workspace"),
            ("AGENT_DISPATCH", "orchestrator", "system", "success", "Dispatched AC-000 Ticket Analyzer"),
            ("PHASE_TRANSITION", "orchestrator", "system", "success", "Advanced to Phase 2: Design Architect"),
            ("SECURITY_AUDIT", "critic@synapse-sdlc.dev", "operator", "success", "Destructive command filter audit passed"),
            ("EXPORT_TELEMETRY", "developer@synapse-sdlc.dev", "admin", "success", "Exported metrics report (CSV)"),
        ]
        now = time.time()
        for idx, (action, user, role, status, details) in enumerate(seed_audit):
            self._audit_logs.append({
                "id": self._audit_id_counter,
                "action": action,
                "user": user,
                "role": role,
                "status": status,
                "details": details,
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now - ((len(seed_audit) - idx) * 400))),
            })
            self._audit_id_counter += 1

    def add_audit_log(self, action: str, user: str, role: str, status: str = "success", details: str = "") -> Dict[str, Any]:
        """Thread-safely appends an immutable security audit event."""
        with self._lock:
            entry = {
                "id": self._audit_id_counter,
                "action": str(action).strip().upper(),
                "user": str(user).strip() or "anonymous",
                "role": str(role).strip().lower(),
                "status": str(status).strip().lower(),
                "details": self._sanitize_text(details),
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            }
            self._audit_id_counter += 1
            self._audit_logs.append(entry)
            if len(self._audit_logs) > self.MAX_AUDIT_LOGS:
                self._audit_logs = self._audit_logs[-self.MAX_AUDIT_LOGS:]
            return entry

    def get_audit_logs(self, limit: int = 50, user_filter: Optional[str] = None, action_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        with self._lock:
            results = list(self._audit_logs)
        if user_filter:
            uf = user_filter.lower().strip()
            results = [r for r in results if uf in r["user"].lower()]
        if action_filter and action_filter.lower() != "all":
            af = action_filter.upper().strip()
            results = [r for r in results if r["action"] == af]
        results.reverse()
        return results[:limit]

    def check_rate_limit(self, client_id: str, max_requests: int = 100, window_seconds: float = 60.0) -> Tuple[bool, int]:
        """Sliding-window rate limiter per client IP / key."""
        now = time.time()
        with self._lock:
            history = self._rate_limits.setdefault(client_id, [])
            # Prune timestamps outside window
            cutoff = now - window_seconds
            self._rate_limits[client_id] = [t for t in history if t > cutoff]
            current_count = len(self._rate_limits[client_id])
            if current_count >= max_requests:
                return False, max_requests - current_count
            self._rate_limits[client_id].append(now)
            return True, max_requests - (current_count + 1)

    def trigger_webhook(self, event_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Simulates enterprise webhook event dispatch."""
        self.add_audit_log(
            action=f"WEBHOOK_{event_type.upper()}",
            user="webhook-dispatcher",
            role="system",
            status="dispatched",
            details=f"Dispatched webhook for {event_type}",
        )
        return {
            "status": "delivered",
            "event_type": event_type,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "payload_size_bytes": len(json.dumps(payload)),
        }

    def detect_anomalies(self, threshold_z: float = 1.8) -> List[Dict[str, Any]]:
        """Statistical Z-score anomaly detector for token spend and latency spikes."""
        import math
        with self._lock:
            if len(self._records) < 3:
                return []
            
            acknowledged = getattr(self, "_acknowledged_alerts", set())
            tokens_list = [r["tokens"] for r in self._records]
            durations_list = [r["duration_seconds"] for r in self._records]

            avg_tok = sum(tokens_list) / len(tokens_list)
            var_tok = sum((x - avg_tok) ** 2 for x in tokens_list) / len(tokens_list)
            std_tok = math.sqrt(var_tok) if var_tok > 0 else 1.0

            avg_dur = sum(durations_list) / len(durations_list)
            var_dur = sum((x - avg_dur) ** 2 for x in durations_list) / len(durations_list)
            std_dur = math.sqrt(var_dur) if var_dur > 0 else 1.0

            anomalies = []
            for r in self._records:
                z_tok = (r["tokens"] - avg_tok) / std_tok
                z_dur = (r["duration_seconds"] - avg_dur) / std_dur
                
                is_spend_spike = z_tok >= threshold_z
                is_latency_spike = z_dur >= threshold_z
                is_error_anomaly = r["status"] == "error"

                if is_spend_spike or is_latency_spike or is_error_anomaly:
                    severity = "CRITICAL" if (z_tok >= 2.5 or is_error_anomaly) else "WARNING"
                    anomaly_type = "SPEND_SPIKE" if is_spend_spike else ("LATENCY_SPIKE" if is_latency_spike else "EXECUTION_ERROR")
                    
                    anomalies.append({
                        "alert_id": r["id"],
                        "contract_id": r["contract_id"],
                        "agent_name": r["agent_name"],
                        "model": r["model"],
                        "tokens": r["tokens"],
                        "cost_usd": r["cost_usd"],
                        "duration_seconds": r["duration_seconds"],
                        "severity": severity,
                        "anomaly_type": anomaly_type,
                        "z_score": round(max(z_tok, z_dur), 2),
                        "acknowledged": r["id"] in acknowledged,
                        "timestamp": r["timestamp"],
                        "recommendation": "Review prompt context length" if is_spend_spike else ("Optimize agent reasoning steps" if is_latency_spike else "Inspect error stack trace"),
                    })

            anomalies.reverse()
            return anomalies

    def acknowledge_alert(self, alert_id: int, user: str, role: str) -> bool:
        """Acknowledges an anomaly alert and logs security audit trail."""
        with self._lock:
            if not hasattr(self, "_acknowledged_alerts"):
                self._acknowledged_alerts = set()
            self._acknowledged_alerts.add(alert_id)
            self.add_audit_log(
                action="ALERT_ACKNOWLEDGE",
                user=user or "operator",
                role=role or "operator",
                status="success",
                details=f"Acknowledged anomaly alert for record #{alert_id}",
            )
            return True

    def get_budget_forecast(self, projected_days: int = 30, monthly_quota_usd: float = 25.0) -> Dict[str, Any]:
        """Calculates 30-day predictive token spend velocity and quota exhaustion projections."""
        with self._lock:
            total_spend = sum(r["cost_usd"] for r in self._records)
            total_runs = len(self._records)
            if total_runs == 0:
                daily_burn_rate = 0.50
            else:
                avg_cost_per_run = total_spend / total_runs
                # Assume 20 automated SDLC runs per day baseline
                daily_burn_rate = round(avg_cost_per_run * 20, 4)

            forecast_points = []
            accumulated = round(total_spend, 4)
            exhaustion_day = None

            for d in range(1, projected_days + 1):
                accumulated = round(accumulated + daily_burn_rate, 4)
                upper_bound = round(accumulated * (1 + (0.02 * d)), 4)
                lower_bound = round(max(0.0, accumulated * (1 - (0.02 * d))), 4)

                if accumulated >= monthly_quota_usd and exhaustion_day is None:
                    exhaustion_day = d

                forecast_points.append({
                    "day": d,
                    "projected_spend_usd": accumulated,
                    "upper_bound_usd": upper_bound,
                    "lower_bound_usd": lower_bound,
                })

            days_remaining = (exhaustion_day or projected_days) if exhaustion_day else projected_days
            recommended_action = "Budget trajectory optimal" if not exhaustion_day else f"Quota projected to exhaust in {exhaustion_day} days. Scale model tier to Claude Haiku."

            return {
                "current_spend_usd": round(total_spend, 4),
                "daily_burn_rate_usd": daily_burn_rate,
                "monthly_quota_usd": monthly_quota_usd,
                "projected_month_end_spend_usd": forecast_points[-1]["projected_spend_usd"] if forecast_points else 0.0,
                "quota_exhaustion_day": exhaustion_day,
                "days_until_exhaustion": days_remaining,
                "recommended_action": recommended_action,
                "forecast_points": forecast_points,
            }

    @staticmethod
    def _sanitize_text(text: str) -> str:
        if not text:
            return ""
        return str(text).replace("<", "&lt;").replace(">", "&gt;").strip()

    @staticmethod
    def _csv_sanitize(val: str) -> str:
        """Prevents CSV formula injection by prefixing dangerous characters with a single quote."""
        if not val:
            return ""
        s = str(val)
        if s.startswith(("=", "+", "-", "@", "\t", "\r")):
            return f"'{s}"
        return s
