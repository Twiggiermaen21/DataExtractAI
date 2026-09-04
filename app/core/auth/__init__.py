from app.core.auth.config import (
    DJANGO_SECRET_KEY,
    JWT_ALGORITHM,
    ACCESS_TOKEN_LIFETIME,
    REFRESH_TOKEN_LIFETIME,
    VERIFY_USER_IN_DB,
    DB_NAME,
    DB_USER,
    DB_PASSWORD,
    DB_HOST,
    DB_PORT
)
from app.core.auth.db import get_db_connection, verify_user_active, find_user_by_email
from app.core.auth.password import check_django_password
from app.core.auth.jwt import generate_tokens, refresh_access_token, decode_jwt
from app.core.auth.decorators import require_auth

__all__ = [
    "DJANGO_SECRET_KEY",
    "JWT_ALGORITHM",
    "ACCESS_TOKEN_LIFETIME",
    "REFRESH_TOKEN_LIFETIME",
    "VERIFY_USER_IN_DB",
    "DB_NAME",
    "DB_USER",
    "DB_PASSWORD",
    "DB_HOST",
    "DB_PORT",
    "get_db_connection",
    "verify_user_active",
    "find_user_by_email",
    "check_django_password",
    "generate_tokens",
    "refresh_access_token",
    "decode_jwt",
    "require_auth",
]
