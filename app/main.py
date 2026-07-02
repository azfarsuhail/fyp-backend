import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from dotenv import load_dotenv

# Load environment variables early
load_dotenv()

from app.api.v1 import auth, upload, diagnostic, recommendation, profile, video, mobile_sync, admin_analytics, medications
from app.core.security_middleware import SecurityHeadersMiddleware, RateLimitAuthMiddleware

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

# ── CORS Configuration Setup ──────────────────────────────────────────────────
# Get allowed origins from environment variable
allowed_origins = os.getenv("ALLOWED_ORIGINS", "")
dev_origins = os.getenv("ALLOW_DEV_ORIGINS", "")

origins = []
if allowed_origins:
    origins.extend([origin.strip() for origin in allowed_origins.split(",")])

# Only add dev origins if DEBUG is enabled
if os.getenv("DEBUG", "false").lower() == "true" and dev_origins:
    origins.extend([origin.strip() for origin in dev_origins.split(",")])

# Add localhost for local development (Including Expo port 8081)
if os.getenv("DEBUG", "false").lower() == "true":
    origins.extend([
        "http://localhost:3000", 
        "http://localhost:8080", 
        "http://localhost:8081", # <-- Expo Port
        "http://127.0.0.1:3000"
    ])

# ── Security Middleware (MUST BE ADDED FIRST) ─────────────────────────────────
# Because FastAPI executes middleware in reverse order, adding these first 
# means they run AFTER the CORSMiddleware.
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RateLimitAuthMiddleware)

# ── CORS Configuration (MUST BE ADDED LAST) ───────────────────────────────────
# Adding this last means it runs FIRST. It will catch the OPTIONS preflight 
# request and return a 200 OK before the security middlewares can block it.
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins if origins else ["*"],  # Fallback to * only in dev
    allow_credentials=True,
    allow_methods=["*"], # Catch everything, including OPTIONS
    allow_headers=["*"], # Allow all headers
    max_age=3600,
)

# ── Global Exception Handlers ─────────────────────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch all unexpected exceptions to prevent stack trace leakage."""
    print(f"Unhandled exception: {exc}") # Or use your logger here
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle FastAPI validation errors cleanly."""
    return JSONResponse(
        status_code=422,
        content={"detail": [{"loc": err["loc"], "msg": err["msg"]} for err in exc.errors()]},
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Pass through standard HTTP exceptions (401, 403, 404, etc.)."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )

# ── Include Routers ───────────────────────────────────────────────────────────
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(upload.router, prefix="/api/v1/upload", tags=["Image Upload"])
app.include_router(diagnostic.router, prefix="/api/v1/diagnostic", tags=["Diagnostic"])
app.include_router(recommendation.router, prefix="/api/v1/recommendation", tags=["Recommendation"])
app.include_router(profile.router, prefix="/api/v1/profile", tags=["Profile"])
app.include_router(video.router, prefix="/api/v1/videos", tags=["Video Library"])
app.include_router(mobile_sync.router, prefix="/api/v1/mobile", tags=["Mobile Sync"])
app.include_router(admin_analytics.router, prefix="/api/v1/admin", tags=["Admin Analytics"])
app.include_router(medications.router, prefix="/api/v1", tags=["Medication Management"])

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
    
    return JSONResponse(content=assetlinks_data)