# Security Fixes - Implementation Guide

## 🚨 CRITICAL FIXES (Implement Immediately)

### Fix 1: Update app/main.py

Replace the entire file with this secure version:

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os

from app.api.v1 import auth, upload, diagnostic, recommendation, profile, video
from app.core.security_middleware import security_headers_middleware, rate_limit_login_middleware

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
app.add_middleware(security_headers_middleware)
app.add_middleware(rate_limit_login_middleware)

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
```

### Fix 2: Update app/core/security.py

Replace the entire file with this secure version:

```python
from datetime import datetime, timedelta
from jose import jwt
from passlib.context import CryptContext
import os

# Configuration - Load from environment variables in production
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise ValueError(
        "CRITICAL: SECRET_KEY not set! "
        "Set a strong random key in .env file (min 32 characters). "
        "Generate with: python -c \"import secrets; print(secrets.token_urlsafe(32))\""
    )

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15"))

# Password Hashing Context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: timedelta = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt
```

### Fix 3: Update app/api/v1/auth.py

Add password validation to registration:

```python
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import datetime

from app.schemas.user_schema import UserCreate, UserOut, Token
from app.core.security import get_password_hash, verify_password, create_access_token
from app.core.dependencies import get_db
from app.models.user import User
from app.core.security_middleware import require_strong_password

router = APIRouter()

@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register_user(user: UserCreate, db: Session = Depends(get_db)):
    # Check if user exists in Neon DB
    db_user = db.query(User).filter(User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Validate password strength
    password_errors = require_strong_password(user.password)
    if password_errors:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"password_validation_errors": password_errors}
        )
    
    # Prevent admin registration - admins must be created manually
    if user.role == "admin":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Registration as admin is not allowed. Contact system administrator."
        )
    
    hashed_password = get_password_hash(user.password)
    
    # Create new user record
    new_user = User(
        email=user.email,
        full_name=user.full_name,
        password_hash=hashed_password,
        role=user.role
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return new_user

@router.post("/login", response_model=Token)
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    # Fetch user from Neon DB
    user = db.query(User).filter(User.email == form_data.username).first()
    
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Update last login timestamp
    user.last_login = datetime.utcnow()
    db.commit()
    
    # Generate Token
    access_token = create_access_token(
        data={"sub": user.email, "role": user.role}
    )
    return {"access_token": access_token, "token_type": "bearer"}
```

### Fix 4: Create .env file

Create a `.env` file in the root directory:

```bash
# ── Security ──────────────────────────────────────────────────────────────────
# Generate a strong secret key: python -c "import secrets; print(secrets.token_urlsafe(32))"
SECRET_KEY=your-32-character-random-secret-key-here

# Token expiry in minutes (recommend 15 for security)
ACCESS_TOKEN_EXPIRE_MINUTES=15

# ── Database (Neon PostgreSQL) ────────────────────────────────────────────────
DATABASE_URL=postgresql://your_user:your_password@your_host/knee_oa?sslmode=require

# ── AWS S3 ───────────────────────────────────────────────────────────────────
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key
AWS_REGION=eu-west-1
S3_BUCKET_NAME=knee-oa-uploads

# ── CORS (Production) ────────────────────────────────────────────────────────
ALLOWED_ORIGINS=https://your-app.com,https://admin.your-app.com

# ── Development Only ─────────────────────────────────────────────────────────
DEBUG=true
ALLOW_DEV_ORIGINS=http://localhost:3000,http://localhost:8080
```

### Fix 5: Change Default Admin Password

After creating the admin account, immediately change the password:

```bash
# Login with admin/admin
# Then call:
POST /api/v1/profile/me/change-password
{
  "current_password": "admin",
  "new_password": "YourStrongPassword123!@#"
}
```

## 📋 VERIFICATION CHECKLIST

After applying fixes, verify:

- [ ] `.env` file exists with all required variables
- [ ] `SECRET_KEY` is at least 32 characters
- [ ] Application starts without errors
- [ ] CORS is restricted to allowed origins
- [ ] Security headers are present in responses
- [ ] Rate limiting works (try 6 login attempts)
- [ ] Password validation rejects weak passwords
- [ ] Admin registration is blocked
- [ ] Default admin password has been changed

## 🚀 DEPLOYMENT CHECKLIST

Before deploying to production:

- [ ] Remove `DEBUG=true` from .env
- [ ] Set production `ALLOWED_ORIGINS`
- [ ] Change all default passwords
- [ ] Use production-grade SECRET_KEY
- [ ] Enable HTTPS on your server
- [ ] Configure S3 bucket encryption
- [ ] Set up firewall rules
- [ ] Enable logging and monitoring
- [ ] Run security scan: `pip install bandit && bandit -r app/`

## 🔧 TESTING THE FIXES

### Test CORS Restriction
```bash
# Should work (allowed origin)
curl -H "Origin: https://your-app.com" http://localhost:8000/health

# Should fail (not in allowed list)
curl -H "Origin: https://evil.com" http://localhost:8000/health
```

### Test Rate Limiting
```bash
# Make 6 login attempts
for i in {1..6}; do
  curl -X POST http://localhost:8000/api/v1/auth/login \
    -d "username=admin&password=admin"
done
# 6th request should return 429 Too Many Requests
```

### Test Password Validation
```bash
# Weak password (should fail)
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@test.com","password":"weak","full_name":"Test","role":"patient"}'

# Strong password (should succeed)
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@test.com","password":"StrongPass123!@#","full_name":"Test","role":"patient"}'
```

---
**Implementation Date**: March 30, 2026
**Recommended Review**: After implementation, before production deployment
