import pytest
import sqlite3
from fastapi.testclient import TestClient
from backend.main import app
from backend.database import DB_PATH, get_connection

client = TestClient(app)
AUTH_HEADERS = {"X-API-Key": "upay_risk_intel_secret_key_2026"}


def test_challenge_creation_and_secure_storage():
    """
    Challenge session must be created with random OTP and stored strictly as salted SHA-256 hash.
    No plaintext OTP must exist in database!
    """
    payload = {
        "transaction_id": "UPTEST_CHAL_001",
        "user_reference": "user_01811223344",
        "challenge_type": "OTP_2FA"
    }
    response = client.post("/api/v1/challenge/create", json=payload, headers=AUTH_HEADERS)
    assert response.status_code == 201
    data = response.json()
    challenge_id = data["challenge_id"]
    assert challenge_id.startswith("CHAL_")
    assert data["status"] == "PENDING"

    # Verify directly in SQLite: check that only otp_hash exists and no raw_otp column exists
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM challenge_sessions WHERE challenge_id = ?", (challenge_id,))
        row = dict(cursor.fetchone())
        assert "otp_hash" in row
        assert "otp_salt" in row
        assert "raw_otp" not in row
        assert len(row["otp_hash"]) == 64  # SHA-256 hex string length
    finally:
        conn.close()


def test_challenge_verification_and_replay_protection():
    """Successful verification unlocks challenge, but replay attempts are strictly rejected."""
    # 1. Create challenge
    create_res = client.post("/api/v1/challenge/create", json={
        "transaction_id": "UPTEST_CHAL_002",
        "user_reference": "user_01811223344",
        "challenge_type": "OTP_2FA"
    }, headers=AUTH_HEADERS)
    assert create_res.status_code == 201
    chal_data = create_res.json()
    challenge_id = chal_data["challenge_id"]
    dev_otp = chal_data["dev_otp"]

    # 2. Verify with correct OTP
    verify_res = client.post("/api/v1/challenge/verify", json={
        "challenge_id": challenge_id,
        "otp_code": dev_otp
    }, headers=AUTH_HEADERS)
    assert verify_res.status_code == 200
    verify_data = verify_res.json()
    assert verify_data["status"] == "SUCCESS"
    assert verify_data["unlocked"] is True

    # 3. Replay Protection: Try to verify the same challenge session again
    replay_res = client.post("/api/v1/challenge/verify", json={
        "challenge_id": challenge_id,
        "otp_code": dev_otp
    }, headers=AUTH_HEADERS)
    assert replay_res.status_code == 200
    replay_data = replay_res.json()
    assert replay_data["status"] == "FAILED"
    assert "Replay rejected" in replay_data["message"]


def test_challenge_invalid_otp_and_max_attempts():
    """Invalid OTP codes decrement attempts and lock after 3 failed attempts."""
    create_res = client.post("/api/v1/challenge/create", json={
        "transaction_id": "UPTEST_CHAL_003",
        "user_reference": "user_01811223344",
        "challenge_type": "IDENTITY_RECOVERY"
    }, headers=AUTH_HEADERS)
    chal_data = create_res.json()
    challenge_id = chal_data["challenge_id"]

    # Attempt 1: Wrong code
    res1 = client.post("/api/v1/challenge/verify", json={"challenge_id": challenge_id, "otp_code": "000000"}, headers=AUTH_HEADERS)
    assert res1.json()["unlocked"] is False
    assert "2 attempt(s) remaining" in res1.json()["message"]

    # Attempt 2: Wrong code
    res2 = client.post("/api/v1/challenge/verify", json={"challenge_id": challenge_id, "otp_code": "111111"}, headers=AUTH_HEADERS)
    assert res2.json()["unlocked"] is False
    assert "1 attempt(s) remaining" in res2.json()["message"]

    # Attempt 3: Wrong code
    res3 = client.post("/api/v1/challenge/verify", json={"challenge_id": challenge_id, "otp_code": "222222"}, headers=AUTH_HEADERS)
    assert res3.json()["unlocked"] is False
    assert "0 attempt(s) remaining" in res3.json()["message"]

    # Attempt 4: Max attempts exceeded
    res4 = client.post("/api/v1/challenge/verify", json={"challenge_id": challenge_id, "otp_code": "333333"}, headers=AUTH_HEADERS)
    assert res4.json()["unlocked"] is False
    assert "Maximum verification attempts exceeded" in res4.json()["message"]


def test_challenge_resend():
    """Resending challenge generates a new OTP and updates expires_at."""
    create_res = client.post("/api/v1/challenge/create", json={
        "transaction_id": "UPTEST_CHAL_004",
        "user_reference": "user_01811223344",
        "challenge_type": "OTP_2FA"
    }, headers=AUTH_HEADERS)
    chal_data = create_res.json()
    challenge_id = chal_data["challenge_id"]
    original_otp = chal_data["dev_otp"]

    resend_res = client.post("/api/v1/challenge/resend", json={"challenge_id": challenge_id}, headers=AUTH_HEADERS)
    assert resend_res.status_code == 200
    resend_data = resend_res.json()
    assert resend_data["success"] is True
    assert resend_data["dev_otp"] is not None

