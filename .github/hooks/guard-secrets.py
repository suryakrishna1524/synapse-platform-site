#!/usr/bin/env python3
"""Synapse Secret Leak Guard Hook.

Prevents exposure of sensitive API keys, credentials, and private keys.
PreToolUse hook conforming to VS Code Copilot hook specification.
"""

import json
import re
import sys
from pathlib import Path

# Add package directory to path if needed
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

try:
    from synapse.guards.secrets import SecretLeakGuard
except ImportError:
    class SecretLeakGuard:
        PATTERNS = [
            (r"-----BEGIN (?:RSA|OPENSSH|DSA|EC|PGP)? ?PRIVATE KEY-----", "Private key"),
            (r"gh[pousr]_[A-Za-z0-9_]{36,255}", "GitHub Token"),
            (r"\bgithub_pat_[A-Za-z0-9_]{60,}\b", "GitHub fine-grained token"),
            (r"['\"]?\b(?:GITHUB_TOKEN|GH_TOKEN|GITHUB_PAT)\b['\"]?\s*[:=]\s*(?:['\"](?!\$\{)[^'\"\r\n]{8,}['\"]|(?!\$\{)[^\s'\",\r\n]{8,})", "GitHub token assignment"),
            (r"(?i)['\"]?\b(?:github|gh)[-_]?(?:token|pat|key)\b['\"]?\s*[:=]\s*(?:['\"](?!\$\{)[^'\"\r\n]{8,}['\"]|(?!\$\{)[^\s'\",\r\n]{8,})", "GitHub token value"),
            (r"glpat-[0-9a-zA-Z_\-]{20,}", "GitLab Token"),
            (r"\bATATT3[A-Za-z0-9_\-=]{20,}\b", "Atlassian / Jira API token"),
            (r"['\"]?\b(?:JIRA_PAT|JIRA_TOKEN|JIRA_API_KEY)\b['\"]?\s*[:=]\s*(?:['\"](?!\$\{)[^'\"\r\n]{8,}['\"]|(?!\$\{)[^\s'\",\r\n]{8,})", "Jira PAT / token assignment"),
            (r"(?i)['\"]?\b(?:jira|atlassian)[-_]?(?:pat|token|key)\b['\"]?\s*[:=]\s*(?:['\"](?!\$\{)[^'\"\r\n]{8,}['\"]|(?!\$\{)[^\s'\",\r\n]{8,})", "Jira PAT value"),
            (r"(?i)\b(?:jira|atlassian)[-_]?(?:pat|token)[-_]?[A-Za-z0-9_\-]{16,}\b", "Jira PAT signature"),
            (r"\bBearer\s+[A-Za-z0-9_\-\.]{20,}\b", "Authorization Bearer token"),
            (r"xox[baprs]-[0-9a-zA-Z]{10,48}", "Slack API token"),
            (r"AKIA[0-9A-Z]{16}", "AWS Access Key"),
            (r"(?:aws_secret_access_key|aws_access_key_id)\s*=\s*[A-Za-z0-9/+=]{20,}", "AWS credentials file entry"),
            (r"AIza[0-9A-Za-z\\-_]{35}", "Google API key"),
            (r"sk-[a-zA-Z0-9]{20,64}", "OpenAI API key"),
            (r"eyJ[A-Za-z0-9-_=]+\.[A-Za-z0-9-_=]+\.[A-Za-z0-9-_.+/=]+", "JSON Web Token (JWT) signature"),
            (r"(?i)['\"]?\b(?:password|passwd|secret|token|api_key|apikey)\b['\"]?\s*[:=]\s*(?:['\"](?!\$\{)[^'\"\r\n]{8,}['\"]|(?!\$\{)[^\s'\",\r\n]{8,})", "Hardcoded password or API secret assignment"),
        ]

        @classmethod
        def inspect_text(cls, text: str, workspace_root=None):
            if not text or not text.strip():
                return True, ""
            for pat, label in cls.PATTERNS:
                if re.search(pat, text, re.I):
                    return False, f"Detected credential: {label}"
            # Check protected filename dumping
            if re.search(r"\b(?:cat|type|Get-Content|gc|more|head|tail)\s+[^\s]*(?:\.env|id_rsa|id_ed25519|credentials\.json)\b", text, re.I):
                return False, "Attempting to dump protected credential file"
            # Scan local .env if present
            candidates = []
            if workspace_root:
                candidates.append(Path(workspace_root) / ".env")
            candidates.extend([Path(".env"), Path.cwd() / ".env"])
            for env_path in candidates:
                if env_path.is_file():
                    try:
                        for line in env_path.read_text(encoding="utf-8").splitlines():
                            line = line.strip()
                            if not line or line.startswith("#") or "=" not in line:
                                continue
                            k, v = line.split("=", 1)
                            v = v.strip().strip("'\"")
                            if len(v) >= 8 and any(s in k.upper() for s in ("TOKEN", "PAT", "KEY", "SECRET")):
                                if v in text:
                                    return False, f"Detected exposure of live workspace credential from .env: '{k.strip()}'"
                    except Exception:
                        pass
            return True, ""


def main():
    try:
        raw = sys.stdin.read()
        if not raw.strip():
            sys.exit(0)

        data = json.loads(raw)
        event_name = data.get("event", data.get("hookEventName", "PreToolUse"))
        tool_input = data.get("toolInput", data.get("tool_input", {}))
        tool_output = data.get("toolResult", data.get("toolOutput", data.get("result", data.get("output", ""))))

        inspect_texts = []
        if isinstance(tool_input, dict):
            for v in tool_input.values():
                if isinstance(v, str):
                    inspect_texts.append(v)
        elif isinstance(tool_input, str):
            inspect_texts.append(tool_input)

        if isinstance(tool_output, dict):
            for v in tool_output.values():
                if isinstance(v, str):
                    inspect_texts.append(v)
        elif isinstance(tool_output, str) and tool_output:
            inspect_texts.append(tool_output)

        for txt in inspect_texts:
            safe, reason = SecretLeakGuard.inspect_text(txt)
            if not safe:
                out = {
                    "hookSpecificOutput": {
                        "hookEventName": event_name or "PreToolUse",
                        "status": "blocked",
                        "reason": f"BLOCKED by Synapse Secret Guard: {reason}",
                    }
                }
                sys.stderr.write(json.dumps(out, indent=2) + "\n")
                sys.exit(2)

        sys.exit(0)
    except Exception as e:
        sys.stderr.write(f"[WARN] Secret guard error: {e}\n")
        sys.exit(0)


if __name__ == "__main__":
    main()
