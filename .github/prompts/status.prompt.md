---
description: "Display active pipeline checkpoint status, metrics, and completed artifacts."
model: Claude Haiku 4.5
---

# Synapse Status Command (`/status`)

Display the current status of the Synapse SDLC delivery pipeline.

## Designated Model Tier & Capability:
- **Contract ID:** `AC-000`
- **Role:** Ticket Analyzer / Status Reporter
- **Tier:** Ingestion Tier
- **Designated Engine:** `Claude Haiku 4.5` (Fallback: `Claude 3.5 Haiku`)
- **Primary Capability:** Status parsing, checkpoint inspection, and telemetry reporting.

## Status Protocol:
1. Attempt to run `python -m synapse status` or `python -m synapse checkpoint status` via terminal tool.
2. If `python -m synapse` is unavailable or returns an error, read `.synapse/checkpoints/checkpoint_state.json` directly using `read_file`.
3. If `.synapse/session_telemetry.json` shows 0 tokens or is missing, run `python .github/hooks/telemetry-hook.py --sync` or `python -m synapse telemetry sync` to reconcile historical tokens and spend.
4. Parse the JSON state and render a Markdown progress table showing:
   - Phase Name
   - Status (completed, in_progress, pending)
   - Completion Timestamp
   - Generated Artifacts
5. Inspect `.synapse/session_telemetry.json` to display:
   - Active Model (read from `.synapse/session_telemetry.json` or `.synapse/active_model.txt`)
   - Session Total Tokens (`total_tokens`)
   - Session Total Spend (`total_spent_usd`)
   - Last Turn Tokens & Cost (if available: `last_prompt_tokens` / `last_prompt_cost_usd`)
6. Telemetry Badge Requirement:
   - Conclude with the Synapse Telemetry badge dynamically reflecting your active model engine:
     `> **Synapse Telemetry:** `[Model Name]` | **Tokens:** ~[Tokens] | **Cost:** ~$[Cost] | **Plan Usage:** [Usage]% ([Plan Name])`
   - Calculate turn cost dynamically based on the active model's rate formula from `.github/copilot-instructions.md`.

## Empty Workspace Handling:
If no checkpoint state exists:
- Display the telemetry status (Active Model, Tokens, Cost).
- State clearly: "No active pipeline runs recorded. Run `/orchestrate [TICKET or REQUIREMENT]` to launch a new software delivery pipeline."
- Zero-Refusal Guarantee: NEVER output "I'm sorry, I can't answer that question with what I currently know about your workspace."
