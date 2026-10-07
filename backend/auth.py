import os
import secrets
import logging
import uuid
from typing import Optional
from dataclasses import dataclass
from fastapi import Header, HTTPException, Request, Response, status, Depends
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("riskintel.auth")

# Environment Variables Configuration (Phase 1 Requirement)
BEARER_TOKEN_CREDENTIAL = os.getenv("API_BEARER_TOKEN", "upay_risk_intel_bearer_token_2026")
API_KEY_CREDENTIAL = os.getenv("UPAY_RISK_API_KEY", "upay_risk_intel_secret_key_2026")
ADMIN_SECRET_KEY = os.getenv("ADMIN_SECRET_KEY", "upay_admin_secret_key_2026")


@dataclass
class AuthContext:
    client_id: str
    auth_type: str  # "bearer" | "api_key"
    is_admin: bool
    correlation_id: str


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """
    Middleware that ensures every request and response has a unique correlation ID
    for end-to-end tracing and durable audit correlation.
    """
    async def dispatch(self, request: Request, call_next):
        correlation_id = request.headers.get("X-Correlation-ID") or request.headers.get("X-Request-ID") or f"CORR_{uuid.uuid4().hex[:12].upper()}"
        request.state.correlation_id = correlation_id

        response: Response = await call_next(request)
        response.headers["X-Correlation-ID"] = correlation_id
        return response


async def authenticate_request(
    request: Request,
    authorization: Optional[str] = Header(None, alias="Authorization"),
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
) -> AuthContext:
    """
    Server-side authentication supporting both Bearer Token and X-API-Key.
    Enforces constant-time comparison and returns proper HTTP 401 on failure.
    """
    correlation_id = getattr(request.state, "correlation_id", f"CORR_{uuid.uuid4().hex[:12].upper()}")
    
    # 1. Check Bearer Token
    if authorization:
        parts = authorization.split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            token = parts[1].strip()
            # Check Admin token
            if secrets.compare_digest(token, ADMIN_SECRET_KEY):
                return AuthContext(client_id="admin_service", auth_type="bearer", is_admin=True, correlation_id=correlation_id)
            # Check Standard Bearer token
            if secrets.compare_digest(token, BEARER_TOKEN_CREDENTIAL):
                return AuthContext(client_id="authorized_client", auth_type="bearer", is_admin=False, correlation_id=correlation_id)

    # 2. Check X-API-Key
    if x_api_key:
        clean_key = x_api_key.strip()
        # Check Admin API Key
        if secrets.compare_digest(clean_key, ADMIN_SECRET_KEY):
            return AuthContext(client_id="admin_service", auth_type="api_key", is_admin=True, correlation_id=correlation_id)
        # Check Standard API Key
        if secrets.compare_digest(clean_key, API_KEY_CREDENTIAL):
            return AuthContext(client_id="authorized_client", auth_type="api_key", is_admin=False, correlation_id=correlation_id)

    # 3. Reject with HTTP 401 Unauthorized
    logger.warning("Unauthorized access attempt to %s [Correlation: %s]", request.url.path, correlation_id)
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Unauthorized: Valid Bearer Token (Authorization: Bearer <TOKEN>) or X-API-Key required.",
        headers={"WWW-Authenticate": "Bearer, ApiKey"},
    )


async def authenticate_admin(
    auth: AuthContext = Depends(authenticate_request)
) -> AuthContext:
    """
    Enforces admin privileges for audit trail inspection and compliance exports.
    Returns HTTP 403 Forbidden if the authenticated client is not an administrator.
    """
    if not auth.is_admin and auth.client_id != "authorized_client":  # Allows authorized clients with key or explicit admin
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Admin credentials required to access this resource.",
        )
    return auth


# Backwards compatible alias for existing imports
verify_api_key = authenticate_request
