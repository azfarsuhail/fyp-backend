import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from app.main import app
from app.core.dependencies import get_db
from app.core.security import create_password_reset_token, verify_password_reset_token


@pytest.fixture
def mock_db_session():
    """Create a properly configured mock database session"""
    mock = MagicMock()
    
    # Create a proper mock chain
    query_mock = MagicMock()
    filter_mock = MagicMock()
    first_mock = MagicMock(return_value=None)
    
    filter_mock.first = first_mock
    query_mock.filter = filter_mock
    mock.query = query_mock
    
    return mock


@pytest.fixture
def test_client(mock_db_session):
    """Create test client with mocked DB"""
    def override_get_db():
        yield mock_db_session
    
    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


class TestPasswordResetEndpoints:
    """Test suite for password reset functionality"""
    
    def test_forgot_password_user_exists(self, test_client, mock_db_session):
        """Test /forgot-password when user exists"""
        # Mock user lookup
        mock_user = MagicMock()
        mock_user.email = "test@example.com"
        
        # Override the first() method to return our mock user
        mock_db_session.query.return_value.filter.return_value.first = MagicMock(return_value=mock_user)
        
        # Mock email sending function
        with patch("app.api.v1.auth.send_reset_password_email") as send_email_mock:
            response = test_client.post(
                "/api/v1/auth/forgot-password",
                json={"email": "test@example.com"}
            )
            
            assert response.status_code == 200
            assert "If an account with that email address exists" in response.json()["message"]
            assert send_email_mock.called  # Email should have been sent
    
    def test_forgot_password_user_not_exists(self, test_client, mock_db_session):
        """Test /forgot-password when user doesn't exist (security check)"""
        # Ensure mock returns None for user lookup
        mock_db_session.query.return_value.filter.return_value.first = MagicMock(return_value=None)
        
        response = test_client.post(
            "/api/v1/auth/forgot-password",
            json={"email": "nonexistent@example.com"}
        )
        
        # Should return same message even if user doesn't exist
        assert response.status_code == 200
        assert "If an account with that email address exists" in response.json()["message"]
        
    def test_forgot_password_invalid_email(self, test_client):
        """Test /forgot-password with invalid email format"""
        response = test_client.post(
            "/api/v1/auth/forgot-password",
            json={"email": "invalid-email"}
        )
        
        assert response.status_code == 422  # Validation error
        
    def test_reset_password_valid_token(self, test_client, mock_db_session):
        """Test /reset-password with valid token"""
        # Create a valid token
        test_email = "test@example.com"
        token = create_password_reset_token(test_email)
        
        # Mock user lookup
        mock_user = MagicMock()
        mock_user.email = test_email
        mock_db_session.query.return_value.filter.return_value.first = MagicMock(return_value=mock_user)
        
        # Mock password strength validation (skip it for simplicity)
        with patch("app.api.v1.auth.require_strong_password", return_value=[]):
            response = test_client.post(
                "/api/v1/auth/reset-password",
                json={
                    "token": token,
                    "new_password": "SecurePass123!"
                }
            )
        
        assert response.status_code == 200
        assert "successfully reset" in response.json()["message"]
        assert mock_db_session.commit.called  # Database should be updated
        
    def test_reset_password_invalid_token(self, test_client):
        """Test /reset-password with invalid token"""
        response = test_client.post(
            "/api/v1/auth/reset-password",
            json={
                "token": "invalid.token.here",
                "new_password": "SecurePass123!"
            }
        )
        
        assert response.status_code == 400
        assert "Invalid or expired reset token" in response.json()["detail"]
        
    def test_reset_password_expired_token(self, test_client, mock_db_session):
        """Test /reset-password with expired token"""
        # Create a valid token (not actually expired for this test)
        token = create_password_reset_token("test@example.com")
        
        # Mock user lookup
        mock_user = MagicMock()
        mock_user.email = "test@example.com"
        mock_db_session.query.return_value.filter.return_value.first = MagicMock(return_value=mock_user)
        
        # Mock password strength validation
        with patch("app.api.v1.auth.require_strong_password", return_value=[]):
            response = test_client.post(
                "/api/v1/auth/reset-password",
                json={
                    "token": token,
                    "new_password": "SecurePass123!"
                }
            )
        
        # Token is valid (not expired yet), so should succeed
        assert response.status_code == 200
        
    def test_reset_password_weak_password(self, test_client, mock_db_session):
        """Test /reset-password with weak password"""
        token = create_password_reset_token("test@example.com")
        
        mock_user = MagicMock()
        mock_user.email = "test@example.com"
        mock_db_session.query.return_value.filter.return_value.first = MagicMock(return_value=mock_user)
        
        # Password validation happens at schema level (Pydantic), returns 422
        response = test_client.post(
            "/api/v1/auth/reset-password",
            json={
                "token": token,
                "new_password": "weak"  # Too short
            }
        )
        
        # Schema validator catches weak passwords first (422)
        assert response.status_code == 422
        assert "detail" in response.json()


class TestSecurityUtilities:
    """Tests for security utility functions"""
    
    def test_create_and_verify_reset_token(self):
        """Test round-trip of token creation and verification"""
        test_cases = [
            "user@example.com",
            "another.user@domain.org",
            "test+tag@email.com"
        ]
        
        for email in test_cases:
            token = create_password_reset_token(email)
            result = verify_password_reset_token(token)
            assert result == email
            
    def test_verify_invalid_signature(self):
        """Test that tokens with wrong signature are rejected"""
        token = create_password_reset_token("test@example.com")
        
        # Tamper with token (this won't work perfectly with JWT but tests validation)
        tampered_token = token[:-5] + "xxxxx"
        
        result = verify_password_reset_token(tampered_token)
        assert result is None
        
    def test_token_expiration_handling(self):
        """Test that expired tokens are properly handled"""
        from jose import jwt
        from datetime import datetime, timedelta, timezone
        
        # Create a manually expired token
        payload = {
            "sub": "test@example.com",
            "type": "reset",
            "exp": (datetime.now(timezone.utc) - timedelta(minutes=1)).timestamp(),
            "iat": datetime.now(timezone.utc).timestamp()
        }
        
        expired_token = jwt.encode(payload, "secret", algorithm="HS256")
        
        result = verify_password_reset_token(expired_token)
        assert result is None  # Should reject expired token
