"""
Endpointy API do zarządzania szablonami dokumentów.
"""

import os
import re
from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required
from werkzeug.utils import secure_filename

from app.services.llm_service import extract_template_fields

templates_bp = Blueprint('templates', __name__)


@templates_bp.route('/api/templates')
@login_required
def get_templates():
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
@login_required
def get_template(filename):
    templates_dir = os.path.join(current_app.root_path, '..', 'templates', 'documents')
    safe_name = secure_filename(filename)
    if not safe_name.endswith('.html'):
        return jsonify({'error': 'Nieprawidłowa nazwa szablonu'}), 400
    template_path = os.path.realpath(os.path.join(templates_dir, safe_name))
    if not template_path.startswith(os.path.realpath(templates_dir)):
        return jsonify({'error': 'Niedozwolona ścieżka szablonu'}), 400
    if not os.path.exists(template_path):
        return jsonify({'error': 'Szablon nie istnieje'}), 404
    try:
        with open(template_path, 'r', encoding='utf-8') as f:
            content = f.read()
        field_names = list(set(re.findall(r'name=["\']([^"\']+)["\']', content)))
        return jsonify({'content': content, 'fields': field_names})
    except Exception:
        return jsonify({'error': 'Błąd odczytu szablonu'}), 500


@templates_bp.route('/api/process_template', methods=['POST'])
@login_required
def process_template():
    data = request.get_json()
    if not data or 'files' not in data or not data['files']:
        return jsonify({'success': False, 'error': 'Brak plików'}), 400
    if 'fields' not in data or not data['fields']:
        return jsonify({'success': False, 'error': 'Brak pól do ekstrakcji'}), 400

    output_folder = current_app.config['OUTPUT_FOLDER']
    json_paths = []
    for f in data['files']:
        safe_name = secure_filename(f)
        if not safe_name.endswith('.json'):
            continue
        full_path = os.path.realpath(os.path.join(output_folder, safe_name))
        if not full_path.startswith(os.path.realpath(output_folder)):
            continue
        if os.path.exists(full_path):
            json_paths.append(full_path)

    if not json_paths:
        return jsonify({'success': False, 'error': 'Żaden z plików nie istnieje'}), 404

    result = extract_template_fields(json_paths, data['fields'], model=data.get('model'))
    if 'error' in result and 'success' not in result:
        return jsonify({'success': False, 'error': 'Błąd przetwarzania szablonu'}), 500
    return jsonify(result)
