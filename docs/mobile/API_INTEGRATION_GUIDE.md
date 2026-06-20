# Mobile API Integration Guide

**Knee OA Backend - Mobile Development Documentation**  
*Version: 1.0.0 | Last Updated: June 20, 2026*

This guide provides mobile developers with comprehensive documentation for integrating with the Knee OA Backend API. It covers authentication, security, rate limiting, and all available endpoints.

---

## Table of Contents

1. [Authentication & Security](#authentication--security)
   - [JWT Bearer Token Flow](#jwt-bearer-token-flow)
   - [OTP Password Reset Flow](#otp-password-reset-flow)
2. [Rate Limiting](#rate-limiting)
3. [Mobile Sync Feature](#mobile-sync-feature)
4. [Diagnostic Pipeline](#diagnostic-pipeline)
5. [Error Handling](#error-handling)
6. [Endpoint Reference](#endpoint-reference)

---

## Authentication & Security

### JWT Bearer Token Flow

The API uses JWT (JSON Web Tokens) for authentication. All protected endpoints require a Bearer token in the `Authorization` header.

#### 1. Register a New User

```http
POST /api/v1/auth/register
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "SecurePass123!",
  "full_name": "John Doe",
  "role": "patient"
}
```

**Response (201 Created):**
```json
{
  "user_id": 1,
  "email": "user@example.com",
  "full_name": "John Doe",
  "role": "patient",
  "created_at": "2026-06-20T10:00:00Z"
}
```

#### 2. Login and Get Access Token

```http
POST /api/v1/auth/login
Content-Type: application/x-www-form-urlencoded

username=user@example.com&password=SecurePass123!
```

**Response (200 OK):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

**Store the token securely** (e.g., in iOS Keychain or Android Keystore).

#### 3. Use Token for Protected Endpoints

Include the token in all subsequent requests:

```http
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
GET /api/v1/profile
```

---

### OTP Password Reset Flow

The OTP (One-Time Password) password reset flow provides a secure way for users to reset their passwords. This flow uses 6-digit numeric codes that expire in 5 minutes.

#### Step 1: Request OTP Code

```http
POST /api/v1/auth/request-otp
Content-Type: application/json

{
  "email": "user@example.com"
}
```

**Response (200 OK):**
```json
{
  "message": "If an account with that email address exists, a password reset code has been sent."
}
```

**Security Notes:**
- Returns a generic message regardless of whether the email exists (prevents email enumeration)
- Rate limited to 3 requests per hour per IP address
- OTP code is sent via email (HTML template with 5-minute expiration notice)

#### Step 2: Verify OTP and Reset Password

```http
POST /api/v1/auth/verify-otp-and-reset
Content-Type: application/json

{
  "email": "user@example.com",
  "otp_code": "123456",
  "new_password": "NewSecurePass456!"
}
```

**Response (200 OK):**
```json
{
  "message": "Your password has been successfully reset using the OTP code. You can now log in with your new password."
}
```

**Password Requirements:**
- Minimum 8 characters
- At least one uppercase letter
- At least one lowercase letter
- At least one number
- At least one special character (`!@#$%^&*()_+-=[]{}|;:,.<>?`)

**Security Features:**
- OTP codes are hashed using bcrypt before storage
- Maximum 3 verification attempts per OTP
- OTP automatically locks after 3 failed attempts
- OTP expires after 5 minutes
- Password changes are logged in the audit trail

**Error Responses:**
- `400 Bad Request`: Invalid OTP, expired code, or weak password
- `422 Unprocessable Entity`: Validation errors (e.g., invalid email format)

---

## Rate Limiting

The API implements rate limiting to prevent abuse. Mobile clients must handle `429 Too Many Requests` responses gracefully.

### Rate Limit Rules

| Endpoint | Limit | Window |
|----------|-------|--------|
| `/api/v1/auth/login` | 5 requests | 1 minute |
| `/api/v1/auth/register` | 5 requests | 60 minutes |
| `/api/v1/auth/forgot-password` | 3 requests | 60 minutes |
| `/api/v1/auth/request-otp` | 3 requests | 60 minutes |

### Handling Rate Limit Errors

When rate limited, the API returns:

```http
HTTP/1.1 429 Too Many Requests
Retry-After: 3600
Content-Type: application/json

{
  "detail": "Too many requests. Please try again in 60 minutes.",
  "retry_after": 3600
}
```

**Mobile Client Best Practices:**
1. **Cache the `Retry-After` header** and display a countdown to the user
2. **Implement exponential backoff** for retry attempts
3. **Show user-friendly messages** like "Too many attempts. Please try again in 5 minutes"
4. **Disable the submit button** temporarily to prevent repeated requests

---

## Mobile Sync Feature

The mobile sync endpoints enable offline-first architecture, allowing users to work offline and sync data when connectivity is restored.

### Sync Data Endpoint

```http
POST /api/v1/mobile/sync/data
Authorization: Bearer <token>
Content-Type: application/json

{
  "device_id": "mobile_device_123",
  "sync_type": "full",
  "data": {
    "images": [
      {
        "image_id": "img_001",
        "status": "pending_upload",
        "local_path": "/path/to/local/image.jpg"
      }
    ],
    "reports": [
      {
        "report_id": "rpt_001",
        "status": "pending_sync",
        "diagnostic_result": {...}
      }
    ]
  }
}
```

**Response (200 OK):**
```json
{
  "sync_id": "sync_20260620_001",
  "status": "completed",
  "synced_count": 2,
  "failed_count": 0,
  "timestamp": "2026-06-20T10:30:00Z"
}
```

### Sync Summary Endpoint

```http
POST /api/v1/mobile/sync/summary
Authorization: Bearer <token>
Content-Type: application/json

{
  "device_id": "mobile_device_123",
  "last_sync_time": "2026-06-19T15:00:00Z"
}
```

**Response (200 OK):**
```json
{
  "pending_items": {
    "images": 3,
    "reports": 1
  },
  "server_timestamp": "2026-06-20T10:30:00Z",
  "conflicts": []
}
```

**Offline-First Architecture Guidelines:**
1. **Local Database**: Store all data locally using SQLite or Realm
2. **Sync Queue**: Maintain a queue of pending operations
3. **Conflict Resolution**: Use last-write-wins or manual resolution for conflicts
4. **Background Sync**: Use device background fetch APIs to sync periodically
5. **Progress Indicators**: Show sync progress to users

---

## Diagnostic Pipeline

The diagnostic pipeline uses a two-step process to analyze knee X-ray images for Osteoarthritis detection.

### Step 1: Upload Image

```http
POST /api/v1/upload/
Authorization: Bearer <token>
Content-Type: multipart/form-data

image: <binary_file>
```

**Response (200 OK):**
```json
{
  "image_id": "img_abc123",
  "filename": "knee_xray_001.jpg",
  "upload_timestamp": "2026-06-20T10:00:00Z",
  "status": "uploaded"
}
```

**Important:** Save the `image_id` for the next step.

### Step 2: Analyze Image

```http
POST /api/v1/diagnostic/analyze
Authorization: Bearer <token>
Content-Type: application/json

{
  "image_id": "img_abc123",
  "patient_id": "patient_001"
}
```

**Response (200 OK):**
```json
{
  "diagnosis_id": "diag_xyz789",
  "image_id": "img_abc123",
  "prediction": {
    "class": "OA",
    "confidence": 0.94,
    "severity": "moderate"
  },
  "analysis_timestamp": "2026-06-20T10:05:00Z",
  "status": "completed"
}
```

### CLIP Zero-Shot Gatekeeper Validation

Before analysis, images pass through a CLIP-based gatekeeper that validates image quality and relevance:

**Possible Responses:**
- `200 OK`: Image is valid and ready for analysis
- `400 Bad Request`: Invalid image (e.g., not an X-ray, poor quality, wrong format)

**Example 400 Response:**
```json
{
  "detail": "Image validation failed: Image does not appear to be a valid knee X-ray"
}
```

**Mobile Client Guidelines:**
1. **Validate image format** before upload (JPEG/PNG only)
2. **Check image size** (max 10MB recommended)
3. **Show error messages** if gatekeeper rejects the image
4. **Allow re-upload** with guidance on image quality

---

## Error Handling

The API uses standard HTTP status codes and structured error responses.

### Global Exception Handlers

#### 422 Unprocessable Entity (Validation Errors)

Returned when request validation fails (e.g., invalid email format, missing required fields).

**Structure:**
```json
{
  "detail": [
    {
      "loc": ["body", "email"],
      "msg": "value is not a valid email address",
      "type": "value_error.email"
    },
    {
      "loc": ["body", "password"],
      "msg": "Password must be at least 8 characters long",
      "type": "value_error"
    }
  ]
}
```

**Mobile Client Parsing:**
```javascript
// Example error handling in mobile app
try {
  const response = await api.login(email, password);
} catch (error) {
  if (error.response.status === 422) {
    const validationErrors = error.response.data.detail;
    
    // Display user-friendly messages
    validationErrors.forEach(err => {
      if (err.loc.includes('email')) {
        showErrorMessage('Please enter a valid email address');
      } else if (err.loc.includes('password')) {
        showErrorMessage(err.msg);
      }
    });
  }
}
```

#### 401 Unauthorized

Returned when authentication token is missing, expired, or invalid.

```json
{
  "detail": "Could not validate credentials"
}
```

**Action:** Redirect user to login screen and clear stored tokens.

#### 403 Forbidden

Returned when user lacks permission for the requested action.

```json
{
  "detail": "Operation not permitted for this role"
}
```

#### 404 Not Found

Returned when the requested resource doesn't exist.

```json
{
  "detail": "User not found"
}
```

#### 429 Too Many Requests

Returned when rate limit is exceeded (see [Rate Limiting](#rate-limiting) section).

#### 500 Internal Server Error

Returned for unexpected server errors.

```json
{
  "detail": "Internal server error"
}
```

**Action:** Show generic error message and log the incident for support.

---

## Endpoint Reference

### Authentication Endpoints

| Method | Endpoint | Description | Rate Limit |
|--------|----------|-------------|------------|
| `POST` | `/api/v1/auth/register` | Register new user | 5/min |
| `POST` | `/api/v1/auth/login` | Login and get token | 5/min |
| `POST` | `/api/v1/auth/request-otp` | Request password reset OTP | 3/hour |
| `POST` | `/api/v1/auth/verify-otp-and-reset` | Verify OTP and reset password | 3/hour |
| `POST` | `/api/v1/auth/forgot-password` | Legacy password reset (deprecated) | 3/hour |

### Upload Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/upload/` | Upload image for analysis |
| `GET` | `/api/v1/upload/{image_id}` | Get image details |

### Diagnostic Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/diagnostic/analyze` | Analyze uploaded image |
| `GET` | `/api/v1/diagnostic/{diagnosis_id}` | Get diagnosis results |

### Mobile Sync Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/mobile/sync/data` | Sync data from device |
| `POST` | `/api/v1/mobile/sync/summary` | Get sync summary |

### Profile Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/profile` | Get current user profile |
| `PUT` | `/api/v1/profile` | Update user profile |

---

## Testing the API

### Using cURL

```bash
# Login
curl -X POST http://localhost:8000/api/v1/auth/login \
  -d "username=user@example.com&password=SecurePass123!"

# Get token and use it
TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
curl -X GET http://localhost:8000/api/v1/profile \
  -H "Authorization: Bearer $TOKEN"
```

### Using Postman

1. Import the API collection (if available)
2. Set up environment variables for `BASE_URL` and `AUTH_TOKEN`
3. Use the built-in authentication tab for OAuth2/JWT

### Mobile SDK Integration

Example using Python requests (for testing):

```python
import requests

BASE_URL = "https://kneeoa.online/api/v1"

# Login
response = requests.post(
    f"{BASE_URL}/auth/login",
    data={"username": "user@example.com", "password": "SecurePass123!"}
)
token = response.json()["access_token"]

# Protected endpoint
headers = {"Authorization": f"Bearer {token}"}
response = requests.get(f"{BASE_URL}/profile", headers=headers)
print(response.json())
```

---

## Support & Contact

For technical support or questions:
- **Email:** support@kneeoa.online
- **Documentation:** [docs/README.md](../../README.md)
- **API Issues:** Check the [CHANGELOG](../../CHANGELOG.md) for known issues

---

*This guide is maintained by the Backend Development Team. Last updated: June 20, 2026*
