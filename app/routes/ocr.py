import os
import json
import logging
from flask import Blueprint, request, jsonify, current_app, send_from_directory
from werkzeug.utils import secure_filename

from app.services.ocr_pipeline import get_pipeline, unload_pipeline
from app.extensions import limiter

log = logging.getLogger(__name__)

ocr_bp = Blueprint('ocr', __name__)

IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif', '.webp'}
ALLOWED_EXTENSIONS = IMAGE_EXTENSIONS | {'.pdf', '.docx', '.doc', '.xml'}
MAX_UPLOAD_SIZE = 20 * 1024 * 1024  # 20 MB


def _safe_upload_path(folder, filename):
    """Zwraca bezpieczną ścieżkę pliku i weryfikuje brak path traversal."""
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


@ocr_bp.route('/api/extract_pdf_text', methods=['POST'])
def extract_pdf_text():
    """Wyciąga surowy tekst z PDF/DOCX bez wysyłania do LLM."""
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

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@ocr_bp.route('/api/process_ocr', methods=['POST'])
@limiter.limit("10 per minute")
def process_ocr():
    """OCR — przetwarza pliki i zwraca wyekstrahowane dane."""
    if 'files' not in request.files:
        return jsonify({'success': False, 'error': 'Brak plików'}), 400

    files = request.files.getlist('files')
    if not files or files[0].filename == '':
        return jsonify({'success': False, 'error': 'Nie wybrano plików'}), 400

    template_name = request.form.get('template', 'wezwanie_do_zaplaty.html')
    template_path = os.path.join(current_app.root_path, '..', 'templates', 'documents', template_name)
    model_name = request.form.get('model')

    # Odczytaj wybrane kolumny (z checkboxów "Dane do odczytu")
    columns_raw = request.form.get('selected_columns', '')
    selected_columns = [c.strip() for c in columns_raw.split(',') if c.strip()] or None

    try:
        pipeline = get_pipeline(template_path if os.path.exists(template_path) else None,
                                model=model_name, selected_columns=selected_columns)
        if pipeline is None:
            return jsonify({'success': False, 'error': 'Nie można połączyć z LM Studio'}), 500
    except Exception as e:
        log.exception("Błąd inicjalizacji pipeline")
        return jsonify({'success': False, 'error': f'Błąd: {str(e)}'}), 500

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
                saved = res.save_to_json(save_path=current_app.config['OUTPUT_FOLDER'])
                if saved:
                    processed_files.append(os.path.basename(saved))

                if hasattr(res, 'extracted_data') and res.extracted_data:
                    documents.append({
                        'filename': filename, 
                        'fields': res.extracted_data,
                        'is_vision': getattr(res, 'is_vision', False)
                    })
                    has_data = True

            if not has_data:
                errors.append({'file': filename, 'error': f'Model nie zwrócił danych dla pliku: {filename}'})

        except Exception as e:
            log.exception("OCR error for %s", filename)
            errors.append({'file': filename, 'error': str(e)})

    # unload_pipeline()

    return jsonify({
        'success': True,
        'processed': processed_files,
        'documents': documents,
        'errors': errors,
        'message': f'Przetworzono {len(processed_files)} plików',
    })


@ocr_bp.route('/api/get_results')
def get_results():
    """Zwraca listę plików JSON z folderu output."""
    output_folder = current_app.config['OUTPUT_FOLDER']
    if not os.path.exists(output_folder):
        return jsonify([])
    try:
        files = sorted([f for f in os.listdir(output_folder) if f.endswith('.json')], reverse=True)
        return jsonify(files)
    except Exception:
        return jsonify([])


@ocr_bp.route('/api/get_result/<filename>')
def get_result(filename):
    """Zwraca zawartość pliku JSON."""
    safe_name = secure_filename(filename)
    if not safe_name or not safe_name.endswith('.json'):
        return jsonify({'error': 'Nieprawidłowa nazwa pliku'}), 400
    output_folder = current_app.config['OUTPUT_FOLDER']
    path = os.path.realpath(os.path.join(output_folder, safe_name))
    if not path.startswith(os.path.realpath(output_folder)):
        return jsonify({'error': 'Niedozwolona ścieżka'}), 400
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return jsonify(json.load(f))
    except FileNotFoundError:
        return jsonify({'error': 'Nie znaleziono pliku'}), 404
    except Exception as e:
        log.exception("Błąd odczytu JSON: %s", safe_name)
        return jsonify({'error': str(e)}), 500


@ocr_bp.route('/input/<filename>')
def serve_input(filename):
    return send_from_directory(current_app.config['UPLOAD_FOLDER'], filename)


@ocr_bp.route('/saved/<filename>')
def serve_saved(filename):
    return send_from_directory(current_app.config['SAVED_FOLDER'], filename)