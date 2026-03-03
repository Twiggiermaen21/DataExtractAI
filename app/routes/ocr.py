import os
import json
import traceback
from flask import Blueprint, request, jsonify, current_app, send_from_directory

from app.services.ocr_pipeline import get_pipeline, unload_pipeline

ocr_bp = Blueprint('ocr', __name__)

IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif', '.webp'}


@ocr_bp.route('/api/extract_pdf_text', methods=['POST'])
def extract_pdf_text():
    """Wyciąga surowy tekst z PDF/DOCX bez wysyłania do LLM. Używane dla KRS."""
    print("Wywołano funkcję: extract_pdf_text")
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
            try:
                import fitz
                doc = fitz.open(filepath)
                for page in doc:
                    text += page.get_text()
                doc.close()
            except ImportError:
                return jsonify({'success': False, 'error': 'PyMuPDF nie zainstalowane'}), 500
        elif ext in ['.docx', '.doc']:
            try:
                from docx import Document as DocxDocument
                doc = DocxDocument(filepath)
                text = "\n".join([p.text for p in doc.paragraphs if p.text.strip()])
            except ImportError:
                return jsonify({'success': False, 'error': 'python-docx nie zainstalowane'}), 500
        else:
            # Dla plików tekstowych
            with open(filepath, 'r', encoding='utf-8') as f:
                text = f.read()
        
        text = text.strip()
        original_len = len(text)
        
        if original_len > 3000:
            pass  # usuniety print
            text = text[:3000]
        
        pass  # usuniety print
        
        return jsonify({
            'success': True,
            'text': text,
            'filename': filename,
            'original_length': original_len,
            'truncated': original_len > 3000
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@ocr_bp.route('/api/process_ocr', methods=['POST'])
def process_ocr():
    """OCR - przetwarza pliki i zwraca wyekstrahowane dane."""
    print("Wywołano funkcję: process_ocr")
    if 'files' not in request.files:
        return jsonify({'success': False, 'error': 'Brak plików'}), 400
    
    files = request.files.getlist('files')
    if not files or files[0].filename == '':
        return jsonify({'success': False, 'error': 'Nie wybrano plików'}), 400
    
    # Pobierz szablon (opcjonalnie)
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
    documents = []  # Tablica z danymi z każdego dokumentu osobno
    errors = []
    
    for file in files:
        if file.filename == '':
            continue
            
        filename = file.filename
        original_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        
        try:
            file.save(original_path)
            pass  # usuniety print
            
            # OCR
            ocr_output = pipeline.predict(original_path)
            
            for res in ocr_output:
                saved = res.save_to_json(save_path=current_app.config['OUTPUT_FOLDER'])
                if saved:
                    processed_files.append(os.path.basename(saved))
                
                # Dodaj dane z tego dokumentu do listy
                if hasattr(res, 'extracted_data') and res.extracted_data:
                    documents.append({
                        'filename': filename,
                        'fields': res.extracted_data
                    })
            
            pass  # usuniety print
            
        except Exception as e:
            pass  # usuniety print
            traceback.print_exc()
            errors.append({'file': filename, 'error': str(e)})
    
    unload_pipeline()
    
    return jsonify({
        'success': True,
        'processed': processed_files,
        'documents': documents,  # Tablica z danymi z każdego pliku
        'errors': errors,
        'message': f'Przetworzono {len(processed_files)} plików'
    })


@ocr_bp.route('/api/get_results')
def get_results():
    """Zwraca listę plików JSON z folderu output."""
    print("Wywołano funkcję: get_results")
    output_folder = current_app.config['OUTPUT_FOLDER']
    
    if not os.path.exists(output_folder):
        return jsonify([])
    
    try:
        files = [f for f in os.listdir(output_folder) if f.endswith('.json')]
        files.sort(reverse=True)
        return jsonify(files)
    except:
        return jsonify([])


@ocr_bp.route('/api/get_result/<filename>')
def get_result(filename):
    """Zwraca zawartość pliku JSON."""
    print("Wywołano funkcję: get_result")
    try:
        path = os.path.join(current_app.config['OUTPUT_FOLDER'], filename)
        with open(path, 'r', encoding='utf-8') as f:
            return jsonify(json.load(f))
    except Exception as e:
        return jsonify({'error': str(e)}), 404


@ocr_bp.route('/input/<filename>')
def serve_input(filename):
    """Serwuje plik wejściowy."""
    print("Wywołano funkcję: serve_input")
    return send_from_directory(current_app.config['UPLOAD_FOLDER'], filename)