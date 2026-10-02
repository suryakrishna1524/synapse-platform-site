"""Automated Test Suite for Anomaly Detection, Alert Acknowledgment & Token Budget Forecasting."""

import json
import pytest
from src.store import TelemetryStore


@pytest.fixture
def store():
    return TelemetryStore()


def test_detect_anomalies_spend_spike(store):
    # Add a massive token spend spike
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
    top_alert = anomalies[0]
    assert top_alert["contract_id"] == "AC-RUNAWAY-LOOP"
    assert top_alert["anomaly_type"] in ("SPEND_SPIKE", "LATENCY_SPIKE")
    assert top_alert["z_score"] >= 1.5


def test_acknowledge_alert(store):
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
    anomalies = store.detect_anomalies(threshold_z=1.0)
    err_alerts = [a for a in anomalies if a["contract_id"] == "AC-ERR-01"]
    assert len(err_alerts) > 0
    alert_id = err_alerts[0]["alert_id"]

    # Acknowledge
    assert not err_alerts[0]["acknowledged"]
    res = store.acknowledge_alert(alert_id, "secops@synapse-sdlc.dev", "operator")
    assert res is True

    # Re-fetch
    updated = store.detect_anomalies(threshold_z=1.0)
    ack_alert = next(a for a in updated if a["alert_id"] == alert_id)
    assert ack_alert["acknowledged"] is True


def test_get_budget_forecast(store):
    forecast = store.get_budget_forecast(projected_days=30, monthly_quota_usd=20.0)
    assert "current_spend_usd" in forecast
    assert "daily_burn_rate_usd" in forecast
    assert "forecast_points" in forecast
    assert len(forecast["forecast_points"]) == 30
    assert forecast["forecast_points"][0]["day"] == 1
    assert forecast["forecast_points"][-1]["day"] == 30
    assert forecast["forecast_points"][-1]["upper_bound_usd"] >= forecast["forecast_points"][-1]["projected_spend_usd"]
