# Knee OA Backend - Project Context

## Tech Stack
- **Framework**: FastAPI (Python 3.10), uvicorn
- **Database**: Neon DB (Serverless PostgreSQL), SQLAlchemy 2.0, Alembic migrations
- **Authentication**: JWT with OAuth2PasswordBearer, bcrypt password hashing (passlib)
- **RBAC**: Role-based access control (Patient, GP, Admin)
- **ML/AI**: TensorFlow-CPU (CNN inference), Sentence-Transformers (RAG embeddings)
- **Cloud**: AWS S3 (image/video storage via boto3)
- **DevOps**: Docker, Docker Compose
- **Testing**: pytest, httpx

## Project Overview
Medical Image Analysis API for Knee Osteoarthritis Detection and Management. The system uses a decoupled multi-agent architecture with a CNN-based Diagnostic Agent for KL grade prediction and a parametric RAG Recommendation Agent for evidence-based lifestyle advice.

## API Endpoints

### Authentication (`/api/v1/auth`)
- `POST /register` - User registration (Patient, GP, Admin)
- `POST /login` - JWT token generation

### Image Upload (`/api/v1/upload`)
- `POST /` - Upload X-ray to S3 + DB metadata (Patient/GP only)

### Diagnostic Pipeline (`/api/v1/diagnostic`)
- `POST /analyze` - Full pipeline: CNN inference + RAG recommendations + DB persistence
- `GET /reports` - List user reports
- `GET /reports/{id}` - Get specific report

### Recommendation (`/api/v1/recommendation`)
- `GET /` - Standalone parametric recommendations by KL grade (+ pain/mobility params)

### Profile Management (`/api/v1/profile`)
- `GET /me` - Get current user profile
- `PUT /me` - Update profile (name, email, age, pain_level, mobility_level, has_support) - **logs all changes**
- `GET /me/history` - Get profile change history (audit trail)
- `POST /me/change-password` - Change password

### Video Library (`/api/v1/videos`)
- `GET /` - Browse exercise videos (filter by KL grade, category)
- `GET /{id}` - Get specific video
- `POST /` - Create video (Admin only)
- `PUT /{id}` - Update video (Admin only)
- `DELETE /{id}` - Delete video (Admin only)

## Database Models

### User (`USER` table)
- `user_id`, `email` (unique), `password_hash`, `full_name`, `role` (patient/gp/admin)
- Patient context: `age`, `pain_level` (0-10), `mobility_level` (limited/moderate/good), `has_support`
- Timestamps: `created_at`, `last_login`
- Relationship: `profile_logs` (one-to-many with ProfileLog)

### ProfileLog (`PROFILE_LOG` table)
- `log_id`, `user_id` (FK), `field_name`, `old_value`, `new_value`, `changed_at`
- Audit trail for all profile field changes
- Indexed by `user_id` and `changed_at`

### Image (`IMAGE` table)
- `image_id`, `user_id` (FK), `s3_url`, `processed_s3_url`, `file_name`, `content_type`, `uploaded_at`

### Report (`REPORT` table)
- `report_id`, `image_id` (FK), `user_id` (FK)
- Diagnostic: `kl_grade` (0-4), `confidence` (float), `diagnosis_summary` (text)
- Recommendation: `recommendation` (text), `lifestyle_plan` (JSON), `warnings` (JSON), `exercise_video_urls` (JSON)
- Timestamp: `created_at`

### ExerciseVideo (`EXERCISE_VIDEO` table)
- `video_id`, `title`, `description`, `s3_url`, `thumbnail_url`
- `kl_grade_min`, `kl_grade_max` (range filter)
- `category` (strengthening/flexibility/low-impact), `difficulty` (beginner/intermediate/advanced), `duration_seconds`

## Core Services

### S3 Service (`app/services/s3_service.py`)
- `upload_file_to_s3(file, folder)` - Upload UploadFile to S3
- `upload_bytes_to_s3(data, key, content_type)` - Upload raw bytes
- `generate_presigned_url(key, expiration)` - Generate temporary access URL

### Image Processor (`app/services/image_processor.py`)
Pipeline: Load → Grayscale → ROI center-crop → Resize 256×256 → Autocontrast → Normalize → (1,256,256,1)

### Diagnostic Agent (`app/agents/diagnostic_agent.py`)
- Singleton CNN loader from `app/ml_assets/cnn_weights/CNN.keras`
- `predict_kl_grade(image_bytes)` → `(kl_grade: int, confidence: float, summary: str)`
- KL Labels: 0=None, 1=Doubtful, 2=Minimal, 3=Moderate, 4=Severe

### Recommendation Agent (`app/agents/recommendation_agent.py`)
- **Parametric RAG** (hallucination-free): Structured parameter table with embeddings
- Fields: `id`, `category`, `action`, `frequency`, `duration_min`, `intensity`, `kl_grade_min/max`, `pain_threshold`, `mobility_req`, `contraindications`, `evidence_level`, `source`
- Retrieval: sentence-transformers (all-MiniLM-L6-v2) + cosine similarity
- Output: List of typed JSON objects (not free-text)

## Authentication & RBAC

### JWT Flow
1. POST `/api/v1/auth/login` with username/email + password
2. Returns `{access_token, token_type: "bearer"}`
3. Include in Authorization header: `Bearer <token>`

### Registration Rules
- **Public registration**: Patient and GP roles only
- **Admin registration**: Disabled - admins must be created manually
- **Default admin account**: `admin` / `admin` (created via `scripts/init_admin.py`)

### Role Guards
- `allow_upload`: patient, gp
- `allow_diagnose`: patient, gp
- `allow_access`: patient, gp (recommendations)
- `allow_browse`: patient, gp, admin (video library)
- `allow_manage`: admin only (video CRUD)

## Testing

### Test Suite (75 tests, ALL PASSING)
- `tests/conftest.py` - In-memory SQLite, DB override, fixtures (patient/gp/admin, seed_image, seed_report, seed_video)
- `tests/test_health.py` - Root + /health (2 tests)
- `tests/test_auth.py` - Register + Login (12 tests) - **includes admin registration prevention**
- `tests/test_upload.py` - X-ray upload with S3 mocking (7 tests)
- `tests/test_diagnostic.py` - Analyze + Reports with CNN/RAG mocking (9 tests)
- `tests/test_recommendation.py` - Standalone recommendation (8 tests)
- `tests/test_profile.py` - Profile CRUD + password change + **logging & history** (26 tests)
- `tests/test_video.py` - Video library CRUD + RBAC (11 tests)

### Profile Logging Tests (15 new tests)
- `TestProfileHistory` - GET /me/history endpoint (4 tests)
- `TestProfileLogging` - Audit trail functionality (11 tests)
  - Logs for: full_name, email, age, pain_level, mobility_level, has_support
  - No duplicate logs for same value
  - Multiple fields in single request

## Admin Initialization

### Default Admin Account
- **Email/Username**: `admin`
- **Password**: `admin`
- **Created by**: `scripts/init_admin.py`

### Setup Instructions
1. Run database migrations: `alembic upgrade head`
2. Initialize admin: `python scripts/init_admin.py`
3. Login with `admin` / `admin`
4. **Change password immediately** after first login

### Security Notes
- Public registration for admin role is **disabled**
- Only manually created admin accounts can have admin role
- Default credentials should be changed in production

## Running Tests
```bash
pytest -v
```

## ML Assets

### CNN Model
- Path: `app/ml_assets/cnn_weights/CNN.keras`
- Input: 256×256 grayscale images (preprocessed)
- Output: 5-class softmax → KL grade 0-4

### Vector Store
- Path: `app/ml_assets/vector_store/`
- Files: `parametric_embeddings.npy`, `parametric_knowledge.json`
- Model: all-MiniLM-L6-v2 (sentence-transformers)

## Docker & Deployment

### Dockerfile
- Base: `python:3.10-slim`
- Installs: gcc, libpq-dev, pip dependencies
- CMD: `uvicorn app.main:app --host 0.0.0.0 --port 8000`

### Docker Compose (Dev)
- Mounts local code for hot-reload
- Overrides CMD with `--reload` flag
- Exposes port 8000

### Environment Variables (.env)
- `DATABASE_URL` - Neon PostgreSQL connection string (sslmode=require)
- `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` - S3 credentials
- `AWS_REGION` - Default: eu-west-1
- `S3_BUCKET_NAME` - Default: knee-oa-uploads
- `SECRET_KEY` - JWT signing key

## Requirements Notes
- `bcrypt==4.0.1` - Pinned (newer versions break passlib)
- `tensorflow-cpu>=2.15.0` - CPU version for smaller Docker image
- `sentence-transformers>=2.3.0` - For RAG embeddings
- `pytest>=8.0.0`, `httpx>=0.27.0` - Testing

## Architecture Diagram
```
┌─────────────┐     ┌──────────────────┐     ┌─────────────┐
│   Client    │────▶│   FastAPI App    │────▶│  Neon DB    │
│ (Mobile/Web)│     │  (FastAPI + CORS)│     │ (PostgreSQL)│
└─────────────┘     └──────────────────┘     └─────────────┘
                           │
           ┌───────────────┼───────────────┐
           ▼               ▼               ▼
    ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
    │  S3 Bucket  │  │  CNN Agent  │  │  RAG Agent  │
    │ (Images/    │  │ (KL Grade   │  │ (Parametric │
    │  Videos)    │  │  Prediction)│  │  Advice)    │
    └─────────────┘  └─────────────┘  └─────────────┘
```

## Current Status
- ✅ All core endpoints implemented and tested
- ✅ Multi-agent architecture (CNN + RAG)
- ✅ RBAC enforcement across all routes
- ✅ Docker setup for local development
- ✅ 59 passing tests covering all functionality
- ⏳ Production deployment (AWS ECS/EKS or Azure Container Apps)
- ⏳ Frontend mobile/web app integration
