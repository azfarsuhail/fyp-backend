# Architecture Documentation

## 📋 Architecture Decision Records (ADRs)

Architecture Decision Records document critical technical decisions, their rationale, and constraints for future developers.

| ADR | Title | Status | Date |
|-----|-------|--------|------|
| [ADR-001](ADR-001-TensorFlow-XLA-ptxas-Fix.md) | TensorFlow XLA ptxas Compiler Bug Fix | ✅ Accepted | 2026-06-16 |

---

## 🗂️ Documentation Structure

```
docs/architecture/
├── STRUCTURE.md              # System structure and module layout
└── ADR-001-TensorFlow-XLA-ptxas-Fix.md  # Critical bug fix documentation
```

---

## 📚 Related Documentation

- [Main Documentation Index](../README.md) - Complete documentation navigation
- [Docker Guide](../docker/) - Docker configuration and deployment
- [Security Guide](../security/) - Security documentation and audits
- **DOCKER_AUDIT.md** - Complete Docker configuration audit with fixes
- **DOCKER_QUICKREF.md** - Quick reference for Docker commands and best practices
- **Status**: ✅ Production-ready Docker configuration

### 📱 Mobile Documentation (`docs/mobile/`)
- **MOBILE_SYNC_GUIDE.md** - Complete mobile app integration guide
- **Status**: ✅ 20 tests passing, full mobile sync implementation

### 📦 Git Documentation (`docs/git/`)
- **GIT_GUIDE.md** - Git configuration, best practices, and security checklist
- **Status**: ✅ Comprehensive Git workflow documented

### 📊 Code Quality Documentation (`docs/code-quality/`)
- **CODE_QUALITY_REPORT.md** - Code quality audit with recommendations
- **Status**: ✅ A- grade (90/100), all tests passing

## 🎯 Quick Navigation

### For Developers
- Start here: [docs/README.md](./README.md)
- Git workflow: [docs/git/GIT_GUIDE.md](./git/GIT_GUIDE.md)
- Code quality: [docs/code-quality/CODE_QUALITY_REPORT.md](./code-quality/CODE_QUALITY_REPORT.md)

### For Security
- Security audit: [docs/security/SECURITY_AUDIT.md](./security/SECURITY_AUDIT.md)
- Security fixes: [docs/security/SECURITY_FIXES.md](./security/SECURITY_FIXES.md)

### For Deployment
- Docker guide: [docs/docker/DOCKER_QUICKREF.md](./docker/DOCKER_QUICKREF.md)
- Docker audit: [docs/docker/DOCKER_AUDIT.md](./docker/DOCKER_AUDIT.md)

### For Mobile Integration
- Mobile guide: [docs/mobile/MOBILE_SYNC_GUIDE.md](./mobile/MOBILE_SYNC_GUIDE.md)

## 📊 Project Status Summary

| Category | Status | Details |
|----------|--------|---------|
| **Tests** | ✅ 105/105 Passing | 100% test coverage |
| **Security** | ✅ Hardened | All critical issues resolved |
| **Docker** | ✅ Production Ready | Multi-stage build, health checks |
| **Mobile** | ✅ Implemented | 20 tests passing |
| **Code Quality** | ✅ A- (90/100) | Best practices followed |
| **Documentation** | ✅ Organized | All docs in structured folders |

## 🚀 Next Steps

### Immediate
- [x] Organize all documentation
- [x] Create documentation index
- [x] Add navigation to all README files

### Recent Changes
- [x] 2026-05-31: Added `GET /api/v1/profile/patients/{patient_id}/history` (GP/Admin) — audit trail access for clinicians

See full changelogs in: [docs/changelog/changelog_2026-05-31.md](./changelog/changelog_2026-05-31.md)

### Short-term
- [ ] Add API documentation (Swagger/OpenAPI)
- [ ] Add deployment guides for cloud providers
- [ ] Add monitoring and logging documentation

### Long-term
- [ ] Add user guides for mobile app
- [ ] Add admin dashboard documentation
- [ ] Add troubleshooting guides

---
**Last Updated**: May 31, 2026  
**Documentation Status**: ✅ Complete and Organized
