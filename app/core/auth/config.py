import os

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
