import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

SAMPLE_PAYLOAD = {
    "txn_amount": 500.0,
    "hour_of_day": 14,
    "device_change_count_30d": 0,
    "velocity_last_1h": 1,
    "agent_distance_km": 1.2,
    "failed_pin_attempts_24h": 0,
    "is_cash_out": 0
}


def test_auth_missing_credentials():
    """Unauthenticated requests must be rejected with 401 Unauthorized."""
    response = client.post("/api/v1/predict-risk", json=SAMPLE_PAYLOAD)
    assert response.status_code == 401
    assert "Unauthorized" in response.json()["detail"]


def test_auth_invalid_bearer_token():
    """Invalid Bearer tokens must be rejected with 401."""
    headers = {"Authorization": "Bearer completely_fake_invalid_token"}
    response = client.post("/api/v1/predict-risk", json=SAMPLE_PAYLOAD, headers=headers)
    assert response.status_code == 401


def test_auth_invalid_api_key():
    """Invalid X-API-Key must be rejected with 401."""
    headers = {"X-API-Key": "wrong_key_12345"}
    response = client.post("/api/v1/predict-risk", json=SAMPLE_PAYLOAD, headers=headers)
    assert response.status_code == 401


def test_auth_valid_bearer_token():
    """Valid Bearer token must succeed with 200 OK and valid assessment payload."""
    headers = {"Authorization": "Bearer upay_risk_intel_bearer_token_2026"}
    response = client.post("/api/v1/predict-risk", json=SAMPLE_PAYLOAD, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "risk_score" in data
    assert "recommended_action" in data
    assert data["recommended_action"] == "ALLOW"


def test_auth_valid_api_key():
    """Valid X-API-Key must succeed with 200 OK."""
    headers = {"X-API-Key": "upay_risk_intel_secret_key_2026"}
    response = client.post("/api/v1/predict-risk", json=SAMPLE_PAYLOAD, headers=headers)
    assert response.status_code == 200


def test_correlation_id_generated_and_propagated():
    """Every response must contain an X-Correlation-ID header, preserving client correlation IDs."""
    # 1. Server generates correlation ID
    headers = {"X-API-Key": "upay_risk_intel_secret_key_2026"}
    res1 = client.post("/api/v1/predict-risk", json=SAMPLE_PAYLOAD, headers=headers)
    assert "X-Correlation-ID" in res1.headers
    assert res1.headers["X-Correlation-ID"].startswith("CORR_")

    # 2. Client-supplied correlation ID is preserved
    custom_corr_id = "CUSTOM_CORR_TEST_9999"
    headers["X-Correlation-ID"] = custom_corr_id
    res2 = client.post("/api/v1/predict-risk", json=SAMPLE_PAYLOAD, headers=headers)
    assert res2.headers["X-Correlation-ID"] == custom_corr_id

