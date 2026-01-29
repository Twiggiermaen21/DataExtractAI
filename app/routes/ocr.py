import os
import json
import traceback
from flask import Blueprint, request, jsonify, current_app, send_from_directory

from app.services.ocr_service import get_pipeline, unload_pipeline
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
            
            # Poprawa obrazu (dla plików graficznych)
            path_to_process = original_path
            file_ext = os.path.splitext(filename)[1].lower()
            
            if file_ext == '.pdf':
                print(f"  📄 Plik PDF - pomijam ulepszanie obrazu")
            elif file_ext in ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif', '.webp']:
                try:
                    temp_enhanced_path = enhance_image_for_ocr(original_path, scale_factor=1.5)
                    path_to_process = temp_enhanced_path
                except Exception as e:
                    print(f"  ⚠️ Nie udało się ulepszyć obrazu: {e}")
                    # Kontynuuj z oryginalnym obrazem
            
            # OCR
            print(f"  🔍 Uruchamiam OCR...")
            ocr_output = pipeline.predict(path_to_process)
            
            # Zapis wyników do JSON
            for res in ocr_output:
                if hasattr(res, 'save_to_json'):
                    res.save_to_json(save_path=current_app.config['OUTPUT_FOLDER'])
                    print(f"  💾 Zapisano JSON")
            
            # Usuń tymczasowy ulepszony obraz
            if temp_enhanced_path and os.path.exists(temp_enhanced_path):
                try:
                    os.remove(temp_enhanced_path)
                except:
                    pass
            
            processed_files.append(filename)
            print(f"  ✅ Sukces!")
            
        except Exception as e:
            print(f"  ❌ Błąd: {e}")
            traceback.print_exc()
            errors.append({'file': filename, 'error': str(e)})
    
    # Zwolnij model z pamięci po zakończeniu przetwarzania
    unload_pipeline()
    print("🧹 Model OCR zwolniony z pamięci")
    
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


@ocr_bp.route('/api/quick_process', methods=['POST'])
def quick_process():
    """
    Szybki OCR - łączy OCR + ekstrakcję szablonu w jeden call.
    Przyjmuje: pliki, nazwa szablonu
    Zwraca: wyekstrahowane dane gotowe do wstawienia w szablon
    """
    from app.services.llm_service import extract_template_fields
    
    if 'files' not in request.files:
        return jsonify({'success': False, 'error': 'Brak plików'}), 400
    
    files = request.files.getlist('files')
    template_name = request.form.get('template', '')
    
    if not files or files[0].filename == '':
        return jsonify({'success': False, 'error': 'Nie wybrano plików'}), 400
    
    if not template_name:
        return jsonify({'success': False, 'error': 'Nie wybrano szablonu'}), 400
    
    # KROK 1: OCR
    try:
        pipeline = get_pipeline()
        if pipeline is None:
            return jsonify({'success': False, 'error': 'Nie można załadować modelu OCR'}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': f'Błąd ładowania modelu: {str(e)}'}), 500
    
    processed_jsons = []
    
    for file in files:
        if file.filename == '':
            continue
        
        filename = file.filename
        original_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        temp_enhanced_path = None
        
        try:
            file.save(original_path)
            print(f"📁 [Quick] Przetwarzanie: {filename}")
            
            # Poprawa obrazu (dla plików graficznych)
            path_to_process = original_path
            file_ext = os.path.splitext(filename)[1].lower()
            
            if file_ext in ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif', '.webp']:
                try:
                    temp_enhanced_path = enhance_image_for_ocr(original_path, scale_factor=1.5)
                    path_to_process = temp_enhanced_path
                except Exception as e:
                    print(f"  ⚠️ Nie udało się ulepszyć obrazu: {e}")
            
            # OCR
            ocr_output = pipeline.predict(path_to_process)
            
            # Zapis wyników do JSON
            for res in ocr_output:
                if hasattr(res, 'save_to_json'):
                    saved_path = res.save_to_json(save_path=current_app.config['OUTPUT_FOLDER'])
                    if saved_path:
                        processed_jsons.append(saved_path)
            
            # Usuń tymczasowy ulepszony obraz
            if temp_enhanced_path and os.path.exists(temp_enhanced_path):
                try:
                    os.remove(temp_enhanced_path)
                except:
                    pass
            
            print(f"✅ [Quick] OCR zakończone: {filename}")
            
        except Exception as e:
            print(f"❌ [Quick] Błąd: {e}")
    
    # Zwolnij model OCR
    unload_pipeline()
    
    if not processed_jsons:
        return jsonify({'success': False, 'error': 'Nie udało się przetworzyć żadnego pliku'}), 500
    
    # KROK 2: Pobierz pola szablonu
    templates_dir = os.path.join(current_app.root_path, '..', 'templates', 'documents')
    template_path = os.path.join(templates_dir, template_name)
    
    if not os.path.exists(template_path):
        return jsonify({'success': False, 'error': f'Nie znaleziono szablonu: {template_name}'}), 404
    
    # Wyciągnij nazwy pól input z szablonu
    import re
    with open(template_path, 'r', encoding='utf-8') as f:
        template_content = f.read()
    
    field_names = re.findall(r'name=["\']([^"\']+)["\']', template_content)
    field_names = list(set(field_names))  # unique
    
    if not field_names:
        return jsonify({'success': False, 'error': 'Szablon nie zawiera pól input'}), 400
    
    # KROK 3: Ekstrakcja przez LLM
    print(f"🤖 [Quick] Ekstrakcja {len(field_names)} pól z {len(processed_jsons)} plików...")
    
    result = extract_template_fields(processed_jsons, field_names)
    
    if 'error' in result:
        return jsonify({'success': False, 'error': result['error']}), 500
    
    print(f"✅ [Quick] Zakończono pomyślnie")
    
    return jsonify({
        'success': True,
        'ocr_files': [os.path.basename(p) for p in processed_jsons],
        'template': template_name,
        'fields': result.get('fields', {})
    })