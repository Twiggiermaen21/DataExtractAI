"""
Endpointy API do zarządzania szablonami dokumentów.
"""

import os
import re
from flask import Blueprint, request, jsonify, current_app

from app.services.llm_service import extract_template_fields

templates_bp = Blueprint('templates', __name__)


@templates_bp.route('/api/templates')
def get_templates():
    """Zwraca listę szablonów HTML z folderu templates/documents/."""
    templates_dir = os.path.join(current_app.root_path, '..', 'templates', 'documents')

    if not os.path.exists(templates_dir):
        return jsonify([])

    try:
        return jsonify([
            {'filename': f, 'name': f.replace('.html', '').replace('_', ' ').title()}
            for f in os.listdir(templates_dir) if f.endswith('.html')
        ])
    except Exception:
        return jsonify([])


@templates_bp.route('/api/template/<filename>')
def get_template(filename):
    """Zwraca zawartość szablonu HTML oraz listę nazw pól formularza."""
    templates_dir = os.path.join(current_app.root_path, '..', 'templates', 'documents')
    template_path = os.path.join(templates_dir, filename)

    if not os.path.exists(template_path):
        return jsonify({'error': 'Szablon nie istnieje'}), 404

    try:
        with open(template_path, 'r', encoding='utf-8') as f:
            content = f.read()

        field_names = list(set(re.findall(r'name=["\']([^"\']+)["\']', content)))
        return jsonify({'content': content, 'fields': field_names})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@templates_bp.route('/api/process_template', methods=['POST'])
def process_template():
    """Przetwarza pliki OCR i wypełnia pola szablonu przez LLM."""
    data = request.get_json()

    if not data or 'files' not in data or not data['files']:
        return jsonify({'success': False, 'error': 'Brak plików'}), 400
    if 'fields' not in data or not data['fields']:
        return jsonify({'success': False, 'error': 'Brak pól do ekstrakcji'}), 400

    json_paths = [
        os.path.join(current_app.config['OUTPUT_FOLDER'], f)
        for f in data['files']
        if os.path.exists(os.path.join(current_app.config['OUTPUT_FOLDER'], f))
    ]

    if not json_paths:
        return jsonify({'success': False, 'error': 'Żaden z plików nie istnieje'}), 404

    result = extract_template_fields(json_paths, data['fields'], model=data.get('model'))

    if 'error' in result and 'success' not in result:
        return jsonify({'success': False, 'error': result['error']}), 500

    return jsonify(result)
