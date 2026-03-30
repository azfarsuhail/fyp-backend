# Mobile App Integration Guide

## Overview

This guide explains how to integrate the Knee OA Backend with your mobile application. The backend provides endpoints to sync only the authenticated user's data to their device.

## Architecture

```
┌─────────────────┐
│   Mobile App    │
│   (SQLite)      │
└────────┬────────┘
         │
         │ HTTPS API Calls
         ▼
┌─────────────────┐
│  FastAPI Backend│
│  /api/v1/mobile │
└────────┬────────┘
         │
         │ SELECT WHERE user_id = ?
         ▼
┌─────────────────┐
│  Neon PostgreSQL│
│  (Cloud DB)     │
└─────────────────┘
```

## Sync Strategy

### What Gets Synced
- ✅ User profile (age, pain_level, mobility_level, has_support)
- ✅ User's uploaded X-ray images (metadata + S3 URLs)
- ✅ User's diagnostic reports (KL grades, recommendations)
- ✅ User's profile change history (audit trail)

### What Does NOT Get Synced
- ❌ Other users' data
- ❌ Exercise video library (downloaded separately if needed)
- ❌ System configurations
- ❌ Global settings

## API Endpoints

### 1. Get User Data (Full Sync)

**Endpoint**: `GET /api/v1/mobile/sync/data`

**Authentication**: Required (Bearer token)

**Response**:
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
    "created_at": "2026-01-15T10:30:00",
    "last_login": "2026-03-30T08:00:00"
  },
  "images": [
    {
      "image_id": 1,
      "s3_url": "https://s3.amazonaws.com/bucket/xray1.png",
      "processed_s3_url": "https://s3.amazonaws.com/bucket/processed1.png",
      "file_name": "knee_xray_20260330.png",
      "content_type": "image/png",
      "uploaded_at": "2026-03-30T09:00:00"
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
      "created_at": "2026-03-30T09:30:00"
    }
  ],
  "history": [
    {
      "log_id": 1,
      "field_name": "pain_level",
      "old_value": "3",
      "new_value": "6",
      "changed_at": "2026-03-30T08:30:00"
    }
  ],
  "synced_at": "2026-03-30T10:00:00"
}
```

**Usage** (Python/Android/iOS):
```python
# Python example
import requests

response = requests.get(
    "https://api.knee-oa.com/api/v1/mobile/sync/data",
    headers={"Authorization": "Bearer YOUR_TOKEN"}
)
user_data = response.json()
```

---

### 2. Get Sync Summary

**Endpoint**: `GET /api/v1/mobile/sync/summary`

**Purpose**: Check how much data will be synced (for progress indicators)

**Response**:
```json
{
  "user_id": 1,
  "images_count": 5,
  "reports_count": 3,
  "history_count": 12,
  "total_records": 20
}
```

---

### 3. Export User Data (JSON Download)

**Endpoint**: `POST /api/v1/mobile/sync/export`

**Purpose**: Download complete user data as JSON file

**Response**: JSON file with `Content-Disposition: attachment` header

**Usage**:
```python
response = requests.post(
    "https://api.knee-oa.com/api/v1/mobile/sync/export",
    headers={"Authorization": "Bearer YOUR_TOKEN"}
)

# Save to file
with open("user_data.json", "wb") as f:
    f.write(response.content)
```

---

### 4. Get Sync Status

**Endpoint**: `GET /api/v1/mobile/sync/status`

**Purpose**: Check sync status and data availability

**Response**:
```json
{
  "user_id": 1,
  "images_count": 5,
  "reports_count": 3,
  "history_count": 12,
  "total_records": 20,
  "last_sync": null,
  "available": true
}
```

---

## Mobile Database Schema

The backend provides data in JSON format. Your mobile app should create a local SQLite database with this schema:

### Tables

#### `user_profile`
```sql
CREATE TABLE user_profile (
    user_id INTEGER PRIMARY KEY,
    email TEXT,
    full_name TEXT,
    role TEXT,
    age INTEGER,
    pain_level INTEGER,
    mobility_level TEXT,
    has_support INTEGER,
    created_at TEXT,
    last_login TEXT
);
```

#### `images`
```sql
CREATE TABLE images (
    image_id INTEGER PRIMARY KEY,
    s3_url TEXT,
    processed_s3_url TEXT,
    file_name TEXT,
    content_type TEXT,
    uploaded_at TEXT
);
```

#### `reports`
```sql
CREATE TABLE reports (
    report_id INTEGER PRIMARY KEY,
    image_id INTEGER,
    kl_grade INTEGER,
    confidence REAL,
    diagnosis_summary TEXT,
    recommendation TEXT,
    lifestyle_plan TEXT,      -- JSON
    warnings TEXT,            -- JSON
    exercise_video_urls TEXT, -- JSON
    created_at TEXT
);
```

#### `profile_history`
```sql
CREATE TABLE profile_history (
    log_id INTEGER PRIMARY KEY,
    field_name TEXT,
    old_value TEXT,
    new_value TEXT,
    changed_at TEXT
);
```

---

## Implementation Examples

### Python (Mobile Backend)

```python
import sqlite3
import json
import requests
from datetime import datetime

class MobileSyncClient:
    def __init__(self, base_url: str, token: str):
        self.base_url = base_url
        self.token = token
        self.headers = {"Authorization": f"Bearer {token}"}
    
    def sync_all(self, db_path: str):
        """Sync all user data to local SQLite database."""
        
        # Get user data
        response = requests.get(
            f"{self.base_url}/api/v1/mobile/sync/data",
            headers=self.headers
        )
        response.raise_for_status()
        user_data = response.json()
        
        # Create local database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Create tables (see schema above)
        self._create_tables(cursor)
        
        # Insert data
        self._insert_user_profile(cursor, user_data['user'])
        self._insert_images(cursor, user_data['images'])
        self._insert_reports(cursor, user_data['reports'])
        self._insert_history(cursor, user_data['history'])
        
        conn.commit()
        conn.close()
        
        print(f"Synced {user_data['synced_at']}")
    
    def _create_tables(self, cursor):
        # Execute CREATE TABLE statements from schema above
        pass
    
    def _insert_user_profile(self, cursor, user):
        cursor.execute('''
            INSERT OR REPLACE INTO user_profile 
            (user_id, email, full_name, role, age, pain_level, mobility_level, has_support, created_at, last_login)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            user['user_id'], user['email'], user['full_name'], user['role'],
            user['age'], user['pain_level'], user['mobility_level'],
            user['has_support'], user['created_at'], user['last_login']
        ))
    
    def _insert_images(self, cursor, images):
        for img in images:
            cursor.execute('''
                INSERT OR REPLACE INTO images 
                (image_id, s3_url, processed_s3_url, file_name, content_type, uploaded_at)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                img['image_id'], img['s3_url'], img['processed_s3_url'],
                img['file_name'], img['content_type'], img['uploaded_at']
            ))
    
    def _insert_reports(self, cursor, reports):
        for rpt in reports:
            cursor.execute('''
                INSERT OR REPLACE INTO reports 
                (report_id, image_id, kl_grade, confidence, diagnosis_summary, 
                 recommendation, lifestyle_plan, warnings, exercise_video_urls, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                rpt['report_id'], rpt['image_id'], rpt['kl_grade'], rpt['confidence'],
                rpt['diagnosis_summary'], rpt['recommendation'],
                json.dumps(rpt['lifestyle_plan']), json.dumps(rpt['warnings']),
                json.dumps(rpt['exercise_video_urls']), rpt['created_at']
            ))
    
    def _insert_history(self, cursor, history):
        for log in history:
            cursor.execute('''
                INSERT OR REPLACE INTO profile_history 
                (log_id, field_name, old_value, new_value, changed_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                log['log_id'], log['field_name'], log['old_value'],
                log['new_value'], log['changed_at']
            ))

# Usage
client = MobileSyncClient(
    base_url="https://api.knee-oa.com",
    token="your_jwt_token"
)
client.sync_all("/path/to/local.db")
```

---

### Android (Kotlin)

```kotlin
class MobileSyncClient(
    private val baseUrl: String,
    private val token: String
) {
    private val client = OkHttpClient()
    private val json = Json { ignoreUnknownKeys = true }
    
    fun syncAll(dbPath: String) {
        val response = client.newCall(
            Request.Builder()
                .url("$baseUrl/api/v1/mobile/sync/data")
                .header("Authorization", "Bearer $token")
                .build()
        ).execute()
        
        val userData = response.body!!.string()
            .jsonObject
            .decodeFromJsonString<UserData>()
        
        // Create local SQLite database
        val db = SQLiteDatabase.openDatabase(dbPath, null, SQLiteDatabase.OPEN_CREATE)
        
        // Create tables and insert data
        createTables(db)
        insertUserData(db, userData)
        
        db.close()
    }
    
    private fun createTables(db: SQLiteDatabase) {
        // Execute CREATE TABLE statements
    }
    
    private fun insertUserData(db: SQLiteDatabase, data: UserData) {
        // Insert user profile, images, reports, history
    }
}

data class UserData(
    val user: User,
    val images: List<Image>,
    val reports: List<Report>,
    val history: List<History>,
    val syncedAt: String
)
```

---

### iOS (Swift)

```swift
class MobileSyncClient {
    private let baseUrl: String
    private let token: String
    private let session = URLSession.shared
    
    func syncAll(dbPath: String) async throws {
        var request = URLRequest(url: URL(string: "\(baseUrl)/api/v1/mobile/sync/data")!)
        request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        
        let (data, _) = try await session.data(for: request)
        let userData = try JSONDecoder().decode(UserData.self, from: data)
        
        // Create local SQLite database using SQLite.swift or similar
        let db = try Connection(dbPath)
        
        // Create tables and insert data
        try db.run(createTablesQuery)
        try insertUserData(db, userData)
    }
}

struct UserData: Decodable {
    let user: User
    let images: [Image]
    let reports: [Report]
    let history: [History]
    let syncedAt: String
}
```

---

## Sync Strategy Recommendations

### 1. Initial Sync
- Trigger on first login
- Download all user data
- Store in local SQLite database

### 2. Incremental Sync
- Check for updates every 24 hours or on demand
- Compare `synced_at` timestamp
- Only download changed records

### 3. Offline Mode
- All read operations use local SQLite
- Write operations queue locally
- Sync changes when online

### 4. Conflict Resolution
- Server data is authoritative
- Mobile app updates on each sync
- Keep local history for audit trail

---

## Security Considerations

### Authentication
- ✅ All endpoints require Bearer token
- ✅ Token expires after 15 minutes
- ✅ Refresh token recommended for mobile apps

### Data Privacy
- ✅ Only user's own data is synced
- ✅ No other users' data accessible
- ✅ S3 URLs are private (use presigned URLs)

### Best Practices
- ✅ Use HTTPS only
- ✅ Store tokens securely (Keychain/Keystore)
- ✅ Encrypt local SQLite database (optional)
- ✅ Implement token refresh logic

---

## Error Handling

### Common Errors

| Status | Error | Solution |
|--------|-------|----------|
| 401 | Unauthorized | Token expired, refresh or re-login |
| 404 | User not found | User doesn't exist |
| 500 | Server error | Retry after a few seconds |

### Retry Logic
```python
import time
from requests.exceptions import RequestException

def sync_with_retry(client, max_retries=3):
    for attempt in range(max_retries):
        try:
            client.sync_all("/path/to/local.db")
            return True
        except RequestException as e:
            if attempt == max_retries - 1:
                raise
            time.sleep(2 ** attempt)  # Exponential backoff
```

---

## Testing

### Test the Sync Endpoint

```bash
# Get token first
TOKEN=$(curl -X POST https://api.knee-oa.com/api/v1/auth/login \
  -d "username=patient@test.com&password=SecurePass123!@#" \
  | jq -r '.access_token')

# Sync data
curl -H "Authorization: Bearer $TOKEN" \
  https://api.knee-oa.com/api/v1/mobile/sync/data \
  | jq .
```

---

## Next Steps

1. **Implement in Mobile App**: Use the examples above
2. **Add Offline Support**: Queue write operations
3. **Implement Conflict Resolution**: Handle concurrent updates
4. **Add Encryption**: Encrypt local SQLite database
5. **Add Analytics**: Track sync success/failure rates

---

**Last Updated**: March 30, 2026  
**Version**: 1.0
