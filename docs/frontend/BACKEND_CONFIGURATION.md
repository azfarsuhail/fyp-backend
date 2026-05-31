# Backend Configuration Guide

## Overview

This guide documents the **actual backend contract currently implemented** in this repository for frontend/mobile sync integration.

It replaces the earlier assumption that pull-sync endpoints were missing.

---

## Mobile Sync Endpoint Status

The mobile app can use both pull and export sync flows against the current backend.

### ✅ Implemented Endpoints

| Endpoint | Method | Purpose | Status |
|----------|--------|---------|--------|
| `/api/v1/mobile/sync/data` | GET | Download authenticated user's profile + images + reports + profile history | IMPLEMENTED |
| `/api/v1/mobile/sync/summary` | GET | Get sync data counts for progress indicators | IMPLEMENTED |
| `/api/v1/mobile/sync/status` | GET | Check sync availability and return summary snapshot | IMPLEMENTED |
| `/api/v1/mobile/sync/export` | POST | Export authenticated user's sync data as JSON file | IMPLEMENTED |

Implementation file: `app/api/v1/mobile_sync.py`

---

## Backend Architecture

```
Mobile App (React Native)
    ↓
[Pull] GET /api/v1/mobile/sync/data
    ↓
FastAPI Backend
    ↓
PostgreSQL (Neon)
    ↓
SELECT user-specific profile, images, reports, and profile_logs WHERE user_id = ?
```

---

## Data Model Notes (Current Backend)

This backend uses the following model set for sync-related payloads:

```sql
-- Users
CREATE TABLE "USER" (
    user_id SERIAL PRIMARY KEY,
    email VARCHAR UNIQUE NOT NULL,
    password_hash VARCHAR NOT NULL,
    full_name VARCHAR NOT NULL,
    role VARCHAR DEFAULT 'patient',
    created_at TIMESTAMP,
    last_login TIMESTAMP
);

-- Images uploaded by user
CREATE TABLE "IMAGE" (
    image_id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES "USER"(user_id),
    s3_url VARCHAR,
    processed_s3_url VARCHAR,
    file_name VARCHAR,
    content_type VARCHAR,
    uploaded_at TIMESTAMP
);

-- Diagnostic reports
CREATE TABLE "REPORT" (
    report_id SERIAL PRIMARY KEY,
    image_id INTEGER REFERENCES "IMAGE"(image_id),
    user_id INTEGER REFERENCES "USER"(user_id),
    kl_grade INTEGER,
    confidence FLOAT,
    diagnosis_summary TEXT,
    recommendation TEXT,
    lifestyle_plan TEXT,
    warnings TEXT,
    exercise_video_urls TEXT,
    created_at TIMESTAMP
);

-- Profile audit history
CREATE TABLE "PROFILE_LOG" (
    log_id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES "USER"(user_id),
    field_name VARCHAR,
    old_value TEXT,
    new_value TEXT,
    changed_at TIMESTAMP
);
```

---

## Current Backend Route Wiring

Mobile sync routes are registered in `app/main.py`:

```python
app.include_router(mobile_sync.router, prefix="/api/v1/mobile", tags=["Mobile Sync"])
```

---

## Current Implementation Notes

- Auth model: bearer access token from `POST /api/v1/auth/login`
- Role access: `patient` and `gp` can access mobile sync endpoints
- Payload source: `MobileSyncService` in `app/services/mobile_sync.py`
- Current `/sync/status` response includes summary fields, `last_sync: null`, and `available: true`

---

## Legacy Implementation Guide (Reference)

The sections below are retained as optional design reference only. In this repository, equivalent endpoints are already implemented under `app/api/v1/mobile_sync.py`.

### 1️⃣ Implement `GET /api/v1/mobile/sync/data`

**Purpose**: Return all user data for first-time pull or full sync

**File**: `app/api/v1/mobile_sync.py` (already exists)

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.models import User, QuestionnaireResponse, ScanHistory, Recommendation
from app.auth import get_current_user
from app.database import get_db
from datetime import datetime
from typing import Optional

router = APIRouter(prefix="/api/v1/mobile", tags=["mobile_sync"])

@router.get("/sync/data")
async def get_sync_data(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    GET /api/v1/mobile/sync/data
    
    Returns all user data for mobile offline-first sync.
    Only returns data belonging to authenticated user.
    """
    try:
        # Get user profile
        user_data = {
            "server_id": current_user.id,
            "email": current_user.email,
            "full_name": current_user.full_name,
            "role": current_user.role,
            "created_at": current_user.created_at.isoformat(),
            "last_login": current_user.updated_at.isoformat()
        }
        
        # Get latest questionnaire
        questionnaire = db.query(QuestionnaireResponse).filter(
            QuestionnaireResponse.user_id == current_user.id
        ).order_by(QuestionnaireResponse.completed_at.desc()).first()
        
        questionnaire_data = None
        if questionnaire:
            questionnaire_data = {
                "age": questionnaire.age,
                "gender": questionnaire.gender,
                "weight": questionnaire.weight,
                "height": questionnaire.height,
                "pain_level": questionnaire.pain_level,
                "pain_location": questionnaire.pain_location,
                "mobility_score": questionnaire.mobility_score,
                "family_history": questionnaire.family_history,
                "completed_at": questionnaire.completed_at.isoformat()
            }
        
        # Get scan history
        scans = db.query(ScanHistory).filter(
            ScanHistory.user_id == current_user.id
        ).order_by(ScanHistory.scanned_at.desc()).all()
        
        scan_history = []
        for scan in scans:
            scan_history.append({
                "id": scan.id,
                "image_uri": scan.image_uri,
                "knee_side": scan.knee_side,
                "view_type": scan.view_type,
                "kl_grade": scan.kl_grade,
                "risk_score": float(scan.risk_score) if scan.risk_score else None,
                "scanned_at": scan.scanned_at.isoformat()
            })
        
        # Get recommendations
        recommendations = db.query(Recommendation).filter(
            Recommendation.user_id == current_user.id
        ).order_by(Recommendation.generated_at.desc()).all()
        
        recommendations_list = []
        for rec in recommendations:
            recommendations_list.append({
                "id": rec.id,
                "scan_id": rec.scan_id,
                "recommendation_text": rec.recommendation_text,
                "exercises": rec.exercises or [],
                "lifestyle_tips": rec.lifestyle_tips or [],
                "generated_at": rec.generated_at.isoformat()
            })
        
        return {
            "user": user_data,
            "questionnaire": questionnaire_data,
            "scan_history": scan_history,
            "recommendations": recommendations_list,
            "synced_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        print(f"[mobile_sync] Error in sync/data: {str(e)}")
        raise HTTPException(status_code=500, detail="Sync failed")
```

---

### 2️⃣ Implement `GET /api/v1/mobile/sync/summary`

**Purpose**: Return data counts for progress indicators

```python
@router.get("/sync/summary")
async def get_sync_summary(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    GET /api/v1/mobile/sync/summary
    
    Returns count of records for progress indicators.
    Useful for checking before full sync.
    """
    try:
        questionnaire_count = db.query(QuestionnaireResponse).filter(
            QuestionnaireResponse.user_id == current_user.id
        ).count()
        
        scan_count = db.query(ScanHistory).filter(
            ScanHistory.user_id == current_user.id
        ).count()
        
        recommendation_count = db.query(Recommendation).filter(
            Recommendation.user_id == current_user.id
        ).count()
        
        return {
            "user_id": current_user.id,
            "questionnaire_count": questionnaire_count,
            "scan_count": scan_count,
            "recommendation_count": recommendation_count,
            "total_records": questionnaire_count + scan_count + recommendation_count,
            "last_sync": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        print(f"[mobile_sync] Error in sync/summary: {str(e)}")
        raise HTTPException(status_code=500, detail="Summary failed")
```

---

### 3️⃣ Implement `GET /api/v1/mobile/sync/status`

**Purpose**: Check overall sync health

```python
@router.get("/sync/status")
async def get_sync_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    GET /api/v1/mobile/sync/status
    
    Returns sync health status and availability.
    Mobile app uses this to determine if sync is ready.
    """
    try:
        # Check if user has any data
        questionnaire_count = db.query(QuestionnaireResponse).filter(
            QuestionnaireResponse.user_id == current_user.id
        ).count()
        
        scan_count = db.query(ScanHistory).filter(
            ScanHistory.user_id == current_user.id
        ).count()
        
        recommendation_count = db.query(Recommendation).filter(
            Recommendation.user_id == current_user.id
        ).count()
        
        total = questionnaire_count + scan_count + recommendation_count
        
        return {
            "user_id": current_user.id,
            "synced": True,
            "available": total > 0,
            "record_count": total,
            "last_sync": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        print(f"[mobile_sync] Error in sync/status: {str(e)}")
        return {
            "user_id": current_user.id,
            "synced": False,
            "available": False,
            "error": str(e)
        }
```

---

### 4️⃣ Register Routes in `main.py`

```python
from fastapi import FastAPI
from app.api.v1 import mobile_sync

app = FastAPI()

# Include mobile sync routes
app.include_router(mobile_sync.router, prefix="/api/v1/mobile", tags=["Mobile Sync"])

# Other routes...
```

---

## Token Refresh Implementation

Currently, access tokens are issued by `POST /api/v1/auth/login` and there is **no refresh token endpoint** implemented yet in `app/api/v1/auth.py`.

If frontend token refresh is required, add `POST /api/v1/auth/refresh` as a future enhancement.

### Add Refresh Token Endpoint

```python
# In app/api/v1/auth.py

@router.post("/auth/refresh")
async def refresh_token(
    refresh_token: str,
    db: Session = Depends(get_db)
):
    """
    POST /api/v1/auth/refresh
    
    Refresh expired access token.
    Mobile app calls this when getting 401 Unauthorized.
    """
    try:
        # Verify refresh token
        payload = verify_token(refresh_token, token_type="refresh")
        user_id = payload.get("sub")
        
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        
        # Generate new access token
        new_access_token = create_token(
            data={"sub": str(user.id)},
            expires_delta=timedelta(minutes=15)
        )
        
        return {
            "access_token": new_access_token,
            "token_type": "bearer",
            "expires_in": 900  # 15 minutes in seconds
        }
        
    except Exception as e:
        raise HTTPException(status_code=401, detail="Token refresh failed")
```

### Update Login Endpoint

```python
@router.post("/auth/login")
async def login(
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    """Return both access_token and refresh_token"""
    user = authenticate_user(db, username, password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
---

## Backend Context (For Frontend Team)

- **API Base:** `/api/v1` — all endpoints in this document are under this prefix.
- **Auth:** Bearer JWT in `Authorization` header. Obtain tokens from `POST /api/v1/auth/login`.
- **Role-based access:** `role` claim in the token is used for RBAC. Common roles: `patient`, `gp`, `admin`.

**Environment / Runtime**
- **DATABASE_URL:** full Postgres/Neon connection string (required in production).
- **DEBUG:** `0|1` or `false|true` (defaults to false). Controls SQLAlchemy echo and verbose logging.
- **TESTING:** `0|1` or `false|true` (set by CI/test runs to enable SQLite in-memory behavior).

**Backend Config Notes**
- The backend now supports SQLite for tests and Postgres for production. For Postgres, engine is created with `pool_pre_ping=True` to avoid stale connections. See `app/core/config.py`.

**New/Updated Endpoints (important for frontend)**
- **GET /api/v1/profile/me** — Get authenticated user's profile (all roles). Returns `ProfileOut`.
- **GET /api/v1/profile/me/history** — Get authenticated user's profile change history (audit logs).
- **GET /api/v1/profile/patients/{patient_id}/history** — NEW: Clinician audit access (allowed roles: `gp`, `admin`). Returns `ProfileHistoryOut` (ordered by `changed_at` desc).

Example: fetch patient history as GP (replace token and id):

```http
GET /api/v1/profile/patients/42/history HTTP/1.1
Host: api.example.com
Authorization: Bearer <ACCESS_TOKEN_WITH_ROLE_gp>
Accept: application/json
```

Successful response shape (abridged):

```json
{
    "user_id": 42,
    "full_name": "Patient Name",
    "total_changes": 3,
    "history": [
        {"log_id": 5, "field_name": "pain_level", "old_value": "2", "new_value": "4", "changed_at": "2026-05-31T12:34:56Z"},
        ...
    ]
}
```

**Auth Header Example**

```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9....
```

**Where to Find Backend Contracts and Tests**
- API routes: `app/api/v1/` (look for `profile.py`, `mobile_sync.py`, `auth.py`).
- Pydantic response schemas: `app/schemas/` (e.g., `profile_schema.py`).
- Tests for profile endpoints: `tests/test_profile.py` (includes access-control tests for the patient-history endpoint).

**Changelog**
- Recent entries and historical changelogs: [docs/changelog/](../changelog/)

If you want, I can also produce a compact JSON or OpenAPI fragment of the updated endpoints for the frontend team to import directly.
    access_token = create_token(
        data={"sub": str(user.id)},
        expires_delta=timedelta(minutes=15)
    )
    
    refresh_token = create_token(
        data={"sub": str(user.id), "type": "refresh"},
        expires_delta=timedelta(days=7)
    )
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user_id": user.id,
        "email": user.email,
        "expires_in": 900
    }
```

---

## Testing the Implementation

### Test 1: Get Sync Data

```bash
# 1. Login to get token
TOKEN=$(curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=test@example.com&password=TestPass123!@#" \
  | jq -r '.access_token')

# 2. Fetch sync data
curl -X GET http://localhost:8000/api/v1/mobile/sync/data \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" | jq .
```

### Test 2: Get Sync Summary

```bash
curl -X GET http://localhost:8000/api/v1/mobile/sync/summary \
  -H "Authorization: Bearer $TOKEN" \
  | jq .
```

### Test 3: Get Sync Status

```bash
curl -X GET http://localhost:8000/api/v1/mobile/sync/status \
  -H "Authorization: Bearer $TOKEN" \
  | jq .
```

### Test 4: Test Token Refresh

```bash
# Refresh token
curl -X POST http://localhost:8000/api/v1/auth/refresh \
  -H "Content-Type: application/json" \
  -d "{\"refresh_token\": \"$REFRESH_TOKEN\"}" \
  | jq .
```

---

## Security Checklist

- ✅ All sync endpoints require Bearer token authentication
- ✅ Only return data for authenticated user (WHERE user_id = current_user.id)
- ✅ Use HTTPS in production
- ✅ Validate token expiration on each request
- ✅ Use secure refresh token handling
- ✅ Log all sync operations for audit trail
- ✅ Implement rate limiting on sync endpoints

---

## Performance Optimization

### Issue: Large Data Sets

If user has many scans/recommendations, the sync response can be huge.

### Solution: Pagination or Limits

```python
# Limit to last 50 scans
scans = db.query(ScanHistory).filter(
    ScanHistory.user_id == current_user.id
).order_by(ScanHistory.scanned_at.desc()).limit(50).all()

# Alternative: Return last 30 days only
from datetime import datetime, timedelta

thirty_days_ago = datetime.utcnow() - timedelta(days=30)
scans = db.query(ScanHistory).filter(
    ScanHistory.user_id == current_user.id,
    ScanHistory.scanned_at >= thirty_days_ago
).all()
```

### Issue: Response Too Large

Compress responses or implement incremental sync:

```python
# Accept optional timestamp for incremental sync
@router.get("/sync/data")
async def get_sync_data(
    current_user: User = Depends(get_current_user),
    since: Optional[str] = None,  # ISO timestamp "2026-03-30T10:00:00"
    db: Session = Depends(get_db)
):
    """Only return records modified since 'since' timestamp"""
    if since:
        since_dt = datetime.fromisoformat(since)
        scans = db.query(ScanHistory).filter(
            ScanHistory.user_id == current_user.id,
            ScanHistory.updated_at >= since_dt  # Compare with updated_at
        ).all()
    else:
        scans = db.query(ScanHistory).filter(
            ScanHistory.user_id == current_user.id
        ).all()
```

---

## Debugging Tips

### Check if Token is Valid

```python
# In any route
@router.get("/debug/token")
async def debug_token(current_user: User = Depends(get_current_user)):
    return {
        "user_id": current_user.id,
        "email": current_user.email,
        "role": current_user.role
    }
```

### Check Database Connection

```python
@router.get("/debug/db")
async def debug_db(db: Session = Depends(get_db)):
    try:
        result = db.execute("SELECT 1")
        return {"status": "connected", "result": result.scalar()}
    except Exception as e:
        return {"status": "error", "error": str(e)}
```

### Monitor Sync Log

```bash
# Check sync success rate
SELECT 
    status, 
    COUNT(*) as count
FROM sync_log
WHERE user_id = 1
GROUP BY status;

# Check recent errors
SELECT 
    table_name, 
    status, 
    error_message, 
    completed_at
FROM sync_log
WHERE user_id = 1 AND status = 'failed'
ORDER BY completed_at DESC
LIMIT 10;
```

---

## Deployment Checklist

- [x] Implement all 3 pull sync endpoints (`/sync/data`, `/sync/summary`, `/sync/status`)
- [x] Implement export sync endpoint (`/sync/export`)
- [ ] Add refresh token endpoint (future enhancement)
- [x] Test endpoints with API test suite
- [x] Update API documentation
- [x] Add authentication and role checks on sync endpoints
- [ ] Monitor sync success/failure metrics
- [ ] Create alerting for sync failures
- [ ] Load test with multiple users
- [ ] Deploy to staging environment
- [ ] Test mobile app against staging
- [ ] Deploy to production

---

## Next Steps for Mobile App Team

With current backend endpoints available:

1. Call `fetchLatestFromCloud()` after login in [src/screens/LoginScreen.js](src/screens/LoginScreen.js)
2. Parse response and save to local SQLite tables
3. Implement token refresh in [src/services/api.js](src/services/api.js)
4. Add sync status UI in a new screen
5. Test full end-to-end flow

---

**Version**: 1.1  
**Last Updated**: April 21, 2026  
**Status**: ✅ Mobile sync pull/export endpoints implemented in backend
