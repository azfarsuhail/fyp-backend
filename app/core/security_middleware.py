"""
Security Middleware
-------------------
Adds security headers and implements basic rate limiting.
"""

from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from functools import wraps
from collections import defaultdict
from datetime import datetime, timedelta, timezone
import time
from starlette.middleware.base import BaseHTTPMiddleware


class RateLimiter:
    """Simple in-memory rate limiter for login attempts."""
    
    def __init__(self, max_attempts: int = 5, window_minutes: int = 1):
        self.max_attempts = max_attempts
        self.window = timedelta(minutes=window_minutes)
        self.attempts: dict[str, list[datetime]] = defaultdict(list)
    
    def _clean_old_attempts(self, identifier: str, now: datetime):
        """Helper to remove timestamps older than the window."""
        self.attempts[identifier] = [
            ts for ts in self.attempts[identifier]
            if now - ts < self.window
        ]

    def is_allowed(self, identifier: str) -> bool:
        """Check if identifier is allowed to make request."""
        now = datetime.now(timezone.utc)
        self._clean_old_attempts(identifier, now)
        
        if len(self.attempts[identifier]) >= self.max_attempts:
            return False
        
        self.attempts[identifier].append(now)
        return True
    
    def get_remaining(self, identifier: str) -> int:
        """Get remaining attempts for identifier."""
        now = datetime.now(timezone.utc)
        self._clean_old_attempts(identifier, now)
        return max(0, self.max_attempts - len(self.attempts[identifier]))


# Global rate limiter instance
login_rate_limiter = RateLimiter(max_attempts=5, window_minutes=1)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses."""
    
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Prevent clickjacking
        response.headers["X-Frame-Options"] = "DENY"
        
        # Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"
        
        # XSS protection
        response.headers["X-XSS-Protection"] = "1; mode=block"
        
        # Referrer policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # Content Security Policy (Updated for FastAPI Docs)
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "img-src 'self' data: https://fastapi.tiangolo.com;"
        )
        
        # Remove server header
        if "server" in response.headers:
            del response.headers["server"]
        
        return response


class RateLimitLoginMiddleware(BaseHTTPMiddleware):
    """Rate limit login attempts."""
    
    async def dispatch(self, request: Request, call_next):
        # Only apply to login endpoint
        if request.url.path == "/api/v1/auth/login" and request.method == "POST":
            
            # Attempt to get the real IP from NGINX headers first
            forwarded_for = request.headers.get("X-Forwarded-For")
            if forwarded_for:
                # X-Forwarded-For can be a comma-separated list; the first is the real client
                identifier = forwarded_for.split(",")[0].strip()
            else:
                # Fallback if accessed directly
                identifier = request.client.host if request.client else "unknown"
            
            if not login_rate_limiter.is_allowed(identifier):
                remaining = login_rate_limiter.get_remaining(identifier)
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={
                        "detail": "Too many login attempts. Please try again later.",
                        "retry_after": 60  # seconds
                    },
                    headers={"Retry-After": "60"}
                )
        
        return await call_next(request)


def require_strong_password(password: str) -> list[str]:
    """
    Validate password strength.
    Returns list of validation errors (empty if valid).
    """
    errors = []
    
    # Minimum length
    if len(password) < 8:
        errors.append("Password must be at least 8 characters long")
    
    # Uppercase requirement
    if not any(c.isupper() for c in password):
        errors.append("Password must contain at least one uppercase letter")
    
    # Lowercase requirement
    if not any(c.islower() for c in password):
        errors.append("Password must contain at least one lowercase letter")
    
    # Number requirement
    if not any(c.isdigit() for c in password):
        errors.append("Password must contain at least one number")
    
    # Special character requirement
    if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
        errors.append("Password must contain at least one special character")
    
    return errors


def sanitize_error_message(error: str) -> str:
    """Sanitize error messages to prevent information leakage."""
    # Don't reveal if user exists
    if "user" in error.lower() or "account" in error.lower():
        return "Invalid credentials"
    
    # Don't reveal database details
    if "database" in error.lower() or "sql" in error.lower():
        return "Service temporarily unavailable"
    
    return error