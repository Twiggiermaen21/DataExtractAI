import logging
import psycopg

from app.core.auth.config import DB_NAME, DB_USER, DB_PASSWORD, DB_HOST, DB_PORT

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Baza danych
# ---------------------------------------------------------------------------

def get_db_connection():
    """Tworzy nowe połączenie do bazy PostgreSQL Django."""
    return psycopg.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT,
    )

def verify_user_active(user_id: int) -> dict | None:
    """
    Sprawdza w bazie Django czy użytkownik istnieje i jest aktywny.
    Zwraca dict z danymi usera lub None.
    """
    try:
        conn = get_db_connection()
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

def find_user_by_email(email: str) -> dict | None:
    """
    Wyszukuje użytkownika po email w tabeli api_user Django.
    Zwraca dict z danymi lub None.
    """
    try:
        conn = get_db_connection()
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

