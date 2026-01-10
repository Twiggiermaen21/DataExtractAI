import os
import json
from flask import Blueprint, request, jsonify, current_app, make_response, render_template_string

generator_bp = Blueprint('generator', __name__)

@generator_bp.route('/api/get_output_data', methods=['GET'])
def get_output_data():
    """
    Skanuje folder 'output', wczytuje wszystkie pliki .json
    i zwraca je jako listę obiektów zawierających nazwę pliku i dane.
    """
    # POPRAWKA 1: Używamy current_app zamiast app
    output_folder = current_app.config['OUTPUT_FOLDER'] 
    
    data_list = []

    # Sprawdź czy folder w ogóle istnieje
    if not os.path.exists(output_folder):
        # Opcjonalnie: stwórz folder jeśli nie istnieje, żeby nie sypało błędem
        try:
            os.makedirs(output_folder)
        except OSError:
            print(f"Błąd: Nie znaleziono folderu {output_folder}")
            return jsonify([])

    # Pobierz listę plików
    try:
        files = [f for f in os.listdir(output_folder) if f.endswith('.json')]
        files.sort()
    except Exception as e:
        print(f"Błąd listowania plików: {e}")
        return jsonify([])

    print(f"Znaleziono plików JSON: {len(files)}")

    for filename in files:
        file_path = os.path.join(output_folder, filename)
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = json.load(f)
                
                # POPRAWKA: Wyciągamy zawartość klucza 'parsing_res_list'
                # Jeśli klucza nie ma, zwracamy pustą listę []
                blocks_list = content.get('parsing_res_list', [])

                item = {
                    "filename": filename,
                    # Tutaj przypisujemy wyciągniętą listę do klucza "parsing_res_list"
                    "parsing_res_list": blocks_list
                }
                
                data_list.append(item)
                
        except Exception as e:
            print(f"Błąd odczytu pliku {filename}: {e}")

    return jsonify(data_list)

@generator_bp.route('/generate_document', methods=['POST'])
def generate_document():
    """
    Scala dane z formularza z szablonem Jinja2 (HTML).
    Zwraca gotowy dokument HTML z auto-printem.
    """
    data = request.get_json()
    template_name = data.get('template')
    form_data = data.get('data', {}) 
    
    # Upewnij się, że ta ścieżka w configu jest poprawna w app.py
    processed_folder = current_app.config.get('PROCESSED_TEMPLATES_FOLDER', 'processed_templates')
    
    # Jeśli ścieżka w configu jest relatywna, łączymy ją z root_path
    if not os.path.isabs(processed_folder):
        path = os.path.join(current_app.root_path, processed_folder, template_name)
    else:
        path = os.path.join(processed_folder, template_name)
    
    if not os.path.exists(path):
        return jsonify({'success': False, 'error': f'Szablon {template_name} nie został znaleziony'}), 404

    try:
        with open(path, 'r', encoding='utf-8') as f:
            html_template = f.read()
        
        # Renderowanie zmiennych Jinja2
        filled_html = render_template_string(html_template, **form_data)
        
        # Skrypt auto-print
        auto_print_script = """
        <script>
            window.onload = function() { 
                setTimeout(function(){ window.print(); }, 500); 
            }
        </script>
        """
        final_html = filled_html + auto_print_script

        response = make_response(final_html)
        response.headers['Content-Type'] = 'text/html; charset=utf-8'
        return response

    except Exception as e:
        print(f"Błąd generowania: {e}")
        return jsonify({'success': False, 'error': f"Błąd generowania: {str(e)}"}), 500