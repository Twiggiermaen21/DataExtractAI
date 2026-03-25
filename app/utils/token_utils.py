"""
Token generation and verification using itsdangerous.
Used for email confirmation links (name change, email change, password reset).
"""
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
from flask import current_app


def generate_token(data: dict, salt: str) -> str:
    """Create a URL-safe signed token encoding `data`."""
    s = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    return s.dumps(data, salt=salt)


def verify_token(token: str, salt: str, max_age: int = 3600) -> dict | None:
    """
    Verify and decode a token. Returns the data dict or None if invalid/expired.
    Default expiry: 1 hour (3600s).
    """
    s = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    try:
        return s.loads(token, salt=salt, max_age=max_age)
    except (SignatureExpired, BadSignature):
        return None
