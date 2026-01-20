import os
import json
import traceback
from flask import Blueprint, request, jsonify, current_app, send_from_directory

from app.services.ocr_service import get_pipeline
from app.services.image_enhancer import enhance_image_for_ocr

ocr_bp = Blueprint('ocr', __name__)


@ocr_bp.route('/api/process_ocr', methods=['POST'])
def process_ocr():
    """
    Główny endpoint OCR:
    1. Przyjmuje pliki
    2. Ładuje model (lazy loading - model pozostaje w pamięci)
    3. Przetwarza każdy plik (poprawa obrazu + OCR)
    4. Zapisuje JSON do output/
    """
    if 'files' not in request.files:
        return jsonify({'success': False, 'error': 'Brak plików'}), 400
    
    files = request.files.getlist('files')
    if not files or files[0].filename == '':
        return jsonify({'success': False, 'error': 'Nie wybrano plików'}), 400

    # Ładowanie modelu
    try:
        pipeline = get_pipeline()
        if pipeline is None:
            return jsonify({'success': False, 'error': 'Nie można załadować modelu OCR'}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': f'Błąd ładowania modelu: {str(e)}'}), 500

    processed_files = []
    errors = []
    
    for file in files:
        if file.filename == '':
            continue
            
        filename = file.filename
        original_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        temp_enhanced_path = None
        
        try:
            # Zapisz plik
            file.save(original_path)
            print(f"📁 Przetwarzanie: {filename}")
            
            # Poprawa obrazu
            path_to_process = original_path
            try:
                temp_enhanced_path = enhance_image_for_ocr(original_path, scale_factor=2)
                path_to_process = temp_enhanced_path
                print(f"  ✨ Obraz ulepszony")
            except Exception as e:
                print(f"  ⚠️ Nie udało się ulepszyć obrazu: {e}")
            
            # OCR
            print(f"  🔍 Uruchamiam OCR...")
            ocr_output = pipeline.predict(path_to_process)
            
            # Zapis wyników do JSON
            for res in ocr_output:
                if hasattr(res, 'save_to_json'):
                    res.save_to_json(save_path=current_app.config['OUTPUT_FOLDER'])
                    print(f"  💾 Zapisano JSON")
            
            processed_files.append(filename)
            print(f"  ✅ Sukces!")
            
        except Exception as e:
            print(f"  ❌ Błąd: {e}")
            traceback.print_exc()
            errors.append({'file': filename, 'error': str(e)})
        
        finally:
            # Usuwanie pliku tymczasowego
            if temp_enhanced_path and os.path.exists(temp_enhanced_path):
                try:
                    os.remove(temp_enhanced_path)
                except:
                    pass
    
    # Model pozostaje w pamięci dla kolejnych żądań
    
    return jsonify({
        'success': True,
        'processed': processed_files,
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
    except Exception as e:
        return jsonify([])


@ocr_bp.route('/api/get_result/<filename>')
def get_result(filename):
    """Zwraca zawartość pliku JSON."""
    try:
        path = os.path.join(current_app.config['OUTPUT_FOLDER'], filename)
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 404


@ocr_bp.route('/input/<filename>')
def serve_input(filename):
    """Serwuje plik wejściowy."""
    return send_from_directory(current_app.config['UPLOAD_FOLDER'], filename)