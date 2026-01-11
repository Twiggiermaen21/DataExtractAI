from datetime import datetime
import os
import json
from flask import Blueprint, request, jsonify, current_app, make_response, render_template_string
from werkzeug.utils import secure_filename
from xhtml2pdf import pisa  # To jest biblioteka, która nie wymaga GTK

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


# --- ENDPOINT DO GENEROWANIA PDF ---
@generator_bp.route('/generate_document', methods=['POST'])
def generate_document():
    try:
        # 1. Pobierz dane
        req_data = request.get_json()
        template_name = req_data.get('template')
        form_data = req_data.get('data', {})

        # 2. Ustalanie ścieżek
        base_dir = current_app.root_path
        templates_dir = current_app.config['PROCESSED_TEMPLATES_FOLDER']
        output_dir = os.path.join(base_dir, 'gotowe_dokumenty')
        
        # --- KLUCZOWE DLA POLSKICH ZNAKÓW ---
        # Ścieżka do pliku czcionki. Upewnij się, że plik nazywa się tak samo!
        # Windows: czasami nazwa to 'arial.ttf', czasami 'Arial.ttf' (wielkość liter ma znaczenie na Linuxie)
        font_path = os.path.join(base_dir, 'GoogleSans.ttf')
        
        # Jeśli nie masz Arial.ttf, kod zadziała, ale bez polskich znaków.
        # Warto dodać sprawdzenie:
        if not os.path.exists(font_path):
            print(f"UWAGA: Nie znaleziono pliku czcionki: {font_path}")

        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        template_path = os.path.join(templates_dir, template_name)
        if not os.path.exists(template_path):
            return jsonify({"error": "Brak szablonu"}), 404

        with open(template_path, 'r', encoding='utf-8') as f:
            raw_html_content = f.read()

            raw_html_content = raw_html_content.replace("<strong>", "").replace("</strong>", "")
            raw_html_content = raw_html_content.replace("<b>", "").replace("</b>", "")

        rendered_body = render_template_string(raw_html_content, **form_data)

        # 3. HTML z naprawą odstępów i czcionki
        # Używamy f-string, więc klamry CSS musimy podwajać: {{ }} to w CSS jedna { }
        full_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                /* DEFINICJA CZCIONKI (naprawa polskich znaków) */
                @font-face {{
                    font-family: 'MojaCzcionka';
                    src: url('{font_path}');
                }}

                body {{
                    font-family: 'MojaCzcionka', sans-serif;
                    font-size: 11pt;
                    padding: 40px;
                    line-height: 1.3; /* Optymalna wysokość linii */
                }}

                /* NAPRAWA DUŻYCH ENTERÓW */
                p {{
                    margin-top: 2px;    /* Minimalny odstęp na górze */
                    margin-bottom: 2px  /* Minimalny odstęp na dole */
                    padding: 0;
                }}
                
                /* Inne tagi, które mogą robić odstępy */
                h1, h2, h3 {{ margin-top: 10px; margin-bottom: 5px; }}

                /* Ukrycie ramek edytora */
                .variable-token {{
                    border: none;
                    background: transparent;
                }}
            </style>
        </head>
        <body>
            {rendered_body}
        </body>
        </html>
        """

        # 4. Generowanie PDF
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"dokument_{timestamp}.pdf"
        save_path = os.path.join(output_dir, filename)

        with open(save_path, "wb") as pdf_file:
            pisa_status = pisa.CreatePDF(
                src=full_html,
                dest=pdf_file,
                encoding='utf-8'
            )

        if pisa_status.err:
            return jsonify({"success": False, "error": "Błąd generowania PDF"}), 500

        return jsonify({
            "success": True, 
            "message": "Zapisano PDF", 
            "filepath": save_path, 
            "filename": filename
        }), 200

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500