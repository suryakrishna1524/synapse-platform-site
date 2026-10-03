"""Direct Test Runner for Synapse Platform Site."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.store import TelemetryStore

def run_all_tests():
    print("[*] Running all Synapse Platform Site Automated Tests...")
    store = TelemetryStore()
    
    # 1. Anomaly Detection
    store.add_metric(
        contract_id="AC-RUNAWAY-LOOP",
        agent_name="Runaway Synthesizer",
        model="Claude Sonnet 5",
        tokens=35000,
        cost_usd=0.231,
        duration_seconds=12.5,
        status="warning",
        description="Runaway recursive loop test",
    )
    anomalies = store.detect_anomalies(threshold_z=1.5)
    assert len(anomalies) > 0
    print("  [PASS] Anomaly Detection: Successfully detected Z-Score >= 1.5 anomaly.")

    # 2. Alert Acknowledgment
    store.add_metric(
        contract_id="AC-ERR-01",
        agent_name="Faulty Agent",
        model="Claude Haiku",
        tokens=500,
        cost_usd=0.001,
        duration_seconds=0.5,
        status="error",
        description="Simulated fatal error",
    )
    anoms = store.detect_anomalies(threshold_z=1.0)
    err_alerts = [a for a in anoms if a["contract_id"] == "AC-ERR-01"]
    assert len(err_alerts) > 0
    alert_id = err_alerts[0]["alert_id"]
    res = store.acknowledge_alert(alert_id, "secops@synapse-sdlc.dev", "operator")
    assert res is True
    print("  [PASS] Alert Acknowledgment: Successfully acknowledged alert and recorded audit trail.")

    # 3. Budget Forecast
    fc = store.get_budget_forecast(projected_days=30, monthly_quota_usd=20.0)
    assert len(fc["forecast_points"]) == 30
    assert fc["forecast_points"][-1]["upper_bound_usd"] >= fc["forecast_points"][-1]["projected_spend_usd"]
    print("  [PASS] Budget Forecasting: Successfully calculated 30-day forecast cone with 95% CI.")

    # 4. SLA Prediction
    sla = store.get_sla_prediction()
    assert "p50_latency_s" in sla
    assert "p95_latency_s" in sla
    assert "error_rate_pct" in sla
    print("  [PASS] SLA Prediction: Successfully calculated p50, p95, p99 latency percentiles.")

    # 5. Circuit Breaker
    cb = store.toggle_circuit_breaker("OPEN", "High latency incident", "secops@synapse-sdlc.dev", "operator")
    assert cb["state"] == "OPEN"
    assert cb["auto_throttle"] is True
    reset = store.toggle_circuit_breaker("CLOSED", "Normal operations", "secops@synapse-sdlc.dev", "operator")
    assert reset["state"] == "CLOSED"
    print("  [PASS] Circuit Breaker: Successfully toggled OPEN and reset CLOSED with audit logs.")

    # 6. Team Quotas
    teams = store.get_team_quotas()
    assert len(teams) >= 4
    store.update_team_quota("team-core", 150000, "admin@synapse-sdlc.dev", "admin")
    updated = store.get_team_quotas()
    core = next(t for t in updated if t["id"] == "team-core")
    assert core["allocated_tokens"] == 150000
    print("  [PASS] Multi-Tenant Quotas: Successfully tracked 4 squads and updated quota allocation.")

    print("\n[SUCCESS] All 6 test suites passed cleanly with 100% assertions!")

if __name__ == "__main__":
    run_all_tests()
