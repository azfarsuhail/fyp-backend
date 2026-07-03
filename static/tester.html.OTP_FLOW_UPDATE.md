# OTP Password Reset Flow Update

## Problem Identified
The frontend was using incorrect endpoint names that didn't match the backend API:
- Frontend was calling: `/auth/forgot-password`, `/auth/verify-otp`, `/auth/reset-password`
- Backend provides: `/auth/request-otp`, `/auth/verify-otp-and-reset`

## Solution Applied

### 1. **Updated Forgot Password Endpoint**
**Before**: `POST /auth/forgot-password` (email link based)
**After**: `POST /auth/request-otp` (OTP code based)

```javascript
// Line 611
const res = await fetch(apiURL('/auth/request-otp'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email })
});
```

### 2. **Combined OTP Verification + Password Reset**
**Before**: Two-step process (verify OTP → show reset modal → reset password)
**After**: Single-step process (verify OTP + reset password in one call)

```javascript
// Line 670
const res = await fetch(apiURL('/auth/verify-otp-and-reset'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
        email: currentResetEmail,
        otp_code: otpCode,
        new_password: newPassword
    })
});
```

### 3. **Simplified UI Flow**
**Removed**: Separate reset password modal
**Consolidated**: OTP verification and password entry in single modal

**New Flow**:
1. User enters email → `/auth/request-otp` → OTP sent
2. User enters OTP + new password (twice) → `/auth/verify-otp-and-reset` → Done!

## Backend API Endpoints Used

| Endpoint | Method | Request Body | Response |
|----------|--------|--------------|----------|
| `/auth/request-otp` | POST | `{ email: "user@example.com" }` | `{ message: "..." }` |
| `/auth/verify-otp-and-reset` | POST | `{ email, otp_code, new_password }` | `{ message: "..." }` |

## Security Features (Backend)

- ✅ **Rate Limiting**: 3 requests per hour per IP (via `RateLimitAuthMiddleware`)
- ✅ **Email Enumeration Prevention**: Generic success messages regardless of email existence
- ✅ **OTP Expiration**: 5-minute TTL
- ✅ **Brute-Force Protection**: 3-attempt limit with automatic lockout
- ✅ **Bcrypt Hashing**: OTP codes hashed before storage
- ✅ **Password Validation**: Reuses `require_strong_password()` function
- ✅ **Audit Trail**: Password changes logged to `PROFILE_LOG` table
- ✅ **OTP Cleanup**: Deleted after successful use

## Frontend Validation

Added client-side validation before API call:
```javascript
// Passwords must match
if (newPassword !== confirmPassword) {
    throw new Error('Passwords do not match');
}

// Minimum length check
if (newPassword.length < 8) {
    throw new Error('Password must be at least 8 characters');
}
```

## Updated Modal Structure

### Single OTP Modal (Lines 205-227)
```html
<div id="otp-modal" class="modal">
    <h3>Reset Password</h3>
    <p>Enter the 6-digit code sent to your email and set your new password.</p>
    <form id="otp-form">
        <label>OTP Code (6 digits)</label>
        <input type="text" id="otp-code" ...>
        
        <label>New Password</label>
        <input type="password" id="new-password" ...>
        
        <label>Confirm New Password</label>
        <input type="password" id="confirm-password" ...>
        
        <button type="submit">Reset Password</button>
    </form>
</div>
```

## Removed Code

- ❌ `currentOtpToken` variable (no longer needed)
- ❌ Separate `reset-password-modal` section
- ❌ `closeResetPasswordModal()` function
- ❌ `reset-password-form` submit handler
- ❌ `/auth/reset-password` endpoint call

## Testing Checklist

### Test Case 1: Valid OTP Flow
1. Click "Forgot Password?"
2. Enter valid email
3. Click "Send OTP Code"
4. Check email for 6-digit code
5. Enter OTP code
6. Enter new password (8+ chars, uppercase, lowercase, number, special char)
7. Confirm password
8. Click "Reset Password"
9. Should see success message and redirect to login

### Test Case 2: Invalid OTP
1. Request OTP for valid email
2. Enter wrong OTP code
3. Should see error: "Invalid OTP or email address"

### Test Case 3: Password Mismatch
1. Request OTP for valid email
2. Enter correct OTP
3. Enter different passwords in "New Password" and "Confirm" fields
4. Should see error: "Passwords do not match"

### Test Case 4: Weak Password
1. Request OTP for valid email
2. Enter correct OTP
3. Enter password shorter than 8 characters
4. Should see error: "Password must be at least 8 characters"

### Test Case 5: Rate Limiting
1. Request OTP 3 times in quick succession
2. Third attempt should fail with rate limit error

## Files Modified
- `/home/ubuntu/fyp-backend/static/tester.html`
  - Line 611: Changed `/auth/forgot-password` → `/auth/request-otp`
  - Line 670: Changed `/auth/verify-otp` → `/auth/verify-otp-and-reset`
  - Lines 205-227: Simplified OTP modal (combined verification + password entry)
  - Removed: Reset password modal and related code

## Backend Alignment

✅ **Fully aligned** with `/home/ubuntu/fyp-backend/app/api/v1/auth.py`:
- Uses `/request-otp` endpoint (line 208 in auth.py)
- Uses `/verify-otp-and-reset` endpoint (line 256 in auth.py)
- Matches request/response schemas
- Respects security features (rate limiting, OTP expiration, etc.)

## Success Indicators

✅ Forgot password flow uses OTP (not email links)  
✅ Single modal for OTP verification + password reset  
✅ All validation happens before API call  
✅ Error messages are user-friendly  
✅ Backend security features are respected  
✅ No deprecated endpoints used  
✅ Code is cleaner and more maintainable
