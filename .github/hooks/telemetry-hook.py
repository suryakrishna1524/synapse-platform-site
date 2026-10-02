#!/usr/bin/env python3
"""Synapse Telemetry Hook.

Collects real-time token metrics, calculates exact model costs, and updates reports.
Handles SessionStart, PreToolUse, PostToolUse, and Stop lifecycle events.
"""

import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional

# Self-contained Pricing & Budgeting Catalog (USD per 1 Million tokens)
MODEL_PRICING_CATALOG = {
    # Anthropic
    "claude-sonnet-5": {"input": 3.00, "cached_input": 0.30, "output": 15.00},
    "claude-opus-5": {"input": 15.00, "cached_input": 1.50, "output": 75.00},
    "claude-haiku-4.5": {"input": 0.80, "cached_input": 0.08, "output": 4.00},
    "claude-3-7-sonnet": {"input": 3.00, "cached_input": 0.30, "output": 15.00},
    "claude-3-5-sonnet": {"input": 3.00, "cached_input": 0.30, "output": 15.00},
    "claude-3-5-haiku": {"input": 0.80, "cached_input": 0.08, "output": 4.00},
    "claude-3-opus": {"input": 15.00, "cached_input": 1.50, "output": 75.00},

    # OpenAI & Codex
    "gpt-5.3-codex": {"input": 2.50, "cached_input": 1.25, "output": 10.00},
    "gpt-5.6-terra": {"input": 3.00, "cached_input": 1.50, "output": 12.00},
    "gpt-5.6-luna": {"input": 0.50, "cached_input": 0.15, "output": 2.00},
    "gpt-5.6": {"input": 3.00, "cached_input": 1.50, "output": 12.00},
    "gpt-5.5": {"input": 5.00, "cached_input": 2.50, "output": 20.00},
    "gpt-5.4": {"input": 3.00, "cached_input": 1.50, "output": 12.00},
    "gpt-5-mini": {"input": 0.15, "cached_input": 0.075, "output": 0.60},
    "gpt-6-astra": {"input": 10.00, "cached_input": 5.00, "output": 40.00},
    "gpt-4.5": {"input": 75.00, "cached_input": 37.50, "output": 150.00},
    "gpt-4o": {"input": 2.50, "cached_input": 1.25, "output": 10.00},
    "gpt-4o-mini": {"input": 0.15, "cached_input": 0.075, "output": 0.60},
    "o1": {"input": 15.00, "cached_input": 7.50, "output": 60.00},
    "o1-mini": {"input": 1.10, "cached_input": 0.55, "output": 4.40},
    "o3-mini": {"input": 1.10, "cached_input": 0.55, "output": 4.40},

    # Google Gemini
    "gemini-3.8-flash": {"input": 0.10, "cached_input": 0.025, "output": 0.40},
    "gemini-2.5-pro": {"input": 1.25, "cached_input": 0.31, "output": 5.00},
    "gemini-2.0-flash": {"input": 0.10, "cached_input": 0.025, "output": 0.40},
    "gemini-2.0-flash-lite": {"input": 0.075, "cached_input": 0.018, "output": 0.30},

    # GitHub Copilot & Fallback
    "github-copilot": {"input": 2.50, "cached_input": 1.25, "output": 10.00},
    "copilot": {"input": 2.50, "cached_input": 1.25, "output": 10.00},
    "default": {"input": 2.50, "cached_input": 0.50, "output": 10.00},
}

UNRESOLVED_MODEL_TOKENS = {
    "auto", "default", "copilot", "github-copilot", "github copilot",
    "unknown", "copilot session", "copilot chat model", "copilot chat",
    "chat model", "", "none"
}


def is_valid_model_name(val) -> bool:
    """Checks if a model string represents a real resolved model rather than a placeholder."""
    if not val:
        return False
    clean = str(val).strip().lower()
    return clean not in UNRESOLVED_MODEL_TOKENS and len(clean) > 0


def infer_dynamic_model_rates(model_name: str):
    """Dynamically infers token pricing rates (USD per 1M tokens) for any model without hardcoded lists."""
    if not model_name:
        return MODEL_PRICING_CATALOG["default"]

    m_lower = str(model_name).strip().lower()

    # 1. Exact or substring match in catalog if present
    catalog_key = resolve_model_key(model_name)
    if catalog_key != "default":
        return MODEL_PRICING_CATALOG[catalog_key]

    # 2. Fast / Lightweight Tier (e.g. Luna, Flash, Mini, Haiku, Lite, Nano, Small)
    if any(k in m_lower for k in ("luna", "mini", "flash", "haiku", "lite", "nano", "small")):
        return {"input": 0.50, "cached_input": 0.15, "output": 2.00}

    # 3. Flagship / Heavy Reasoning Tier (e.g. Opus, o1, o3, Astra, Ultra, Large)
    if any(k in m_lower for k in ("opus", "o1", "o3", "astra", "ultra", "large")):
        return {"input": 15.00, "cached_input": 1.50, "output": 75.00}

    # 4. Standard Coding & Reasoning Tier (e.g. Sonnet, Codex, Pro, GPT-4, GPT-5)
    return {"input": 3.00, "cached_input": 0.30, "output": 15.00}


def get_blended_rate(model_name: str, input_ratio: float = 0.7, output_ratio: float = 0.3) -> float:
    """Computes blended token rate per 1M tokens matching copilot-instructions.md (70% in, 30% out)."""
    rates = infer_dynamic_model_rates(model_name)
    return round((input_ratio * rates["input"]) + (output_ratio * rates["output"]), 4)


def resolve_model_key(model_name: str) -> str:
    """Matches a runtime model name to our pricing catalog."""
    if not model_name:
        return "default"

    def _norm(s: str) -> str:
        return s.strip().lower().replace("_", "").replace("-", "").replace(".", "").replace(" ", "")

    n_input = _norm(model_name)
    if not n_input:
        return "default"

    # Exact normalized match
    for key in MODEL_PRICING_CATALOG:
        if key != "default" and _norm(key) == n_input:
            return key

    # Substring match
    for key in MODEL_PRICING_CATALOG:
        if key != "default":
            n_key = _norm(key)
            if n_key in n_input or n_input in n_key:
                return key

    return "default"


def calculate_token_cost(
    model_name: str,
    prompt_tokens: int,
    completion_tokens: int,
    cached_prompt_tokens: int = 0,
):
    """Calculates USD cost for given token counts with guaranteed non-zero floor."""
    key = resolve_model_key(model_name)
    rates = infer_dynamic_model_rates(model_name)

    effective_standard_prompt = max(0, prompt_tokens - cached_prompt_tokens)

    input_cost = (effective_standard_prompt / 1_000_000.0) * rates["input"]
    cached_cost = (cached_prompt_tokens / 1_000_000.0) * rates["cached_input"]
    output_cost = (completion_tokens / 1_000_000.0) * rates["output"]

    total = input_cost + cached_cost + output_cost

    # When tokens are greater than zero, guarantee a non-zero cost floor
    if (prompt_tokens + completion_tokens) > 0 and total < 0.0001:
        total = 0.0001

    breakdown = {
        "model": key,
        "input_cost_usd": round(input_cost, 6),
        "cached_input_cost_usd": round(cached_cost, 6),
        "output_cost_usd": round(output_cost, 6),
        "total_cost_usd": round(total, 6),
    }

    return round(total, 6), breakdown


class SubscriptionPlan:
    """Developer subscription plan definition with spend ceilings and metering flags."""
    def __init__(self, code, name, budget_usd, unmetered=False, description=""):
        self.code = code
        self.name = name
        self.budget_usd = budget_usd
        self.unmetered = unmetered
        self.description = description

    def to_dict(self):
        return {
            "code": self.code,
            "name": self.name,
            "budget_usd": self.budget_usd,
            "unmetered": self.unmetered,
            "description": self.description,
        }


class SubscriptionPlanCatalog:
    """Catalog of supported developer subscription plans and spend ceilings."""

    PLANS = {
        "free": SubscriptionPlan(
            code="free",
            name="Copilot Free",
            budget_usd=2.00,
            unmetered=False,
            description="Free Tier (50 chat requests/month)",
        ),
        "individual": SubscriptionPlan(
            code="individual",
            name="Copilot Individual",
            budget_usd=10.00,
            unmetered=False,
            description="Individual / Pro Plan ($10.00 allowance)",
        ),
        "business": SubscriptionPlan(
            code="business",
            name="Copilot Business",
            budget_usd=25.00,
            unmetered=False,
            description="Business Team Plan ($25.00 seat allowance)",
        ),
        "enterprise": SubscriptionPlan(
            code="enterprise",
            name="Copilot Enterprise",
            budget_usd=100.00,
            unmetered=True,
            description="Enterprise Plan (Unmetered / Policy Audited)",
        ),
        "custom": SubscriptionPlan(
            code="custom",
            name="Custom Allowance",
            budget_usd=50.00,
            unmetered=False,
            description="Custom user-defined budget ceiling",
        ),
    }

    @classmethod
    def get_plan(cls, code):
        if not code:
            return cls.PLANS["individual"]
        normalized = str(code).strip().lower()
        if normalized in cls.PLANS:
            return cls.PLANS[normalized]
        if "enterprise" in normalized or "corp" in normalized:
            return cls.PLANS["enterprise"]
        if "biz" in normalized or "business" in normalized or "team" in normalized:
            return cls.PLANS["business"]
        if "free" in normalized:
            return cls.PLANS["free"]
        if "pro" in normalized or "indiv" in normalized:
            return cls.PLANS["individual"]
        return cls.PLANS["individual"]


def resolve_active_plan(repo_path=None):
    """Resolves active subscription plan using environment, workspace config, and remotes."""
    # 1. Environment variable override
    env_plan = os.environ.get("SYNAPSE_PLAN") or os.environ.get("COPILOT_PLAN")
    if env_plan:
        plan = SubscriptionPlanCatalog.get_plan(env_plan)
        custom_cap = os.environ.get("SYNAPSE_MAX_TICKET_BUDGET") or os.environ.get("SYNAPSE_BUDGET_CAP")
        if custom_cap:
            try:
                cap_val = float(custom_cap)
                return SubscriptionPlan(plan.code, plan.name, cap_val, False, plan.description)
            except ValueError:
                pass
        return plan

    # 2. Local workspace configuration file: .synapse/plan.json
    base_dir = Path(repo_path).resolve() if repo_path else Path.cwd()
    plan_file = base_dir / ".synapse" / "plan.json"
    if plan_file.exists():
        try:
            cfg = json.loads(plan_file.read_text(encoding="utf-8"))
            p_code = cfg.get("plan") or cfg.get("code")
            if p_code:
                plan = SubscriptionPlanCatalog.get_plan(p_code)
                custom_budget = cfg.get("budget_usd")
                if custom_budget is not None:
                    return SubscriptionPlan(
                        plan.code,
                        cfg.get("name") or plan.name,
                        float(custom_budget),
                        bool(cfg.get("unmetered", plan.unmetered)),
                        cfg.get("description", plan.description),
                    )
                return plan
        except Exception:
            pass

    # 3. Remote URL heuristic detection (e.g. corporate GitLab, Azure, Enterprise GitHub)
    try:
        git_config = base_dir / ".git" / "config"
        if git_config.exists():
            remote_urls = []
            for line in git_config.read_text(encoding="utf-8").splitlines():
                stripped = line.strip()
                if stripped.lower().startswith("url =") or stripped.lower().startswith("url="):
                    remote_urls.append(stripped.split("=", 1)[1].strip().lower())

            for url in remote_urls:
                if any(k in url for k in ("git.epam.com", "ghe.", "github.enterprise", "/enterprise/")):
                    return SubscriptionPlanCatalog.get_plan("enterprise")
                if any(k in url for k in ("gitlab.com", "dev.azure.com", "visualstudio.com")):
                    return SubscriptionPlanCatalog.get_plan("business")
    except Exception:
        pass

    return SubscriptionPlanCatalog.get_plan("individual")


class TokenBudgetGuard:
    """Enforces spending limits per ticket/session based on user subscription plans."""

    DEFAULT_BUDGET_USD: float = 10.00

    @classmethod
    def check_budget(cls, current_spent_usd: float, max_budget_usd=None, plan=None):
        active_plan = plan or resolve_active_plan()

        if max_budget_usd is not None:
            ceiling = max_budget_usd
            unmetered = False
        else:
            env_budget = os.environ.get("SYNAPSE_MAX_TICKET_BUDGET") or os.environ.get("SYNAPSE_BUDGET_CAP")
            if env_budget:
                try:
                    ceiling = float(env_budget)
                    unmetered = False
                except ValueError:
                    ceiling = active_plan.budget_usd
                    unmetered = active_plan.unmetered
            else:
                ceiling = active_plan.budget_usd
                unmetered = active_plan.unmetered

        if unmetered:
            return True, ""

        if current_spent_usd >= ceiling:
            return False, f"Plan spend (${current_spent_usd:.2f}) reached or exceeded plan budget cap of ${ceiling:.2f} ({active_plan.name})"
        if current_spent_usd >= (ceiling * 0.8):
            return True, f"Warning: Plan spend (${current_spent_usd:.2f}) is at 80% of plan budget cap (${ceiling:.2f} - {active_plan.name})"
        return True, ""


def _ensure_git_ignored(repo_path=None):
    """Ensures .synapse/ is never tracked by git across local repositories."""
    try:
        cwd = Path(repo_path).resolve() if repo_path else Path.cwd()
        ign = cwd / ".synapse" / ".gitignore"
        if not ign.exists():
            ign.write_text("# Synapse runtime state - do not commit\n*\n", encoding="utf-8")

        git_dir = cwd / ".git"
        if git_dir.is_dir():
            exclude_file = git_dir / "info" / "exclude"
            exclude_file.parent.mkdir(parents=True, exist_ok=True)
            content = exclude_file.read_text(encoding="utf-8") if exclude_file.exists() else ""
            if ".synapse" not in content:
                with open(exclude_file, "a", encoding="utf-8") as f:
                    f.write("\n# Synapse SDLC developer runtime state\n.synapse/\n.synapse\n")
    except Exception:
        pass


def resolve_active_model(repo_path=None) -> str:
    """Dynamically resolves the active LLM from environment, workspace state, or agent frontmatter."""
    base_dir = Path(repo_path).resolve() if repo_path else Path.cwd()

    # 1. Environment variable override
    env_model = os.environ.get("SYNAPSE_DEFAULT_MODEL") or os.environ.get("COPILOT_MODEL") or os.environ.get("VSCODE_COPILOT_MODEL")
    if is_valid_model_name(env_model):
        return env_model.strip()

    # 2. Local workspace state file: .synapse/active_model.txt
    active_model_file = base_dir / ".synapse" / "active_model.txt"
    if active_model_file.exists():
        try:
            val = active_model_file.read_text(encoding="utf-8").strip()
            if is_valid_model_name(val):
                return val
        except Exception:
            pass

    # 3. Existing session telemetry: .synapse/session_telemetry.json
    session_file = base_dir / ".synapse" / "session_telemetry.json"
    if session_file.exists():
        try:
            data = json.loads(session_file.read_text(encoding="utf-8"))
            val = str(data.get("active_model", "")).strip()
            if is_valid_model_name(val):
                return val
        except Exception:
            pass

    # 4. Agent definitions in .github/agents/
    agents_dir = base_dir / ".github" / "agents"
    if agents_dir.is_dir():
        import re
        orch_candidates = [agents_dir / "orchestrator.agent.md", agents_dir / "synapse-orchestrator.agent.md"]
        for of in orch_candidates:
            if of.exists():
                try:
                    content = of.read_text(encoding="utf-8")
                    m = re.search(r"^model:\s*(.+)$", content, re.MULTILINE)
                    if m:
                        val = m.group(1).strip()
                        if is_valid_model_name(val):
                            return val
                except Exception:
                    pass
        for agent_file in sorted(agents_dir.glob("*.agent.md")):
            try:
                content = agent_file.read_text(encoding="utf-8")
                m = re.search(r"^model:\s*(.+)$", content, re.MULTILINE)
                if m:
                    val = m.group(1).strip()
                    if is_valid_model_name(val):
                        return val
            except Exception:
                pass

    return "Copilot Chat Model"


def _atomic_write_json(file_path: Path, data: Any) -> None:
    """Writes JSON atomically using a process-specific temporary file and os.replace."""
    tmp_path = file_path.with_name(f".{file_path.name}.tmp.{os.getpid()}")
    try:
        tmp_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        os.replace(tmp_path, file_path)
    except Exception:
        try:
            if tmp_path.exists():
                tmp_path.unlink()
        except Exception:
            pass
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)


def _safe_load_json(file_path: Path, retries: int = 3, backoff_sec: float = 0.02) -> Optional[Dict[str, Any]]:
    """Safely reads a JSON file with retries to prevent race conditions during rapid hook invocations."""
    if not file_path.exists():
        return None
    for attempt in range(retries):
        try:
            content = file_path.read_text(encoding="utf-8").strip()
            if content:
                loaded = json.loads(content)
                if isinstance(loaded, dict):
                    return loaded
        except (json.JSONDecodeError, OSError):
            time.sleep(backoff_sec * (attempt + 1))
    return None


def get_or_update_session_spend(
    cost: float = 0.0,
    tokens: int = 0,
    model: str = "",
    plan=None,
    repo_path=None,
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
) -> tuple:
    """Reads or updates running session spend in .synapse/session_telemetry.json.

    Returns (total_spent_usd, total_session_tokens, active_model, active_plan).
    """
    try:
        base_dir = Path(repo_path).resolve() if repo_path else Path.cwd()
        session_dir = base_dir / ".synapse"
        session_dir.mkdir(parents=True, exist_ok=True)
        _ensure_git_ignored(str(base_dir))
        session_file = session_dir / "session_telemetry.json"
        active_plan = plan or resolve_active_plan(str(base_dir))
        default_model = model or resolve_active_model(str(base_dir))
        data = {
            "total_spent_usd": 0.0,
            "total_tokens": 0,
            "calls": 0,
            "active_model": default_model,
            "last_prompt_tokens": 0,
            "last_prompt_cost_usd": 0.0,
            "models": {},
            "plan": active_plan.code,
            "plan_name": active_plan.name,
            "plan_budget_usd": active_plan.budget_usd,
            "unmetered": active_plan.unmetered,
        }
        session_exists = session_file.exists()
        loaded = None
        if session_exists:
            loaded = _safe_load_json(session_file)
            if loaded is not None:
                data.update(loaded)
            else:
                # If file exists on disk but reading failed after retries, do not overwrite with 0 tokens
                return (
                    float(data.get("total_spent_usd", 0.0)),
                    int(data.get("total_tokens", 0)),
                    str(data.get("active_model", default_model)),
                    active_plan,
                )

        resolved_model = model.strip() if model else ""
        if is_valid_model_name(resolved_model):
            data["active_model"] = resolved_model
            try:
                (session_dir / "active_model.txt").write_text(resolved_model + "\n", encoding="utf-8")
            except Exception:
                pass
        elif not is_valid_model_name(data.get("active_model", "")):
            data["active_model"] = default_model

        data["plan"] = active_plan.code
        data["plan_name"] = active_plan.name
        data["plan_budget_usd"] = active_plan.budget_usd
        data["unmetered"] = active_plan.unmetered

        if cost > 0.0 or tokens > 0:
            data["total_spent_usd"] = round(float(data.get("total_spent_usd", 0.0)) + cost, 6)
            data["total_tokens"] = int(data.get("total_tokens", 0)) + tokens
            data["calls"] = int(data.get("calls", 0)) + 1
            data["last_prompt_tokens"] = tokens
            data["last_prompt_cost_usd"] = round(cost, 6)
            if prompt_tokens > 0 or completion_tokens > 0:
                data["last_prompt_input_tokens"] = prompt_tokens
                data["last_prompt_output_tokens"] = completion_tokens

            curr_model = data.get("active_model", default_model)
            if "models" not in data or not isinstance(data["models"], dict):
                data["models"] = {}
            m_stat = data["models"].setdefault(curr_model, {"tokens": 0, "spent_usd": 0.0, "calls": 0})
            m_stat["tokens"] = int(m_stat.get("tokens", 0)) + tokens
            m_stat["spent_usd"] = round(float(m_stat.get("spent_usd", 0.0)) + cost, 6)
            m_stat["calls"] = int(m_stat.get("calls", 0)) + 1

            data["last_updated"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            _atomic_write_json(session_file, data)
        elif not session_file.exists():
            data["last_updated"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            _atomic_write_json(session_file, data)
        elif not is_valid_model_name(data.get("active_model", "")):
            data["active_model"] = default_model
            data["last_updated"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            _atomic_write_json(session_file, data)

        return (
            float(data.get("total_spent_usd", 0.0)),
            int(data.get("total_tokens", 0)),
            str(data.get("active_model", default_model)),
            active_plan,
        )
    except Exception:
        active_plan = plan or resolve_active_plan(repo_path)
        return float(cost), int(tokens), model or "Copilot Chat Model", active_plan


def reconcile_workspace_telemetry(repo_path=None):
    """Reconciles session telemetry by inspecting checkpoint state and git history."""
    try:
        base_dir = Path(repo_path).resolve() if repo_path else Path.cwd()
        total_tokens = 0
        calls = 0
        detected_model = resolve_active_model(str(base_dir))

        # 1. Inspect checkpoints
        cp_file = base_dir / ".synapse" / "checkpoints" / "checkpoint_state.json"
        if cp_file.exists():
            try:
                cp_data = json.loads(cp_file.read_text(encoding="utf-8"))
                phases = cp_data.get("phases", {})
                completed_count = sum(1 for p in phases.values() if isinstance(p, dict) and p.get("status") == "completed")
                if completed_count > 0:
                    total_tokens += completed_count * 5000
                    calls += completed_count
            except Exception:
                pass

        # 2. Inspect git commit history for recent code authored in this workspace
        import subprocess
        try:
            res = subprocess.run(
                ["git", "rev-list", "--count", "HEAD"],
                cwd=base_dir,
                capture_output=True,
                text=True
            )
            commit_count = int(res.stdout.strip()) if res.stdout.strip().isdigit() else 0
            if commit_count > 0:
                shortstat = subprocess.run(
                    ["git", "diff", "HEAD~5..HEAD", "--shortstat"],
                    cwd=base_dir,
                    capture_output=True,
                    text=True
                )
                import re
                m = re.search(r"(\d+)\s+insertions?", shortstat.stdout)
                ins = int(m.group(1)) if m else 0
                git_tokens = max(1500, ins * 10)
                total_tokens += git_tokens
                calls += min(commit_count, 10)
        except Exception:
            pass

        # 3. Inspect workspace source files if checkpoints and git commits are absent
        if total_tokens == 0:
            try:
                code_files = [
                    f for f in base_dir.rglob("*")
                    if f.is_file() and not any(p in f.parts for p in (".git", ".synapse", "node_modules", "dist", "build", ".DS_Store", "__pycache__", ".github"))
                ]
                if code_files:
                    total_bytes = sum(f.stat().st_size for f in code_files)
                    if total_bytes > 0:
                        total_tokens += max(1200, min(30000, total_bytes // 4))
                        calls += max(1, len(code_files) // 2)
            except Exception:
                pass

        if total_tokens == 0:
            active_plan = resolve_active_plan(str(base_dir))
            session_file = base_dir / ".synapse" / "session_telemetry.json"
            if session_file.exists():
                try:
                    data = json.loads(session_file.read_text(encoding="utf-8"))
                    curr = str(data.get("active_model", "")).strip()
                    if not is_valid_model_name(curr):
                        data["active_model"] = detected_model
                        with open(session_file, "w", encoding="utf-8") as f:
                            json.dump(data, f, indent=2)
                except Exception:
                    pass
            return 0.0, 0, detected_model, active_plan

        cost, _ = calculate_token_cost(detected_model, prompt_tokens=int(total_tokens * 0.7), completion_tokens=int(total_tokens * 0.3))
        active_plan = resolve_active_plan(str(base_dir))
        return get_or_update_session_spend(cost=cost, tokens=total_tokens, model=detected_model, plan=active_plan, repo_path=str(base_dir))
    except Exception:
        active_plan = resolve_active_plan(repo_path)
        return 0.0, 0, resolve_active_model(repo_path), active_plan


def reset_session_telemetry(repo_path=None):
    """Resets session telemetry in .synapse/session_telemetry.json to zero."""
    base_dir = Path(repo_path).resolve() if repo_path else Path.cwd()
    session_dir = base_dir / ".synapse"
    session_dir.mkdir(parents=True, exist_ok=True)
    session_file = session_dir / "session_telemetry.json"
    active_plan = resolve_active_plan(str(base_dir))
    data = {
        "total_spent_usd": 0.0,
        "total_tokens": 0,
        "calls": 0,
        "active_model": "Copilot Session",
        "plan": active_plan.code,
        "plan_name": active_plan.name,
        "plan_budget_usd": active_plan.budget_usd,
        "unmetered": active_plan.unmetered,
        "last_updated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    with open(session_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    return data


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Synapse Telemetry Hook & Standalone Recorder", add_help=False)
    parser.add_argument("--tokens", type=int, default=0, help="Tokens to record")
    parser.add_argument("--prompt-tokens", type=int, default=0)
    parser.add_argument("--completion-tokens", type=int, default=0)
    parser.add_argument("--cost", type=float, default=0.0)
    parser.add_argument("--model", type=str, default="")
    parser.add_argument("--agent", type=str, default="orchestrator")
    parser.add_argument("--sync", action="store_true", help="Reconcile telemetry from checkpoint state and git history")
    parser.add_argument("--reset", action="store_true", help="Reset session telemetry to zero")
    parser.add_argument("--status", action="store_true", help="Show session telemetry status")
    parser.add_argument("--path", type=str, default=".")

    args, unknown = parser.parse_known_args()
    base_dir = Path(getattr(args, "path", None) or ".").resolve()

    if args.reset:
        reset_session_telemetry(str(base_dir))
        sys.stderr.write(f"[SYNAPSE TELEMETRY] Reset session telemetry to zero in {base_dir}\n")
        sys.exit(0)

    if args.sync:
        spent, tokens, model, plan = reconcile_workspace_telemetry(str(base_dir))
        sys.stderr.write(f"[SYNAPSE TELEMETRY] Reconciled: {tokens:,} tokens | ${spent:.4f} | Plan: {plan.name}\n")
        sys.exit(0)

    if args.status:
        session_file = base_dir / ".synapse" / "session_telemetry.json"
        plan = resolve_active_plan(str(base_dir))
        spent = 0.0
        tokens = 0
        calls = 0
        model = resolve_active_model(str(base_dir))
        last_prompt_tokens = 0
        last_prompt_cost = 0.0
        if session_file.exists():
            try:
                with open(session_file, "r", encoding="utf-8") as f:
                    tel = json.load(f)
                if isinstance(tel, dict):
                    spent = float(tel.get("total_spent_usd", 0.0))
                    tokens = int(tel.get("total_tokens", 0))
                    calls = int(tel.get("calls", 0))
                    model = str(tel.get("active_model", model))
                    last_prompt_tokens = int(tel.get("last_prompt_tokens", 0))
                    last_prompt_cost = float(tel.get("last_prompt_cost_usd", 0.0))
            except Exception:
                pass
        disp_tok = tokens if tokens > 0 else last_prompt_tokens
        disp_cost = spent if spent > 0.0 else last_prompt_cost
        sys.stdout.write(f"Model: {model} | Tokens: {disp_tok:,} | Cost: ${disp_cost:.4f}\n")
        sys.exit(0)

    if args.tokens > 0 or args.prompt_tokens > 0 or args.completion_tokens > 0 or args.cost > 0.0:
        model = args.model or resolve_active_model(str(base_dir))
        p_tokens = args.prompt_tokens or int(args.tokens * 0.7)
        c_tokens = args.completion_tokens or int(args.tokens * 0.3)
        cost = args.cost
        if cost <= 0.0 and (p_tokens + c_tokens) > 0:
            cost, _ = calculate_token_cost(model, p_tokens, c_tokens)
        spent, tokens, active_model, active_plan = get_or_update_session_spend(
            cost,
            p_tokens + c_tokens,
            model,
            repo_path=str(base_dir),
            prompt_tokens=p_tokens,
            completion_tokens=c_tokens,
        )
        sys.stderr.write(f"[SYNAPSE TELEMETRY] Recorded: {p_tokens + c_tokens:,} tokens | ${cost:.4f} | Session Total: ${spent:.4f}\n")
        sys.exit(0)

    try:
        raw = ""
        if not sys.stdin.isatty():
            try:
                raw = sys.stdin.read()
            except Exception:
                raw = ""
        if not raw.strip():
            sys.exit(0)

        data = json.loads(raw)
        event_name = data.get("event", data.get("hookEventName", data.get("eventName", "")))
        usage = data.get("usage", {})
        prompt_tokens = usage.get("prompt_tokens", usage.get("input_tokens", 0)) if isinstance(usage, dict) else 0
        completion_tokens = usage.get("completion_tokens", usage.get("output_tokens", 0)) if isinstance(usage, dict) else 0
        cached_tokens = usage.get("cached_prompt_tokens", usage.get("cached_tokens", 0)) if isinstance(usage, dict) else 0
        raw_model = (
            data.get("model")
            or data.get("modelName")
            or data.get("model_name")
            or data.get("selectedModel")
            or data.get("chatModel")
            or data.get("activeModel")
            or (data.get("configuration") or {}).get("model")
            or (data.get("context") or {}).get("model")
            or ""
        )
        agent_name = data.get("agent", data.get("toolName", "orchestrator"))

        # If explicit token counts are omitted by Copilot runtime, estimate from payload text
        if prompt_tokens == 0 and completion_tokens == 0:
            input_text = ""
            for k in (
                "prompt", "userPrompt", "message", "query", "user_input"
            ):
                val = data.get(k)
                if isinstance(val, (dict, list)):
                    input_text += " " + json.dumps(val)
                elif isinstance(val, str):
                    input_text += " " + val

            # Check tool arguments: if tool writes/generates code, treat that as output (completion tokens)
            tool_input = data.get("toolInput", data.get("tool_input", data.get("arguments", data.get("args", {}))))
            output_code = ""
            tool_args_str = ""
            if isinstance(tool_input, dict):
                for k in ("content", "ReplacementContent", "code", "file_text", "text", "body", "data"):
                    if k in tool_input and isinstance(tool_input[k], str):
                        output_code += " " + tool_input[k]
                tool_args_str = json.dumps(tool_input)
            elif isinstance(tool_input, str):
                tool_args_str = tool_input

            output_text = output_code
            for k in (
                "response", "toolResult", "toolOutput", "result",
                "code", "content", "body", "data"
            ):
                val = data.get(k)
                if isinstance(val, (dict, list)):
                    output_text += " " + json.dumps(val)
                elif isinstance(val, str):
                    output_text += " " + val

            # If input_text is empty, use non-code tool arguments or raw payload
            if not input_text.strip():
                input_text = tool_args_str if not output_code else data.get("command", "")
            if not input_text.strip() and not output_text.strip() and raw.strip():
                input_text = raw.strip()

            if input_text.strip():
                prompt_tokens = max(10, len(input_text.strip()) // 4)
            if output_text.strip():
                completion_tokens = max(10, len(output_text.strip()) // 4)
            elif prompt_tokens > 10 and str(event_name).strip().lower() != "pretooluse":
                completion_tokens = max(10, int(prompt_tokens * 0.3))

        # Resolve model name dynamically: if generic or omitted, check agent file or active model file
        model = raw_model.strip() if raw_model else ""
        if not is_valid_model_name(model):
            agents_dir = base_dir / ".github" / "agents"
            if agent_name and agents_dir.is_dir():
                for af in agents_dir.glob(f"*{agent_name}*.agent.md"):
                    try:
                        import re
                        m = re.search(r"^model:\s*(.+)$", af.read_text(encoding="utf-8"), re.MULTILINE)
                        if m:
                            val = m.group(1).strip()
                            if is_valid_model_name(val):
                                model = val
                                break
                    except Exception:
                        pass
        if not is_valid_model_name(model):
            model = resolve_active_model(str(base_dir))
        else:
            try:
                (base_dir / ".synapse" / "active_model.txt").write_text(model + "\n", encoding="utf-8")
            except Exception:
                pass

        active_plan = resolve_active_plan(str(base_dir))

        turn_tokens = prompt_tokens + completion_tokens
        cost = 0.0
        if turn_tokens > 0:
            cost, _ = calculate_token_cost(model, prompt_tokens, completion_tokens, cached_tokens)

        is_pre_tool = bool(event_name and str(event_name).strip().lower() == "pretooluse")
        if is_pre_tool:
            # PreToolUse: Pure budget guardrail check before tool executes.
            # Do NOT increment turn tokens or spend to avoid double-counting with PostToolUse.
            current_spent, _, active_model, _ = get_or_update_session_spend(
                0.0, 0, model, active_plan, repo_path=str(base_dir)
            )
            projected_spend = current_spent + cost
            within_budget, message = TokenBudgetGuard.check_budget(projected_spend, plan=active_plan)
            if not within_budget:
                out = {
                    "hookSpecificOutput": {
                        "hookEventName": "PreToolUse",
                        "status": "blocked",
                        "reason": f"BLOCKED by Synapse Token Budget Guard: {message}",
                    }
                }
                sys.stderr.write(json.dumps(out, indent=2) + "\n")
                sys.exit(2)
            elif message and turn_tokens > 0:
                sys.stderr.write(f"[SYNAPSE BUDGET WARNING] {message}\n")

            output = {
                "continue": True,
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "status": "success",
                }
            }
            sys.stdout.write(json.dumps(output) + "\n")
            sys.exit(0)

        total_spent, session_tokens, active_model, active_plan = get_or_update_session_spend(
            cost,
            turn_tokens,
            model,
            active_plan,
            repo_path=str(base_dir),
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
        )
        display_model = active_model or model

        if turn_tokens > 0:
            sys.stderr.write(
                f"[SYNAPSE TELEMETRY] Agent: {agent_name} | Model: {display_model} | Plan: {active_plan.name} | "
                f"Tokens: {turn_tokens:,} | Cost: ${cost:.4f} | Session Total: ${total_spent:.4f}\n"
            )

        # Budget enforcement
        within_budget, message = TokenBudgetGuard.check_budget(total_spent, plan=active_plan)
        if not within_budget:
            out = {
                "hookSpecificOutput": {
                    "hookEventName": event_name or "TelemetryEvent",
                    "status": "blocked",
                    "reason": f"BLOCKED by Synapse Token Budget Guard: {message}",
                }
            }
            sys.stderr.write(json.dumps(out, indent=2) + "\n")
            sys.exit(2)
        elif message and turn_tokens > 0:
            sys.stderr.write(f"[SYNAPSE BUDGET WARNING] {message}\n")

        if turn_tokens > 0:
            turn_cost_str = f"~${cost:.4f}"
            turn_tokens_str = f"~{turn_tokens:,}"
        else:
            turn_cost_str = "$0.0000"
            turn_tokens_str = "0"

        # Determine overall user plan usage percentage based on cumulative spend vs plan budget
        session_data = {}
        session_file = base_dir / ".synapse" / "session_telemetry.json"
        if session_file.exists():
            try:
                session_data = json.loads(session_file.read_text(encoding="utf-8"))
            except Exception:
                pass

        budget = getattr(active_plan, "budget_usd", 0.0)
        total_tokens_spent = int(session_data.get("total_tokens", 0))

        if budget > 0:
            usage_pct = min(100.0, (total_spent / budget) * 100.0)
        else:
            usage_pct = min(100.0, (total_tokens_spent / 100_000.0) * 100.0)

        if usage_pct < 10.0:
            plan_usage_str = f"{usage_pct:.2f}% ({active_plan.name})"
        else:
            plan_usage_str = f"{usage_pct:.1f}% ({active_plan.name})"

        if session_file.exists():
            try:
                curr_data = json.loads(session_file.read_text(encoding="utf-8"))
                curr_data["plan_usage_pct"] = round(usage_pct, 2)
                curr_data["plan_usage_str"] = plan_usage_str
                session_file.write_text(json.dumps(curr_data, indent=2), encoding="utf-8")
            except Exception:
                pass
                pass

        telemetry_badge = (
            f"> **Synapse Telemetry:** `{display_model}` | "
            f"**Tokens:** {turn_tokens_str} | "
            f"**Cost:** {turn_cost_str} | "
            f"**Plan Usage:** {plan_usage_str}"
        )

        output = {
            "continue": True,
            "systemMessage": telemetry_badge,
            "hookSpecificOutput": {
                "hookEventName": event_name or "TelemetryEvent",
                "status": "success",
                "additionalContext": telemetry_badge,
            }
        }
        sys.stdout.write(json.dumps(output) + "\n")
        sys.exit(0)
    except Exception as e:
        sys.stderr.write(f"[SYNAPSE TELEMETRY] Error: {e}\n")
        sys.exit(0)


if __name__ == "__main__":
    main()
