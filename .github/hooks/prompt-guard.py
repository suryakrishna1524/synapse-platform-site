#!/usr/bin/env python3
"""Synapse Prompt Safety Guard Hook.

Inspects incoming prompts for injection attacks, exfiltration, or guardrail breaches.
UserPromptSubmit hook conforming to VS Code Copilot hook specification.
"""

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

try:
    from synapse.guards.prompt import PromptSafetyGuard
except ImportError:
    class PromptSafetyGuard:
        PATTERNS = [
            (r"ignore\s+(all\s+)?(previous|prior|above|system)\s+(instructions|directives|rules|guidelines)", "Prompt jailbreak / override attempt"),
            (r"disregard\s+(all\s+)?(previous|prior|above|system)\s+(instructions|directives|rules|guidelines)", "Prompt override attempt"),
            (r"\bdan\s+mode\b|you\s+are\s+now\s+in\s+(developer|dan|jailbreak|unrestricted|god)\s+mode", "Jailbreak mode declaration"),
            (r"act\s+as\s+an?\s+(unfiltered|jailbroken|unrestricted)\s+(ai|assistant|model)", "Jailbreak persona request"),
            (r"do\s+anything\s+now\b", "DAN jailbreak phrase"),
            (r"bypass\s+all\s+(security|compliance|guardrail|safety|policy)\s+(checks|rules|filters)", "Explicit guardrail bypass request"),
            (r"override\s+(system|agent|role)\s+(prompt|directive|instruction|instructions)", "System prompt override attempt"),
            (r"(?:dump|export)\s+(?:all\s+)?(?:passwords|api[_-]?keys|secrets|credentials|tokens|\.env)", "Sensitive credential harvesting attempt"),
            (r"(?:print|dump|reveal|show|display|cat)\s+(?:the\s+)?(?:contents?\s+of\s+)?(?:\.env|system\s+prompt|initial\s+instructions|hidden\s+prompt|secret\s+key)", "Prompt/credential extraction attempt"),
            (r"(?:exfiltrate|send|leak)\s+(?:the\s+|all\s+)?(?:secrets|tokens|(?:api\s+)?keys|passwords|credentials)\s+to\b", "Data exfiltration attempt"),
            (r"!\[.*?\]\(https?://[^\s)]*(?:token|secret|key|passwd|password)=", "Markdown image credential exfiltration payload"),
            (r"(?:<\|im_start\|>system|\[SYSTEM\s+PROMPT\]|\bSYSTEM:\s*you\s+are\s+now\b)", "Indirect system prompt delimiter injection"),
            (r"drop\s+database\b|truncate\s+table\b", "Unapproved destructive SQL command prompt"),
        ]

        @classmethod
        def evaluate(cls, text: str):
            for pat, label in cls.PATTERNS:
                if re.search(pat, text, re.I):
                    return False, label
            return True, ""


def main():
    try:
        raw = sys.stdin.read()
        if not raw.strip():
            sys.exit(0)

        data = json.loads(raw)
        prompt_str = data.get("prompt", data.get("userPrompt", data.get("message", "")))

        safe, reason = PromptSafetyGuard.evaluate(prompt_str)
        if not safe:
            out = {
                "hookSpecificOutput": {
                    "hookEventName": "UserPromptSubmit",
                    "status": "blocked",
                    "reason": f"BLOCKED by Synapse Prompt Guard: {reason}",
                }
            }
            sys.stderr.write(json.dumps(out, indent=2) + "\n")
            sys.exit(2)

        sys.exit(0)
    except Exception as e:
        sys.stderr.write(f"[WARN] Prompt guard error: {e}\n")
        sys.exit(0)


if __name__ == "__main__":
    main()
