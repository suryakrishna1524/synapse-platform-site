#!/usr/bin/env python3
"""Synapse Quality Gate Hook.

Triggers project linters and formatters upon file modification.
PostToolUse hook conforming to VS Code Copilot hook specification.
"""

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

try:
    from synapse.guards.quality import QualityGateHook
except ImportError:
    import shutil
    import subprocess

    class QualityGateHook:
        COMMANDS = {
            ".py": ["ruff", "check", "--fix"],
            ".js": ["npx", "eslint", "--fix"],
            ".ts": ["npx", "eslint", "--fix"],
            ".jsx": ["npx", "eslint", "--fix"],
            ".tsx": ["npx", "eslint", "--fix"],
            ".go": ["gofmt", "-w"],
            ".rs": ["rustfmt"],
        }

        @classmethod
        def lint_file(cls, path: str):
            p = Path(path)
            if not p.exists() or not p.is_file():
                return True
            cmd = cls.COMMANDS.get(p.suffix.lower())
            if not cmd or not shutil.which(cmd[0]):
                return True
            try:
                subprocess.run(cmd + [str(p)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=30)
            except Exception:
                pass
            return True


def main():
    try:
        raw = sys.stdin.read()
        if not raw.strip():
            sys.exit(0)

        data = json.loads(raw)
        tool_input = data.get("toolInput", data.get("tool_input", {}))

        target = ""
        if isinstance(tool_input, dict):
            target = (
                tool_input.get("filePath")
                or tool_input.get("file_path")
                or tool_input.get("path")
                or tool_input.get("TargetFile")
                or ""
            )

        if target and os.path.exists(target):
            QualityGateHook.lint_file(target)

        sys.exit(0)
    except Exception:
        sys.exit(0)


if __name__ == "__main__":
    main()
