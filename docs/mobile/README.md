# Mobile App Integration Documentation

## 📱 Mobile Sync Overview

This folder contains documentation for integrating the Knee OA Backend with mobile applications.

## 📄 Files

### [MOBILE_SYNC_GUIDE.md](./MOBILE_SYNC_GUIDE.md)
Complete guide for mobile app integration including:
- API endpoints documentation
- Mobile database schema
- Implementation examples (Python, Android, iOS)
- Sync strategy recommendations
- Security considerations

## 🔄 Mobile Sync Feature

### What Gets Synced
- ✅ User profile (age, pain_level, mobility_level, has_support)
- ✅ User's uploaded X-ray images (metadata + S3 URLs)
- ✅ User's diagnostic reports (KL grades, recommendations)
- ✅ User's profile change history (audit trail)

### What Does NOT Get Synced
- ❌ Other users' data
- ❌ Exercise video library (downloaded separately if needed)
- ❌ System configurations

## 🔗 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/mobile/sync/data` | GET | Get all user-specific data |
| `/api/v1/mobile/sync/summary` | GET | Get data count summary |
| `/api/v1/mobile/sync/export` | POST | Export user data as JSON |
| `/api/v1/mobile/sync/status` | GET | Get sync status |

## 📊 Test Coverage

- ✅ 20 tests passing
- ✅ RBAC protection (patient/GP only)
- ✅ Service layer tested
- ✅ SQLite database creation tested
- ✅ JSON export tested

## 🚀 Quick Start

### 1. Get User Data
```python
import requests

response = requests.get(
    "https://api.knee-oa.com/api/v1/mobile/sync/data",
    headers={"Authorization": "Bearer YOUR_TOKEN"}
)

user_data = response.json()
```

### 2. Create Local Database
```python
from app.services.mobile_sync import MobileSyncService

service = MobileSyncService(db, user_id)
service.create_mobile_db("/path/to/local.db")
```

## 📱 Mobile Database Schema

### Tables
- `user_profile` - User's personal information
- `images` - X-ray image metadata
- `reports` - Diagnostic reports with KL grades
- `profile_history` - Audit trail of profile changes

## 🔒 Security

- ✅ All endpoints require Bearer token
- ✅ Token expires after 15 minutes
- ✅ Only user's own data is synced
- ✅ No other users' data accessible
- ✅ S3 URLs are private (use presigned URLs)

---

**Last Updated**: March 30, 2026
