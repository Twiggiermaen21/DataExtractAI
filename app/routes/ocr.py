import os
import logging
from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required
from werkzeug.utils import secure_filename

from app.services.ocr_pipeline import get_pipeline
from app.extensions import limiter

log = logging.getLogger(__name__)

ocr_bp = Blueprint('ocr', __name__)

IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif', '.webp'}
ALLOWED_EXTENSIONS = IMAGE_EXTENSIONS | {'.pdf', '.docx', '.doc', '.xml'}
MAX_UPLOAD_SIZE = 20 * 1024 * 1024  # 20 MB


def _safe_upload_path(folder, filename):
    filename = secure_filename(filename)
    if not filename:
        return None, "Nieprawidłowa nazwa pliku"
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        return None, f"Niedozwolone rozszerzenie: {ext}"
    path = os.path.realpath(os.path.join(folder, filename))
    if not path.startswith(os.path.realpath(folder)):
        return None, "Niedozwolona ścieżka pliku"
    return path, None


def _safe_unlink(path):
    try:
        if path and os.path.exists(path):
            os.remove(path)
    except Exception:
        log.warning("Nie udało się usunąć pliku tymczasowego: %s", path)


@ocr_bp.route('/api/extract_pdf_text', methods=['POST'])
@login_required
def extract_pdf_text():
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'Brak pliku'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'error': 'Pusta nazwa pliku'}), 400

    file.stream.seek(0, 2)
    size = file.stream.tell()
    file.stream.seek(0)
    if size > MAX_UPLOAD_SIZE:
        return jsonify({'success': False, 'error': 'Plik za duży (max 20 MB)'}), 413

    filepath, err = _safe_upload_path(current_app.config['UPLOAD_FOLDER'], file.filename)
    if err:
        return jsonify({'success': False, 'error': err}), 400
    filename = os.path.basename(filepath)

    try:
        file.save(filepath)
        ext = os.path.splitext(filename)[1].lower()
        text = ''

        if ext == '.pdf':
            import fitz
            doc = fitz.open(filepath)
            text = "".join(page.get_text() for page in doc)
            doc.close()
        elif ext in ('.docx', '.doc'):
            from docx import Document as DocxDocument
            doc = DocxDocument(filepath)
            text = "\n".join(p.text for p in doc.paragraphs if p.text.strip())
        else:
            with open(filepath, 'r', encoding='utf-8') as f:
                text = f.read()

        text = text.strip()
        original_len = len(text)
        if original_len > 3000:
            text = text[:3000]

        return jsonify({
            'success': True,
            'text': text,
            'filename': filename,
            'original_length': original_len,
            'truncated': original_len > 3000,
        })
    except Exception:
        log.exception("Błąd extract_pdf_text")
        return jsonify({'success': False, 'error': 'Błąd przetwarzania pliku'}), 500
    finally:
        _safe_unlink(filepath)


@ocr_bp.route('/api/process_ocr', methods=['POST'])
@limiter.limit("100 per minute")
@login_required
def process_ocr():
    if 'files' not in request.files:
        return jsonify({'success': False, 'error': 'Brak plików'}), 400

    files = request.files.getlist('files')
    if not files or files[0].filename == '':
        return jsonify({'success': False, 'error': 'Nie wybrano plików'}), 400

    template_name = request.form.get('template', 'wezwanie_do_zaplaty.html')
    model_name = request.form.get('model')
    columns_raw = request.form.get('selected_columns', '')
    selected_columns = [c.strip() for c in columns_raw.split(',') if c.strip()] or None

    try:
        template_full_path = None
        if template_name:
            safe_template_name = secure_filename(template_name)
            if safe_template_name.endswith(".html"):
                candidate = os.path.realpath(os.path.join(current_app.root_path, '..', 'templates', 'documents', safe_template_name))
                templates_root = os.path.realpath(os.path.join(current_app.root_path, '..', 'templates', 'documents'))
                if candidate.startswith(templates_root) and os.path.exists(candidate):
                    template_full_path = candidate

        pipeline = get_pipeline(template_full_path, model=model_name, selected_columns=selected_columns)
        if pipeline is None:
            return jsonify({'success': False, 'error': 'Nie można połączyć z LM Studio'}), 500
    except Exception:
        log.exception("Błąd inicjalizacji pipeline")
        return jsonify({'success': False, 'error': 'Błąd inicjalizacji OCR'}), 500

    processed_files = []
    documents = []
    errors = []

    for file in files:
        if file.filename == '':
            continue

        file.stream.seek(0, 2)
        size = file.stream.tell()
        file.stream.seek(0)
        if size > MAX_UPLOAD_SIZE:
            errors.append({'file': file.filename, 'error': 'Plik za duży (max 20 MB)'})
            continue

        original_path, err = _safe_upload_path(current_app.config['UPLOAD_FOLDER'], file.filename)
        if err:
            errors.append({'file': file.filename, 'error': err})
            continue
        filename = os.path.basename(original_path)

        try:
            file.save(original_path)
            ocr_output = pipeline.predict(original_path)
            has_data = False
            for res in ocr_output:
                processed_files.append(filename)
                if hasattr(res, 'extracted_data') and res.extracted_data:
                    documents.append({
                        'filename': filename,
                        'fields': res.extracted_data,
                        'is_vision': getattr(res, 'is_vision', False)
                    })
                    has_data = True

            if not has_data:
                errors.append({'file': filename, 'error': f'Model nie zwrócił danych dla pliku: {filename}'})
        except Exception:
            log.exception("OCR error for %s", filename)
            errors.append({'file': filename, 'error': 'Błąd OCR dla pliku'})
        finally:
            _safe_unlink(original_path)

    return jsonify({
        'success': True,
        'processed': processed_files,
        'documents': documents,
        'errors': errors,
        'message': f'Przetworzono {len(processed_files)} plików',
    })


@ocr_bp.route('/api/get_results')
@login_required
def get_results():
    return jsonify([])


@ocr_bp.route('/api/get_result/<filename>')
@login_required
def get_result(filename):
    return jsonify({'error': 'Odczyt zapisanych wyników jest wyłączony w tej wersji.'}), 410


@ocr_bp.route('/input/<filename>')
@login_required
def serve_input(filename):
    return jsonify({'error': 'Dostęp do katalogu input jest wyłączony w tej wersji.'}), 410


@ocr_bp.route('/saved/<filename>')
@login_required
def serve_saved(filename):
    return jsonify({'error': 'Dostęp do katalogu saved jest wyłączony w tej wersji.'}), 410
