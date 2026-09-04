import functools
from flask import request, jsonify, g

from app.core.auth.config import VERIFY_USER_IN_DB
from app.core.auth.jwt import decode_jwt
from app.core.auth.db import verify_user_active

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

        payload = decode_jwt(token)
        if payload is None:
            return jsonify({"success": False, "error": "Nieprawidłowy lub wygasły token"}), 401

        user_id = payload.get("user_id")
        if user_id is None:
            return jsonify({"success": False, "error": "Token nie zawiera user_id"}), 401

        g.jwt_payload = payload
        g.user_id = user_id

        if VERIFY_USER_IN_DB:
            user = verify_user_active(user_id)
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

