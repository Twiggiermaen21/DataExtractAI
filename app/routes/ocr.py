import os
import json
import traceback
from flask import Blueprint, request, jsonify, current_app, send_from_directory

from app.services.ocr_service import get_pipeline, unload_pipeline
from app.services.image_enhancer import enhance_image_for_ocr

ocr_bp = Blueprint('ocr', __name__)

IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif', '.webp'}


@ocr_bp.route('/api/process_ocr', methods=['POST'])
def process_ocr():
    """OCR - przetwarza pliki i zwraca wyekstrahowane dane."""
    if 'files' not in request.files:
        return jsonify({'success': False, 'error': 'Brak plików'}), 400
    
    files = request.files.getlist('files')
    if not files or files[0].filename == '':
        return jsonify({'success': False, 'error': 'Nie wybrano plików'}), 400
    
    # Pobierz szablon (opcjonalnie)
    template_name = request.form.get('template', 'wezwanie_do_zaplaty.html')
    template_path = os.path.join(current_app.root_path, '..', 'templates', 'documents', template_name)
    
    try:
        pipeline = get_pipeline(template_path if os.path.exists(template_path) else None)
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
        temp_enhanced_path = None
        
        try:
            file.save(original_path)
            print(f"📁 Przetwarzanie: {filename}")
            
            path_to_process = original_path
            file_ext = os.path.splitext(filename)[1].lower()
            
            if file_ext in IMAGE_EXTENSIONS:
                try:
                    temp_enhanced_path = enhance_image_for_ocr(original_path, scale_factor=1.5)
                    path_to_process = temp_enhanced_path
                except:
                    pass
            
            # OCR
            ocr_output = pipeline.predict(path_to_process)
            
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
            
            # Usuń temp
            if temp_enhanced_path and os.path.exists(temp_enhanced_path):
                try: os.remove(temp_enhanced_path)
                except: pass
            
            print(f"  ✅ Sukces!")
            
        except Exception as e:
            print(f"  ❌ Błąd: {e}")
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
    try:
        path = os.path.join(current_app.config['OUTPUT_FOLDER'], filename)
        with open(path, 'r', encoding='utf-8') as f:
            return jsonify(json.load(f))
    except Exception as e:
        return jsonify({'error': str(e)}), 404


@ocr_bp.route('/input/<filename>')
def serve_input(filename):
    """Serwuje plik wejściowy."""
    return send_from_directory(current_app.config['UPLOAD_FOLDER'], filename)