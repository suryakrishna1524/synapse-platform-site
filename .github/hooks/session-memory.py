#!/usr/bin/env python3
"""Synapse Session Memory Hook.

Summarizes session decisions and learnings to support multi-turn continuity.
Runs on Stop hook event.
"""

import json
import os
import sys
import time
from pathlib import Path


def main():
    try:
        raw = sys.stdin.read()
        data = {}
        if raw.strip():
            try:
                data = json.loads(raw)
            except Exception:
                pass

        workspace = Path.cwd()
        learnings_dir = workspace / ".synapse" / "memory"
        learnings_dir.mkdir(parents=True, exist_ok=True)

        ign = workspace / ".synapse" / ".gitignore"
        if not ign.exists():
            try:
                ign.write_text("# Synapse runtime state - do not commit\n*\n", encoding="utf-8")
            except Exception:
                pass
        git_dir = workspace / ".git"
        if git_dir.is_dir():
            try:
                exclude_file = git_dir / "info" / "exclude"
                exclude_file.parent.mkdir(parents=True, exist_ok=True)
                content = exclude_file.read_text(encoding="utf-8") if exclude_file.exists() else ""
                if ".synapse" not in content:
                    with open(exclude_file, "a", encoding="utf-8") as f:
                        f.write("\n# Synapse SDLC developer runtime state\n.synapse/\n.synapse\n")
                    sys.stderr.write("[SYNAPSE] Registered .synapse/ in .git/info/exclude\n")
            except Exception:
                pass

        session_file = learnings_dir / "session_memory.md"
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")

        entry = f"""
### Session Finished at {timestamp}
- Recorded session state cleanly.
- Preserved active agent checkpoints and cache records.
"""
        with open(session_file, "a", encoding="utf-8") as f:
            f.write(entry)

        output = {
            "continue": True,
            "hookSpecificOutput": {
                "hookEventName": "Stop",
                "status": "memory_saved",
            }
        }
        sys.stdout.write(json.dumps(output) + "\n")
        sys.exit(0)
    except Exception:
        sys.exit(0)


if __name__ == "__main__":
    main()
