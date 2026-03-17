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


def check_connection(api_url):
    """Sprawdza połączenie z API LLM."""
    import requests
    try:
        base_url = api_url.replace("/chat/completions", "/models")
        response = requests.get(base_url, timeout=5)
        if response.status_code == 200:
            log.info("Połączono z LLM API: %s", base_url)
    except Exception:
        log.warning("Brak połączenia z LLM API: %s", api_url)


def extract_fields_from_template(template_path):
    """Pobiera pola z szablonu HTML (atrybuty name z inputów)."""
    try:
        with open(template_path, 'r', encoding='utf-8') as f:
            content = f.read()
        all_fields = list(set(re.findall(r'name=["\']([^"\']+)["\']', content)))
        return [f for f in all_fields if not f.startswith('$') and '{' not in f]
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
