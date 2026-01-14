import hashlib
import os
from typing import Tuple

def generate_salt() -> bytes:
    """Generate a random salt."""
    return os.urandom(16)

def hash_password(password: str, salt: bytes = None) -> Tuple[bytes, bytes]:
    """
    Hash a password using PBKDF2 with SHA-256.
    
    Args:
        password: The password to hash
        salt: Optional salt. If not provided, a new one will be generated.
    
    Returns:
        A tuple of (hashed_password, salt)
    """
    if salt is None:
        salt = generate_salt()
    
    # Using PBKDF2 with SHA-256, 100,000 iterations
    hashed = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt,
        100000
    )
    
    return hashed, salt

def verify_password(plain_password: str, hashed_password: bytes, salt: bytes) -> bool:
    """
    Verify a password against a stored hash and salt.
    
    Args:
        plain_password: The password to verify
        hashed_password: The stored hashed password
        salt: The salt used for the stored hash
    
    Returns:
        bool: True if the password matches, False otherwise
    """
    new_hash, _ = hash_password(plain_password, salt)
    return new_hash == hashed_password

def get_password_hash(password: str) -> str:
    """
    Hash a password and return the hash and salt as a combined string.
    Format: salt:hash (both hex-encoded)
    """
    hashed, salt = hash_password(password)
    return f"{salt.hex()}:{hashed.hex()}"

def verify_password_stored_format(plain_password: str, stored_password: str) -> bool:
    """
    Verify a password against a stored password in 'salt:hash' format.
    """
    try:
        salt_hex, hash_hex = stored_password.split(":")
        salt = bytes.fromhex(salt_hex)
        stored_hash = bytes.fromhex(hash_hex)
        
        hashed, _ = hash_password(plain_password, salt)
        return hashed == stored_hash
    except (ValueError, AttributeError):
        return False
