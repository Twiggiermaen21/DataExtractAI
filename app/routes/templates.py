import os
import uuid
from flask import Blueprint, request, jsonify, current_app, render_template

templates_bp = Blueprint('templates', __name__)

@templates_bp.route('/upload_template', methods=['POST'])
def upload_template():
    """Obsługa wgrywania surowych plików DOCX."""
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'Brak pliku'}), 400
    
    files = request.files.getlist('file')
    saved_count = 0
    
    for file in files:
        if file.filename != '':
            # Zapisujemy do folderu 'docs' (TEMPLATES_FOLDER)
            save_path = os.path.join(current_app.config['TEMPLATES_FOLDER'], file.filename)
            file.save(save_path)
            saved_count += 1
            
    return jsonify({'success': True, 'count': saved_count})

@templates_bp.route('/templates_list_html')
def templates_list_html():
    """Zwraca fragment HTML z listą dostępnych surowych szablonów DOCX."""
    try:
        files = os.listdir(current_app.config['TEMPLATES_FOLDER'])
    except OSError:
        files = []
    return render_template('components/template_list.html', files=files)

@templates_bp.route('/save_template_html', methods=['POST'])
def save_template_html():
    """
    Zapisuje wyedytowany w przeglądarce szablon jako gotowy plik HTML.
    To z tego pliku będziemy później generować PDF.
    """
    try:
        data = request.get_json()
        html_content = data.get('html')
        template_name = data.get('name', f"szablon_{uuid.uuid4().hex[:8]}")
        
        # Wymuszamy rozszerzenie .html
        if not template_name.endswith('.html'):
            template_name += '.html'

        save_path = os.path.join(current_app.config['PROCESSED_TEMPLATES_FOLDER'], template_name)
        
        with open(save_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
            
        return jsonify({'success': True, 'filename': template_name})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@templates_bp.route('/api/get_templates_json')
def get_templates_json():
    """API dla JavaScriptu: zwraca listę gotowych szablonów HTML do selecta."""
    try:
        files = [f for f in os.listdir(current_app.config['PROCESSED_TEMPLATES_FOLDER']) if f.endswith('.html')]
        return jsonify(files)
    except Exception:
        return jsonify([])

@templates_bp.route('/get_template_content/<filename>')
def get_template_content(filename):
    """Pobiera treść HTML konkretnego szablonu (do podglądu lub edycji)."""
    try:
        path = os.path.join(current_app.config['PROCESSED_TEMPLATES_FOLDER'], filename)
        if not os.path.exists(path):
            return "Szablon nie istnieje", 404
            
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        return f"Błąd serwera: {e}", 500