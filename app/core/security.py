from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple
import os
import hashlib
import binascii
from jose import jwt
from app.core.config import settings, SERVER_INSTANCE_ID

# PBKDF2 configuration
PBKDF2_ITERATIONS = 100000
SALT_LENGTH = 32
HASH_LENGTH = 64

def create_access_token(subject: str, expires_delta: Optional[timedelta] = None) -> str:
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    # Convert datetime to Unix timestamp (seconds since epoch)
    expire_timestamp = int(expire.timestamp())
    to_encode = {
        "exp": expire_timestamp, 
        "sub": str(subject),
        "instance_id": SERVER_INSTANCE_ID  # Include server instance ID to invalidate tokens on restart
    }
    encoded_jwt = jwt.encode(
        to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM
    )
    return encoded_jwt

def generate_salt() -> bytes:
    """Generate a random salt."""
    return os.urandom(SALT_LENGTH)

def hash_password(password: str, salt: Optional[bytes] = None) -> Tuple[bytes, bytes]:
    """
    Hash a password using PBKDF2 with SHA-256.
    Returns a tuple of (hash, salt).
    """
    if salt is None:
        salt = generate_salt()
    
    # Using PBKDF2 with SHA-256
    dk = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt,
        PBKDF2_ITERATIONS,
        dklen=HASH_LENGTH
    )
    return dk, salt

def verify_password(plain_password: str, stored_hash: str) -> bool:
    """
    Verify a password against a stored hash.
    The stored hash should be in the format: salt:hash (both hex-encoded)
    """
    try:
        # Split the stored hash into salt and hash
        salt_hex, hash_hex = stored_hash.split(':')
        salt = binascii.unhexlify(salt_hex)
        stored_hash_bytes = binascii.unhexlify(hash_hex)
        
        # Hash the provided password with the same salt
        new_hash, _ = hash_password(plain_password, salt)
        
        # Compare the hashes
        return new_hash == stored_hash_bytes
    except (ValueError, binascii.Error):
        return False

def get_password_hash(password: str) -> str:
    """
    Hash a password and return a string in the format "salt:hash"
    where both salt and hash are hex-encoded.
    """
    hashed, salt = hash_password(password)
    return f"{salt.hex()}:{hashed.hex()}"

def create_refresh_token(subject: str, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a refresh token with longer expiration time.
    """
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    # Convert datetime to Unix timestamp (seconds since epoch)
    expire_timestamp = int(expire.timestamp())
    to_encode = {
        "exp": expire_timestamp, 
        "sub": str(subject), 
        "type": "refresh",
        "instance_id": SERVER_INSTANCE_ID  # Include server instance ID to invalidate tokens on restart
    }
    encoded_jwt = jwt.encode(
        to_encode, settings.REFRESH_SECRET_KEY, algorithm=settings.ALGORITHM
    )
    return encoded_jwt

def verify_token(token: str, is_refresh: bool = False) -> Optional[dict]:
    """
    Verify and decode a JWT token.
    Returns the decoded token payload if valid, None otherwise.
    
    Args:
        token: The JWT token to verify
        is_refresh: If True, uses REFRESH_SECRET_KEY, otherwise uses SECRET_KEY
    """
    try:
        secret_key = settings.REFRESH_SECRET_KEY if is_refresh else settings.SECRET_KEY
        # Explicitly verify expiration by not disabling it in options
        payload = jwt.decode(
            token, 
            secret_key, 
            algorithms=[settings.ALGORITHM],
            options={"verify_exp": True}  # Explicitly enable expiration verification
        )
        
        # Verify server instance ID matches (invalidates tokens from previous server instances)
        token_instance_id = payload.get("instance_id")
        if token_instance_id != SERVER_INSTANCE_ID:
            # Token was issued by a different server instance (server was restarted)
            return None
        
        return payload
    except jwt.ExpiredSignatureError:
        # Token has expired
        return None
    except jwt.JWTError:
        # Other JWT errors (invalid signature, malformed token, etc.)
        return None
