# Password Reset Flow Implementation Guide

## 🎯 Overview
Complete implementation of a secure "Forgot Password" / "Reset Password" flow for Android mobile application using FastAPI, SQLAlchemy/PostgreSQL, Resend for emails, and Nginx as reverse proxy.

**Implementation Date:** 2026-06-18  
**Token Expiry:** 15 minutes (updated from 30 for enhanced security)  
**Android Package:** `com.azfarsuhail.kneeoaapp`  
**App SHA-256:** `93:1A:94:70:8D:C3:EB:8B:67:64:E9:64:54:34:28:1E:7D:66:7A:60:27:8E:1E:D4:1E:0E:5E:FA:1C:79:AE:A5`

---

## ✅ What Was Implemented

### 1. Android App Links Verification (`app/main.py`) ⭐ NEW
- ✅ `GET /.well-known/assetlinks.json` endpoint
- ✅ Returns Android App Links verification JSON
- ✅ Enables deep linking for password reset URLs
- ✅ Media type: `application/json`

**Response:**
```json
[
  {
    "relation": ["delegate_permission/common.handle_all_urls"],
    "target": {
      "namespace": "android_app",
      "package_name": "com.azfarsuhail.kneeoaapp",
      "sha256_cert_fingerprints": ["93:1A:94:70:8D:C3:EB:8B:67:64:E9:64:54:34:28:1E:7D:66:7A:60:27:8E:1E:D4:1E:0E:5E:FA:1C:79:AE:A5"]
    }
  }
]
```

### 2. Nginx Configuration (`nginx/nginx.conf`) ⭐ NEW
- ✅ Added `.well-known/` location block
- ✅ Proxies to FastAPI backend at `http://api:8000/.well-known/`
- ✅ Proper header forwarding for deep linking

**Configuration:**
```nginx
location /.well-known/ {
    proxy_pass http://api:8000/.well-known/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

### 3. Email Service (`app/services/email.py`)
- ✅ `send_reset_password_email(email_to, token)` function
- ✅ HTML email template with professional styling
- ✅ Uses `resend` Python SDK
- ✅ Graceful error handling (won't crash API if email fails)
- ✅ Configurable via `RESEND_API_KEY` and `APP_URL` environment variables
- ✅ **Updated**: Default APP_URL changed to `https://kneeoa.online`
- ✅ **Refactored**: Moved from `app/utils/email.py` to `app/services/email.py` for better organization

### 4. Security Updates (`app/core/security.py`) ⭐ UPDATED
- ✅ `create_password_reset_token(email)` - generates JWT with **15-min expiry** (updated from 30)
- ✅ `verify_password_reset_token(token)` - validates and decodes reset tokens
- ✅ Type-scoped tokens (`"type": "reset"`) prevent reuse as access tokens
- ✅ Added `RESET_TOKEN_EXPIRE_MINUTES` configuration (default: **15**)

**Token Payload:**
```python
{
    "sub": "user@example.com",
    "type": "reset",
    "iat": 1718712345,
    "exp": 1718713245  # 15 minutes later
}
```

### 5. Schema Updates (`app/schemas/user_schema.py`)
- ✅ `ForgotPasswordRequest` - email field with validation
- ✅ `ResetPasswordRequest` - token + new_password with password strength validator

### 6. API Endpoints (`app/api/v1/auth.py`)
- ✅ `POST /forgot-password` - sends reset email asynchronously
- ✅ `POST /reset-password` - validates token and updates password
- ✅ Uses `BackgroundTasks` for non-blocking email sending
- ✅ Prevents email enumeration (same response for valid/invalid emails)
- ✅ Correct import: `from app.services.email import send_reset_password_email`

### 7. Configuration
- ✅ Added `resend>=1.0.0` to `requirements.txt`
- ✅ Updated `.env.example` with `RESEND_API_KEY` and `APP_URL`
- ✅ Created comprehensive documentation in `docs/PASSWORD_RESET_IMPLEMENTATION.md`

### 8. Testing
- ✅ Created `tests/test_password_reset.py` with 10 test cases
- ✅ Tests cover: valid/invalid emails, token validation, security checks
- ✅ All tests passing after refactoring

---

## 🚀 Quick Start

### Step 1: Install Dependencies
```bash
pip install resend
```

### Step 2: Configure Environment
Add to your `.env` file:
```bash
# Get from https://resend.com/api-keys
RESEND_API_KEY=re_your_actual_api_key_here

# Your app's base URL (production or local)
APP_URL=https://kneeoa.online
# For local development:
# APP_URL=http://localhost:8000

# JWT Secret (generate with: python -c "import secrets; print(secrets.token_urlsafe(32))")
SECRET_KEY=your_super_secret_key_min_32_characters
```

### Step 3: Test the Endpoints

**Test Android App Links:**
```bash
curl https://kneeoa.online/.well-known/assetlinks.json
```

**Request Password Reset:**
```bash
curl -X POST https://kneeoa.online/api/v1/auth/forgot-password \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com"}'
```

**Reset Password:**
```bash
curl -X POST https://kneeoa.online/api/v1/auth/reset-password \
  -H "Content-Type: application/json" \
  -d '{
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "new_password": "SecurePass123!"
  }'
```

### Step 4: Run Tests
```bash
pytest tests/test_password_reset.py -v
```

---

## 🔒 Security Features

1. **Token Type Scoping** - Reset tokens cannot be used as access tokens
2. **Short Expiry** - **15-minute** token lifetime (updated from 30 for enhanced security)
3. **Email Enumeration Prevention** - Generic success messages
4. **Asynchronous Email** - Background tasks prevent blocking
5. **Password Validation** - Reuses existing `require_strong_password()`
6. **Graceful Degradation** - API works even if email service fails
7. **HTTPS Only** - All communications encrypted via SSL/TLS
8. **JWT Signature Validation** - Prevents token tampering

---

## 📁 Files Modified/Created

| File | Status | Description |
|------|--------|-------------|
| `app/services/email.py` | ✨ Created | Email service with Resend integration (refactored from utils) |
| `app/core/security.py` | ✏️ Modified | Added token creation/verification functions |
| `app/schemas/user_schema.py` | ✏️ Modified | Added request/response schemas |
| `app/api/v1/auth.py` | ✏️ Modified | Added `/forgot-password` and `/reset-password` endpoints |
| `requirements.txt` | ✏️ Modified | Added `resend` dependency |
| `.env.example` | ✏️ Modified | Added email configuration variables |
| `docs/password-reset-flow.md` | ✏️ Updated | Updated file paths and structure |
| `docs/PASSWORD_RESET_IMPLEMENTATION.md` | ✏️ Updated | Added refactoring notes |
| `tests/test_password_reset.py` | ✏️ Updated | Updated import paths |

---

## 🎯 Next Steps

1. **Sign up for Resend** at https://resend.com and get your API key
2. **Verify your domain** in Resend dashboard (required for production)
3. **Test locally** - emails will be logged to console if `RESEND_API_KEY` is missing
4. **Update frontend** to integrate with the new endpoints
5. **Add rate limiting** to prevent abuse (recommended for production)

---

## 📚 Documentation

- **API Documentation:** `docs/password-reset-flow.md`
- **Test Suite:** `tests/test_password_reset.py`
- **Security Best Practices:** See `docs/password-reset-flow.md` → Security Features section

---

## ⚠️ Important Notes

- The `resend` package must be installed: `pip install resend`
- Without `RESEND_API_KEY`, emails won't be sent but the API won't crash
- Reset tokens expire after 30 minutes (configurable)
- The same success message is returned for both valid and invalid emails (security best practice)

---

## 🐛 Troubleshooting

**Email not arriving?**
- Check spam folder
- Verify `RESEND_API_KEY` is set correctly
- Review server logs for `[Email Service]` messages

**Token validation fails?**
- Ensure full token is passed (no truncation)
- Check if `SECRET_KEY` changed between generation and verification

**Background task not executing?**
- Ensure running with Uvicorn (not synchronous server)
- Check for startup exceptions

---

**Need help?** See the full documentation in `docs/password-reset-flow.md`
