"""
Endpointy API do przetwarzania wyników OCR przez model LLM.
"""

import os
from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required
from werkzeug.utils import secure_filename

from app.services.llm_service import extract_invoice_data

llm_bp = Blueprint('llm', __name__)


@llm_bp.route('/api/process_llm', methods=['POST'])
@login_required
def process_llm():
    data = request.get_json()

    if not data or 'filename' not in data:
        return jsonify({'success': False, 'error': 'Brak nazwy pliku'}), 400

    filename = secure_filename(data['filename'])
    if not filename or not filename.endswith('.json'):
        return jsonify({'success': False, 'error': 'Nieprawidłowa nazwa pliku'}), 400

    custom_attributes = data.get('attributes', '')
    model_name = data.get('model')

    output_folder = current_app.config['OUTPUT_FOLDER']
    json_path = os.path.realpath(os.path.join(output_folder, filename))
    if not json_path.startswith(os.path.realpath(output_folder)):
        return jsonify({'success': False, 'error': 'Niedozwolona ścieżka pliku'}), 400
    if not os.path.exists(json_path):
        return jsonify({'success': False, 'error': 'Plik nie istnieje'}), 404

    result = extract_invoice_data(json_path, custom_attributes, model=model_name)
    if 'error' in result and 'success' not in result:
        return jsonify({'success': False, 'error': 'Błąd przetwarzania LLM'}), 500

    return jsonify(result)


@llm_bp.route('/api/ocr_results')
@login_required
def get_ocr_results():
    return jsonify([])
