import time
import pytest
from fastapi import HTTPException
from backend.rate_limiter import InMemoryRateLimiter


def test_rate_limiter_normal_and_limit_reached():
    """Tests normal request tracking and limit threshold."""
    limiter = InMemoryRateLimiter(max_requests=5, window_ms=2000)
    test_ip = "192.168.1.100"

    # 1. First 5 requests should pass without error
    for i in range(5):
        limiter.check_rate_limit(test_ip)

    # 2. 6th request must exceed limit and raise HTTP 429
    with pytest.raises(HTTPException) as exc_info:
        limiter.check_rate_limit(test_ip)

    assert exc_info.value.status_code == 429
    assert "Rate limit exceeded" in exc_info.value.detail
    assert "Retry-After" in exc_info.value.headers


def test_rate_limiter_excess_requests():
    """Repeated excess calls while rate-limited continue to return 429."""
    limiter = InMemoryRateLimiter(max_requests=3, window_ms=3000)
    test_ip = "10.0.0.55"

    for _ in range(3):
        limiter.check_rate_limit(test_ip)

    # Subsequent multiple excess calls all get 429
    for _ in range(3):
        with pytest.raises(HTTPException) as exc_info:
            limiter.check_rate_limit(test_ip)
        assert exc_info.value.status_code == 429


def test_rate_limiter_reset():
    """Manual reset or window expiration resets rate limit counters."""
    limiter = InMemoryRateLimiter(max_requests=2, window_ms=1000)
    test_ip = "172.16.0.12"

    limiter.check_rate_limit(test_ip)
    limiter.check_rate_limit(test_ip)

    # Limit reached
    with pytest.raises(HTTPException):
        limiter.check_rate_limit(test_ip)

    # Reset specific IP
    limiter.reset(test_ip)

    # Should now pass again
    limiter.check_rate_limit(test_ip)

