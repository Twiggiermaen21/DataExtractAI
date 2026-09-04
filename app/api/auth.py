"""
Moduł autoryzacji JWT — weryfikuje tokeny SimpleJWT z Django
oraz zapewnia endpoint logowania.

Flask sprawdza token Bearer z nagłówka Authorization, dekoduje go
kluczem SECRET_KEY Django (HS256) i opcjonalnie waliduje użytkownika
w bazie PostgreSQL (tabela auth_user).

Endpoint /api/auth/login przyjmuje username+password, weryfikuje
hasło (PBKDF2-SHA256 — format Django) i zwraca tokeny access+refresh
kompatybilne z SimpleJWT.
"""

import os
import time
import hashlib
import hmac
import base64
import logging
import functools

import jwt
import psycopg
from flask import Blueprint, request, jsonify, g

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Konfiguracja
# ---------------------------------------------------------------------------

DJANGO_SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "")
JWT_ALGORITHM = os.environ.get("JWT_ALGORITHM", "HS256")

# Czas życia tokenów (sekundy) — domyślne jak SimpleJWT
ACCESS_TOKEN_LIFETIME = int(os.environ.get("JWT_ACCESS_LIFETIME", 300))       # 5 minut
REFRESH_TOKEN_LIFETIME = int(os.environ.get("JWT_REFRESH_LIFETIME", 86400))   # 1 dzień

# Czy weryfikować użytkownika w bazie danych (is_active)?
# Jeśli False, wystarczy poprawny token JWT.
VERIFY_USER_IN_DB = os.environ.get("VERIFY_USER_IN_DB", "true").lower() in ("1", "true", "yes")

# PostgreSQL Django
DB_NAME = os.environ.get("DB_NAME", "iusfully")
DB_USER = os.environ.get("DB_USER", "iusfully_user")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "iusfully_pass")
DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_PORT = os.environ.get("DB_PORT", "5433")


# ---------------------------------------------------------------------------
# Blueprint — /api/auth/*
# ---------------------------------------------------------------------------

auth_bp = Blueprint("auth", __name__)


# ---------------------------------------------------------------------------
# Baza danych
# ---------------------------------------------------------------------------

def _get_db_connection():
    """Tworzy nowe połączenie do bazy PostgreSQL Django."""
    return psycopg.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT,
    )


def _verify_user_active(user_id: int) -> dict | None:
    """
    Sprawdza w bazie Django czy użytkownik istnieje i jest aktywny.
    Zwraca dict z danymi usera lub None.
    """
    try:
        conn = _get_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id, email, email, is_active, is_staff "
                    "FROM api_user WHERE id = %s",
                    (user_id,),
                )
                row = cur.fetchone()
                if row is None:
                    log.warning("User id=%s not found in database", user_id)
                    return None
                user = {
                    "id": str(row[0]),
                    "username": row[1],
                    "email": row[2],
                    "is_active": row[3],
                    "is_staff": row[4],
                }
                if not user["is_active"]:
                    log.warning("User id=%s is inactive", user_id)
                    return None
                return user
        finally:
            conn.close()
    except psycopg.Error as e:
        log.error("Database error verifying user id=%s: %s", user_id, e)
        return None


def _find_user_by_email(email: str) -> dict | None:
    """
    Wyszukuje użytkownika po email w tabeli api_user Django.
    Zwraca dict z danymi lub None.
    """
    try:
        conn = _get_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id, email, email, password, is_active, is_staff, "
                    "first_name, last_name "
                    "FROM api_user WHERE email = %s",
                    (email,),
                )
                row = cur.fetchone()
                if row is None:
                    return None
                return {
                    "id": str(row[0]),
                    "username": row[1],
                    "email": row[2],
                    "password": row[3],
                    "is_active": row[4],
                    "is_staff": row[5],
                    "first_name": row[6],
                    "last_name": row[7],
                }
        finally:
            conn.close()
    except psycopg.Error as e:
        log.error("Database error finding user '%s': %s", email, e)
        return None


# ---------------------------------------------------------------------------
# Weryfikacja hasła Django (PBKDF2-SHA256)
# ---------------------------------------------------------------------------

def _check_django_password(raw_password: str, encoded: str) -> bool:
    """
    Weryfikuje hasło w formacie Django:
        <algorithm>$<iterations>$<salt>$<hash>

    Wspiera pbkdf2_sha256 (domyślny hasher Django).
    """
    try:
        parts = encoded.split("$")
        if len(parts) != 4:
            log.warning("Unknown password hash format: %d parts", len(parts))
            return False

        algorithm, iterations, salt, stored_hash = parts
        iterations = int(iterations)

        if algorithm == "pbkdf2_sha256":
            dk = hashlib.pbkdf2_hmac(
                "sha256",
                raw_password.encode("utf-8"),
                salt.encode("utf-8"),
                iterations,
            )
            computed_hash = base64.b64encode(dk).decode("ascii")
            # Porównanie bezpieczne czasowo
            return hmac.compare_digest(computed_hash, stored_hash)

        elif algorithm == "pbkdf2_sha1":
            dk = hashlib.pbkdf2_hmac(
                "sha1",
                raw_password.encode("utf-8"),
                salt.encode("utf-8"),
                iterations,
            )
            computed_hash = base64.b64encode(dk).decode("ascii")
            return hmac.compare_digest(computed_hash, stored_hash)

        else:
            log.warning("Unsupported password algorithm: %s", algorithm)
            return False

    except Exception as e:
        log.error("Password verification error: %s", e)
        return False


# ---------------------------------------------------------------------------
# Generowanie tokenów JWT (kompatybilne z SimpleJWT)
# ---------------------------------------------------------------------------

def _generate_tokens(user_id: int) -> dict:
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


def _refresh_access_token(refresh_token_str: str) -> dict | None:
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


# ---------------------------------------------------------------------------
# Dekodowanie / walidacja JWT
# ---------------------------------------------------------------------------

def _decode_jwt(token: str) -> dict | None:
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


# ---------------------------------------------------------------------------
# Dekorator @require_auth
# ---------------------------------------------------------------------------

def require_auth(f):
    """
    Dekorator do zabezpieczania endpointów.

    Oczekuje nagłówka:
        Authorization: Bearer <jwt_token>

    Po pomyślnej weryfikacji ustawia:
        g.user_id   — ID użytkownika Django
        g.user      — dict z danymi usera (jeśli VERIFY_USER_IN_DB=true)
        g.jwt_payload — cały payload JWT
    """
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")

        if not auth_header.startswith("Bearer "):
            return jsonify({"success": False, "error": "Brak tokenu autoryzacji"}), 401

        token = auth_header[7:]  # Usuń "Bearer "

        payload = _decode_jwt(token)
        if payload is None:
            return jsonify({"success": False, "error": "Nieprawidłowy lub wygasły token"}), 401

        user_id = payload.get("user_id")
        if user_id is None:
            return jsonify({"success": False, "error": "Token nie zawiera user_id"}), 401

        g.jwt_payload = payload
        g.user_id = user_id

        if VERIFY_USER_IN_DB:
            user = _verify_user_active(user_id)
            if user is None:
                return jsonify({
                    "success": False,
                    "error": "Użytkownik nieaktywny lub nie istnieje",
                }), 403
            g.user = user
        else:
            g.user = {"id": user_id}

        return f(*args, **kwargs)

    return decorated


# ---------------------------------------------------------------------------
# Endpointy logowania
# ---------------------------------------------------------------------------

@auth_bp.route("/api/auth/login", methods=["POST"])
def login():
    """
    Logowanie — weryfikuje email + password w bazie Django,
    zwraca tokeny access + refresh (kompatybilne z SimpleJWT).

    Request body (JSON):
        { "email": "...", "password": "..." }

    Response 200:
        {
            "success": true,
            "access": "<jwt_access_token>",
            "refresh": "<jwt_refresh_token>",
            "user": { "id": 1, "username": "...", "email": "...", ... }
        }
    """
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"success": False, "error": "Brak danych JSON"}), 400

    # Frontend może przysyłać pole jako "username", "email" lub "login"
    email = (data.get("email") or data.get("username") or data.get("login") or "").strip()
    password = data.get("password") or ""

    if not email or not password:
        return jsonify({"success": False, "error": "Podaj email i hasło"}), 400

    if not DJANGO_SECRET_KEY:
        log.error("DJANGO_SECRET_KEY is not configured — cannot generate tokens")
        return jsonify({"success": False, "error": "Serwer nie jest skonfigurowany do autoryzacji"}), 500

    # Znajdź użytkownika w bazie
    user = _find_user_by_email(email)
    if user is None:
        log.info("Login failed: user '%s' not found", email)
        return jsonify({"success": False, "error": "Nieprawidłowy login lub hasło"}), 401

    # Logujemy dane pobrane z bazy (ukrywając hash hasła)
    safe_user_data = {k: v for k, v in user.items() if k != "password"}
    log.info("Dane uzytkownika pobrane z bazy: %s", safe_user_data)

    # Sprawdź czy konto jest aktywne
    if not user["is_active"]:
        log.info("Login failed: user '%s' is inactive", email)
        return jsonify({"success": False, "error": "Konto jest nieaktywne"}), 403

    # Weryfikuj hasło
    if not _check_django_password(password, user["password"]):
        log.info("Login failed: wrong password for user '%s'", email)
        return jsonify({"success": False, "error": "Nieprawidłowy login lub hasło"}), 401

    # Generuj tokeny
    tokens = _generate_tokens(user["id"])

    log.info("Login successful: user='%s' id=%s", email, user["id"])
    return jsonify({
        "success": True,
        **tokens,
        "user": {
            "id": user["id"],
            "username": user["username"],
            "email": user["email"],
            "first_name": user["first_name"],
            "last_name": user["last_name"],
            "is_staff": user["is_staff"],
        },
    })


@auth_bp.route("/api/auth/refresh", methods=["POST"])
def refresh():
    """
    Odświeżanie tokenu — przyjmuje refresh token, zwraca nowy access token.

    Request body (JSON):
        { "refresh": "<jwt_refresh_token>" }

    Response 200:
        { "success": true, "access": "<new_jwt_access_token>" }
    """
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"success": False, "error": "Brak danych JSON"}), 400

    refresh_token = (data.get("refresh") or "").strip()
    if not refresh_token:
        return jsonify({"success": False, "error": "Brak refresh tokenu"}), 400

    result = _refresh_access_token(refresh_token)
    if result is None:
        return jsonify({"success": False, "error": "Nieprawidłowy lub wygasły refresh token"}), 401

    return jsonify({"success": True, **result})


@auth_bp.route("/api/auth/me", methods=["GET"])
@require_auth
def me():
    """
    Zwraca dane zalogowanego użytkownika na podstawie tokenu.

    Response 200:
        { "success": true, "user": { ... } }
    """
    user_data = g.user.copy()
    user_data.pop("password", None)
    return jsonify({"success": True, "user": user_data})
