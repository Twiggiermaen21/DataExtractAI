import os
import json
import logging
import pandas as pd
from flask import Blueprint, request, jsonify, current_app, send_file
from io import BytesIO

excel_export_bp = Blueprint('excel_export', __name__)
log = logging.getLogger(__name__)

@excel_export_bp.route('/api/export_excel', methods=['POST'])
def export_excel():
    """Generates an Excel file from a list of JSON filenames."""
    data = request.get_json()
    if not data or 'files' not in data or not data['files']:
        return jsonify({'success': False, 'error': 'Brak plików do eksportu'}), 400

    files = data['files']
    output_dir = current_app.config['OUTPUT_FOLDER']

    extracted_records = []
    
    for filename in files:
        # Pamiętajmy, że ocr.py domyślnie zapisuje wyniki w głównym folderze OUTPUT_FOLDER, 
        # a invoices.py w OUTPUT_FOLDER/wezwania_faktury.
        
        # Szukamy najpierw bezpośrednio w OUTPUT_FOLDER, a potem w wezwania_faktury
        path1 = os.path.join(output_dir, filename)
        path2 = os.path.join(output_dir, 'wezwania_faktury', filename)
        
        json_path = path1 if os.path.exists(path1) else (path2 if os.path.exists(path2) else None)
        
        if not json_path:
            # Może to być nazwa pliku wejściowego, musimy poszukać pliku extracted_...json
            # Ta logika może wymagać dostosowania, zależnie od tego co frondend dokładnie wysyła.
            base_name = os.path.splitext(filename)[0]
            # Przykładowe dopasowanie np. faktura_...
            for f in os.listdir(output_dir):
                if f.endswith('.json') and base_name in f:
                    json_path = os.path.join(output_dir, f)
                    break
        
        if json_path and os.path.exists(json_path):
            try:
                with open(json_path, 'r', encoding='utf-8') as f:
                    doc_data = json.load(f)
                    
                    # W zależności od formatu zapisu (ocr.py vs invoices.py), ekstrakcja może być w 'extracted_data' lub na najwyższym poziomie
                    fields = doc_data.get('extracted_data', doc_data.get('fields', doc_data))
                    
                    # Czasem ocr_result w ocr.py pakuje wszystko w listę 'parsing_res_list' z kluczem 'extracted_data'
                    # Dostosowujemy mapowanie w locie na wypadek różnych struktur zapisu
                    if isinstance(fields, str):
                        try:
                            fields = json.loads(fields)
                        except:
                            fields = {}
                    
                    record = {
                        'Plik Źródłowy': doc_data.get('source_file', filename),
                        'Sprzedawca': fields.get('sprzedawca', ''),
                        'Data Wystawienia': fields.get('data_wystawienia', ''),
                        'Wolumen Energii': fields.get('wolumen_energii', ''),
                        'Kwota Netto': fields.get('kwota_netto', ''),
                        'Kwota Brutto': fields.get('kwota_brutto', ''),
                        'Kwota VAT': fields.get('kwota_vat', ''),
                        'Pewność OCR (%)': fields.get('pewnosc_ocr_procent', '')
                    }
                    extracted_records.append(record)
            except Exception as e:
                log.exception(f"Error reading JSON {json_path}")

    if not extracted_records:
        return jsonify({'success': False, 'error': 'Nie znaleziono poprawnych danych do eksportu'}), 404

    try:
        df = pd.DataFrame(extracted_records)
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Faktury Energia')
            
            # Autodopasowanie szerokości kolumn (opcjonalne, ale przydatne)
            worksheet = writer.sheets['Faktury Energia']
            for col_idx, col in enumerate(df.columns, 1):
                max_len = max(
                    df[col].astype(str).map(len).max(),
                    len(col)
                ) + 2
                worksheet.column_dimensions[openpyxl.utils.get_column_letter(col_idx)].width = max_len

        output.seek(0)
        
        return send_file(
            output,
            as_attachment=True,
            download_name='raport_faktury_energia.xlsx',
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
    except Exception as e:
        log.exception("Error generating Excel")
        return jsonify({'success': False, 'error': f"Błąd generowania pliku Excel: {str(e)}"}), 500
