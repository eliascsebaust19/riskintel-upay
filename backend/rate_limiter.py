import os
import time
import logging
from typing import Dict, List, Optional
from threading import Lock
from fastapi import Request, HTTPException, status

logger = logging.getLogger("riskintel.rate_limiter")

# Configurable environment variables (Phase 1 Requirement)
DEFAULT_WINDOW_MS = int(os.getenv("RATE_LIMIT_WINDOW_MS", "60000"))  # 60,000 ms = 1 minute
DEFAULT_MAX_REQUESTS = int(os.getenv("RATE_LIMIT_MAX_REQUESTS", "60"))


class InMemoryRateLimiter:
    """
    Thread-safe in-memory sliding-window rate limiter per client IP.
    Designed with an abstraction layer so it can be swapped for Redis in distributed production.
    """
    def __init__(self, max_requests: int = DEFAULT_MAX_REQUESTS, window_ms: int = DEFAULT_WINDOW_MS):
        self.max_requests = max_requests
        self.window_seconds = window_ms / 1000.0
        self.lock = Lock()
        self.ip_records: Dict[str, List[float]] = {}

    def get_client_ip(self, request: Request) -> str:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
        if request.client and request.client.host:
            return request.client.host
        return "127.0.0.1"

    def check_rate_limit(self, client_ip: str) -> None:
        current_time = time.time()
        window_start = current_time - self.window_seconds

        with self.lock:
            timestamps = self.ip_records.get(client_ip, [])
            valid_timestamps = [t for t in timestamps if t > window_start]

            if len(valid_timestamps) >= self.max_requests:
                oldest_timestamp = valid_timestamps[0]
                retry_after = max(1, int(self.window_seconds - (current_time - oldest_timestamp)))
                logger.warning(
                    "Rate limit exceeded for IP %s (%d requests in %.1fs window)",
                    client_ip, len(valid_timestamps), self.window_seconds
                )
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Rate limit exceeded. Maximum {self.max_requests} requests per {int(self.window_seconds)}s allowed.",
                    headers={"Retry-After": str(retry_after)},
                )

            valid_timestamps.append(current_time)
            self.ip_records[client_ip] = valid_timestamps

    def reset(self, client_ip: Optional[str] = None) -> None:
        """Reset rate limiter state (useful for test isolation)."""
        with self.lock:
            if client_ip:
                self.ip_records.pop(client_ip, None)
            else:
                self.ip_records.clear()

    async def __call__(self, request: Request) -> None:
        client_ip = self.get_client_ip(request)
        self.check_rate_limit(client_ip)


# Global standard limiter instance
global_rate_limiter = InMemoryRateLimiter(max_requests=DEFAULT_MAX_REQUESTS, window_ms=DEFAULT_WINDOW_MS)

# Stricter limiter for sensitive OTP / challenge endpoints (e.g., 10 req/min)
strict_otp_rate_limiter = InMemoryRateLimiter(max_requests=15, window_ms=DEFAULT_WINDOW_MS)

