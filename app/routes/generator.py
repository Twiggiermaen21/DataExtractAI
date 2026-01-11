
from datetime import datetime
import os
import json
from flask import Blueprint, request, jsonify, current_app,  render_template_string

from fpdf import FPDF 

# Tworzymy klasę PDF z obsługą HTML (w fpdf2 jest to wbudowane, ale czasem warto wymusić klasę)
class PDF(FPDF):
    pass


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
    try:
        # 1. Pobierz dane
        req_data = request.get_json()
        template_name = req_data.get('template')
        form_data = req_data.get('data', {})

        # 2. Ustalanie ścieżek
        base_dir = current_app.root_path
        templates_dir = current_app.config['PROCESSED_TEMPLATES_FOLDER']
        output_dir = os.path.join(base_dir, 'gotowe_dokumenty')
        
        # --- KONFIGURACJA CZCIONKI DLA FPDF ---
        # FPDF potrzebuje ścieżki do pliku .ttf (nie Base64!)
        # Najlepiej użyj Arial lub DejaVuSans
        font_name = 'Arial.ttf' 
        font_path = os.path.join(base_dir, font_name)

        # Fallback na Arial jeśli brak DejaVu
        if not os.path.exists(font_path):
            font_name = 'arial.ttf'
            font_path = os.path.join(base_dir, font_name)

        if not os.path.exists(font_path):
            return jsonify({"success": False, "error": f"Brak pliku czcionki {font_path} (wymagany dla FPDF)"}), 500

        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        # Wczytanie szablonu
        template_path = os.path.join(templates_dir, template_name)
        if not os.path.exists(template_path):
            return jsonify({"error": "Brak szablonu"}), 404

        with open(template_path, 'r', encoding='utf-8') as f:
            raw_html_content = f.read()

        # Renderowanie zmiennych Jinja2
        rendered_body = render_template_string(raw_html_content, **form_data)

        # 3. Generowanie PDF za pomocą FPDF
        # Inicjalizacja PDF (A4, orientacja pionowa, jednostka mm)
        pdf = PDF(orientation='P', unit='mm', format='A4')
        
        # Dodanie obsługi polskich znaków (UTF-8)
        # Musimy zarejestrować czcionkę. 'uni=True' jest domyślne w fpdf2 dla add_font
        pdf.add_font('PolskiFont', style='', fname=font_path)
        pdf.add_font('PolskiFont', style='B', fname=font_path) # Rejestrujemy też jako pogrubioną (użyje tego samego pliku)
        pdf.add_font('PolskiFont', style='I', fname=font_path) # I jako kursywę
        
        pdf.add_page()
        
        # Ustawiamy czcionkę startową
        pdf.set_font("PolskiFont", size=11)
        
        # Opcjonalnie: Ustawienie marginesów
        pdf.set_margins(20, 20, 20)

        # --- ZAPISYWANIE TREŚCI ---
        # write_html parsuje proste tagi: <b>, <i>, <u>, <br>, <p>, <center>, <table> (proste)
        # UWAGA: FPDF ignoruje CSS w <style>! Style muszą być proste lub inline.
        try:
            # write_html automatycznie obsługuje zawijanie wierszy i proste formatowanie
            pdf.write_html(rendered_body)
        except Exception as html_err:
            print(f"Błąd parsowania HTML przez FPDF: {html_err}")
            # Fallback: jeśli HTML jest zbyt skomplikowany, zapisz jako czysty tekst
            pdf.multi_cell(0, 5, text="Ostrzeżenie: HTML był zbyt skomplikowany dla FPDF. Zrzut tekstu:")
            pdf.ln()
            # Usuń tagi HTML do czystego tekstu (proste czyszczenie)
            import re
            clean_text = re.sub('<[^<]+?>', '', rendered_body)
            pdf.multi_cell(0, 5, text=clean_text)

        # 4. Zapis do pliku
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"dokument_{timestamp}.pdf"
        save_path = os.path.join(output_dir, filename)

        pdf.output(save_path)

        print(f"PDF zapisany: {save_path}")

        return jsonify({
            "success": True, 
            "message": "Zapisano PDF", 
            "filepath": save_path, 
            "filename": filename
        }), 200

    except Exception as e:
        print(f"CRITICAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500