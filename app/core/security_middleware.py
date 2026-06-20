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
    """Simple in-memory rate limiter for auth endpoints."""
    
    def __init__(self):
        # Config: endpoint -> (max_attempts, window_minutes)
        self.config = {
            "/api/v1/auth/login": (5, 1),
            "/api/v1/auth/register": (5, 60),
            "/api/v1/auth/forgot-password": (3, 60),
            "/api/v1/auth/request-otp": (3, 60),  # 3 OTP requests per hour per IP
        }
        self.attempts: dict[str, list[datetime]] = defaultdict(list)
    
    def _clean_old_attempts(self, identifier: str, endpoint: str, now: datetime):
        """Helper to remove timestamps older than the window."""
        key = f"{endpoint}:{identifier}"
        max_attempts, window_minutes = self.config.get(endpoint, (float("inf"), 1))
        window = timedelta(minutes=window_minutes)
        self.attempts[key] = [ts for ts in self.attempts[key] if now - ts < window]

    def is_allowed(self, identifier: str, endpoint: str) -> bool:
        """Check if identifier is allowed to make request to endpoint."""
        if endpoint not in self.config:
            return True
        
        now = datetime.now(timezone.utc)
        max_attempts, _ = self.config[endpoint]
        self._clean_old_attempts(identifier, endpoint, now)
        
        key = f"{endpoint}:{identifier}"
        if len(self.attempts[key]) >= max_attempts:
            return False
        
        self.attempts[key].append(now)
        return True
    
    def get_remaining(self, identifier: str, endpoint: str) -> int:
        """Get remaining attempts for identifier on endpoint."""
        if endpoint not in self.config:
            return float("inf")
        
        now = datetime.now(timezone.utc)
        max_attempts, window_minutes = self.config[endpoint]
        window = timedelta(minutes=window_minutes)
        
        key = f"{endpoint}:{identifier}"
        self.attempts[key] = [ts for ts in self.attempts[key] if now - ts < window]
        return max(0, max_attempts - len(self.attempts[key]))


# Global rate limiter instance
auth_rate_limiter = RateLimiter()


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


class RateLimitAuthMiddleware(BaseHTTPMiddleware):
    """Rate limit auth endpoints (login, register, forgot-password, request-otp)."""
    
    async def dispatch(self, request: Request, call_next):
        # Only apply to POST auth endpoints
        if request.url.path in ["/api/v1/auth/login", "/api/v1/auth/register", "/api/v1/auth/forgot-password", "/api/v1/auth/request-otp"] and request.method == "POST":
            
            # Attempt to get the real IP from NGINX headers first
            forwarded_for = request.headers.get("X-Forwarded-For")
            if forwarded_for:
                # X-Forwarded-For can be a comma-separated list; the first is the real client
                identifier = forwarded_for.split(",")[0].strip()
            else:
                # Fallback if accessed directly
                identifier = request.client.host if request.client else "unknown"
            
            if not auth_rate_limiter.is_allowed(identifier, request.url.path):
                remaining = auth_rate_limiter.get_remaining(identifier, request.url.path)
                max_attempts, window_minutes = auth_rate_limiter.config.get(request.url.path, (5, 1))
                retry_after = window_minutes * 60  # seconds
                
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={
                        "detail": f"Too many requests. Please try again in {window_minutes} minutes.",
                        "retry_after": retry_after
                    },
                    headers={"Retry-After": str(retry_after)}
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