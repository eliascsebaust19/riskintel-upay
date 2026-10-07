import os
import json
import sqlite3
import hashlib
import secrets
import logging
import uuid
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional, Tuple

logger = logging.getLogger("riskintel.database")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", "data"))
DB_PATH = os.path.join(DATA_DIR, "audit_ledger.db")


def hash_otp(otp: str, salt: str) -> str:
    """Computes a salted SHA-256 hash of the OTP for secure persistent storage."""
    return hashlib.sha256((salt + otp.strip()).encode("utf-8")).hexdigest()


def get_connection() -> sqlite3.Connection:
    """Thread-safe SQLite connection factory."""
    os.makedirs(DATA_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=15.0)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """
    Initializes durable tables with full schema, constraints, and indexes.
    Implements Phase 1 Requirements 3 (Audit Ledger) & 4 (Challenge Sessions).
    """
    conn = get_connection()
    try:
        with conn:
            cursor = conn.cursor()

            # Automatic Schema Migration Check for legacy prototype tables
            cursor.execute("PRAGMA table_info(audit_logs)")
            existing_audit_cols = [row[1] for row in cursor.fetchall()]
            if existing_audit_cols and "transaction_id" not in existing_audit_cols:
                logger.info("Migrating legacy audit_logs schema to Phase 1 compliant schema...")
                cursor.execute("DROP TABLE IF EXISTS audit_logs")

            cursor.execute("PRAGMA table_info(challenge_sessions)")
            existing_chal_cols = [row[1] for row in cursor.fetchall()]
            if existing_chal_cols and "otp_hash" not in existing_chal_cols:
                logger.info("Migrating legacy challenge_sessions schema to secure salted hash schema...")
                cursor.execute("DROP TABLE IF EXISTS challenge_sessions")

            # 1. Audit Trail / Ledger Table (Phase 1 Requirement 3)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS audit_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    transaction_id TEXT NOT NULL UNIQUE,
                    timestamp TEXT NOT NULL,
                    user_reference TEXT NOT NULL,
                    transaction_amount REAL NOT NULL,
                    transaction_type TEXT NOT NULL,
                    input_risk_features TEXT NOT NULL,
                    risk_score REAL NOT NULL,
                    risk_level TEXT NOT NULL,
                    model_version TEXT NOT NULL DEFAULT 'RiskIntel-LGBM-v2.0',
                    final_policy_decision TEXT NOT NULL,
                    shap_explanation TEXT NOT NULL,
                    explanation_language TEXT NOT NULL DEFAULT 'bn',
                    processing_latency_ms REAL NOT NULL,
                    authentication_context TEXT NOT NULL,
                    action_taken TEXT NOT NULL DEFAULT 'SCORED',
                    narrative TEXT,
                    created_at TEXT NOT NULL
                )
            """)

            cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_transaction_id ON audit_logs(transaction_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_logs(timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_user_reference ON audit_logs(user_reference)")

            # 2. Challenge Sessions Table (Phase 1 Requirement 4)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS challenge_sessions (
                    challenge_id TEXT PRIMARY KEY,
                    transaction_id TEXT NOT NULL,
                    user_reference TEXT NOT NULL,
                    challenge_type TEXT NOT NULL,
                    otp_salt TEXT NOT NULL,
                    otp_hash TEXT NOT NULL,
                    attempts INTEGER NOT NULL DEFAULT 0,
                    max_attempts INTEGER NOT NULL DEFAULT 3,
                    resend_count INTEGER NOT NULL DEFAULT 0,
                    max_resends INTEGER NOT NULL DEFAULT 3,
                    status TEXT NOT NULL DEFAULT 'PENDING',
                    created_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL
                )
            """)

            cursor.execute("CREATE INDEX IF NOT EXISTS idx_challenge_transaction_id ON challenge_sessions(transaction_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_challenge_status ON challenge_sessions(status)")

        logger.info("Durable database schema & indexes verified at %s", DB_PATH)
    finally:
        conn.close()


def log_audit_trail(
    transaction_id: str,
    user_reference: str,
    transaction_amount: float,
    transaction_type: str,
    input_risk_features: Dict[str, Any],
    risk_score: float,
    risk_level: str,
    final_policy_decision: str,
    shap_explanation: List[Any],
    processing_latency_ms: float,
    authentication_context: Dict[str, Any],
    narrative: Optional[str] = None,
    action_taken: str = "SCORED",
    explanation_language: str = "bn",
    model_version: str = "RiskIntel-LGBM-v2.0"
) -> int:
    """
    Persists a complete, non-repudiable transaction risk audit record.
    """
    now_iso = datetime.now(timezone.utc).isoformat()
    shap_json = json.dumps(
        [d.model_dump() if hasattr(d, "model_dump") else (d.dict() if hasattr(d, "dict") else d) for d in shap_explanation]
    )
    features_json = json.dumps(input_risk_features)
    auth_json = json.dumps(authentication_context)

    conn = get_connection()
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO audit_logs (
                    transaction_id, timestamp, user_reference, transaction_amount,
                    transaction_type, input_risk_features, risk_score, risk_level,
                    model_version, final_policy_decision, shap_explanation,
                    explanation_language, processing_latency_ms, authentication_context,
                    action_taken, narrative, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                transaction_id, now_iso, user_reference, float(transaction_amount),
                transaction_type, features_json, float(risk_score), risk_level,
                model_version, final_policy_decision, shap_json,
                explanation_language, float(processing_latency_ms), auth_json,
                action_taken, narrative, now_iso
            ))
            return cursor.lastrowid or 0
    finally:
        conn.close()


def get_audit_trail(
    limit: int = 50,
    offset: int = 0,
    decision: Optional[str] = None,
    risk_level: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Retrieves paginated audit logs with optional filtering."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        query = "SELECT * FROM audit_logs"
        params: List[Any] = []
        conditions: List[str] = []

        if decision:
            conditions.append("final_policy_decision = ?")
            params.append(decision.upper())
        if risk_level:
            conditions.append("risk_level = ?")
            params.append(risk_level.upper())

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY id DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        cursor.execute(query, tuple(params))
        rows = cursor.fetchall()

        results = []
        for row in rows:
            entry = dict(row)
            try:
                entry["shap_explanation"] = json.loads(entry["shap_explanation"])
            except Exception:
                entry["shap_explanation"] = []
            try:
                entry["input_risk_features"] = json.loads(entry["input_risk_features"])
            except Exception:
                entry["input_risk_features"] = {}
            try:
                entry["authentication_context"] = json.loads(entry["authentication_context"])
            except Exception:
                entry["authentication_context"] = {}
            results.append(entry)
        return results
    finally:
        conn.close()


def get_audit_by_transaction_id(transaction_id: str) -> Optional[Dict[str, Any]]:
    """Fetches a single audit ledger entry by transaction_id."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM audit_logs WHERE transaction_id = ?", (transaction_id,))
        row = cursor.fetchone()
        if not row:
            return None
        entry = dict(row)
        try:
            entry["shap_explanation"] = json.loads(entry["shap_explanation"])
        except Exception:
            entry["shap_explanation"] = []
        try:
            entry["input_risk_features"] = json.loads(entry["input_risk_features"])
        except Exception:
            entry["input_risk_features"] = {}
        try:
            entry["authentication_context"] = json.loads(entry["authentication_context"])
        except Exception:
            entry["authentication_context"] = {}
        return entry
    finally:
        conn.close()


def get_audit_stats() -> Dict[str, Any]:
    """Computes aggregated compliance and transaction stats from the persistent audit ledger."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                COUNT(*) as total_transactions,
                SUM(CASE WHEN final_policy_decision = 'ALLOW' THEN 1 ELSE 0 END) as allowed_count,
                SUM(CASE WHEN final_policy_decision = 'STEP_UP_2FA' THEN 1 ELSE 0 END) as step_up_count,
                SUM(CASE WHEN final_policy_decision = 'BLOCK' THEN 1 ELSE 0 END) as blocked_count,
                AVG(risk_score) as avg_risk_score,
                AVG(processing_latency_ms) as avg_latency_ms,
                SUM(transaction_amount) as total_volume_bdt
            FROM audit_logs
        """)
        row = cursor.fetchone()
        if not row or row["total_transactions"] == 0:
            return {
                "total_transactions": 0,
                "allowed_count": 0,
                "step_up_count": 0,
                "blocked_count": 0,
                "avg_risk_score": 0.0,
                "avg_latency_ms": 0.0,
                "total_volume_bdt": 0.0,
            }
        return {
            "total_transactions": int(row["total_transactions"] or 0),
            "allowed_count": int(row["allowed_count"] or 0),
            "step_up_count": int(row["step_up_count"] or 0),
            "blocked_count": int(row["blocked_count"] or 0),
            "avg_risk_score": round(float(row["avg_risk_score"] or 0.0), 4),
            "avg_latency_ms": round(float(row["avg_latency_ms"] or 0.0), 2),
            "total_volume_bdt": round(float(row["total_volume_bdt"] or 0.0), 2),
        }
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Server-Side Challenge Session System (Phase 1 Requirement 4)
# ---------------------------------------------------------------------------
def create_challenge_session(
    transaction_id: str,
    user_reference: str,
    challenge_type: str = "OTP_2FA",
    expiry_seconds: int = 300
) -> Dict[str, Any]:
    """
    Generates a secure random 6-digit OTP and stores only its salted SHA-256 hash.
    Returns challenge_id and raw OTP (for transmission/dev delivery only).
    """
    challenge_id = f"CHAL_{uuid.uuid4().hex[:12].upper()}"
    raw_otp = f"{secrets.randbelow(900000) + 100000}"  # Secure 6-digit random code
    salt = secrets.token_hex(16)
    hashed_otp = hash_otp(raw_otp, salt)

    now = datetime.now(timezone.utc)
    expires_at = (now + timedelta(seconds=expiry_seconds)).isoformat()
    now_iso = now.isoformat()

    conn = get_connection()
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO challenge_sessions (
                    challenge_id, transaction_id, user_reference, challenge_type,
                    otp_salt, otp_hash, attempts, max_attempts, resend_count,
                    max_resends, status, created_at, expires_at
                ) VALUES (?, ?, ?, ?, ?, ?, 0, 3, 0, 3, 'PENDING', ?, ?)
            """, (challenge_id, transaction_id, user_reference, challenge_type, salt, hashed_otp, now_iso, expires_at))
        return {
            "challenge_id": challenge_id,
            "raw_otp": raw_otp,
            "expires_at": expires_at,
            "challenge_type": challenge_type,
        }
    finally:
        conn.close()


def verify_challenge_session(
    challenge_id: str,
    submitted_otp: str
) -> Tuple[bool, str, Optional[str]]:
    """
    Validates submitted OTP against the stored salted hash.
    Enforces replay protection, maximum attempts, and expiration.
    Updates audit ledger on successful unlock.
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM challenge_sessions WHERE challenge_id = ?", (challenge_id,))
        session = cursor.fetchone()

        if not session:
            return False, "Challenge session not found or invalid ID.", None

        # Replay Protection
        if session["status"] == "VERIFIED":
            return False, "Challenge session has already been verified and consumed. Replay rejected.", session["transaction_id"]

        if session["status"] in ("FAILED", "EXPIRED"):
            return False, f"Challenge session is {session['status'].lower()}. Please initiate a new transaction.", session["transaction_id"]

        # Check Expiration
        now = datetime.now(timezone.utc)
        expires_at = datetime.fromisoformat(session["expires_at"])
        if now > expires_at:
            with conn:
                conn.cursor().execute("UPDATE challenge_sessions SET status = 'EXPIRED' WHERE challenge_id = ?", (challenge_id,))
            return False, "Challenge OTP has expired. Please request a new code.", session["transaction_id"]

        # Check Attempts
        current_attempts = session["attempts"] + 1
        if current_attempts > session["max_attempts"]:
            with conn:
                conn.cursor().execute(
                    "UPDATE challenge_sessions SET attempts = ?, status = 'FAILED' WHERE challenge_id = ?",
                    (current_attempts, challenge_id)
                )
            return False, "Maximum verification attempts exceeded. Transaction locked.", session["transaction_id"]

        # Constant-time verification
        computed_hash = hash_otp(submitted_otp, session["otp_salt"])
        is_match = secrets.compare_digest(computed_hash, session["otp_hash"])

        if is_match:
            with conn:
                c = conn.cursor()
                c.execute(
                    "UPDATE challenge_sessions SET attempts = ?, status = 'VERIFIED' WHERE challenge_id = ?",
                    (current_attempts, challenge_id)
                )
                # Update durable audit trail record
                c.execute("""
                    UPDATE audit_logs
                    SET action_taken = 'RECOVERED_BY_USER'
                    WHERE transaction_id = ?
                """, (session["transaction_id"],))
            return True, "Identity verified successfully. Transaction approved and account unblocked.", session["transaction_id"]
        else:
            with conn:
                conn.cursor().execute(
                    "UPDATE challenge_sessions SET attempts = ? WHERE challenge_id = ?",
                    (current_attempts, challenge_id)
                )
            remaining = session["max_attempts"] - current_attempts
            return False, f"Incorrect OTP code. {remaining} attempt(s) remaining.", session["transaction_id"]
    finally:
        conn.close()


def resend_challenge_session(challenge_id: str, expiry_seconds: int = 300) -> Tuple[bool, Optional[str], str, Optional[str]]:
    """
    Regenerates a new random OTP and salted hash for an active session with resend limit enforcement.
    Returns (success, raw_otp, message, expires_at).
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM challenge_sessions WHERE challenge_id = ?", (challenge_id,))
        session = cursor.fetchone()

        if not session:
            return False, None, "Challenge session not found.", None

        if session["status"] != "PENDING":
            return False, None, f"Cannot resend OTP for session in status '{session['status']}'.", None

        resend_count = session["resend_count"] + 1
        if resend_count > session["max_resends"]:
            return False, None, "Maximum resend limit reached for this session.", None

        new_otp = f"{secrets.randbelow(900000) + 100000}"
        salt = secrets.token_hex(16)
        hashed_otp = hash_otp(new_otp, salt)

        now = datetime.now(timezone.utc)
        expires_at = (now + timedelta(seconds=expiry_seconds)).isoformat()

        with conn:
            conn.cursor().execute("""
                UPDATE challenge_sessions
                SET otp_salt = ?, otp_hash = ?, resend_count = ?, attempts = 0, expires_at = ?
                WHERE challenge_id = ?
            """, (salt, hashed_otp, resend_count, expires_at, challenge_id))

        return True, new_otp, "New OTP generated successfully.", expires_at
    finally:
        conn.close()
