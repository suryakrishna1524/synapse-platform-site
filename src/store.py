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

    def __init__(self):
        self._lock = threading.Lock()
        self._records: List[Dict[str, Any]] = []
        self._subscribers: List[queue.Queue] = []
        self._id_counter = 1
        self._seed_initial_data()

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
