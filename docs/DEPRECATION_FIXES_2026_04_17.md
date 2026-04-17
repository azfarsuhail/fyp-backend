# Deprecation Fixes - April 17, 2026

## Overview
Fixed Python 3.12+ deprecation warnings to ensure compatibility with future Python versions and pass all tests with `-W error` flag.

## Issues Resolved

### 1. Pydantic V2 Config Deprecation
**Issue**: Class-based `Config` attribute is deprecated in Pydantic V2.0 (to be removed in V3.0)

**Error Message**:
```
pydantic.warnings.PydanticDeprecatedSince20: Support for class-based `config` is deprecated, use ConfigDict instead.
```

**Solution**: Replaced all `class Config:` blocks with `model_config = ConfigDict(...)`

**Files Updated**:
- `app/schemas/user_schema.py` - `UserOut` class
- `app/schemas/profile_schema.py` - `ProfileOut`, `ProfileLogOut` classes
- `app/schemas/image_schema.py` - `ImageUploadResponse`, `ImageOut` classes
- `app/schemas/report_schema.py` - `ReportOut` class
- `app/api/v1/video.py` - `VideoOut` class

**Migration Pattern**:
```python
# Before (deprecated)
class MyModel(BaseModel):
    field: str
    
    class Config:
        from_attributes = True

# After (current)
from pydantic import ConfigDict

class MyModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    field: str
```

---

### 2. datetime.utcnow() Deprecation
**Issue**: `datetime.utcnow()` is deprecated in Python 3.12+ and scheduled for removal

**Error Message**:
```
DeprecationWarning: datetime.datetime.utcnow() is deprecated and scheduled for removal in a future version. 
Use timezone-aware objects to represent datetimes in UTC: datetime.datetime.now(datetime.UTC).
```

**Solution**: Replaced all `datetime.utcnow()` with `datetime.now(timezone.utc)`

**Files Updated**:

#### Application Code (15+ occurrences):
- `app/core/security.py` - Token expiration calculation (2 occurrences)
- `app/core/security_middleware.py` - Rate limiter timestamps (2 occurrences)
- `app/api/v1/auth.py` - Last login timestamp
- `app/api/v1/admin_analytics.py` - Analytics date calculations (9 occurrences)
- `app/services/mobile_sync.py` - Sync timestamp

#### SQLAlchemy Models (4 occurrences):
- `app/models/user.py` - `created_at` default function
- `app/models/image.py` - `uploaded_at` default function
- `app/models/report.py` - `created_at` default function
- `app/models/profile_log.py` - `changed_at` default function

**Migration Pattern**:

For direct calls:
```python
# Before (deprecated)
from datetime import datetime
now = datetime.utcnow()

# After (current)
from datetime import datetime, timezone
now = datetime.now(timezone.utc)
```

For SQLAlchemy column defaults:
```python
# Before (deprecated)
from sqlalchemy import Column, DateTime
from datetime import datetime

created_at = Column(DateTime, default=datetime.utcnow)

# After (current)
from datetime import datetime, timezone

created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
```

---

## Testing Results

**Command**: `pytest -W error`

**Result**: ✅ All 105 tests passing

```
tests/test_auth.py ...........                                                                                 [ 10%]
tests/test_diagnostic.py ............                                                                          [ 21%]
tests/test_health.py ..                                                                                        [ 23%]
tests/test_mobile_sync.py ....................                                                                 [ 42%]
tests/test_profile.py ............................                                                             [ 69%]
tests/test_recommendation.py ........                                                                          [ 77%]
tests/test_upload.py .......                                                                                   [ 83%]
tests/test_video.py .................                                                                          [100%]

105 passed in 25.28s
```

---

## Impact

- ✅ No breaking changes to API or functionality
- ✅ All existing tests pass without modification
- ✅ Compatible with Python 3.12+ and future versions
- ✅ Pydantic V2 best practices followed
- ✅ Timezone-aware datetimes improve reliability across timezones

---

## References

- [Pydantic V2 Migration Guide](https://docs.pydantic.dev/2.12/migration/)
- [Python 3.12 Deprecations](https://docs.python.org/3/whatsnew/3.12.html#deprecations)
- [datetime.utcnow() Deprecation](https://docs.python.org/3/library/datetime.html#datetime.datetime.utcnow)

---

**Date**: April 17, 2026  
**Status**: ✅ Complete  
**Test Coverage**: 105/105 tests passing
