#!/usr/bin/env python3
"""Synapse Observability Hook.

Supervises OTel Collector and Prometheus background processes.
Runs at SessionStart and Stop.
"""

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

try:
    from synapse.telemetry.daemon import ObservabilityDaemon
except ImportError:
    class ObservabilityDaemon:
        def __init__(self, root=None): pass
        def status(self): return {}
        def stop_daemon(self): return {}


def main():
    try:
        raw = sys.stdin.read()
        event_name = "SessionStart"
        if raw.strip():
            try:
                data = json.loads(raw)
                event_name = data.get("event", data.get("hookEventName", "SessionStart"))
            except Exception:
                pass

        daemon = ObservabilityDaemon()
        if event_name == "Stop":
            daemon.stop_daemon()

        output = {
            "continue": True,
            "hookSpecificOutput": {
                "hookEventName": event_name,
                "status": "active",
            }
        }
        sys.stdout.write(json.dumps(output) + "\n")
        sys.exit(0)
    except Exception:
        sys.exit(0)


if __name__ == "__main__":
    main()
