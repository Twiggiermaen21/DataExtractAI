import os
import json
import traceback
import logging
from flask import Blueprint, request, jsonify, current_app, send_from_directory

from app.services.ocr_pipeline import get_pipeline, unload_pipeline

log = logging.getLogger(__name__)

ocr_bp = Blueprint('ocr', __name__)

IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif', '.webp'}


@ocr_bp.route('/api/extract_pdf_text', methods=['POST'])
def extract_pdf_text():
    """Wyciąga surowy tekst z PDF/DOCX bez wysyłania do LLM."""
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'Brak pliku'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'error': 'Pusta nazwa pliku'}), 400

    filename = file.filename
    filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)

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

    try:
        pipeline = get_pipeline(template_path if os.path.exists(template_path) else None, model=model_name)
        if pipeline is None:
            return jsonify({'success': False, 'error': 'Nie można połączyć z LM Studio'}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': f'Błąd: {str(e)}'}), 500

    processed_files = []
    documents = []
    errors = []

    for file in files:
        if file.filename == '':
            continue

        filename = file.filename
        original_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)

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

    unload_pipeline()

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
    try:
        path = os.path.join(current_app.config['OUTPUT_FOLDER'], filename)
        with open(path, 'r', encoding='utf-8') as f:
            return jsonify(json.load(f))
    except Exception as e:
        return jsonify({'error': str(e)}), 404


@ocr_bp.route('/input/<filename>')
def serve_input(filename):
    return send_from_directory(current_app.config['UPLOAD_FOLDER'], filename)


@ocr_bp.route('/saved/<filename>')
def serve_saved(filename):
    return send_from_directory(current_app.config['SAVED_FOLDER'], filename)