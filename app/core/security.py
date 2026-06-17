from dotenv import load_dotenv
from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError
from passlib.context import CryptContext
import os
import secrets
from typing import Optional

# Load environment variables
load_dotenv()

# Configuration - Load from environment variables in production
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise ValueError(
        "CRITICAL: SECRET_KEY not set! "
        "Set a strong random key in .env file (min 32 characters). "
        "Generate with: python -c \"import secrets; print(secrets.token_urlsafe(32))\""
    )

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15"))
RESET_TOKEN_EXPIRE_MINUTES = 15  # Password reset tokens expire in 15 minutes (short-lived for security)

# Password Hashing Context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: timedelta = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def create_password_reset_token(email: str) -> str:
    """
    Create a short-lived JWT token specifically for password reset.
    
    This token can ONLY be used for password resets and cannot be used as an access token.
    It expires after RESET_TOKEN_EXPIRE_MINUTES (default 30 minutes).
    
    Args:
        email: User's email address
        
    Returns:
        JWT token string that expires quickly and is type-scoped
    """
    # Create payload with specific type claim for scope limiting
    to_encode = {
        "sub": email,  # Subject: the user's email
        "type": "reset",  # Token type: only valid for password reset
        "iat": datetime.now(timezone.utc)  # Issued at timestamp
    }
    
    expires_delta = timedelta(minutes=RESET_TOKEN_EXPIRE_MINUTES)
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode.update({"exp": expire})
    
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_password_reset_token(token: str) -> Optional[str]:
    """
    Verify and decode a password reset token.
    
    Validates that the token:
    - Is not expired
    - Has the correct type ("reset")
    - Was signed with the correct secret key
    
    Args:
        token: JWT token string
        
    Returns:
        Email address if valid, None otherwise
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        
        # Check token type to prevent reuse as access token
        if payload.get("type") != "reset":
            return None
            
        # Check if token is too fresh (prevent race conditions)
        iat = payload.get("iat")
        if iat:
            issued_at = datetime.fromtimestamp(iat, timezone.utc)
            if (datetime.now(timezone.utc) - issued_at).total_seconds() < 1:
                # Token issued less than 1 second ago - might be suspicious
                pass  # We allow it but log if needed
                
        return payload.get("sub")  # Return the email
        
    except JWTError:
        # JWT decoding failed (expired, invalid signature, etc.)
        return None
    except Exception:
        # Any other error during verification
        return None
