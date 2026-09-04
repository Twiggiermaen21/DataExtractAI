import hashlib
import hmac
import base64
import logging

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Weryfikacja hasła Django (PBKDF2-SHA256)
# ---------------------------------------------------------------------------

def check_django_password(raw_password: str, encoded: str) -> bool:
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

