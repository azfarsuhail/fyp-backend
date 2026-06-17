# Documentation Index

## 📚 Project Documentation

### Core Documentation
- [README.md](../README.md) - Main project README
- [PROJECT_CONTEXT.md](../PROJECT_CONTEXT.md) - Detailed project context

### Architecture
- [architecture/STRUCTURE.md](architecture/STRUCTURE.md) - System structure and module layout
- [architecture/ADR-001-TensorFlow-XLA-ptxas-Fix.md](architecture/ADR-001-TensorFlow-XLA-ptxas-Fix.md) - Critical TensorFlow XLA compiler bug fix

### Agents & AI
- [agents/RECOMMENDATION_AGENT_UPDATE.md](agents/RECOMMENDATION_AGENT_UPDATE.md) - Recommendation agent architecture
- [agents/RAG_AGENT_PROFILE_FILTERING.md](agents/RAG_AGENT_PROFILE_FILTERING.md) - Clinical profile-based RAG filtering
- [agents/VALIDATION_AGENT.md](agents/VALIDATION_AGENT.md) - Gatekeeper validation agent guide
- [agents/VALIDATION_AGENT_IMPLEMENTATION.md](agents/VALIDATION_AGENT_IMPLEMENTATION.md) - Validation agent implementation summary

### Changelog
- [changelog/changelog_2026-04-21.md](changelog/changelog_2026-04-21.md) - API contract verification and diagnostic fix
- [changelog/changelog_2026-04-18.md](changelog/changelog_2026-04-18.md) - Clinical parameters and RAG filtering update
- [changelog/changelog_2026-06-02.md](changelog/changelog_2026-06-02.md) - S3 presigned URL migration
- [changelog/changelog_2026-06-16.md](changelog/changelog_2026-06-16.md) - Mobile sync and profile logging updates
- [changelog/DEPRECATION_FIXES_2026_04_17.md](changelog/DEPRECATION_FIXES_2026_04_17.md) - Deprecation and compatibility fixes

### Security
- [Security Overview](security/) - Security documentation

### Docker & Deployment
- [Docker Guide](docker/) - Docker configuration and deployment

### Mobile Integration
- [Mobile Sync Guide](mobile/) - Mobile app integration

### S3 Presigned URL Migration
- [Changelog: Presigned URL migration (2026-06-02)](changelog/changelog_2026-06-02.md) - Notes on replacing public S3 URLs with object keys + presigned URLs, IAM guidance, and test results.

### Git & Version Control
- [Git Guide](git/) - Git configuration and best practices

### Code Quality
- [Code Quality Report](code-quality/) - Code audit and quality metrics

---

## 📁 File Structure

```
docs/
├── README.md                      # This file
├── architecture/
│   └── STRUCTURE.md              # Architecture and structure notes
├── agents/
│   ├── RECOMMENDATION_AGENT_UPDATE.md
│   ├── RAG_AGENT_PROFILE_FILTERING.md
│   ├── VALIDATION_AGENT.md
│   └── VALIDATION_AGENT_IMPLEMENTATION.md
├── changelog/
│   ├── changelog_2026-04-18.md
│   ├── changelog_2026-04-21.md
│   └── DEPRECATION_FIXES_2026_04_17.md
├── security/
│   ├── SECURITY_AUDIT.md         # Security audit report
│   ├── SECURITY_FIXES.md         # Security fixes guide
│   └── SECURITY_APPLIED.md       # Applied security fixes
├── docker/
│   ├── DOCKER_AUDIT.md           # Docker configuration audit
│   └── DOCKER_QUICKREF.md        # Docker quick reference
├── frontend/
│   └── FRONTEND_CONTEXT.md       # Frontend integration context
├── mobile/
│   └── MOBILE_SYNC_GUIDE.md      # Mobile app integration guide
├── git/
│   └── GIT_GUIDE.md              # Git configuration guide
└── code-quality/
    └── CODE_QUALITY_REPORT.md    # Code quality audit report
```

---

## 🔗 Quick Links

- [Main README](../README.md)
- [Project Context](../PROJECT_CONTEXT.md)
- [Admin Dashboard](../admin-dashboard.html)
- [Admin Login](../admin-login.html)

---

## 📡 Complete API Endpoints

### Authentication
- `POST /api/v1/auth/register` - Register new user (Patient, GP only)
- `POST /api/v1/auth/login` - Login and receive JWT token (rate-limited)
- `POST /api/v1/auth/forgot-password` - Request password reset email
- `POST /api/v1/auth/reset-password` - Reset password with token

### Image Upload
- `POST /api/v1/upload/` - Upload knee X-ray (PNG/JPEG) with Gatekeeper validation

### Diagnostic
- `POST /api/v1/diagnostic/analyze` - Run full CNN + RAG pipeline on an image
- `GET /api/v1/diagnostic/reports` - List all reports for current user
- `GET /api/v1/diagnostic/reports/{id}` - Get a specific report

### Recommendation
- `GET /api/v1/recommendation/` - Get standalone recommendations by KL grade

### Profile
- `GET /api/v1/profile/me` - Get current user's profile
- `PUT /api/v1/profile/me` - Update profile (name, email, clinical parameters)
- `POST /api/v1/profile/me/change-password` - Change password
- `GET /api/v1/profile/me/history` - Get profile change history
- `GET /api/v1/profile/patients/{id}/history` - Get patient history (GP/Admin only)

### Video Library
- `GET /api/v1/videos/` - List videos (filter by KL grade, category)
- `GET /api/v1/videos/{id}` - Get a specific video
- `POST /api/v1/videos/` - Create video entry (Admin only)
- `PUT /api/v1/videos/{id}` - Update video entry (Admin only)
- `DELETE /api/v1/videos/{id}` - Delete video entry (Admin only)

### Mobile Sync
- `GET /api/v1/mobile/sync/data` - Sync full user data (images, reports, history)
- `GET /api/v1/mobile/sync/summary` - Get sync summary (counts only)
- `POST /api/v1/mobile/sync/export` - Export user data to JSON file

### Admin Analytics
- `GET /api/v1/admin/analytics/dashboard` - Dashboard statistics (Admin only)

### System
- `GET /` - Welcome message
- `GET /health` - Health check

---

**Last Updated**: June 18, 2026
