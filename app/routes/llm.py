import os
from flask import Blueprint, request, jsonify, current_app

from app.services.llm_service import extract_invoice_data

llm_bp = Blueprint('llm', __name__)


@llm_bp.route('/api/process_llm', methods=['POST'])
def process_llm():
    """
    Przetwarza plik JSON z wynikami OCR przez model LLM.
    Oczekuje: { "filename": "nazwa_pliku.json", "attributes": "lista atrybutów" }
    """
    data = request.get_json()
    
    if not data or 'filename' not in data:
        return jsonify({'success': False, 'error': 'Brak nazwy pliku'}), 400
    
    filename = data['filename']
    custom_attributes = data.get('attributes', '')
    
    # Sprawdź czy plik istnieje
    json_path = os.path.join(current_app.config['OUTPUT_FOLDER'], filename)
    if not os.path.exists(json_path):
        return jsonify({'success': False, 'error': 'Plik nie istnieje'}), 404
    
    # Przetwórz przez LLM
    result = extract_invoice_data(json_path, custom_attributes)
    
    if 'error' in result and 'success' not in result:
        return jsonify({'success': False, 'error': result['error']}), 500
    
    return jsonify(result)


@llm_bp.route('/api/ocr_results')
def get_ocr_results():
    """Zwraca listę dostępnych plików JSON z wynikami OCR."""
    output_folder = current_app.config['OUTPUT_FOLDER']
    
    if not os.path.exists(output_folder):
        return jsonify([])
    
    try:
        files = [f for f in os.listdir(output_folder) if f.endswith('.json')]
        files.sort(key=lambda x: os.path.getmtime(os.path.join(output_folder, x)), reverse=True)
        return jsonify(files)
    except Exception as e:
        return jsonify([])
