"""
Password hashing and verification utilities
"""

import bcrypt
import logging

logger = logging.getLogger("auth")


def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt.
    
    Args:
        password: Plain text password
        
    Returns:
        bcrypt hash string
    """
    if not isinstance(password, bytes):
        password = password.encode('utf-8')
    
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password, salt)
    return hashed.decode('utf-8')


def verify_password(password: str, password_hash: str) -> bool:
    """
    Verify a password against its hash.
    
    Args:
        password: Plain text password
        password_hash: bcrypt hash to verify against
        
    Returns:
        True if password matches, False otherwise
    """
    try:
        if not isinstance(password, bytes):
            password = password.encode('utf-8')
        if not isinstance(password_hash, bytes):
            password_hash = password_hash.encode('utf-8')
        
        return bcrypt.checkpw(password, password_hash)
    except Exception as e:
        logger.error(f"Error verifying password: {e}")
        return False


def is_strong_password(password: str, config=None) -> tuple[bool, str]:
    """
    Validate password strength based on configuration.
    
    Args:
        password: Password to validate
        config: AuthConfig object with password rules
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if config is None:
        # Default config
        min_length = 12
        require_upper = True
        require_lower = True
        require_digits = True
        require_special = True
    else:
        min_length = config.password_min_length
        require_upper = config.password_require_upper
        require_lower = config.password_require_lower
        require_digits = config.password_require_digits
        require_special = config.password_require_special
    
    # Check length
    if len(password) < min_length:
        return False, f"Password must be at least {min_length} characters"
    
    # Check for uppercase
    if require_upper and not any(c.isupper() for c in password):
        return False, "Password must contain at least one uppercase letter"
    
    # Check for lowercase
    if require_lower and not any(c.islower() for c in password):
        return False, "Password must contain at least one lowercase letter"
    
    # Check for digits
    if require_digits and not any(c.isdigit() for c in password):
        return False, "Password must contain at least one digit"
    
    # Check for special characters
    if require_special:
        special_chars = "!@#$%^&*()_+-=[]{}|;:,.<>?"
        if not any(c in special_chars for c in password):
            return False, "Password must contain at least one special character"
    
    return True, ""
