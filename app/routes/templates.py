"""
Endpointy API do zarządzania szablonami dokumentów.
Obsługuje listowanie szablonów, pobieranie zawartości
i przetwarzanie szablonów przez model LLM.
"""

import os
import re
from flask import Blueprint, request, jsonify, current_app

from app.services.llm_service import extract_template_fields

templates_bp = Blueprint('templates', __name__)


# ============================================================
# Endpoint: GET /api/templates — lista dostępnych szablonów
# ============================================================

@templates_bp.route('/api/templates')
def get_templates():
    """
    Zwraca listę szablonów HTML z folderu templates/documents/.
    Każdy szablon opisany jest nazwą pliku i sformatowaną nazwą wyświetlaną.
    """
    templates_dir = os.path.join(current_app.root_path, '..', 'templates', 'documents')

    if not os.path.exists(templates_dir):
        return jsonify([])

    try:
        files = [f for f in os.listdir(templates_dir) if f.endswith('.html')]
        templates = []
        for f in files:
            # Zamień "pozew_nakazowy.html" → "Pozew Nakazowy"
            name = f.replace('.html', '').replace('_', ' ').title()
            templates.append({'filename': f, 'name': name})
        return jsonify(templates)
    except Exception as e:
        return jsonify([])


# ============================================================
# Endpoint: GET /api/template/<filename> — zawartość szablonu
# ============================================================

@templates_bp.route('/api/template/<filename>')
def get_template(filename):
    """
    Zwraca zawartość szablonu HTML oraz listę nazw pól formularza.
    Pola wyodrębniane są z atrybutów name="" elementów <input>.
    """
    templates_dir = os.path.join(current_app.root_path, '..', 'templates', 'documents')
    template_path = os.path.join(templates_dir, filename)

    if not os.path.exists(template_path):
        return jsonify({'error': 'Szablon nie istnieje'}), 404

    try:
        with open(template_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Wyodrębnij nazwy pól z atrybutu name="" w inputach
        field_names = re.findall(r'name=["\']([^"\']+)["\']', content)
        field_names = list(set(field_names))  # Usuń duplikaty

        return jsonify({
            'content': content,
            'fields': field_names
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================================
# Endpoint: POST /api/process_template — przetwarzanie szablonu przez LLM
# ============================================================

@templates_bp.route('/api/process_template', methods=['POST'])
def process_template():
    """
    Przetwarza wiele plików JSON (wyniki OCR) i wypełnia pola szablonu
    za pomocą modelu LLM.
    
    Oczekuje JSON: { "files": ["plik1.json", ...], "fields": ["pole1", ...] }
    Zwraca JSON:   { "success": true, "fields": {...} }
    """
    data = request.get_json()

    # Walidacja danych wejściowych
    if not data or 'files' not in data or not data['files']:
        return jsonify({'success': False, 'error': 'Brak plików'}), 400

    if 'fields' not in data or not data['fields']:
        return jsonify({'success': False, 'error': 'Brak pól do ekstrakcji'}), 400

    files = data['files']
    fields = data['fields']
    model_name = data.get('model')

    # Zbierz ścieżki do istniejących plików JSON
    json_paths = []
    for filename in files:
        json_path = os.path.join(current_app.config['OUTPUT_FOLDER'], filename)
        if os.path.exists(json_path):
            json_paths.append(json_path)

    if not json_paths:
        return jsonify({'success': False, 'error': 'Żaden z plików nie istnieje'}), 404

    # Przetwórz przez LLM
    result = extract_template_fields(json_paths, fields, model=model_name)

    if 'error' in result and 'success' not in result:
        return jsonify({'success': False, 'error': result['error']}), 500

    return jsonify(result)
