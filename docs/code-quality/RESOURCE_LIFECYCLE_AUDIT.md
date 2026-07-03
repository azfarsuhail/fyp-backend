# Resource Lifecycle Audit Report
**Date:** 2026-07-02  
**Scope:** `app/services/`, `app/api/v1/`, `app/agents/`  
**Severity Levels:** 🔴 High | 🟡 Medium | 🟢 Low

---

## Executive Summary

| Category | Total Issues | High | Medium | Low |
|----------|-------------|------|--------|-----|
| File Operations | 2 | 0 | 1 | 1 |
| S3/Boto3 Clients | 1 | 🔴 1 | 0 | 0 |
| HTTP Clients | 0 | 0 | 0 | 0 |
| Database Sessions | 8 | 🟡 8 | 0 | 0 |
| SQLite Connections | 1 | 🟡 1 | 0 | 0 |
| **TOTAL** | **12** | **1** | **10** | **1** |

---

## 🔴 HIGH SEVERITY ISSUES

### 1. **Global S3 Client - No Context Manager**
**File:** `app/services/s3_service.py`  
**Line:** 13-19  
**Issue:** `s3_client = boto3.client(...)` is initialized as a global singleton and reused across all requests without proper cleanup.

```python
# ❌ BAD: Global boto3 client without context management
s3_client = boto3.client(
    "s3",
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    region_name=AWS_REGION,
)
```

**Impact:**
- Connection pool exhaustion under high load
- No graceful shutdown on application termination
- Potential resource leaks during scaling events

**Recommendation:**
```python
# ✅ GOOD: Use dependency injection or context manager
from contextlib import contextmanager

@contextmanager
def get_s3_client():
    client = boto3.client(...)
    try:
        yield client
    finally:
        client.close()

# In FastAPI dependency
@app.get("/upload")
async def upload(..., s3_client: boto3.client = Depends(get_s3_client)):
    ...
```

**Severity:** 🔴 **HIGH** - Can cause connection pool exhaustion and resource leaks under production load.

---

## 🟡 MEDIUM SEVERITY ISSUES

### 2. **Database Session - No Try/Finally Block**
**File:** `app/services/otp_service.py`  
**Lines:** 60-93, 140-209  
**Issue:** Multiple database operations commit without try/finally blocks for rollback on exceptions.

```python
# ❌ BAD: No exception handling
def create_otp_record(db: Session, user_id: int) -> OTPVerification:
    otp_record = OTPVerification(...)
    db.add(otp_record)
    db.commit()  # ❌ No try/except/finally
    db.refresh(otp_record)
    return otp_record, otp_code
```

**Locations:**
- `create_otp_record()` (line 93)
- `verify_otp_and_increment_attempts()` (lines 157, 166, 169)
- `cleanup_expired_otps()` (line 194)
- `delete_otp_for_user()` (line 209)

**Impact:**
- Partial transactions left in inconsistent state on errors
- Database locks not released properly
- Potential data corruption

**Recommendation:**
```python
# ✅ GOOD: Proper transaction management
def create_otp_record(db: Session, user_id: int) -> OTPVerification:
    try:
        otp_record = OTPVerification(...)
        db.add(otp_record)
        db.commit()
        db.refresh(otp_record)
        return otp_record, otp_code
    except Exception as e:
        db.rollback()
        raise
```

**Severity:** 🟡 **MEDIUM** - Affects data integrity and transaction consistency.

---

### 3. **Database Session - No Try/Finally Block**
**File:** `app/api/v1/auth.py`  
**Lines:** 60, 79, 192  
**Issue:** Database commits without exception handling in authentication endpoints.

**Locations:**
- `register_user()` (line 60)
- `login_for_access_token()` (line 79)
- `forgot_password()` (line 192)

**Impact:**
- User registration failures leave partial records
- Session state inconsistency
- No rollback on authentication errors

**Severity:** 🟡 **MEDIUM** - Authentication and user management affected.

---

### 4. **Database Session - No Try/Finally Block**
**File:** `app/api/v1/upload.py`  
**Line:** 69  
**Issue:** Image upload commit without exception handling.

```python
# ❌ BAD: No exception handling
db.add(new_image)
db.commit()  # Line 69
db.refresh(new_image)
```

**Impact:**
- Failed uploads leave orphan database records
- No cleanup on S3 upload failures

**Severity:** 🟡 **MEDIUM** - Data integrity in image uploads.

---

### 5. **Database Session - No Try/Finally Block**
**File:** `app/api/v1/diagnostic.py`  
**Lines:** 124, 166  
**Issue:** Diagnostic pipeline commits without exception handling.

**Locations:**
- Processed image upload commit (line 124)
- Report creation commit (line 166)

**Impact:**
- Incomplete diagnostic reports on failure
- Database state inconsistency

**Severity:** 🟡 **MEDIUM** - Core diagnostic functionality affected.

---

### 6. **Database Session - No Try/Finally Block**
**File:** `app/api/v1/profile.py`  
**Lines:** 189, 209  
**Issue:** Profile updates commit without exception handling.

**Locations:**
- `update_my_profile()` (line 189)
- `change_password()` (line 209)

**Impact:**
- Partial profile updates on failure
- Password changes may leave inconsistent state

**Severity:** 🟡 **MEDIUM** - User profile data integrity.

---

### 7. **Database Session - No Try/Finally Block**
**File:** `app/api/v1/video.py`  
**Lines:** 125, 176, 196, 251, 268  
**Issue:** Video CRUD operations commit without exception handling.

**Locations:**
- `create_video()` (line 125)
- `create_video_with_file()` (line 176)
- `update_video()` (line 196)
- `delete_video()` (lines 251, 268)

**Impact:**
- Video library corruption on failures
- Orphaned S3 uploads

**Severity:** 🟡 **MEDIUM** - Content management affected.

---

### 8. **SQLite Connection - No Try/Finally Block**
**File:** `app/services/mobile_sync.py`  
**Lines:** 135, 253-254  
**Issue:** SQLite connection opened without context manager or try/finally.

```python
# ❌ BAD: SQLite connection without cleanup
def create_mobile_db(self, db_path: str) -> None:
    conn = sqlite3.connect(db_path)  # Line 135
    cursor = conn.cursor()
    # ... many operations ...
    conn.commit()
    conn.close()  # ❌ Only closes on success, not on exception
```

**Impact:**
- File handle leaks on exceptions
- Database corruption if process crashes mid-operation
- Lock files not cleaned up

**Recommendation:**
```python
# ✅ GOOD: Use context manager
def create_mobile_db(self, db_path: str) -> None:
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        # ... operations ...
        # Auto-commits and closes on exit
```

**Severity:** 🟡 **MEDIUM** - File handle leaks and potential corruption.

---

## 🟢 LOW SEVERITY ISSUES

### 9. **PIL Image - Not Explicitly Closed**
**File:** `app/services/image_processor.py`  
**Line:** 18  
**Issue:** `Image.open()` not wrapped in context manager (though PIL handles this reasonably well internally).

```python
# ⚠️ LOW RISK: PIL Image not explicitly closed
def load_image_from_bytes(image_bytes: bytes) -> Image.Image:
    image = Image.open(io.BytesIO(image_bytes))  # Line 18
    return ImageOps.exif_transpose(image).convert("RGB")
```

**Impact:**
- Minimal - PIL's `BytesIO` wrapper handles cleanup
- No file handle leak (in-memory operation)

**Recommendation:**
```python
# ✅ BETTER: Explicit context management
def load_image_from_bytes(image_bytes: bytes) -> Image.Image:
    with Image.open(io.BytesIO(image_bytes)) as image:
        return ImageOps.exif_transpose(image).convert("RGB")
```

**Severity:** 🟢 **LOW** - In-memory operation, minimal risk.

---

### 10. **PIL Image - Not Explicitly Closed**
**File:** `app/agents/validation_agent.py`  
**Lines:** 109, 164  
**Issue:** Same as #9 - PIL Image operations without context managers.

**Locations:**
- `validate_image()` method (line 109)
- Module-level `validate_image()` function (line 164)

**Impact:**
- Minimal - in-memory operations
- No file handle leaks

**Severity:** 🟢 **LOW** - In-memory operation, minimal risk.

---

## ✅ PROPERLY MANAGED RESOURCES

### HTTP Clients - Correctly Used
**File:** `app/api/v1/diagnostic.py`  
**Line:** 80

```python
# ✅ GOOD: Async HTTP client with context manager
async with httpx.AsyncClient() as client:
    response = await client.get(presigned, timeout=30.0)
```

**Status:** Properly managed with `async with` context manager.

---

## Summary of Recommendations

### Priority 1 (Critical)
1. **Refactor S3 client** to use dependency injection or context managers
2. **Add try/finally blocks** to all database operations in service layer

### Priority 2 (High)
3. **Add exception handling** to all API route handlers that commit transactions
4. **Refactor SQLite connection** in `mobile_sync.py` to use context manager

### Priority 3 (Medium)
5. **Add explicit context managers** for PIL Image operations (optional, low risk)
6. **Implement connection pool monitoring** for S3 client

---

## Code Patterns to Adopt

### Database Session Management
```python
from contextlib import contextmanager

@contextmanager
def get_db_session(db: Session):
    """Ensure proper commit/rollback on database operations."""
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
```

### S3 Client Management
```python
from contextlib import contextmanager
import boto3

@contextmanager
def get_s3_client():
    """Manage S3 client lifecycle."""
    client = boto3.client('s3', ...)
    try:
        yield client
    finally:
        client.close()
```

### SQLite Connection Management
```python
# Use built-in context manager
with sqlite3.connect(db_path) as conn:
    cursor = conn.cursor()
    # operations...
    # Auto-commits and closes
```

---

## Testing Recommendations

1. **Load Testing:** Simulate high concurrent requests to verify no connection leaks
2. **Failure Injection:** Test exception handling in all transaction paths
3. **Resource Monitoring:** Use `psutil` to track file descriptor usage
4. **Database Lock Testing:** Verify no deadlocks under concurrent access

---

## References

- [Boto3 Best Practices](https://boto3.amazonaws.com/v1/documentation/api/latest/guide/resources.html#best-practices)
- [SQLAlchemy Transaction Management](https://docs.sqlalchemy.org/en/20/orm/session_basics.html#saving-and-committing)
- [FastAPI Dependency Injection](https://fastapi.tiangolo.com/tutorial/dependencies/)
