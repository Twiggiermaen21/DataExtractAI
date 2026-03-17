"""
Endpointy API dla zarządzania wezwaniami do zapłaty.
"""

import os
from flask import Blueprint, request, jsonify

from app.services.wezwania_service import (
    save_wezwanie,
    get_all_wezwania,
    get_wezwanie,
    get_wezwania_by_ids,
    calculate_summary,
)

wezwania_bp = Blueprint('wezwania', __name__)


@wezwania_bp.route('/api/wezwania', methods=['GET'])
def list_wezwania():
    return jsonify(get_all_wezwania())


@wezwania_bp.route('/api/wezwania/<wezwanie_id>', methods=['GET'])
def get_wezwanie_details(wezwanie_id):
    wezwanie = get_wezwanie(wezwanie_id)
    if wezwanie:
        return jsonify(wezwanie)
    return jsonify({'error': 'Wezwanie nie znalezione'}), 404


@wezwania_bp.route('/api/wezwania/save', methods=['POST'])
def save_wezwanie_endpoint():
    """Zapisuje wezwanie do zapłaty."""
    data = request.get_json()
    if not data or 'fields' not in data:
        return jsonify({'success': False, 'error': 'Brak danych formularza'}), 400
    return jsonify(save_wezwanie(data['fields']))


@wezwania_bp.route('/api/wezwania/summary', methods=['POST'])
def get_wezwania_summary():
    """Oblicza podsumowanie z wybranych wezwań."""
    data = request.get_json()
    if not data or 'ids' not in data or not data['ids']:
        return jsonify({'error': 'Brak ID wezwań'}), 400

    wezwania = get_wezwania_by_ids(data['ids'])
    if not wezwania:
        return jsonify({'error': 'Nie znaleziono wezwań'}), 404

    return jsonify({
        'success': True,
        'summary': calculate_summary(wezwania),
        'wezwania': wezwania,
    })


@wezwania_bp.route('/api/wezwania/save_file', methods=['POST'])
def save_file():
    """Zapisuje plik tekstowy do folderu output/pobrane/."""
    data = request.get_json()
    if not data or 'filename' not in data or 'content' not in data:
        return jsonify({'success': False, 'error': 'Brak filename lub content'}), 400

    filename = data['filename']
    content = data['content']

    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    pobrane_dir = os.path.join(project_root, 'output', 'pobrane')
    os.makedirs(pobrane_dir, exist_ok=True)

    filepath = os.path.join(pobrane_dir, filename)

    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return jsonify({'success': True, 'filename': filename, 'filepath': filepath})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
