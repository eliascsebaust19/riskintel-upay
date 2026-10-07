from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class TransactionPayload(BaseModel):
    txn_amount: float = Field(..., description="Transaction amount in BDT", ge=0.0, examples=[18500.0])
    hour_of_day: int = Field(..., description="Hour of day (0-23)", ge=0, le=23, examples=[2])
    device_change_count_30d: int = Field(..., description="Device switches past 30 days", ge=0, examples=[1])
    velocity_last_1h: int = Field(..., description="Transaction velocity past 1 hour", ge=0, examples=[4])
    agent_distance_km: float = Field(..., description="Endpoint distance in km", ge=0.0, examples=[8.5])
    failed_pin_attempts_24h: int = Field(..., description="Failed PIN count past 24h", ge=0, examples=[1])
    is_cash_out: int = Field(..., description="Channel (1 for Agent Cash-Out, 0 for P2P Send Money)", ge=0, le=1, examples=[1])
    transaction_id: Optional[str] = Field(None, description="Client transaction tracking ID", examples=["UP9472A802"])
    txn_id: Optional[str] = Field(None, description="Backwards-compatible alias for transaction_id")
    user_reference: Optional[str] = Field("user_01812345678", description="Non-sensitive customer identifier")
    user_id: Optional[str] = Field(None, description="Backwards-compatible alias for user_reference")
    explanation_language: Optional[str] = Field("bn", description="Explanation language ('bn' or 'en')")


class SHAPDriver(BaseModel):
    feature: str = Field(..., description="Feature name")
    impact: float = Field(..., description="Local SHAP attribution score")


class RiskAssessmentResponse(BaseModel):
    transaction_id: str = Field(..., description="Unique transaction ID recorded in audit ledger")
    txn_id: Optional[str] = Field(None, description="Backwards-compatible alias for transaction_id")
    risk_score: float = Field(..., description="Calibrated risk index (0.0 to 100.0)")
    risk_level: str = Field(..., description="Risk category: LOW, MEDIUM, or HIGH")
    recommended_action: str = Field(..., description="Policy action: ALLOW, STEP_UP_REQUIRED, or BLOCK")
    key_risk_drivers: List[SHAPDriver] = Field(..., description="Top features by absolute SHAP impact")
    narrative: str = Field(..., description="Compliance narrative briefing")
    model_version: str = Field("RiskIntel-LGBM-v2.0", description="Serving model version identifier")
    inference_time_ms: float = Field(..., description="Server inference latency in ms")
    correlation_id: Optional[str] = Field(None, description="Request correlation tracing ID")
    challenge_id: Optional[str] = Field(None, description="Challenge session ID if step-up/recovery required")
    dev_otp: Optional[str] = Field(None, description="Dev OTP (populated strictly when DEV_MODE=true for local evaluation)")
    mock_otp: Optional[str] = Field(None, description="Backwards-compatible alias for dev_otp")


class ChallengeCreateRequest(BaseModel):
    transaction_id: str = Field(..., description="Transaction tracking ID requiring step-up")
    user_reference: Optional[str] = Field("user_01812345678", description="Customer identifier")
    challenge_type: Optional[str] = Field("OTP_2FA", description="Type: OTP_2FA, IDENTITY_RECOVERY, or BIOMETRIC")


class ChallengeCreateResponse(BaseModel):
    challenge_id: str
    transaction_id: str
    challenge_type: str
    status: str
    expires_at: str
    dev_otp: Optional[str] = None


class ChallengeVerifyRequest(BaseModel):
    challenge_id: str = Field(..., description="Challenge session identifier")
    otp_code: str = Field(..., description="6-digit OTP code submitted by user")


class ChallengeVerifyResponse(BaseModel):
    status: str = Field(..., description="Result status: SUCCESS or FAILED")
    unlocked: bool = Field(..., description="Whether transaction/account is unblocked")
    message: str = Field(..., description="Human-readable result explanation")
    transaction_id: Optional[str] = Field(None, description="Associated transaction ID")
    txn_id: Optional[str] = Field(None, description="Backwards-compatible alias")


class ChallengeResendRequest(BaseModel):
    challenge_id: str = Field(..., description="Challenge session identifier to resend")


class ChallengeResendResponse(BaseModel):
    success: bool
    challenge_id: str
    message: str
    expires_at: Optional[str] = None
    dev_otp: Optional[str] = None


class AuditLogEntry(BaseModel):
    id: int
    transaction_id: str
    timestamp: str
    user_reference: str
    transaction_amount: float
    transaction_type: str
    input_risk_features: Dict[str, Any]
    risk_score: float
    risk_level: str
    model_version: str
    final_policy_decision: str
    shap_explanation: List[Dict[str, Any]]
    explanation_language: str
    processing_latency_ms: float
    authentication_context: Dict[str, Any]
    action_taken: str
    narrative: Optional[str] = None
    created_at: str


class AuditListResponse(BaseModel):
    total: int
    limit: int
    offset: int
    items: List[AuditLogEntry]
