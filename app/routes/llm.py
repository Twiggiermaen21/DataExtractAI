import os
import re
from flask import Blueprint, request, jsonify, current_app

from app.services.llm_service import extract_invoice_data, extract_template_fields

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


@llm_bp.route('/api/templates')
def get_templates():
    """Zwraca listę dostępnych szablonów dokumentów."""
    templates_dir = os.path.join(current_app.root_path, '..', 'templates', 'documents')
    
    if not os.path.exists(templates_dir):
        return jsonify([])
    
    try:
        files = [f for f in os.listdir(templates_dir) if f.endswith('.html')]
        templates = []
        for f in files:
            name = f.replace('.html', '').replace('_', ' ').title()
            templates.append({'filename': f, 'name': name})
        return jsonify(templates)
    except Exception as e:
        return jsonify([])


@llm_bp.route('/api/template/<filename>')
def get_template(filename):
    """Zwraca zawartość szablonu HTML."""
    templates_dir = os.path.join(current_app.root_path, '..', 'templates', 'documents')
    template_path = os.path.join(templates_dir, filename)
    
    if not os.path.exists(template_path):
        return jsonify({'error': 'Szablon nie istnieje'}), 404
    
    try:
        with open(template_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Wyodrębnij nazwy pól input
        field_names = re.findall(r'name=["\']([^"\']+)["\']', content)
        field_names = list(set(field_names))  # Usuń duplikaty
        
        return jsonify({
            'content': content,
            'fields': field_names
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@llm_bp.route('/api/process_template', methods=['POST'])
def process_template():
    """
    Przetwarza wiele plików JSON i wypełnia szablon.
    Oczekuje: { "files": ["plik1.json", "plik2.json"], "fields": ["pole1", "pole2"] }
    """
    data = request.get_json()
    
    if not data or 'files' not in data or not data['files']:
        return jsonify({'success': False, 'error': 'Brak plików'}), 400
    
    if 'fields' not in data or not data['fields']:
        return jsonify({'success': False, 'error': 'Brak pól do ekstrakcji'}), 400
    
    files = data['files']
    fields = data['fields']
    
    # Zbierz ścieżki do plików
    json_paths = []
    for filename in files:
        json_path = os.path.join(current_app.config['OUTPUT_FOLDER'], filename)
        if os.path.exists(json_path):
            json_paths.append(json_path)
    
    if not json_paths:
        return jsonify({'success': False, 'error': 'Żaden z plików nie istnieje'}), 404
    
    # Przetwórz przez LLM
    result = extract_template_fields(json_paths, fields)
    
    if 'error' in result and 'success' not in result:
        return jsonify({'success': False, 'error': result['error']}), 500
    
    return jsonify(result)
