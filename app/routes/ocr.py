import os
import json
import logging
import tempfile
from flask import Blueprint, request, jsonify, current_app
from werkzeug.utils import secure_filename

from app.services.ocr_pipeline import get_pipeline, unload_pipeline
from app.extensions import limiter

log = logging.getLogger(__name__)

ocr_bp = Blueprint('ocr', __name__, url_prefix='/api')

IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif', '.webp'}
ALLOWED_EXTENSIONS = IMAGE_EXTENSIONS | {'.pdf', '.docx', '.doc', '.xml'}
MAX_UPLOAD_SIZE = 20 * 1024 * 1024  # 20 MB



def _save_upload_to_temp(file_storage):
    """Zapisuje upload do pliku tymczasowego (bez input/output)."""
    filename = secure_filename(file_storage.filename or "")
    if not filename:
        return None, "Nieprawidlowa nazwa pliku"

    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        return None, f"Niedozwolone rozszerzenie: {ext}"

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
    tmp_path = tmp.name
    tmp.close()
    file_storage.save(tmp_path)
    return tmp_path, None


@ocr_bp.route('/extract_pdf_text', methods=['POST'])
def extract_pdf_text():
    """Wyciaga surowy tekst z PDF/DOCX bez wysylania do LLM."""
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'Brak pliku'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'error': 'Pusta nazwa pliku'}), 400

    file.stream.seek(0, 2)
    size = file.stream.tell()
    file.stream.seek(0)
    if size > MAX_UPLOAD_SIZE:
        return jsonify({'success': False, 'error': 'Plik za duzy (max 20 MB)'}), 413

    filename = secure_filename(file.filename)
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        return jsonify({'success': False, 'error': f'Niedozwolone rozszerzenie: {ext}'}), 400

    filepath, err = _save_upload_to_temp(file)
    if err:
        return jsonify({'success': False, 'error': err}), 400

    try:
        text = ''

        if ext == '.pdf':
            import fitz
            doc = fitz.open(filepath)
            text = ''.join(page.get_text() for page in doc)
            doc.close()
        elif ext in ('.docx', '.doc'):
            from docx import Document as DocxDocument
            doc = DocxDocument(filepath)
            text = '\n'.join(p.text for p in doc.paragraphs if p.text.strip())
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

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        try:
            if filepath and os.path.exists(filepath):
                os.remove(filepath)
        except Exception:
            pass


@ocr_bp.route('/process_ocr', methods=['POST'])
@limiter.limit('100 per minute', methods=['POST'])
def process_ocr():
    """OCR - przetwarza pliki i zwraca wyekstrahowane dane (bez zapisu input/output)."""
    if 'files' not in request.files:
        return jsonify({'success': False, 'error': 'Brak plikow'}), 400

    files = request.files.getlist('files')
    if not files or files[0].filename == '':
        return jsonify({'success': False, 'error': 'Nie wybrano plikow'}), 400

    template_name = request.form.get('template', 'podsumowanie.html')
    template_path = os.path.join(current_app.config['TEMPLATES_FOLDER'], template_name)
    model_name = request.form.get('model')

    columns_raw = request.form.get('selected_columns', '')
    selected_columns = [c.strip() for c in columns_raw.split(',') if c.strip()] or None

    try:
        pipeline = get_pipeline(
            template_path if os.path.exists(template_path) else None,
            model=model_name,
            selected_columns=selected_columns,
        )
        if pipeline is None:
            return jsonify({'success': False, 'error': 'Nie mozna polaczyc z LM Studio'}), 500
    except Exception as e:
        log.exception('Blad inicjalizacji pipeline')
        return jsonify({'success': False, 'error': f'Blad: {str(e)}'}), 500

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
            errors.append({'file': file.filename, 'error': 'Plik za duzy (max 20 MB)'})
            continue

        temp_path, err = _save_upload_to_temp(file)
        if err:
            errors.append({'file': file.filename, 'error': err})
            continue

        filename = secure_filename(file.filename)

        try:
            ocr_output = pipeline.predict(temp_path)

            has_data = False
            for res in ocr_output:
                if hasattr(res, 'extracted_data') and res.extracted_data:
                    documents.append({
                        'filename': filename,
                        'fields': res.extracted_data,
                        'is_vision': getattr(res, 'is_vision', False),
                    })
                    has_data = True

            if not has_data:
                errors.append({'file': filename, 'error': f'Model nie zwrocil danych dla pliku: {filename}'})

        except Exception as e:
            log.exception('OCR error for %s', filename)
            errors.append({'file': filename, 'error': str(e)})
        finally:
            try:
                if temp_path and os.path.exists(temp_path):
                    os.remove(temp_path)
            except Exception:
                pass

    return jsonify({
        'success': True,
        'processed': processed_files,
        'documents': documents,
        'errors': errors,
        'message': f'Przetworzono {len(documents)} rekordow',
    })
