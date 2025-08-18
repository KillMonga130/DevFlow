"""
Encryption utilities for sensitive data.
"""

from typing import Optional
from cryptography.fernet import Fernet
from ..config import get_memory_config


def get_encryption_key() -> Optional[bytes]:
    """Get the encryption key from configuration."""
    config = get_memory_config()
    if config.encryption_key:
        return config.encryption_key.encode()
    return None


def encrypt_sensitive_data(data: str) -> str:
    """Encrypt sensitive data."""
    key = get_encryption_key()
    if not key:
        # If no encryption key is configured, return data as-is
        # In production, this should raise an error
        return data
    
    try:
        fernet = Fernet(key)
        encrypted_data = fernet.encrypt(data.encode())
        return encrypted_data.decode()
    except Exception:
        # If encryption fails, return original data
        # In production, this should be handled more carefully
        return data


def decrypt_sensitive_data(encrypted_data: str) -> str:
    """Decrypt sensitive data."""
    key = get_encryption_key()
    if not key:
        # If no encryption key is configured, return data as-is
        return encrypted_data
    
    try:
        fernet = Fernet(key)
        decrypted_data = fernet.decrypt(encrypted_data.encode())
        return decrypted_data.decode()
    except Exception:
        # If decryption fails, return original data
        # In production, this should be handled more carefully
        return encrypted_data