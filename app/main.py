from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
import os
from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(app: FastAPI):
    # This runs when the server starts
    print("Initializing server and loading heavy models...")
    # Add any explicit model warming here if needed
    yield
    # This runs when the server shuts down
    print("Shutting down server and cleaning up resources...")

app = FastAPI(
    title="Medical Image Analysis API",
    description="Backend for Knee OA Detection and Management",
    version="1.0.0",
    lifespan=lifespan
)

# ── Load environment variables ────────────────────────────────────────────────
from dotenv import load_dotenv
load_dotenv()
from app.api.v1 import auth, upload, diagnostic, recommendation, profile, video, mobile_sync, admin_analytics
from app.core.security_middleware import SecurityHeadersMiddleware, RateLimitLoginMiddleware
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


# ── Android App Links Verification ────────────────────────────────────────────
# This endpoint is required for Android App Links to work with password reset deep linking
@app.get("/.well-known/assetlinks.json")
def android_assetlinks():
    """
    Serve Android App Links verification file.
    
    This allows the Android app to receive deep links for password reset URLs.
    The app can then handle URLs like: https://kneeoa.online/reset-password?token={token}
    """
    assetlinks_data = [
        {
            "relation": ["delegate_permission/common.handle_all_urls"],
            "target": {
                "namespace": "android_app",
                "package_name": "com.azfarsuhail.kneeoaapp",
                "sha256_cert_fingerprints": [
                    "93:1A:94:70:8D:C3:EB:8B:67:64:E9:64:54:34:28:1E:7D:66:7A:60:27:8E:1E:D4:1E:0E:5E:FA:1C:79:AE:A5"
                ]
            }
        }
    ]
    
    return Response(
        content=str(assetlinks_data).replace("'", '"'),
        media_type="application/json"
    )
