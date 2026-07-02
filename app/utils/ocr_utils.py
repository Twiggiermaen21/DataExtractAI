import os
import base64
import re
import logging

import fitz  # PyMuPDF

try:
    from docx import Document as DocxDocument
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False

log = logging.getLogger(__name__)


def get_llm_api_url(default=None):
    """Read the LLM chat-completions endpoint from supported env names."""
    return (
        os.environ.get("llm_api_url")
        or os.environ.get("LLM_API_URL")
        or default
    )


def normalize_llm_api_url(api_url):
    """Return the configured LLM API URL without adding an endpoint path."""
    if not api_url or not api_url.strip():
        raise ValueError("Brak LLM_API_URL w konfiguracji")

    return api_url.strip().rstrip("/")


def get_llm_models_url(api_url):
    """Return the model-list endpoint for the configured LLM API."""
    completion_url = normalize_llm_api_url(api_url)
    return completion_url.removesuffix("/chat/completions") + "/models"


def llm_get(api_url, **kwargs):
    import requests

    session = requests.Session()
    session.trust_env = False
    return session.get(normalize_llm_api_url(api_url), **kwargs)


def llm_post(api_url, **kwargs):
    import requests

    session = requests.Session()
    session.trust_env = False
    return session.post(normalize_llm_api_url(api_url), **kwargs)


def check_connection(api_url):
    """Sprawdza połączenie z API LLM."""
    try:
        models_url = get_llm_models_url(api_url)
        response = llm_get(models_url, timeout=5)
        if response.status_code == 200:
            log.info("Połączono z LLM API: %s", models_url)
        else:
            log.warning("LLM API odpowiedziało kodem %s: %s", response.status_code, models_url)
    except Exception:
        log.warning("Brak połączenia z LLM API: %s", api_url)


def extract_fields_from_template(template_path):
    """Pobiera pola z szablonu HTML (atrybuty name z inputów)."""
    try:
        with open(template_path, 'r', encoding='utf-8') as f:
            content = f.read()
        fields = []
        seen = set()
        for field in re.findall(r'name=["\']([^"\']+)["\']', content):
            if field.startswith('$') or '{' in field or field in seen:
                continue
            seen.add(field)
            fields.append(field)

        return fields
    except Exception:
        return []


def image_to_base64(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def get_mime_type(path):
    ext = os.path.splitext(path)[1].lower()
    return {
        ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
        ".png": "image/png", ".webp": "image/webp",
    }.get(ext, "image/png")


def extract_text_from_docx(path):
    """Wyciąga tekst z pliku DOCX."""
    if not DOCX_AVAILABLE:
        raise Exception("python-docx nie jest zainstalowane")
    doc = DocxDocument(path)
    return "\n".join(p.text for p in doc.paragraphs if p.text.strip())


def extract_text_from_pdf(path):
    """Wyciąga tekst z całego pliku PDF."""
    doc = fitz.open(path)
    text = "".join(page.get_text() for page in doc)
    doc.close()
    return text.strip()


def extract_text_from_pdf_pages(path):
    """Wyciąga tekst z każdej strony PDF osobno. Zwraca listę stringów."""
    doc = fitz.open(path)
    pages = [page.get_text().strip() for page in doc]
    doc.close()
    return pages
