# Knee OA Backend - Project Context

## Tech Stack
- FastAPI (Python 3.10), Neon DB (Serverless PostgreSQL), SQLAlchemy + Alembic
- JWT Auth with RBAC (Patient, GP, Admin)
- TensorFlow-CPU for CNN inference, Sentence-Transformers for RAG
- Docker & Docker Compose, AWS S3

## Completed Files
- `app/main.py` - FastAPI app with auth router
- `app/api/v1/auth.py` - Register + Login endpoints
- `app/core/config.py` - SQLAlchemy engine/session/Base (Neon DB)
- `app/core/dependencies.py` - DB session, JWT auth, RBAC (RoleChecker)
- `app/core/security.py` - Password hashing (bcrypt), JWT creation
- `app/models/user.py` - User model (user_id, email, password_hash, full_name, role, created_at, last_login)
- `app/schemas/user_schema.py` - UserCreate, UserOut, Token
- `requirements.txt`, `Dockerfile`, `docker-compose.yml`

## NOW IMPLEMENTED (Session 2)
- `app/models/image.py` - Image table (image_id, user_id FK, s3_url, processed_s3_url, file_name, content_type, uploaded_at)
- `app/models/report.py` - Report table (report_id, image_id FK, user_id FK, kl_grade, confidence, diagnosis_summary, recommendation, exercise_video_urls JSON, created_at)
- `app/models/library.py` - ExerciseVideo table (video_id, title, description, s3_url, thumbnail_url, kl_grade_min/max, category, difficulty, duration_seconds)
- `app/schemas/image_schema.py` - ImageUploadResponse, ImageOut
- `app/schemas/report_schema.py` - DiagnosticRequest, DiagnosticResult, RecommendationResult, ReportOut
- `app/schemas/profile_schema.py` - ProfileUpdate, ProfileOut, PasswordChange
- `app/services/s3_service.py` - upload_file_to_s3, upload_bytes_to_s3, generate_presigned_url
- `app/services/image_processor.py` - Full pipeline: grayscale → ROI → resize 256x256 → CLAHE → normalize → (1,256,256,1)
- `app/agents/diagnostic_agent.py` - Singleton CNN loader, predict_kl_grade(bytes) → (grade, confidence, summary)
- `app/agents/recommendation_agent.py` - RAG with sentence-transformers, fallback knowledge base, cosine similarity retrieval, KL-grade boosting
- `app/api/v1/upload.py` - POST / (upload X-ray to S3 + DB)
- `app/api/v1/diagnostic.py` - POST /analyze, GET /reports, GET /reports/{id}
- `app/api/v1/recommendation.py` - GET / (standalone recommendation by KL grade)
- `app/api/v1/profile.py` - GET/PUT /me, POST /me/change-password
- `app/api/v1/video.py` - Full CRUD for exercise video library (admin manage, patient browse)
- `app/main.py` - All 6 routers registered + CORS + /health endpoint
- `alembic/env.py` - Configured with all models, loads DATABASE_URL from .env
- `alembic/script.py.mako` - Migration template
- `requirements.txt` - Added requests>=2.31.0, bcrypt==4.0.1 pin, pytest, httpx

## Tests (Session 2)
- `tests/conftest.py` - In-memory SQLite, DB override, fixtures for patient/gp/admin, seed_image, seed_report, seed_video
- `tests/test_health.py` - Root + /health (2 tests)
- `tests/test_auth.py` - Register + Login (11 tests)
- `tests/test_upload.py` - Upload X-ray with S3 mocking (7 tests)
- `tests/test_diagnostic.py` - Analyze + Reports with CNN/RAG mocking (9 tests)
- `tests/test_recommendation.py` - Standalone recommendation (8 tests)
- `tests/test_profile.py` - Profile CRUD + password change (11 tests)
- `tests/test_video.py` - Video library CRUD + RBAC (11 tests)
- **Total: 59 tests, ALL PASSING**
- Note: bcrypt must be pinned to 4.0.1 (newer versions break passlib)

## CNN Model
- Located at `app/ml_assets/cnn_weights/CNN.keras`
- Predicts Kellgren-Lawrence (KL) severity grade (0-4) from knee X-rays
- Input: 256x256 grayscale images

## Architecture
- Decoupled Multi-Agent: Diagnostic Agent (CNN) + Recommendation Agent (RAG)
- RAG uses sentence-transformers embeddings + vector store
