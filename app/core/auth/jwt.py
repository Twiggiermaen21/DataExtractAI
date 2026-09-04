import time
import hashlib
import logging
import jwt

from app.core.auth.config import (
    DJANGO_SECRET_KEY, 
    JWT_ALGORITHM, 
    ACCESS_TOKEN_LIFETIME, 
    REFRESH_TOKEN_LIFETIME
)

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Generowanie i walidacja tokenów JWT (kompatybilne z SimpleJWT)
# ---------------------------------------------------------------------------

def generate_tokens(user_id: int) -> dict:
    """
    Generuje parę access + refresh tokenów JWT
    kompatybilnych z djangorestframework-simplejwt.
    """
    now = int(time.time())

    access_payload = {
        "token_type": "access",
        "exp": now + ACCESS_TOKEN_LIFETIME,
        "iat": now,
        "jti": hashlib.sha256(f"access-{user_id}-{now}".encode()).hexdigest()[:32],
        "user_id": str(user_id),
    }

    refresh_payload = {
        "token_type": "refresh",
        "exp": now + REFRESH_TOKEN_LIFETIME,
        "iat": now,
        "jti": hashlib.sha256(f"refresh-{user_id}-{now}".encode()).hexdigest()[:32],
        "user_id": str(user_id),
    }

    access_token = jwt.encode(access_payload, DJANGO_SECRET_KEY, algorithm=JWT_ALGORITHM)
    refresh_token = jwt.encode(refresh_payload, DJANGO_SECRET_KEY, algorithm=JWT_ALGORITHM)

    return {
        "access": access_token,
        "refresh": refresh_token,
    }

def refresh_access_token(refresh_token_str: str) -> dict | None:
    """
    Weryfikuje refresh token i generuje nowy access token.
    Zwraca dict z nowym access tokenem lub None.
    """
    if not DJANGO_SECRET_KEY:
        log.error("DJANGO_SECRET_KEY is not configured")
        return None

    try:
        payload = jwt.decode(
            refresh_token_str,
            DJANGO_SECRET_KEY,
            algorithms=[JWT_ALGORITHM],
            options={"verify_exp": True, "verify_iat": True},
        )

        if payload.get("token_type") != "refresh":
            log.warning("Token is not a refresh token: type=%s", payload.get("token_type"))
            return None

        user_id = payload.get("user_id")
        if user_id is None:
            return None

        now = int(time.time())
        access_payload = {
            "token_type": "access",
            "exp": now + ACCESS_TOKEN_LIFETIME,
            "iat": now,
            "jti": hashlib.sha256(f"access-{user_id}-{now}".encode()).hexdigest()[:32],
            "user_id": str(user_id),
        }
        access_token = jwt.encode(access_payload, DJANGO_SECRET_KEY, algorithm=JWT_ALGORITHM)

        return {"access": access_token}

    except jwt.ExpiredSignatureError:
        log.info("Refresh token expired")
        return None
    except jwt.InvalidTokenError as e:
        log.warning("Invalid refresh token: %s", e)
        return None

def decode_jwt(token: str) -> dict | None:
    """Dekoduje i waliduje token JWT (SimpleJWT access token)."""
    if not DJANGO_SECRET_KEY:
        log.error("DJANGO_SECRET_KEY is not configured — cannot verify JWT")
        return None

    try:
        payload = jwt.decode(
            token,
            DJANGO_SECRET_KEY,
            algorithms=[JWT_ALGORITHM],
            options={
                "verify_exp": True,
                "verify_iat": True,
            },
        )

        # SimpleJWT access tokeny mają token_type == "access"
        token_type = payload.get("token_type")
        if token_type != "access":
            log.warning("Invalid token_type: %s (expected 'access')", token_type)
            return None

        return payload

    except jwt.ExpiredSignatureError:
        log.info("JWT token expired")
        return None
    except jwt.InvalidTokenError as e:
        log.warning("Invalid JWT token: %s", e)
        return None

