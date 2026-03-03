import os
import base64
import requests
import re

try:
    from docx import Document as DocxDocument
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False
    print("⚠️ python-docx not installed - DOCX support disabled")

def check_connection(api_url):
    try:
        base_url = api_url.replace("/chat/completions", "/models")
        response = requests.get(base_url, timeout=5)
        if response.status_code == 200:
            print("✅ Połączono z LM Studio!")
    except:
        print("⚠️ LM Studio nie odpowiada")

def extract_fields_from_template(template_path):
    """Pobiera pola z szablonu HTML (atrybuty name z inputów)."""
    try:
        with open(template_path, 'r', encoding='utf-8') as f:
            content = f.read()
        # Wyciągnij nazwy pól i odfiltruj błędne (np. JavaScript template literals)
        all_fields = list(set(re.findall(r'name=["\']([^"\']+)["\']', content)))
        fields = [f for f in all_fields if not f.startswith('$') and not '{' in f]
        return fields
    except Exception as e:
        print(f"⚠️ Błąd odczytu szablonu: {e}")
        return []

def image_to_base64(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")

def get_mime_type(path):
    ext = os.path.splitext(path)[1].lower()
    return {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}.get(ext, "image/png")

def extract_text_from_docx(path):
    """Wyciąga tekst z pliku DOCX."""
    if not DOCX_AVAILABLE:
        raise Exception("python-docx nie jest zainstalowane")
    doc = DocxDocument(path)
    return "\n".join([p.text for p in doc.paragraphs if p.text.strip()])

def extract_text_from_pdf(path):
    """Wyciąga tekst z pliku PDF."""
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(path)
        text = ""
        for page in doc:
            text += page.get_text()
        doc.close()
        return text.strip()
    except ImportError:
        raise Exception("PyMuPDF (fitz) nie jest zainstalowane. Uruchom: pip install pymupdf")
