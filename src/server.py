"""Platform Server — High-Performance HTTP Microservice & REST Dispatcher."""

import json
import mimetypes
import os
import sys
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Dict, Any, Optional

from src.store import TelemetryStore

GLOBAL_STORE = TelemetryStore()
SERVER_START_TIME = time.time()
STATIC_DIR = Path(__file__).resolve().parent / "static"


class PlatformRequestHandler(BaseHTTPRequestHandler):
    """Handles REST API queries, static asset delivery, and error boundaries."""

    server_version = "SynapsePlatformServer/1.0"

    def do_GET(self) -> None:
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path
        query = urllib.parse.parse_qs(parsed_url.query)

        # 1. API Endpoints
        if path == "/api/health":
            self._send_json(200, {
                "status": "ok",
                "uptime_seconds": round(time.time() - SERVER_START_TIME, 1),
                "version": "1.0.0",
                "service": "Synapse Telemetry Platform",
            })
        elif path == "/api/stats":
            stats = GLOBAL_STORE.get_statistics()
            self._send_json(200, stats)
        elif path == "/api/metrics":
            agent_filter = query.get("agent", [None])[0]
            status_filter = query.get("status", [None])[0]
            limit = int(query.get("limit", [100])[0])
            items = GLOBAL_STORE.get_metrics(agent_filter=agent_filter, status_filter=status_filter, limit=limit)
            self._send_json(200, {"count": len(items), "items": items})
        elif path == "/api/export":
            fmt = query.get("format", ["json"])[0]
            content, ctype = GLOBAL_STORE.export_data(fmt)
            ext = "csv" if fmt == "csv" else "json"
            self.send_response(200)
            self.send_header("Content-Type", f"{ctype}; charset=utf-8")
            self.send_header("Content-Disposition", f'attachment; filename="synapse_telemetry.{ext}"')
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(content.encode("utf-8"))
        elif path == "/api/auth/me":
            role = self.headers.get("X-User-Role", "admin").lower()
            permissions = {
                "admin": ["read", "write", "purge", "export", "configure"],
                "operator": ["read", "write", "export"],
                "viewer": ["read", "export"],
            }.get(role, ["read"])
            self._send_json(200, {
                "user": "developer@synapse-sdlc.dev",
                "role": role,
                "plan": "Copilot Enterprise",
                "permissions": permissions,
            })
        elif path == "/api/audit-logs":
            limit = int(query.get("limit", [50])[0])
            user_f = query.get("user", [None])[0]
            action_f = query.get("action", [None])[0]
            logs = GLOBAL_STORE.get_audit_logs(limit=limit, user_filter=user_f, action_filter=action_f)
            self._send_json(200, {"count": len(logs), "logs": logs})
        elif path == "/api/alerts/anomalies":
            threshold_z = float(query.get("threshold_z", [1.8])[0])
            anomalies = GLOBAL_STORE.detect_anomalies(threshold_z=threshold_z)
            self._send_json(200, {"count": len(anomalies), "anomalies": anomalies})
        elif path == "/api/forecast":
            days = int(query.get("days", [30])[0])
            quota = float(query.get("quota", [25.0])[0])
            forecast = GLOBAL_STORE.get_budget_forecast(projected_days=days, monthly_quota_usd=quota)
            self._send_json(200, forecast)
        elif path == "/api/stream":
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "keep-alive")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()

            q = GLOBAL_STORE.subscribe()
            try:
                # Initial handshake event
                self.wfile.write(b"data: " + json.dumps({"type": "connected", "time": time.time()}).encode("utf-8") + b"\n\n")
                self.wfile.flush()
                while True:
                    try:
                        event = q.get(timeout=1.0)
                        msg = f"data: {json.dumps(event)}\n\n".encode("utf-8")
                        self.wfile.write(msg)
                        self.wfile.flush()
                    except Exception:
                        self.wfile.write(b": ping\n\n")
                        self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError, OSError):
                pass
            finally:
                GLOBAL_STORE.unsubscribe(q)
            return
        elif path.startswith("/api/"):
            self._send_json(404, {"error": "API endpoint not found", "path": path})
        else:
            # 2. Static Web Assets
            self._serve_static_file(path)

    def do_POST(self) -> None:
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path

        # Rate Limiting Check
        client_ip = self.client_address[0] if self.client_address else "127.0.0.1"
        allowed, remaining = GLOBAL_STORE.check_rate_limit(client_ip, max_requests=120, window_seconds=60.0)
        if not allowed:
            self._send_json(429, {"error": "Rate limit exceeded (120 requests/minute limit)", "retry_after_seconds": 60})
            return

        content_length = int(self.headers.get("Content-Length", 0))
        if content_length > 1_048_576:  # 1MB limit
            self._send_json(413, {"error": "Payload too large (1MB maximum)"})
            return

        body = self.rfile.read(content_length).decode("utf-8")
        try:
            payload = json.loads(body) if body else {}
        except json.JSONDecodeError:
            self._send_json(400, {"error": "Malformed JSON payload"})
            return

        if path == "/api/metrics":
            contract_id = payload.get("contract_id", "AC-CUSTOM")
            agent_name = payload.get("agent_name", "Custom Sub-agent")
            model = payload.get("model", "Claude Sonnet 5")
            tokens = int(payload.get("tokens", 1000))
            cost_usd = float(payload.get("cost_usd", 0.005))
            duration_s = float(payload.get("duration_seconds", 1.0))
            status = payload.get("status", "success")
            description = payload.get("description", "Agent turn execution")

            record = GLOBAL_STORE.add_metric(
                contract_id=contract_id,
                agent_name=agent_name,
                model=model,
                tokens=tokens,
                cost_usd=cost_usd,
                duration_seconds=duration_s,
                status=status,
                description=description,
            )
            GLOBAL_STORE.add_audit_log("METRIC_RECORDED", "agent", "system", status, f"Turn recorded for {contract_id}")
            self._send_json(201, {"status": "created", "record": record})
        elif path == "/api/webhooks/test":
            event_type = payload.get("event", "ALERT_TRIGGERED")
            result = GLOBAL_STORE.trigger_webhook(event_type, payload)
            self._send_json(200, result)
        elif path == "/api/alerts/acknowledge":
            role = self.headers.get("X-User-Role", "operator").lower()
            if role not in ("admin", "operator"):
                self._send_json(403, {"error": "Forbidden: Requires Operator or Admin role"})
                return
            alert_id = int(payload.get("alert_id", 0))
            user = payload.get("user", "operator@synapse-sdlc.dev")
            GLOBAL_STORE.acknowledge_alert(alert_id, user, role)
            self._send_json(200, {"status": "acknowledged", "alert_id": alert_id})
        elif path == "/api/admin/purge":
            role = self.headers.get("X-User-Role", "admin").lower()
            if role != "admin":
                self._send_json(403, {"error": "Forbidden: Requires Admin role"})
                return
            count = GLOBAL_STORE.purge()
            self._send_json(200, {"status": "purged", "records_removed": count})
        else:
            self._send_json(404, {"error": "API POST endpoint not found", "path": path})

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-User-Role, Authorization")
        self.end_headers()

    def _serve_static_file(self, rel_path: str) -> None:
        """Securely serves static frontend files preventing path traversal."""
        clean_path = rel_path.lstrip("/")
        if not clean_path or clean_path == "":
            clean_path = "index.html"

        target_file = (STATIC_DIR / clean_path).resolve()
        # Path Traversal Guard
        try:
            if not str(target_file).startswith(str(STATIC_DIR.resolve())):
                self._send_json(403, {"error": "Forbidden: Path traversal attempt blocked"})
                return
        except Exception:
            self._send_json(403, {"error": "Forbidden"})
            return

        if not target_file.exists() or not target_file.is_file():
            # Fallback to index.html for SPA routing
            target_file = STATIC_DIR / "index.html"

        if not target_file.exists():
            self._send_json(404, {"error": "Static file not found"})
            return

        mime_type, _ = mimetypes.guess_type(str(target_file))
        mime_type = mime_type or "application/octet-stream"

        try:
            content = target_file.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", f"{mime_type}; charset=utf-8")
            self.send_header("Content-Length", str(len(content)))
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            self.wfile.write(content)
        except Exception as e:
            self._send_json(500, {"error": f"Failed to read file: {e}"})

    def _send_json(self, status_code: int, data: Dict[str, Any]) -> None:
        body = json.dumps(data, indent=2).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: Any) -> None:
        # Clean logging format
        sys.stderr.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {args[0]} - {args[1]} {args[2]}\n")


def create_server(port: int = 8080) -> ThreadingHTTPServer:
    return ThreadingHTTPServer(("0.0.0.0", port), PlatformRequestHandler)


def run_server(port: int = 8080) -> None:
    server = create_server(port)
    print(f"[*] Synapse Telemetry Platform live on http://127.0.0.1:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[*] Server shutdown.")
        server.server_close()


if __name__ == "__main__":
    port_arg = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
    run_server(port_arg)
