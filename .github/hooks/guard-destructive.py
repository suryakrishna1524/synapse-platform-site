#!/usr/bin/env python3
"""Synapse Destructive Command Guard Hook.

Prevents irreversible damage to host machines and protected git branches.
PreToolUse hook conforming to VS Code Copilot hook specification.
"""

import json
import re
import sys
from pathlib import Path

# Add package directory to path if needed
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

try:
    from synapse.guards.destructive import DestructiveCommandGuard
except ImportError:
    # Standalone fallback implementation with parity
    class DestructiveCommandGuard:
        CRITICAL = (
            "/", "~", "$HOME", "${HOME}", "/etc", "/usr", "/bin", "/sbin",
            "/var", "/opt", "/System", "/Library", "/Applications",
            "C:\\", "C:\\Users", "C:\\Windows", "C:\\Program Files",
            "C:\\Program Files (x86)", "C:\\ProgramData", "D:\\",
            "$env:USERPROFILE", "%USERPROFILE%", "$env:SystemRoot", "%SystemRoot%",
        )

        STATIC_PATTERNS = [
            (r"\bmkfs(\.[a-z0-9]+)?\b", "Filesystem format command (mkfs)"),
            (r"\bdd\b.+of\s*=\s*(/dev/(disk|sd[a-z]+|nvme|rd/)|\\\\.\\PhysicalDrive)", "Raw write targeting block device (dd)"),
            (r"\bdiskutil\s+(eraseDisk|eraseVolume|zeroDisk|secureErase|reformat)\b", "Destructive diskutil operation"),
            (r"\bformat\s+[A-Za-z]:\s*(\/fs|\/q)?", "Windows drive format command"),
            (r"\bFormat-Volume\b", "PowerShell volume format command (Format-Volume)"),
            (r"\bClear-Disk\b", "PowerShell disk clear command (Clear-Disk)"),
            (r"\bInitialize-Disk\b", "PowerShell disk initialization command (Initialize-Disk)"),
            (r"\b(?:del|erase)\b[^\n|;&]*\/[sS]\b", "Windows cmd recursive file deletion (del /s)"),
            (r"\b(?:rd|rmdir)\b[^\n|;&]*\/[sS]\b", "Windows cmd recursive directory deletion (rd /s)"),
            (r"\bRemove-Item\b.*(?:\s|^)(?:-[a-zA-Z]*[rR]|--recursive)\b.*(?:\s|^)(?:-[a-zA-Z]*fo|--force)\b", "PowerShell recursive forced deletion (Remove-Item -Recurse -Force)"),
            (r"\bRemove-Item\b.*(?:\s|^)(?:-[a-zA-Z]*fo|--force)\b.*(?:\s|^)(?:-[a-zA-Z]*[rR]|--recursive)\b", "PowerShell recursive forced deletion (Remove-Item -Force -Recurse)"),
            (r"\b(?:ri|rmdir)\b.*(?:\s|^)(?:-[a-zA-Z]*[rR]|--recursive)\b.*(?:\s|^)(?:-[a-zA-Z]*fo|--force)\b", "PowerShell recursive forced deletion via alias"),
            (r":\(\)\s*\{\s*:\|:&\s*\};:", "Fork bomb pattern"),
            (r"\bgit\s+reset\s+--hard\b", "Hard git reset discarding uncommitted changes and commit history"),
            (r"\bgit\s+clean\s+-[a-zA-Z]*f[a-zA-Z]*\b", "Forceful git clean removing untracked workspace files"),
            (r"\bgit\s+push\b.*(-f|--force)\b", "Forced git push to remote repository"),
            (r"\bpython[0-9.]*\s+-c\s+.*shutil\.rmtree\b", "Python script invocation of recursive shutil.rmtree"),
            (r"\bfind\b.+\s+-delete\b", "Arbitrary find deletion with -delete flag"),
        ]

        @classmethod
        def evaluate(cls, cmd: str):
            if not cmd or not cmd.strip():
                return True, ""
            # Check rm and Remove-Item targeting critical paths
            if re.search(r"\b(?:rm|remove-item|ri)\s+.*(?:-[a-zA-Z]*[rR]|--recursive).*", cmd, re.I):
                for p in cls.CRITICAL:
                    if re.search(rf"(?:^|\s)[\"']?{re.escape(p)}[\"']?(?:\s|/|\\|\*|$)", cmd, re.I):
                        return False, f"Recursive deletion targeting critical system path: '{p}'"
            for pat, label in cls.STATIC_PATTERNS:
                if re.search(pat, cmd, re.I):
                    return False, label
            return True, ""


def main():
    try:
        raw = sys.stdin.read()
        if not raw.strip():
            sys.exit(0)

        data = json.loads(raw)
        tool_input = data.get("toolInput", data.get("tool_input", {}))

        cmd = ""
        if isinstance(tool_input, dict):
            cmd = tool_input.get("command", tool_input.get("cmd", ""))
        elif isinstance(tool_input, str):
            cmd = tool_input

        if cmd:
            safe, reason = DestructiveCommandGuard.evaluate(cmd)
            if not safe:
                out = {
                    "hookSpecificOutput": {
                        "hookEventName": "PreToolUse",
                        "status": "blocked",
                        "reason": f"BLOCKED by Synapse Destructive Guard: {reason}",
                    }
                }
                sys.stderr.write(json.dumps(out, indent=2) + "\n")
                sys.exit(2)

        sys.exit(0)
    except Exception as e:
        sys.stderr.write(f"[WARN] Destructive guard bypassed due to parse error: {e}\n")
        sys.exit(0)


if __name__ == "__main__":
    main()
