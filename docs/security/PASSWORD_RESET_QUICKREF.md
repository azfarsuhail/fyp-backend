# Password Reset - Quick Reference Card

## 📡 API Endpoints

### POST `/api/v1/auth/forgot-password`
**Request:**
```json
{"email": "user@example.com"}
```

**Response:**
```json
{"message": "If an account with that email address exists, a password reset link has been sent."}
```

---

### POST `/api/v1/auth/reset-password`
**Request:**
```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "new_password": "SecurePass123!"
}
```

**Response:**
```json
{"message": "Your password has been successfully reset. You can now log in with your new password."}
```

---

## 🔧 Environment Variables

```bash
RESEND_API_KEY=re_your_api_key_here
APP_URL=http://localhost:8000
RESET_TOKEN_EXPIRE_MINUTES=30
```

---

## 📦 Installation

```bash
pip install resend
```

---

## 🔒 Security Features

- ✅ Type-scoped JWT tokens (reset-only)
- ✅ 30-minute token expiry
- ✅ Email enumeration prevention
- ✅ Async email sending
- ✅ Password strength validation

---

## 🧪 Quick Test

```bash
# Request reset
curl -X POST http://localhost:8000/api/v1/auth/forgot-password \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com"}'

# Reset password (use token from email link)
curl -X POST http://localhost:8000/api/v1/auth/reset-password \
  -H "Content-Type: application/json" \
  -d '{"token":"<TOKEN>","new_password":"SecurePass123!"}'
```

---

## 📚 Full Docs

- **API Reference:** `docs/password-reset-flow.md`
- **Implementation Summary:** `docs/PASSWORD_RESET_IMPLEMENTATION.md`
- **Tests:** `tests/test_password_reset.py`

## 🔄 Refactoring Notes

- Email service moved from `app/utils/email.py` to `app/services/email.py`
- All imports updated to use `app.services.email`
- Tests updated to reflect new import paths
- All 10 tests passing ✅
