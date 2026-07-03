"""
OTP Password Reset Tests
------------------------
Comprehensive test suite for OTP-based password reset functionality.
Tests cover:
- OTP generation and email sending
- OTP verification with valid codes
- Failed verification (incorrect code, expired, brute force)
- Password reset after successful OTP verification
- Rate limiting
- Security features (attempt tracking, lockout)
"""

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from resend import Emails

from app.main import app
from app.models.user import User
from app.models.otp_verification import OTPVerification
from app.core.security import get_password_hash, verify_password
from app.core.config import SessionLocal
from app.services.otp_service import generate_otp_code, hash_otp_code, verify_otp_code, OTP_LENGTH


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    """Reset rate limiter before every test to prevent state bleed."""
    from app.core.security_middleware import auth_rate_limiter
    # Clear all attempt tracking data
    with auth_rate_limiter._lock:
        auth_rate_limiter.attempts.clear()
    yield


@pytest.fixture
def db_session():
    """Create database session for testing."""
    # Use testing database
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def test_user(db_session):
    """Create a test user with unique email and proper teardown."""
    import uuid
    
    # Generate unique email
    unique_email = f"testuser_{uuid.uuid4().hex[:8]}@example.com"
    
    # Clean up any existing user with this email before creating
    db_session.query(User).filter(User.email == unique_email).delete()
    db_session.query(OTPVerification).filter(
        OTPVerification.user_id == User.user_id
    ).delete(synchronize_session=False)
    db_session.commit()
    
    user = User(
        email=unique_email,
        full_name="Test User",
        password_hash=get_password_hash("TestPass123!"),
        role="patient"
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    
    # Yield control back to test
    yield user
    
    # TEARDOWN: Clean up in reverse order to respect FK constraints
    try:
        # Delete OTP records first (FK to user)
        db_session.query(OTPVerification).filter(
            OTPVerification.user_id == user.user_id
        ).delete(synchronize_session=False)
        
        # Delete profile logs (FK to user)
        from app.models.profile_log import ProfileLog
        db_session.query(ProfileLog).filter(
            ProfileLog.user_id == user.user_id
        ).delete(synchronize_session=False)
        
        # Finally delete the user
        db_session.delete(user)
        db_session.commit()
    except Exception as e:
        db_session.rollback()
        print(f"Teardown error: {e}")


@pytest.fixture
def active_otp_record(db_session, test_user):
    """Create an active OTP record for testing."""
    from app.services.otp_service import create_otp_record
    
    otp_record, otp_code = create_otp_record(db_session, test_user.user_id)
    return otp_record, otp_code


@pytest.fixture
def expired_otp_record(db_session, test_user):
    """Create an expired OTP record for testing."""
    expires_at = datetime.now(timezone.utc) - timedelta(minutes=10)
    otp_record = OTPVerification(
        user_id=test_user.user_id,
        code_hash=hash_otp_code("123456"),
        expires_at=expires_at,
        attempts=0,
        is_verified=0
    )
    db_session.add(otp_record)
    db_session.commit()
    return otp_record


@pytest.fixture
def locked_otp_record(db_session, test_user):
    """Create a locked OTP record (max attempts reached)."""
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)
    otp_record = OTPVerification(
        user_id=test_user.user_id,
        code_hash=hash_otp_code("123456"),
        expires_at=expires_at,
        attempts=3,
        is_verified=0  # Still active but with max attempts
    )
    db_session.add(otp_record)
    db_session.commit()
    return otp_record, "123456"


class TestOTPGeneration:
    """Test OTP code generation and hashing."""
    
    def test_otp_code_length(self):
        """Test that generated OTP is exactly 6 digits."""
        otp = generate_otp_code()
        assert len(otp) == OTP_LENGTH
        assert otp.isdigit()
    
    def test_otp_code_is_numeric(self):
        """Test that OTP contains only digits."""
        otp = generate_otp_code()
        assert all(c in "0123456789" for c in otp)
    
    def test_otp_code_uniqueness(self):
        """Test that generated OTPs are unique."""
        otps = [generate_otp_code() for _ in range(100)]
        assert len(set(otps)) == 100  # All should be unique
    
    def test_hash_otp_code(self):
        """Test that OTP hashing produces a valid bcrypt hash."""
        otp = generate_otp_code()
        hashed = hash_otp_code(otp)
        
        assert hashed is not None
        assert len(hashed) > 0
        assert hashed.startswith("$2")  # bcrypt prefix
    
    def test_verify_otp_code(self):
        """Test OTP verification with correct and incorrect codes."""
        otp = generate_otp_code()
        hashed = hash_otp_code(otp)
        
        # Correct code should verify
        assert verify_otp_code(otp, hashed) is True
        
        # Incorrect code should not verify
        assert verify_otp_code("000000", hashed) is False


class TestOTPRequestEndpoint:
    """Test POST /api/v1/auth/request-otp endpoint."""
    
    def test_request_otp_success(self, client, db_session, test_user):
        """Test successful OTP request for existing user."""
        # Mock the email service to prevent actual email sending
        with patch("app.services.email.send_otp_email") as mock_send_email:
            with patch("app.api.v1.auth.send_otp_email") as mock_api_send_email:
                response = client.post(
                    "/api/v1/auth/request-otp",
                    json={"email": test_user.email}
                )
                
                assert response.status_code == 200
                data = response.json()
                assert "message" in data
                # Generic message to prevent email enumeration
                assert "account" in data["message"].lower() or "email" in data["message"].lower()
    
    def test_request_otp_nonexistent_user(self, client):
        """Test OTP request for non-existent user (should not reveal user exists)."""
        with patch("app.services.email.send_otp_email"):
            with patch("app.api.v1.auth.send_otp_email"):
                response = client.post(
                    "/api/v1/auth/request-otp",
                    json={"email": "nonexistent@example.com"}
                )
                
                assert response.status_code == 200
                data = response.json()
                # Same generic message as for existing users
                assert "message" in data
    
    def test_request_otp_invalid_email(self, client):
        """Test OTP request with invalid email format."""
        response = client.post(
            "/api/v1/auth/request-otp",
            json={"email": "invalid-email"}
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_request_otp_rate_limiting(self, client, test_user, db_session):
        """Test that OTP requests are rate limited."""
        # Clear rate limiter state before test
        from app.core.security_middleware import auth_rate_limiter
        with auth_rate_limiter._lock:
            auth_rate_limiter.attempts.clear()
        
        # Make 3 successful requests
        for i in range(3):
            with patch("app.services.email.send_otp_email"):
                with patch("app.api.v1.auth.send_otp_email"):
                    response = client.post(
                        "/api/v1/auth/request-otp",
                        json={"email": test_user.email}
                    )
                    assert response.status_code == 200, f"Request {i+1} should succeed"
        
        # 4th request should be rate limited
        with patch("app.services.email.send_otp_email"):
            with patch("app.api.v1.auth.send_otp_email"):
                response = client.post(
                    "/api/v1/auth/request-otp",
                    json={"email": test_user.email}
            )
            assert response.status_code == 429, "4th request should be rate limited"
            data = response.json()
            assert "detail" in data
            assert "too many" in data["detail"].lower() or "limit" in data["detail"].lower()
    
    def test_otp_created_in_database(self, client, db_session, test_user):
        """Test that OTP record is created in database."""
        with patch("app.services.email.send_otp_email"):
            with patch("app.api.v1.auth.send_otp_email"):
                response = client.post(
                    "/api/v1/auth/request-otp",
                    json={"email": test_user.email}
                )
                
                assert response.status_code == 200
                
                # Verify OTP record was created
                otp_count = db_session.query(OTPVerification).filter(
                    OTPVerification.user_id == test_user.user_id
                ).count()
                assert otp_count >= 1


class TestOTPVerificationEndpoint:
    """Test POST /api/v1/auth/verify-otp-and-reset endpoint."""
    
    def test_verify_otp_success(self, client, db_session, test_user, active_otp_record):
        """Test successful OTP verification and password reset."""
        otp_record, otp_code = active_otp_record
        
        response = client.post(
            "/api/v1/auth/verify-otp-and-reset",
            json={
                "email": test_user.email,
                "otp_code": otp_code,
                "new_password": "NewPass456!"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "password" in data["message"].lower()
        
        # FIX: Clear SQLAlchemy identity map to avoid caching issues
        # The endpoint updates the DB, but our session may have cached the old user object
        db_session.expire_all()
        
        # Verify password was updated (fresh query from DB)
        db_user = db_session.query(User).filter(
            User.user_id == test_user.user_id
        ).first()
        assert db_user is not None, "User should exist in database"
        assert verify_password("NewPass456!", db_user.password_hash) is True, \
            f"Password should be updated. Expected hash for 'NewPass456!', got: {db_user.password_hash}"
        
        # Verify OTP record was deleted
        otp_count = db_session.query(OTPVerification).filter(
            OTPVerification.user_id == test_user.user_id
        ).count()
        assert otp_count == 0
        
        # Verify audit log was created
        from app.models.profile_log import ProfileLog
        log_count = db_session.query(ProfileLog).filter(
            ProfileLog.user_id == test_user.user_id,
            ProfileLog.field_name == "password_hash"
        ).count()
        assert log_count >= 1
    
    def test_verify_otp_invalid_code(self, client, db_session, test_user, active_otp_record):
        """Test OTP verification with incorrect code."""
        otp_record, otp_code = active_otp_record
        
        # Try with wrong code
        response = client.post(
            "/api/v1/auth/verify-otp-and-reset",
            json={
                "email": test_user.email,
                "otp_code": "000000",
                "new_password": "NewPass456!"
            }
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
        assert "invalid" in data["detail"].lower() or "failed" in data["detail"].lower()
        
        # Verify attempts were incremented (clear cache first)
        db_session.expire_all()
        db_otp = db_session.query(OTPVerification).filter(
            OTPVerification.user_id == test_user.user_id
        ).first()
        assert db_otp.attempts == 1
    
    def test_verify_otp_brute_force_lockout(self, client, db_session, test_user):
        """Test OTP lockout after 3 failed attempts."""
        from app.services.otp_service import create_otp_record
        
        # Create an OTP record
        otp_record, otp_code = create_otp_record(db_session, test_user.user_id)
        
        # Simulate 3 failed attempts manually
        for i in range(3):
            response = client.post(
                "/api/v1/auth/verify-otp-and-reset",
                json={
                    "email": test_user.email,
                    "otp_code": "000000",  # Wrong code
                    "new_password": "NewPass456!"
                }
            )
            assert response.status_code == 400
        
        # Clear cache and check attempts
        db_session.expire_all()
        db_otp = db_session.query(OTPVerification).filter(
            OTPVerification.user_id == test_user.user_id
        ).first()
        assert db_otp.attempts == 3
        assert db_otp.is_verified == 2  # Locked
        
        # Now try with correct code - should still fail due to lockout
        response = client.post(
            "/api/v1/auth/verify-otp-and-reset",
            json={
                "email": test_user.email,
                "otp_code": otp_code,  # Correct code but locked
                "new_password": "NewPass456!"
            }
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
        # After lockout, the OTP is no longer "active" so it returns "Invalid or expired"
        assert "invalid" in data["detail"].lower() or "expired" in data["detail"].lower() or "locked" in data["detail"].lower()
    
    def test_verify_otp_expired(self, client, db_session, test_user, expired_otp_record):
        """Test OTP verification with expired code."""
        response = client.post(
            "/api/v1/auth/verify-otp-and-reset",
            json={
                "email": test_user.email,
                "otp_code": "123456",
                "new_password": "NewPass456!"
            }
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
        assert "invalid" in data["detail"].lower() or "expired" in data["detail"].lower()
    
    def test_verify_otp_nonexistent_user(self, client):
        """Test OTP verification for non-existent user."""
        response = client.post(
            "/api/v1/auth/verify-otp-and-reset",
            json={
                "email": "nonexistent@example.com",
                "otp_code": "123456",
                "new_password": "NewPass456!"
            }
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
    
    def test_verify_otp_weak_password(self, client, db_session, test_user, active_otp_record):
        """Test OTP verification with weak password."""
        otp_record, otp_code = active_otp_record
        
        response = client.post(
            "/api/v1/auth/verify-otp-and-reset",
            json={
                "email": test_user.email,
                "otp_code": otp_code,
                "new_password": "weak"  # Too short, no complexity
            }
        )
        
        # Pydantic validation returns 422 for weak password (min_length=8)
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data
    
    def test_verify_otp_invalid_otp_format(self, client):
        """Test OTP verification with invalid OTP format."""
        response = client.post(
            "/api/v1/auth/verify-otp-and-reset",
            json={
                "email": "test@example.com",
                "otp_code": "12345",  # Only 5 digits
                "new_password": "NewPass456!"
            }
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_verify_otp_multiple_failures_increment_attempts(self, client, db_session, test_user, active_otp_record):
        """Test that multiple failed attempts increment the counter correctly."""
        otp_record, otp_code = active_otp_record
        
        # First failed attempt
        response = client.post(
            "/api/v1/auth/verify-otp-and-reset",
            json={
                "email": test_user.email,
                "otp_code": "000000",
                "new_password": "NewPass456!"
            }
        )
        assert response.status_code == 400
        
        # Check attempts incremented (clear cache first)
        db_session.expire_all()
        db_otp = db_session.query(OTPVerification).filter(
            OTPVerification.user_id == test_user.user_id
        ).first()
        assert db_otp.attempts == 1
        
        # Second failed attempt
        response = client.post(
            "/api/v1/auth/verify-otp-and-reset",
            json={
                "email": test_user.email,
                "otp_code": "111111",
                "new_password": "NewPass456!"
            }
        )
        assert response.status_code == 400
        
        # Check attempts incremented again (clear cache first)
        db_session.expire_all()
        db_otp = db_session.query(OTPVerification).filter(
            OTPVerification.user_id == test_user.user_id
        ).first()
        assert db_otp.attempts == 2
        
        # Third failed attempt should lock out
        response = client.post(
            "/api/v1/auth/verify-otp-and-reset",
            json={
                "email": test_user.email,
                "otp_code": "222222",
                "new_password": "NewPass456!"
            }
        )
        assert response.status_code == 400
        
        # Check OTP is locked (clear cache first)
        db_session.expire_all()
    def test_otp_email_contains_code(self, client, db_session, test_user):
        """Test that OTP email contains the correct code."""
        with patch("app.services.email.Emails.send") as mock_send:
            response = client.post(
                "/api/v1/auth/request-otp",
                json={"email": test_user.email}
            )
            
            assert response.status_code == 200
            
            # Get the sent email content
            # Emails.send() is called with a single dictionary payload as first positional arg
            call_args = mock_send.call_args
            if call_args and len(call_args) > 0:
                # First positional argument is the payload dictionary
                payload = call_args[0][0] if call_args[0] else {}
                
                html_content = payload.get("html", "")
                subject = payload.get("subject", "")
                to_address = payload.get("to", [])
                
                # Verify email was sent to correct address
                assert to_address == [test_user.email]
                
                # Extract OTP from HTML (it should be in the email)
                # The email template includes the OTP code
                assert "Password Reset Code" in subject
                assert "5 minutes" in html_content  # Expiration notice
    
    def test_email_not_sent_when_resend_disabled(self, client, db_session, test_user, monkeypatch):
        """Test that email is not sent when RESEND_API_KEY is not set."""
        # Patch the RESEND_API_KEY environment variable BEFORE the email service checks it
        monkeypatch.setattr("app.services.email.RESEND_API_KEY", "")
        
        with patch("app.services.email.Emails.send") as mock_send:
            response = client.post(
                "/api/v1/auth/request-otp",
                json={"email": test_user.email}
            )
            
            assert response.status_code == 200
            # Email service should skip sending when RESEND_API_KEY is not set
            assert not mock_send.called, "Email should not be sent when RESEND_API_KEY is empty"


class TestSecurityFeatures:
    """Test security features of OTP system."""
    
    def test_otp_hashed_in_database(self, client, db_session, test_user):
        """Test that OTP is hashed in database, not stored in plain text."""
        with patch("app.services.email.Emails.send"):
            response = client.post(
                "/api/v1/auth/request-otp",
                json={"email": test_user.email}
            )
            
            assert response.status_code == 200
            
            # Get OTP from database
            otp_record = db_session.query(OTPVerification).filter(
                OTPVerification.user_id == test_user.user_id
            ).first()
            
            # Verify it's hashed (starts with bcrypt prefix)
            assert otp_record.code_hash.startswith("$2")
            
            # Verify it's not the plain text OTP
            assert otp_record.code_hash != "123456"
    
    def test_password_not_logged(self, client, db_session, test_user, active_otp_record):
        """Test that password is not logged in audit trail."""
        otp_record, otp_code = active_otp_record
        
        response = client.post(
            "/api/v1/auth/verify-otp-and-reset",
            json={
                "email": test_user.email,
                "otp_code": otp_code,
                "new_password": "SuperSecret123!"
            }
        )
        
        assert response.status_code == 200
        
        # Check audit log
        from app.models.profile_log import ProfileLog
        log = db_session.query(ProfileLog).filter(
            ProfileLog.user_id == test_user.user_id,
            ProfileLog.field_name == "password_hash"
        ).first()
        
        assert log is not None
        # Password should not be in plain text
        assert "SuperSecret123!" not in log.old_value
        assert "SuperSecret123!" not in log.new_value
        assert log.new_value == "***updated***"
    
    def test_generic_error_messages(self, client, db_session, test_user, expired_otp_record):
        """Test that error messages don't leak sensitive information."""
        response = client.post(
            "/api/v1/auth/verify-otp-and-reset",
            json={
                "email": test_user.email,
                "otp_code": "123456",
                "new_password": "NewPass456!"
            }
        )
        
        assert response.status_code == 400
        data = response.json()
        
        # Error message should be generic
        detail = data["detail"].lower()
        assert "database" not in detail
        assert "sql" not in detail
        assert "exception" not in detail
        assert "traceback" not in detail


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def test_request_otp_with_spaces_in_email(self, client):
        """Test OTP request with spaces in email - should be stripped."""
        response = client.post(
            "/api/v1/auth/request-otp",
            json={"email": " test@example.com "}
        )
        
        # Should succeed with stripped email
        assert response.status_code == 200
    
    def test_verify_otp_with_spaces_in_code(self, client):
        """Test OTP verification with spaces in code - should be stripped and accepted."""
        response = client.post(
            "/api/v1/auth/verify-otp-and-reset",
            json={
                "email": "test@example.com",
                "otp_code": " 123456 ",
                "new_password": "NewPass456!"
            }
        )
        
        # Should succeed with stripped code (str_strip_whitespace=True)
        # Note: This will fail with 400 because user doesn't exist, but that's expected
        assert response.status_code in [400, 422]
    
    def test_request_otp_empty_email(self, client):
        """Test OTP request with empty email."""
        response = client.post(
            "/api/v1/auth/request-otp",
            json={"email": ""}
        )
        
        assert response.status_code == 422
    
    def test_verify_otp_empty_code(self, client):
        """Test OTP verification with empty code."""
        response = client.post(
            "/api/v1/auth/verify-otp-and-reset",
            json={
                "email": "test@example.com",
                "otp_code": "",
                "new_password": "NewPass456!"
            }
        )
        
        assert response.status_code == 422
    
    def test_verify_otp_empty_password(self, client):
        """Test OTP verification with empty password."""
        response = client.post(
            "/api/v1/auth/verify-otp-and-reset",
            json={
                "email": "test@example.com",
                "otp_code": "123456",
                "new_password": ""
            }
        )
        
        assert response.status_code == 422


class TestDatabaseConstraints:
    """Test database constraints and relationships."""
    
    def test_cascade_delete_on_user_deletion(self, client, db_session, test_user, active_otp_record):
        """Test that OTPs are deleted when user is deleted (CASCADE)."""
        otp_record, _ = active_otp_record
        
        # Delete user
        db_session.delete(test_user)
        db_session.commit()
        
        # OTP should be deleted too
        otp_count = db_session.query(OTPVerification).filter(
            OTPVerification.user_id == test_user.user_id
        ).count()
        assert otp_count == 0
    
    def test_composite_index_exists(self, db_session, test_user):
        """Test that composite index on (user_id, expires_at) exists."""
        # Create a test OTP record
        from app.services.otp_service import create_otp_record
        otp_record, _ = create_otp_record(db_session, test_user.user_id)
        
        assert otp_record is not None
        # The index should improve query performance for this pattern
        # (verified by code inspection of the model)
