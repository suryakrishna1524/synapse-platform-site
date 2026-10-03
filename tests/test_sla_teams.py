"""Automated Test Suite for SLA Prediction, Circuit Breaker & Multi-Tenant Team Workspaces."""

import pytest
from src.store import TelemetryStore


@pytest.fixture
def store():
    return TelemetryStore()


def test_sla_prediction_calculation(store):
    sla = store.get_sla_prediction()
    assert "p50_latency_s" in sla
    assert "p95_latency_s" in sla
    assert "p99_latency_s" in sla
    assert "error_rate_pct" in sla
    assert "sla_status" in sla
    assert sla["sla_status"] in ("OPTIMAL", "HEALTHY", "WARNING", "CRITICAL")
    assert sla["target_p95_sla_s"] == 2.5


def test_circuit_breaker_toggle_and_state(store):
    cb = store.get_circuit_breaker_state()
    assert cb["state"] in ("CLOSED", "OPEN", "HALF_OPEN")

    # Trip the circuit breaker
    updated = store.toggle_circuit_breaker("OPEN", "High error rate spike", "secops@synapse-sdlc.dev", "operator")
    assert updated["state"] == "OPEN"
    assert updated["auto_throttle"] is True
    assert updated["tripped_count"] >= 1

    # Reset
    reset = store.toggle_circuit_breaker("CLOSED", "Resolved incident", "secops@synapse-sdlc.dev", "operator")
    assert reset["state"] == "CLOSED"
    assert reset["auto_throttle"] is False


def test_multi_tenant_team_quotas(store):
    teams = store.get_team_quotas()
    assert len(teams) >= 4
    core_team = next(t for t in teams if t["id"] == "team-core")
    assert "allocated_tokens" in core_team
    assert "utilization_pct" in core_team
    assert core_team["allocated_tokens"] == 100000

    # Update quota
    res = store.update_team_quota("team-core", 150000, "admin@synapse-sdlc.dev", "admin")
    assert res is True

    updated_teams = store.get_team_quotas()
    updated_core = next(t for t in updated_teams if t["id"] == "team-core")
    assert updated_core["allocated_tokens"] == 150000
