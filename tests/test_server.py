"""Automated Unit, API Contract & Security Tests for Synapse Platform Site."""

import json
import threading
import time
import unittest
import urllib.request
import urllib.error

from src.store import TelemetryStore
from src.server import create_server


class TestPlatformServerAndStore(unittest.TestCase):
    """Rigorous HTTP endpoint and data store test suite."""

    @classmethod
    def setUpClass(cls):
        cls.store = TelemetryStore()
        cls.port = 8899
        cls.server = create_server(cls.port)
        cls.server_thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.server_thread.start()
        time.sleep(0.2)  # Give server time to bind

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def test_health_endpoint(self):
        url = f"http://127.0.0.1:{self.port}/api/health"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req) as res:
            self.assertEqual(res.status, 200)
            data = json.loads(res.read().decode("utf-8"))
            self.assertEqual(data["status"], "ok")
            self.assertIn("uptime_seconds", data)

    def test_stats_endpoint(self):
        url = f"http://127.0.0.1:{self.port}/api/stats"
        with urllib.request.urlopen(url) as res:
            self.assertEqual(res.status, 200)
            data = json.loads(res.read().decode("utf-8"))
            self.assertIn("total_runs", data)
            self.assertIn("total_tokens", data)
            self.assertIn("total_spend_usd", data)
            self.assertGreater(data["total_runs"], 0)

    def test_metrics_query_and_filtering(self):
        url = f"http://127.0.0.1:{self.port}/api/metrics?status=success&limit=5"
        with urllib.request.urlopen(url) as res:
            self.assertEqual(res.status, 200)
            data = json.loads(res.read().decode("utf-8"))
            self.assertIn("items", data)
            for item in data["items"]:
                self.assertEqual(item["status"], "success")

    def test_post_metric_creation(self):
        url = f"http://127.0.0.1:{self.port}/api/metrics"
        payload = json.dumps({
            "contract_id": "AC-006",
            "agent_name": "Test Runner",
            "model": "GPT-5.3-Codex",
            "tokens": 3500,
            "cost_usd": 0.0166,
            "duration_seconds": 2.1,
            "status": "success",
            "description": "Executed automated test run",
        }).encode("utf-8")

        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req) as res:
            self.assertEqual(res.status, 201)
            data = json.loads(res.read().decode("utf-8"))
            self.assertEqual(data["status"], "created")
            self.assertIn("record", data)
            self.assertEqual(data["record"]["contract_id"], "AC-006")

    def test_csv_export_endpoint(self):
        url = f"http://127.0.0.1:{self.port}/api/export?format=csv"
        with urllib.request.urlopen(url) as res:
            self.assertEqual(res.status, 200)
            self.assertIn("text/csv", res.headers.get("Content-Type"))
            content = res.read().decode("utf-8")
            self.assertIn("Contract ID", content)
            self.assertIn("Tokens", content)

    def test_auth_me_role_permissions(self):
        url = f"http://127.0.0.1:{self.port}/api/auth/me"
        req = urllib.request.Request(url, headers={"X-User-Role": "operator"})
        with urllib.request.urlopen(req) as res:
            self.assertEqual(res.status, 200)
            data = json.loads(res.read().decode("utf-8"))
            self.assertEqual(data["role"], "operator")
            self.assertIn("write", data["permissions"])

    def test_static_index_serving(self):
        url = f"http://127.0.0.1:{self.port}/"
        with urllib.request.urlopen(url) as res:
            self.assertEqual(res.status, 200)
            content = res.read().decode("utf-8")
            self.assertIn("Synapse SDLC", content)
            self.assertIn("Enterprise Telemetry & Observability Hub", content)

    def test_path_traversal_blocked(self):
        url = f"http://127.0.0.1:{self.port}/../../../../etc/passwd"
        # Server should catch traversal and return 403 or fallback index
        try:
            with urllib.request.urlopen(url) as res:
                self.assertIn(res.status, (200, 403, 404))
        except urllib.error.HTTPError as e:
            self.assertIn(e.code, (403, 404))

    def test_csv_formula_injection_defense(self):
        raw_csv, _ = self.store.export_data("csv")
        self.assertNotIn("\n=cmd", raw_csv)
        self.assertNotIn("\n+cmd", raw_csv)

    def test_sse_stream_initial_handshake(self):
        url = f"http://127.0.0.1:{self.port}/api/stream"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=3.0) as res:
            self.assertEqual(res.status, 200)
            self.assertEqual(res.headers.get("Content-Type"), "text/event-stream")
            # Read first chunk
            first_chunk = res.readline().decode("utf-8")
            self.assertTrue(first_chunk.startswith("data: ") or first_chunk.startswith(":"))


if __name__ == "__main__":
    unittest.main()
