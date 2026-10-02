---
description: "Run Synapse preflight validation to inspect repos, verify credentials, and refresh submodules."
model: Claude Haiku 4.5
---

# Synapse Preflight Command (`/preflight`)

Validate workspace readiness, repository configuration, credentials, and tool availability before starting development.

## Designated Model Tier & Capability:
- **Contract ID:** `AC-000`
- **Role:** Ticket Analyzer / Preflight Agent
- **Tier:** Ingestion Tier
- **Designated Engine:** `Claude Haiku 4.5` (Fallback: `Claude 3.5 Haiku`)
- **Primary Capability:** Environment preflight, workspace scan, and credential validation.

## Concluding Telemetry Badge Requirement:
At the conclusion of execution, append the Synapse Telemetry badge dynamically reflecting the active LLM engine:
```markdown
---
> **Synapse Telemetry:** `[Model Name]` | **Tokens:** ~[Tokens] | **Cost:** ~$[Cost] | **Plan Usage:** [Usage]% ([Plan Name])
```
- **Dynamic Model Name (`[Model Name]`):** MUST dynamically reflect the active LLM engine powering the response from your VS Code Copilot Chat model picker dropdown (e.g., `GPT-5.3-Codex`, `Claude 3.7 Sonnet`, `Claude Sonnet 5`, `Gemini 3.8 Flash`, `GPT-4o`). Check `.synapse/active_model.txt` if available. NEVER hardcode a fixed model name.
- **Tokens & Cost:** Calculate dynamically based on the active model's rate formula from `.github/copilot-instructions.md`.
- **Plan Usage:** Read from `.synapse/session_telemetry.json` or advance dynamically with each prompt.

## Preflight Verification Sequence:

1. **Repository & SCM Detection:**
   - Run `git config --get remote.origin.url` to check the current repository remote host (GitHub, GitLab, Azure DevOps, Bitbucket).
   - If `.github/skills/` contains connector skills for a different platform (e.g. `gitlab-connector` in a GitHub repository), display:
     `> [!WARNING] Mismatched SCM connector detected: Workspace contains skills for another platform. Run 'synapse init' to reconfigure connectors automatically for this repository.`

2. **Quality & Contract Verification:**
   - Attempt to run `python -m synapse verify .` via terminal tool.
   - The verification summary MUST explicitly report both Error Count AND Warning Count (e.g. `Inspection Summary: 7 checks evaluated | Errors: 0 | Warnings: 2`).
   - If warnings are present, list each warning check ID, message, and target file. NEVER report "All quality gates passed" without explicitly reporting the warnings count and warning details so the team has full visibility before proceeding.
   - If `synapse` CLI is absent:
     - Check essential directories (`.github/agents`, `.github/hooks`).
     - Display:
       `> [!NOTE] Synapse CLI is not installed in the active environment. Install via: pip install ./synapse-sdlc or git repository URL for automated quality gate inspection.`

3. **Dynamic Model Self-Declaration:**
   - Identify your active LLM model engine (e.g. `Claude Sonnet 5`, `GPT-5.6 Luna`, `Gemini 3.8 Flash`, `GPT-5.3-Codex`).
   - Run `python -m synapse model set "<Your Self-Identified Model>"` to register your exact model in `.synapse/active_model.txt`.

4. **Workspace Summary:**
   - Summarize repository branch, detected tech stack, active model, tool availability, and readiness to run `/orchestrate`.

## Zero-Refusal Guarantee:
NEVER output "I'm sorry, I can't answer that question with what I currently know about your workspace." Summarize all discovered environment facts, git state, and readiness clearly.
