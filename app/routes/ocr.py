import os
from flask import Blueprint, request, jsonify, current_app, send_from_directory, redirect, url_for
from app.services.ocr_service import get_pipeline

ocr_bp = Blueprint('ocr', __name__)

@ocr_bp.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'Brak pliku'}), 400
    files = request.files.getlist('file')
    saved_count = 0
    for file in files:
        if file.filename != '':
            file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], file.filename))
            saved_count += 1
    return jsonify({'success': True, 'count': saved_count})

@ocr_bp.route('/process_selected', methods=['POST'])
def process_selected():
    pipeline = get_pipeline()
    if pipeline is None:
        return jsonify({'success': False, 'error': 'Model AI niedostępny'}), 500

    data = request.get_json()
    files_to_process = data.get('files', [])
    processed_count = 0
    
    for filename in files_to_process:
        path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        if os.path.exists(path):
            try:
                output = pipeline.predict(path)
                for res in output:
                    res.save_to_json(save_path=current_app.config['OUTPUT_FOLDER'])
                    res.save_to_markdown(save_path=current_app.config['OUTPUT_FOLDER'])
                processed_count += 1
            except Exception as e:
                print(f"Błąd OCR {filename}: {e}")

    return jsonify({'success': True, 'count': processed_count})

# Obsługa serwowania plików dla podglądu
@ocr_bp.route('/input/<filename>')
def serve_input(filename):
    return send_from_directory(current_app.config['UPLOAD_FOLDER'], filename)

@ocr_bp.route('/delete_selected', methods=['POST'])
def delete_selected():
    data = request.get_json()
    count = 0
    for filename in data.get('files', []):
        path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        if os.path.exists(path):
            os.remove(path)
            count += 1
    return jsonify({'success': True, 'count': count})

import os
from flask import current_app, redirect, url_for
# Pamiętaj o imporcie funkcji! 
# Jeśli image_enhancer.py jest w tym samym folderze co ten plik, użyj kropki:
from services.image_enhancer import enhance_image_for_ocr 

@ocr_bp.route('/process/<filename>')
def process_single_file(filename):
    """
    Kompatybilność wsteczna: przetwarza jeden plik i wraca na dashboard.
    """
    pipeline = get_pipeline()
    if pipeline is None:
        return "Model AI niedostępny", 500

    original_file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
    
    if os.path.exists(original_file_path):
        # Domyślnie ścieżką do procesowania jest oryginał
        path_to_process = original_file_path
        temp_enhanced_path = None

        # --- KROK 1: Upscaling i poprawa jakości ---
        try:
            # Próbujemy powiększyć i wyczyścić obraz (skala 2x)
            print(f"Rozpoczynam optymalizację obrazu: {filename}")
            temp_enhanced_path = enhance_image_for_ocr(original_file_path, scale_factor=2)
            
            # Jeśli się udało, podmieniamy ścieżkę na ulepszoną
            path_to_process = temp_enhanced_path
            print(f"Sukces! OCR otrzyma ulepszony plik: {temp_enhanced_path}")
            
        except Exception as e:
            print(f"Nie udało się ulepszyć obrazu (błąd: {e}). Używam oryginału.")
            # W razie błędu path_to_process nadal wskazuje na original_file_path

        # --- KROK 2: Właściwy OCR ---
        try:
            # pipeline.predict dostaje teraz (potencjalnie) lepszy obraz
            output = pipeline.predict(path_to_process)
            
            for res in output:
                # Zapisujemy wyniki. Uwaga: res.save_to_json może użyć nazwy pliku 
                # tymczasowego (np. 'ocr_ready_faktura.json'). 
                res.save_to_json(save_path=current_app.config['OUTPUT_FOLDER'])
                res.save_to_markdown(save_path=current_app.config['OUTPUT_FOLDER'])
                
        except Exception as e:
            print(f"Błąd przetwarzania OCR: {e}")
            
        finally:
            # --- KROK 3: Sprzątanie ---
            # Usuwamy plik tymczasowy 'ocr_ready_...', żeby nie zaśmiecać serwera
            if temp_enhanced_path and os.path.exists(temp_enhanced_path):
                try:
                    os.remove(temp_enhanced_path)
                    print(f"Usunięto plik tymczasowy: {temp_enhanced_path}")
                except Exception as cleanup_error:
                    print(f"Błąd przy usuwaniu pliku tmp: {cleanup_error}")
            
    # Przekieruj z powrotem do widoku głównego
    return redirect(url_for('main.index'))