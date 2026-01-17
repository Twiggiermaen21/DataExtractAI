import os
import json
import traceback
from flask import Blueprint, request, jsonify, current_app, send_from_directory, redirect, url_for
from werkzeug.utils import secure_filename

# --- IMPORTY TWOICH SERWISÓW ---
# Upewnij się, że ścieżki importów są poprawne względem struktury Twojego projektu
from app.services.ocr_service import get_pipeline
from app.services.image_enhancer import enhance_image_for_ocr 
from app.services.regex_extractor import extract_data_regex

ocr_bp = Blueprint('ocr', __name__)

# =========================================================================
# 1. ENDPOINT DLA AUTOUZUPEŁNIANIA (Frontend Drag & Drop)
# =========================================================================
@ocr_bp.route('/api/extract_data', methods=['POST'])
def api_extract_data():
    print(">>> Otrzymano żądanie POST /api/extract_data") # Log startu
    
    if 'file' not in request.files:
        return jsonify({'error': 'Brak pliku'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'Nie wybrano pliku'}), 400

    # 1. Ładowanie modelu (zabezpieczone try-except)
    try:
        pipeline = get_pipeline()
        if pipeline is None:
            raise ValueError("Pipeline zwrócił None")
    except Exception as e:
        print(f"!!! Błąd ładowania modelu AI: {e}")
        return jsonify({'error': 'Błąd serwera: Nie można załadować modelu AI'}), 500

    filename = secure_filename(file.filename)
    original_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
    
    try:
        file.save(original_path)
        print(f"Plik zapisany: {original_path}")
    except Exception as e:
        print(f"!!! Błąd zapisu pliku: {e}")
        return jsonify({'error': 'Błąd zapisu pliku na serwerze'}), 500
    
    temp_enhanced_path = None
    path_to_process = original_path

    try:
        # 2. Poprawa jakości
        try:
            temp_enhanced_path = enhance_image_for_ocr(original_path, scale_factor=2)
            path_to_process = temp_enhanced_path
            print(f"Obraz ulepszony: {temp_enhanced_path}")
        except Exception as e:
            print(f"Warning: Nie udało się ulepszyć obrazu (używam oryginału): {e}")

        # 3. OCR Pipeline
        print("Uruchamiam Pipeline OCR...")
        ocr_output = pipeline.predict(path_to_process)
        print("OCR zakończony sukcesem.")
        
        # 4. Parsowanie wyników do formatu dla regexa
        blocks_for_regex = []
        
        # --- Zabezpieczona logika wyciągania tekstu ---
        for res in ocr_output:
            # Sprawdzamy co to za obiekt i logujemy jego typ
            # print(f"Typ wyniku OCR: {type(res)}") 
            
            try:
                # Dostosuj to do swojego modelu! 
                # Jeśli używasz PaddleOCR/LayoutLMv3, struktura może być różna.
                # Najbardziej uniwersalna metoda (jeśli obiekt ma metodę save_to_json):
                if hasattr(res, 'save_to_json'):
                    import json
                    
                    json_str = res.save_to_json(save_path=current_app.config['OUTPUT_FOLDER'])
                    data = json.loads(json_str)
                    if 'parsing_res_list' in data:
                        blocks_for_regex.extend(data['parsing_res_list'])
                    elif 'res' in data: # Czasami Paddle zwraca w 'res'
                         for line in data['res']:
                             if isinstance(line, dict) and 'text' in line:
                                 blocks_for_regex.append({"block_content": line['text']})
                
                # Fallbacki dla słowników i list
                elif isinstance(res, dict):
                    if 'parsing_res_list' in res:
                        blocks_for_regex.extend(res['parsing_res_list'])
                
                # Jeśli to surowa lista tekstów
                elif isinstance(res, str):
                    blocks_for_regex.append({"block_content": res})

            except Exception as parse_err:
                print(f"Błąd parsowania pojedynczego wyniku OCR: {parse_err}")

        # Jeśli lista jest pusta, to znaczy że parsowanie nie zadziałało
        if not blocks_for_regex:
            print("Warning: Lista bloków tekstu jest pusta! Sprawdź strukturę obiektu 'res'.")

        regex_input = {"parsing_res_list": blocks_for_regex}
        
        # 5. Regex
        print("Uruchamiam Regex Extractor...")
        extracted_fields = extract_data_regex(regex_input)
        print("Dane wyekstrahowane:", extracted_fields)
        
        return jsonify(extracted_fields)

    except Exception as e:
        # To złapie CRASH i wypisze go w konsoli zamiast zrywać połączenie bez słowa
        print("!!! KRYTYCZNY BŁĄD PODCZAS PRZETWARZANIA !!!")
        traceback.print_exc() 
        return jsonify({'error': f'Błąd przetwarzania: {str(e)}'}), 500

    finally:
        # Sprzątanie
        if temp_enhanced_path and os.path.exists(temp_enhanced_path):
            try:
                os.remove(temp_enhanced_path)
            except: pass

# =========================================================================
# 2. POZOSTAŁE ENDPOINTY (Upload, Process, Delete)
# =========================================================================

@ocr_bp.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'Brak pliku'}), 400
    files = request.files.getlist('file')
    saved_count = 0
    for file in files:
        if file.filename != '':
            file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], secure_filename(file.filename)))
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

# Obsługa serwowania plików wejściowych (np. do podglądu)
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
        path_to_process = original_file_path
        temp_enhanced_path = None

        try:
            print(f"Rozpoczynam optymalizację obrazu: {filename}")
            temp_enhanced_path = enhance_image_for_ocr(original_file_path, scale_factor=2)
            path_to_process = temp_enhanced_path
            print(f"Sukces! OCR otrzyma ulepszony plik: {temp_enhanced_path}")
        except Exception as e:
            print(f"Nie udało się ulepszyć obrazu (błąd: {e}). Używam oryginału.")

        try:
            output = pipeline.predict(path_to_process)
            for res in output:
                res.save_to_json(save_path=current_app.config['OUTPUT_FOLDER'])
                res.save_to_markdown(save_path=current_app.config['OUTPUT_FOLDER'])
        except Exception as e:
            print(f"Błąd przetwarzania OCR: {e}")
        finally:
            if temp_enhanced_path and os.path.exists(temp_enhanced_path):
                try:
                    os.remove(temp_enhanced_path)
                except:
                    pass
            
    return redirect(url_for('main.index'))