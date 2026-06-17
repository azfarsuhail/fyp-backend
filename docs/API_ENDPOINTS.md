# API Endpoints Documentation

> Complete reference for all implemented endpoints in the Knee OA Backend

---

## 🔐 Authentication Endpoints

### POST `/api/v1/auth/register`
Register a new user account.

**Request Body:**
```json
{
  "email": "patient@example.com",
  "password": "SecurePass123!@#",
  "full_name": "John Doe",
  "role": "patient"  // or "gp"
}
```

**Response:** `201 Created`
```json
{
  "user_id": 1,
  "email": "patient@example.com",
  "full_name": "John Doe",
  "role": "patient",
  "created_at": "2026-06-18T10:00:00"
}
```

**Notes:**
- Admin registration is blocked (manual creation only)
- Password must be 8+ chars with uppercase, lowercase, numbers, special chars
- Rate limited: 5 login attempts per minute per IP

---

### POST `/api/v1/auth/login`
Authenticate and receive JWT token.

**Request Body:**
```json
{
  "username": "patient@example.com",
  "password": "SecurePass123!@#"
}
```

**Response:** `200 OK`
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer"
}
```

**Notes:**
- Token expires after 15 minutes
- Updates `last_login` timestamp
- Rate limited: 5 attempts per minute per IP

---

### POST `/api/v1/auth/forgot-password`
Request password reset email.

**Request Body:**
```json
{
  "email": "patient@example.com"
}
```

**Response:** `200 OK`
```json
{
  "message": "Password reset email sent"
}
```

---

### POST `/api/v1/auth/reset-password`
Reset password with token.

**Request Body:**
```json
{
  "token": "reset_token_from_email",
  "new_password": "NewSecurePass123!@#"
}
```

**Response:** `200 OK`
```json
{
  "message": "Password reset successful"
}
```

---

## 📤 Image Upload Endpoints

### POST `/api/v1/upload/`
Upload a knee X-ray image.

**Request:** `multipart/form-data`
- `file`: Image file (PNG/JPEG, max 10MB)

**Response:** `201 Created`
```json
{
  "image_id": 1,
  "s3_url": "s3://bucket/xrays/abc123.png",
  "file_name": "knee_xray.png",
  "content_type": "image/png",
  "uploaded_at": "2026-06-18T10:00:00"
}
```

**Notes:**
- Gatekeeper validates image authenticity (CLIP zero-shot)
- S3 object stored privately, returns object key (not public URL)
- Presigned URLs generated for download

---

## 🩺 Diagnostic Endpoints

### POST `/api/v1/diagnostic/analyze`
Run full CNN + RAG pipeline on uploaded image.

**Request:** `multipart/form-data`
- `image`: Image file (PNG/JPEG)

**Response:** `200 OK`
```json
{
  "report_id": 1,
  "image_id": 1,
  "kl_grade": 2,
  "confidence": 0.87,
  "diagnosis_summary": "Grade 2 — Minimal OA",
  "recommendation": "Stay active with low-impact exercises",
  "lifestyle_plan": [...],
  "warnings": [...],
  "exercise_video_urls": [...]
}
```

**Pipeline:**
1. Gatekeeper validates image
2. Image preprocessing (grayscale, ROI, CLAHE)
3. CNN predicts KL grade (0-4)
4. RAG generates personalized recommendations
5. Report saved to database

---

### GET `/api/v1/diagnostic/reports`
List all reports for current user.

**Response:** `200 OK`
```json
[
  {
    "report_id": 1,
    "image_id": 1,
    "kl_grade": 2,
    "confidence": 0.87,
    "diagnosis_summary": "Grade 2 — Minimal OA",
    "created_at": "2026-06-18T10:00:00"
  }
]
```

---

### GET `/api/v1/diagnostic/reports/{id}`
Get a specific report by ID.

**Response:** `200 OK`
```json
{
  "report_id": 1,
  "image_id": 1,
  "user_id": 1,
  "kl_grade": 2,
  "confidence": 0.87,
  "diagnosis_summary": "Grade 2 — Minimal OA",
  "recommendation": "Stay active with low-impact exercises",
  "lifestyle_plan": [...],
  "warnings": [...],
  "exercise_video_urls": [...],
  "created_at": "2026-06-18T10:00:00"
}
```

---

## 💡 Recommendation Endpoints

### GET `/api/v1/recommendation/`
Get standalone recommendations by KL grade.

**Query Parameters:**
- `kl_grade` (required): 0-4
- `pain_level` (optional): 0-10
- `mobility_level` (optional): limited/moderate/good

**Response:** `200 OK`
```json
{
  "kl_grade": 2,
  "confidence": 0.87,
  "diagnosis_summary": "Grade 2 — Minimal OA",
  "recommendation": "Stay active with low-impact exercises",
  "lifestyle_plan": [
    {
      "id": "EX-001",
      "category": "exercise",
      "action": "Walk daily",
      "evidence_level": "strong",
      "source": "OARSI 2019"
    }
  ],
  "warnings": [
    {
      "level": "caution",
      "message": "Avoid high-impact activities."
    }
  ],
  "exercise_video_urls": [
    "https://presigned-url.example.com/video1.mp4"
  ]
}
```

---

## 👤 Profile Endpoints

### GET `/api/v1/profile/me`
Get current user's profile.

**Response:** `200 OK`
```json
{
  "user_id": 1,
  "email": "patient@example.com",
  "full_name": "John Doe",
  "role": "patient",
  "age": 45,
  "pain_level": 6,
  "mobility_level": "moderate",
  "has_support": true,
  "kinesiophobia": "low",
  "occupation_type": "sedentary",
  "has_stairs": true,
  "current_meds": ["ibuprofen"],
  "sleep_quality": "good",
  "created_at": "2026-01-15T10:00:00",
  "last_login": "2026-06-18T08:00:00"
}
```

---

### PUT `/api/v1/profile/me`
Update profile information.

**Request Body:**
```json
{
  "full_name": "John Smith",
  "email": "john.smith@example.com",
  "age": 46,
  "pain_level": 5,
  "mobility_level": "good",
  "has_support": false,
  "kinesiophobia": "moderate",
  "occupation_type": "light_manual",
  "has_stairs": false,
  "current_meds": ["acetaminophen"],
  "sleep_quality": "fair"
}
```

**Response:** `200 OK`
```json
{
  "user_id": 1,
  "email": "john.smith@example.com",
  "full_name": "John Smith",
  "updated_at": "2026-06-18T10:00:00"
}
```

**Notes:**
- All fields are optional
- Profile changes are logged to `PROFILE_LOG` table
- Email must be unique

---

### POST `/api/v1/profile/me/change-password`
Change user password.

**Request Body:**
```json
{
  "current_password": "OldPass123!@#",
  "new_password": "NewPass456!@#"
}
```

**Response:** `200 OK`
```json
{
  "message": "Password updated successfully"
}
```

---

### GET `/api/v1/profile/me/history`
Get profile change history for current user.

**Response:** `200 OK`
```json
[
  {
    "log_id": 1,
    "user_id": 1,
    "field_name": "pain_level",
    "old_value": "3",
    "new_value": "6",
    "changed_at": "2026-06-18T08:30:00"
  },
  {
    "log_id": 2,
    "user_id": 1,
    "field_name": "full_name",
    "old_value": "John Doe",
    "new_value": "John Smith",
    "changed_at": "2026-06-18T09:00:00"
  }
]
```

---

### GET `/api/v1/profile/patients/{id}/history`
Get patient's profile history (GP/Admin only).

**Path Parameters:**
- `id`: Patient user ID

**Response:** `200 OK`
```json
{
  "user_id": 1,
  "full_name": "John Doe",
  "history": [
    {
      "log_id": 1,
      "field_name": "pain_level",
      "old_value": "3",
      "new_value": "6",
      "changed_at": "2026-06-18T08:30:00"
    }
  ],
  "total_changes": 1
}
```

---

## 🎥 Video Library Endpoints

### GET `/api/v1/videos/`
List exercise videos with optional filters.

**Query Parameters:**
- `kl_grade_min` (optional): Minimum KL grade
- `kl_grade_max` (optional): Maximum KL grade
- `category` (optional): strengthening/flexibility/low-impact
- `difficulty` (optional): beginner/intermediate/advanced

**Response:** `200 OK`
```json
[
  {
    "video_id": 1,
    "title": "Gentle Knee Stretches",
    "description": "Low-impact stretching for KL Grade 1-2",
    "s3_url": "s3://bucket/videos/stretch.mp4",
    "thumbnail_url": "s3://bucket/thumbs/stretch.jpg",
    "kl_grade_min": 0,
    "kl_grade_max": 2,
    "category": "flexibility",
    "difficulty": "beginner",
    "duration_seconds": 300
  }
]
```

---

### GET `/api/v1/videos/{id}`
Get a specific video by ID.

**Response:** `200 OK`
```json
{
  "video_id": 1,
  "title": "Gentle Knee Stretches",
  "description": "Low-impact stretching for KL Grade 1-2",
  "s3_url": "s3://bucket/videos/stretch.mp4",
  "thumbnail_url": "s3://bucket/thumbs/stretch.jpg",
  "kl_grade_min": 0,
  "kl_grade_max": 2,
  "category": "flexibility",
  "difficulty": "beginner",
  "duration_seconds": 300
}
```

---

### POST `/api/v1/videos/` (Admin only)
Create a new video entry.

**Request Body:**
```json
{
  "title": "Quad Strengthening",
  "description": "Build knee strength with these exercises",
  "s3_url": "s3://bucket/videos/quad.mp4",
  "thumbnail_url": "s3://bucket/thumbs/quad.jpg",
  "kl_grade_min": 1,
  "kl_grade_max": 3,
  "category": "strengthening",
  "difficulty": "intermediate",
  "duration_seconds": 420
}
```

**Response:** `201 Created`
```json
{
  "video_id": 2,
  "title": "Quad Strengthening",
  ...
}
```

---

### PUT `/api/v1/videos/{id}` (Admin only)
Update a video entry.

**Request Body:** (same as POST)

**Response:** `200 OK`

---

### DELETE `/api/v1/videos/{id}` (Admin only)
Delete a video entry.

**Response:** `204 No Content`

---

## 📱 Mobile Sync Endpoints

### GET `/api/v1/mobile/sync/data`
Sync full user data (images, reports, history).

**Response:** `200 OK`
```json
{
  "user": {
    "user_id": 1,
    "email": "patient@example.com",
    "full_name": "John Doe",
    "role": "patient",
    "age": 45,
    "pain_level": 6,
    "mobility_level": "moderate",
    "has_support": true,
    "kinesiophobia": "low",
    "occupation_type": "sedentary",
    "has_stairs": true,
    "current_meds": ["ibuprofen"],
    "sleep_quality": "good",
    "created_at": "2026-01-15T10:00:00",
    "last_login": "2026-06-18T08:00:00"
  },
  "images": [
    {
      "image_id": 1,
      "s3_url": "s3://bucket/xrays/abc123.png",
      "file_name": "knee_xray.png",
      "content_type": "image/png",
      "uploaded_at": "2026-06-18T10:00:00"
    }
  ],
  "reports": [
    {
      "report_id": 1,
      "image_id": 1,
      "kl_grade": 2,
      "confidence": 0.87,
      "diagnosis_summary": "Grade 2 — Minimal OA",
      "recommendation": "Stay active with low-impact exercises",
      "lifestyle_plan": [...],
      "warnings": [...],
      "exercise_video_urls": [...],
      "created_at": "2026-06-18T10:00:00"
    }
  ],
  "history": [
    {
      "log_id": 1,
      "field_name": "pain_level",
      "old_value": "3",
      "new_value": "6",
      "changed_at": "2026-06-18T08:30:00"
    }
  ],
  "synced_at": "2026-06-18T10:00:00"
}
```

---

### GET `/api/v1/mobile/sync/summary`
Get sync summary (counts only, faster).

**Response:** `200 OK`
```json
{
  "user": {
    "user_id": 1,
    "email": "patient@example.com",
    "full_name": "John Doe",
    "role": "patient"
  },
  "image_count": 5,
  "report_count": 3,
  "history_count": 12,
  "synced_at": "2026-06-18T10:00:00"
}
```

---

### POST `/api/v1/mobile/sync/export`
Export user data to JSON file.

**Response:** `200 OK`
```json
{
  "message": "Export completed",
  "file_path": "/exports/user_1_20260618_100000.json",
  "file_size_bytes": 102400
}
```

---

## 📊 Admin Analytics Endpoints

### GET `/api/v1/admin/analytics/dashboard`
Get dashboard statistics (Admin only).

**Response:** `200 OK`
```json
{
  "total_users": 150,
  "total_images": 450,
  "total_reports": 420,
  "users_by_role": {
    "patient": 120,
    "gp": 25,
    "admin": 5
  },
  "kl_grade_distribution": {
    "0": 20,
    "1": 50,
    "2": 150,
    "3": 120,
    "4": 80
  },
  "recent_activity": [
    {
      "action": "diagnostic_report_created",
      "user_id": 1,
      "timestamp": "2026-06-18T09:00:00"
    }
  ]
}
```

---

## 🔧 System Endpoints

### GET `/`
Welcome message.

**Response:** `200 OK`
```json
{
  "message": "Welcome to Knee OA Backend API",
  "version": "1.0.0",
  "docs": "/docs"
}
```

---

### GET `/health`
Health check endpoint.

**Response:** `200 OK`
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "database": "connected",
  "s3": "connected",
  "ml_models": "loaded"
}
```

---

## 🔒 Role-Based Access Control (RBAC)

| Endpoint | Patient | GP | Admin |
|----------|---------|-----|-------|
| `POST /auth/register` | ✅ | ✅ | ✅ |
| `POST /auth/login` | ✅ | ✅ | ✅ |
| `POST /upload/` | ✅ | ✅ | ❌ |
| `POST /diagnostic/analyze` | ✅ (own) | ✅ (any) | ❌ |
| `GET /diagnostic/reports` | ✅ (own) | ✅ (own) | ❌ |
| `GET /recommendation/` | ✅ | ✅ | ❌ |
| `GET/PUT /profile/me` | ✅ | ✅ | ✅ |
| `POST /profile/me/change-password` | ✅ | ✅ | ✅ |
| `GET /profile/me/history` | ✅ | ✅ | ✅ |
| `GET /profile/patients/*/history` | ❌ | ✅ | ✅ |
| `GET /videos/` | ✅ | ✅ | ✅ |
| `POST/PUT/DELETE /videos/` | ❌ | ❌ | ✅ |
| `GET /mobile/sync/*` | ✅ | ✅ | ❌ |
| `GET /admin/analytics/*` | ❌ | ❌ | ✅ |

---

## 📝 Error Responses

### 400 Bad Request
```json
{
  "detail": "Email already in use"
}
```

### 401 Unauthorized
```json
{
  "detail": "Could not validate credentials"
}
```

### 403 Forbidden
```json
{
  "detail": "You do not have permission to access this resource"
}
```

### 404 Not Found
```json
{
  "detail": "Image not found"
}
```

### 422 Validation Error
```json
{
  "detail": [
    {
      "loc": ["body", "email"],
      "msg": "invalid email",
      "type": "value_error"
    }
  ]
}
```

---

**Last Updated**: June 18, 2026
