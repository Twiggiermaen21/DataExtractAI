"""
Endpointy API do przetwarzania wyników OCR przez model LLM.
Obsługuje ekstrakcję danych z dokumentów i listowanie plików OCR.
"""

import os
from flask import Blueprint, request, jsonify, current_app
from dotenv import load_dotenv

load_dotenv()

from app.services.llm_service import extract_invoice_data

llm_bp = Blueprint('llm', __name__)


# ============================================================
# Endpoint: POST /api/process_llm — ekstrakcja danych z dokumentu
# ============================================================

@llm_bp.route('/api/process_llm', methods=['POST'])
def process_llm():
    """
    Przetwarza plik JSON z wynikami OCR przez model LLM.
    Wyodrębnia dane z dokumentu na podstawie podanych atrybutów.
    
    Oczekuje JSON: { "filename": "nazwa_pliku.json", "attributes": "lista atrybutów" }
    Zwraca JSON:   { "success": true, "extracted_data": {...} }
    """
    print("Wywołano funkcję: process_llm")
    data = request.get_json()

    if not data or 'filename' not in data:
        return jsonify({'success': False, 'error': 'Brak nazwy pliku'}), 400

    filename = data['filename']
    custom_attributes = data.get('attributes', '')
    model_name = data.get('model')

    # Sprawdź czy plik z wynikami OCR istnieje
    json_path = os.path.join(current_app.config['OUTPUT_FOLDER'], filename)
    if not os.path.exists(json_path):
        return jsonify({'success': False, 'error': 'Plik nie istnieje'}), 404

    # Przetwórz przez LLM i zwróć wyekstrahowane dane
    result = extract_invoice_data(json_path, custom_attributes, model=model_name)

    if 'error' in result and 'success' not in result:
        return jsonify({'success': False, 'error': result['error']}), 500

    return jsonify(result)


# ============================================================
# Endpoint: GET /api/ocr_results — lista plików JSON z wynikami OCR
# ============================================================

@llm_bp.route('/api/ocr_results')
def get_ocr_results():
    """
    Zwraca listę plików JSON z wynikami OCR, posortowaną od najnowszego.
    Pliki pobierane z folderu OUTPUT_FOLDER.
    """
    print("Wywołano funkcję: get_ocr_results")
    output_folder = current_app.config['OUTPUT_FOLDER']

    if not os.path.exists(output_folder):
        return jsonify([])

    try:
        # Znajdź wszystkie pliki .json i posortuj wg daty modyfikacji (najnowsze pierwsze)
        files = [f for f in os.listdir(output_folder) if f.endswith('.json')]
        files.sort(key=lambda x: os.path.getmtime(os.path.join(output_folder, x)), reverse=True)
        return jsonify(files)
    except Exception as e:
        return jsonify([])
