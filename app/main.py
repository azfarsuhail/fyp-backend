from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import auth, upload, diagnostic, recommendation, profile, video

app = FastAPI(
    title="Medical Image Analysis API",
    description="Backend for Knee OA Detection and Management",
    version="1.0.0",
)

# ── CORS Middleware (allow mobile app to connect) ─────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Include Routers ───────────────────────────────────────────────────────────
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(upload.router, prefix="/api/v1/upload", tags=["Image Upload"])
app.include_router(diagnostic.router, prefix="/api/v1/diagnostic", tags=["Diagnostic"])
app.include_router(recommendation.router, prefix="/api/v1/recommendation", tags=["Recommendation"])
app.include_router(profile.router, prefix="/api/v1/profile", tags=["Profile"])
app.include_router(video.router, prefix="/api/v1/videos", tags=["Video Library"])


@app.get("/")
def root():
    return {"message": "Welcome to the Medical Image Analysis API"}


@app.get("/health")
def health_check():
    return {"status": "healthy", "version": "1.0.0"}