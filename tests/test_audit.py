import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)
AUTH_HEADERS = {"X-API-Key": "upay_risk_intel_secret_key_2026"}


def test_audit_persisted_on_predict():
    """Predict risk creates an immutable, non-repudiable audit ledger entry in SQLite."""
    test_txn_id = "UPTEST_AUDIT_7777"
    payload = {
        "transaction_id": test_txn_id,
        "txn_amount": 12500.0,
        "hour_of_day": 2,
        "device_change_count_30d": 1,
        "velocity_last_1h": 3,
        "agent_distance_km": 5.5,
        "failed_pin_attempts_24h": 1,
        "is_cash_out": 1,
        "user_reference": "user_01999888777"
    }

    pred_res = client.post("/api/v1/predict-risk", json=payload, headers=AUTH_HEADERS)
    assert pred_res.status_code == 200

    # Fetch single audit record by transaction ID
    audit_res = client.get(f"/api/v1/audit/{test_txn_id}", headers=AUTH_HEADERS)
    assert audit_res.status_code == 200
    entry = audit_res.json()

    # Validate Phase 1 Required Schema Fields
    assert entry["transaction_id"] == test_txn_id
    assert entry["user_reference"] == "user_01999888777"
    assert entry["transaction_amount"] == 12500.0
    assert entry["transaction_type"] == "AGENT_CASH_OUT"
    assert "input_risk_features" in entry
    assert "risk_score" in entry
    assert "risk_level" in entry
    assert entry["model_version"] == "RiskIntel-LGBM-v2.0"
    assert entry["final_policy_decision"] in ("ALLOW", "STEP_UP_REQUIRED", "BLOCK")
    assert "shap_explanation" in entry
    assert isinstance(entry["shap_explanation"], list)
    assert len(entry["shap_explanation"]) > 0
    assert "processing_latency_ms" in entry
    assert "authentication_context" in entry
    assert "created_at" in entry


def test_audit_list_query_and_pagination():
    """GET /api/v1/audit returns list of stored entries with filtering."""
    res = client.get("/api/v1/audit?limit=10", headers=AUTH_HEADERS)
    assert res.status_code == 200
    items = res.json()
    assert isinstance(items, list)
    assert len(items) >= 1


def test_audit_not_found():
    """Requesting non-existent transaction ID returns 404."""
    res = client.get("/api/v1/audit/UPNONEXISTENT_99999", headers=AUTH_HEADERS)
    assert res.status_code == 404


def test_audit_unauthorized():
    """Unauthenticated requests to audit ledger must be rejected with 401."""
    res = client.get("/api/v1/audit")
    assert res.status_code == 401

