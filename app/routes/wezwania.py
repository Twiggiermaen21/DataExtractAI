"""
Endpointy API dla zarządzania wezwaniami do zapłaty.
"""

import os
from flask import Blueprint, request, jsonify, current_app

from app.services.wezwania_service import (
    save_wezwanie,
    get_all_wezwania,
    get_wezwanie,
    get_wezwania_by_ids,
    calculate_summary
)

wezwania_bp = Blueprint('wezwania', __name__)


@wezwania_bp.route('/api/wezwania', methods=['GET'])
def list_wezwania():
    """Zwraca listę wszystkich zapisanych wezwań."""
    print("Wywołano funkcję: list_wezwania")
    wezwania = get_all_wezwania()
    return jsonify(wezwania)


@wezwania_bp.route('/api/wezwania/<wezwanie_id>', methods=['GET'])
def get_wezwanie_details(wezwanie_id):
    """Zwraca szczegóły wezwania po ID."""
    print("Wywołano funkcję: get_wezwanie_details")
    wezwanie = get_wezwanie(wezwanie_id)
    if wezwanie:
        return jsonify(wezwanie)
    return jsonify({'error': 'Wezwanie nie znalezione'}), 404


@wezwania_bp.route('/api/wezwania/save', methods=['POST'])
def save_wezwanie_endpoint():
    """
    Zapisuje wezwanie do zapłaty.
    Oczekuje: { "fields": { ... pola formularza ... } }
    """
    print("Wywołano funkcję: save_wezwanie_endpoint")
    data = request.get_json()
    
    if not data or 'fields' not in data:
        return jsonify({'success': False, 'error': 'Brak danych formularza'}), 400
    
    result = save_wezwanie(data['fields'])
    return jsonify(result)


@wezwania_bp.route('/api/wezwania/summary', methods=['POST'])
def get_wezwania_summary():
    """
    Oblicza podsumowanie z wybranych wezwań.
    Oczekuje: { "ids": ["id1", "id2", ...] }
    """
    print("Wywołano funkcję: get_wezwania_summary")
    data = request.get_json()
    
    if not data or 'ids' not in data or not data['ids']:
        return jsonify({'error': 'Brak ID wezwań'}), 400
    
    wezwania = get_wezwania_by_ids(data['ids'])
    
    if not wezwania:
        return jsonify({'error': 'Nie znaleziono wezwań'}), 404
    
    summary = calculate_summary(wezwania)
    
    return jsonify({
        'success': True,
        'summary': summary,
        'wezwania': wezwania
    })


@wezwania_bp.route('/api/wezwania/save_file', methods=['POST'])
def save_file():
    """
    Zapisuje plik tekstowy (np. .md) do folderu output/pobrane/.
    Oczekuje: { "filename": "nazwa.md", "content": "zawartość pliku" }
    """
    print("Wywołano funkcję: save_file")
    data = request.get_json()
    
    if not data or 'filename' not in data or 'content' not in data:
        return jsonify({'success': False, 'error': 'Brak filename lub content'}), 400
    
    filename = data['filename']
    content = data['content']
    
    # Folder na pobrane pliki
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    pobrane_dir = os.path.join(project_root, 'output', 'pobrane')
    os.makedirs(pobrane_dir, exist_ok=True)
    
    filepath = os.path.join(pobrane_dir, filename)
    
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        pass  # usuniety print
        return jsonify({
            'success': True,
            'filename': filename,
            'filepath': filepath
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
