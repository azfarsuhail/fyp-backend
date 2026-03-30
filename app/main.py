from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os

from app.api.v1 import auth, upload, diagnostic, recommendation, profile, video, mobile_sync, admin_analytics
from app.core.security_middleware import SecurityHeadersMiddleware, RateLimitLoginMiddleware

app = FastAPI(
    title="Medical Image Analysis API",
    description="Backend for Knee OA Detection and Management",
    version="1.0.0",
)

# ── Load environment variables ────────────────────────────────────────────────
from dotenv import load_dotenv
load_dotenv()

# ── CORS Configuration ────────────────────────────────────────────────────────
# Get allowed origins from environment variable
allowed_origins = os.getenv("ALLOWED_ORIGINS", "")
dev_origins = os.getenv("ALLOW_DEV_ORIGINS", "")

origins = []
if allowed_origins:
    origins.extend([origin.strip() for origin in allowed_origins.split(",")])

# Only add dev origins if DEBUG is enabled
if os.getenv("DEBUG", "false").lower() == "true" and dev_origins:
    origins.extend([origin.strip() for origin in dev_origins.split(",")])

# Add localhost for local development
if os.getenv("DEBUG", "false").lower() == "true":
    origins.extend(["http://localhost:3000", "http://localhost:8080", "http://127.0.0.1:3000"])

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins if origins else ["*"],  # Fallback to * only in dev
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
    max_age=3600,
)

# ── Security Middleware ───────────────────────────────────────────────────────
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RateLimitLoginMiddleware)

# ── Include Routers ───────────────────────────────────────────────────────────
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(upload.router, prefix="/api/v1/upload", tags=["Image Upload"])
app.include_router(diagnostic.router, prefix="/api/v1/diagnostic", tags=["Diagnostic"])
app.include_router(recommendation.router, prefix="/api/v1/recommendation", tags=["Recommendation"])
app.include_router(profile.router, prefix="/api/v1/profile", tags=["Profile"])
app.include_router(video.router, prefix="/api/v1/videos", tags=["Video Library"])
app.include_router(mobile_sync.router, prefix="/api/v1/mobile", tags=["Mobile Sync"])
app.include_router(admin_analytics.router, prefix="/api/v1/admin", tags=["Admin Analytics"])


@app.get("/")
def root():
    return {"message": "Welcome to the Medical Image Analysis API"}


@app.get("/health")
def health_check():
    return {"status": "healthy", "version": "1.0.0"}
