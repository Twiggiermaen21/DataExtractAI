"""
Endpointy autoryzacji JWT — /api/auth/*
"""

import logging
from flask import Blueprint, request, jsonify, g

from app.core.auth import (
    find_user_by_email,
    check_django_password,
    generate_tokens,
    refresh_access_token,
    require_auth,
    DJANGO_SECRET_KEY,
)

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Blueprint — /api/auth/*
# ---------------------------------------------------------------------------

auth_bp = Blueprint("auth", __name__)


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
    user = find_user_by_email(email)
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
    if not check_django_password(password, user["password"]):
        log.info("Login failed: wrong password for user '%s'", email)
        return jsonify({"success": False, "error": "Nieprawidłowy login lub hasło"}), 401

    # Generuj tokeny
    tokens = generate_tokens(user["id"])

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

    result = refresh_access_token(refresh_token)
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
