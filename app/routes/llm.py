import os
import re
from flask import Blueprint, request, jsonify, current_app

from app.services.llm_service import extract_invoice_data, extract_template_fields

llm_bp = Blueprint('llm', __name__)


@llm_bp.route('/api/process_llm', methods=['POST'])
def process_llm():
    """
    Przetwarza plik JSON z wynikami OCR przez model LLM.
    Oczekuje: { "filename": "nazwa_pliku.json", "attributes": "lista atrybutów" }
    """
    data = request.get_json()
    
    if not data or 'filename' not in data:
        return jsonify({'success': False, 'error': 'Brak nazwy pliku'}), 400
    
    filename = data['filename']
    custom_attributes = data.get('attributes', '')
    
    # Sprawdź czy plik istnieje
    json_path = os.path.join(current_app.config['OUTPUT_FOLDER'], filename)
    if not os.path.exists(json_path):
        return jsonify({'success': False, 'error': 'Plik nie istnieje'}), 404
    
    # Przetwórz przez LLM
    result = extract_invoice_data(json_path, custom_attributes)
    
    if 'error' in result and 'success' not in result:
        return jsonify({'success': False, 'error': result['error']}), 500
    
    return jsonify(result)


@llm_bp.route('/api/ocr_results')
def get_ocr_results():
    """Zwraca listę dostępnych plików JSON z wynikami OCR."""
    output_folder = current_app.config['OUTPUT_FOLDER']
    
    if not os.path.exists(output_folder):
        return jsonify([])
    
    try:
        files = [f for f in os.listdir(output_folder) if f.endswith('.json')]
        files.sort(key=lambda x: os.path.getmtime(os.path.join(output_folder, x)), reverse=True)
        return jsonify(files)
    except Exception as e:
        return jsonify([])


@llm_bp.route('/api/analyze_pozew', methods=['POST'])
def analyze_pozew():
    """
    Analizuje dane z KRS i wezwania, mapuje je na pola Pozew.
    Automatycznie wyszukuje odpowiedni sąd na podstawie kodu pocztowego pozwanego.
    Oczekuje: { "wezwanie": {...}, "krs": [...] }
    """
    import requests
    import json
    
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': 'Brak danych'}), 400
    
    wezwanie = data.get('wezwanie', {})
    krs_list = data.get('krs', [])
    
    # Przygotuj prompt dla LLM
    prompt = f"""Przeanalizuj poniższe dane i wypełnij pola dla pozwu sądowego.

DANE Z WEZWANIA DO ZAPŁATY:
{wezwanie}

DANE Z DOKUMENTÓW KRS:
{krs_list}

ZASADY MAPOWANIA:
- POWÓD (wierzyciel) = Sprzedawca z wezwania (firma która wystawiła fakturę)
- POZWANY (dłużnik) = Nabywca z wezwania (firma która ma zapłacić)
- Dane KRS uzupełniają numery KRS dla powoda i pozwanego
- pozwany_kod_pocztowy_miasto = kod pocztowy i miasto z adresu pozwanego w formacie "XX-XXX Miasto" (np. "03-301 Warszawa")

Zwróć TYLKO obiekt JSON z wypełnionymi polami:
{{
  "powod_nazwa_pelna": "pełna nazwa sprzedawcy/wierzyciela",
  "powod_adres_pelny": "adres sprzedawcy",
  "powod_numer_krs": "numer KRS sprzedawcy (jeśli znaleziony w KRS)",
  "powod_siedziba_miasto": "miasto siedziby sprzedawcy",
  "pozwany_nazwa_pelna": "pełna nazwa nabywcy/dłużnika",
  "pozwany_adres_pelny": "adres nabywcy",
  "pozwany_kod_pocztowy_miasto": "kod pocztowy i miasto pozwanego w formacie XX-XXX Miasto",
  "pozwany_numer_krs": "numer KRS nabywcy (jeśli znaleziony w KRS)",
  "platnosc_kwota_glowna": "kwota do zapłaty",
  "roszczenie_kwota_glowna": "kwota roszczenia (ta sama co kwota główna)",
  "roszczenie_odsetki_data_poczatkowa": "data od której liczyć odsetki (dzień po terminie płatności)",
  "dowod_faktura_numer": "numer faktury",
  "dowod_faktura_data_wystawienia": "data wystawienia faktury",
  "uzasadnienie_faktura_data": "data faktury",
  "uzasadnienie_termin_platnosci": "termin płatności"
}}"""

    try:
        print(prompt)
        response = requests.post(
            "http://127.0.0.1:1234/v1/chat/completions",
            json={
                "model": "google/gemma-3-12b",
                "messages": [
                    {"role": "system", "content": "Jesteś asystentem prawnym. Analizujesz dokumenty i wypełniasz formularze pozwów."},
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": 2048,
                "temperature": 0.1
            },
            timeout=300
        )
        
        if response.status_code == 200:
            result = response.json()
            output = result["choices"][0]["message"]["content"]
            
            # Parsuj JSON z odpowiedzi
            try:
                clean = output.strip()
                if clean.startswith("```"):
                    lines = clean.split("\n")
                    clean = "\n".join(lines[1:-1])
                fields = json.loads(clean)
                
                # === WYSZUKIWANIE SĄDU NA PODSTAWIE KODU POCZTOWEGO POZWANEGO ===
                pozwany_kod_miasto = fields.get('pozwany_kod_pocztowy_miasto', '')
                if pozwany_kod_miasto:
                    # Wyodrębnij sam kod pocztowy (format XX-XXX)
                    kod_match = re.search(r'\d{2}-\d{3}', pozwany_kod_miasto)
                    kod_pocztowy = kod_match.group(0) if kod_match else pozwany_kod_miasto
                    
                    # Wczytaj plik sady.json
                    sady_path = os.path.join(current_app.root_path, '..', 'assets', 'sady.json')
                    try:
                        with open(sady_path, 'r', encoding='utf-8') as f:
                            sady_data = json.load(f)
                        
                        # Określ typ sądu na podstawie WPS (wartość przedmiotu sporu)
                        # Domyślnie rejonowy, okręgowy gdy WPS > 100 000 zł
                        wps = 0
                        kwota_str = fields.get('platnosc_kwota_glowna', '0')
                        if kwota_str:
                            kwota_clean = str(kwota_str).replace(',', '.').replace(' ', '').replace('zł', '')
                            kwota_clean = ''.join(c for c in kwota_clean if c.isdigit() or c == '.')
                            try:
                                wps = float(kwota_clean)
                            except:
                                wps = 0
                        
                        sad_typ = 'okregowy' if wps > 100000 else 'rejonowy'
                        
                        # Szukaj sądu dla danego kodu pocztowego
                        # Najpierw próbuj dokładne dopasowanie, potem po samym kodzie
                        sad_info = None
                        if sad_typ in sady_data:
                            # Dokładne dopasowanie
                            if pozwany_kod_miasto in sady_data[sad_typ]:
                                sad_info = sady_data[sad_typ][pozwany_kod_miasto]
                            else:
                                # Szukaj po kodzie pocztowym w kluczach
                                for klucz, dane in sady_data[sad_typ].items():
                                    if klucz.startswith(kod_pocztowy):
                                        sad_info = dane
                                        break
                        
                        if sad_info:
                            fields['sad_nazwa_pelna'] = sad_info.get('sad_nazwa_pelna', '')
                            fields['sad_wydzial_gospodarczy'] = sad_info.get('sad_wydzial_gospodarczy', '')
                            fields['sad_adres_pelny'] = sad_info.get('sad_adres_pelny', '')
                            print(f"✅ Znaleziono sąd dla {pozwany_kod_miasto} (kod: {kod_pocztowy}): {sad_info.get('sad_nazwa_pelna')}")
                        else:
                            print(f"⚠️ Nie znaleziono sądu dla kodu: {pozwany_kod_miasto} ({kod_pocztowy})")
                    except Exception as e:
                        print(f"❌ Błąd wczytywania sady.json: {e}")
                
                return jsonify({'success': True, 'fields': fields})
            except:
                return jsonify({'success': True, 'fields': {}, 'raw': output})
        else:
            return jsonify({'success': False, 'error': f'API błąd: {response.status_code}'}), 500
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@llm_bp.route('/api/templates')
def get_templates():
    """Zwraca listę dostępnych szablonów dokumentów."""
    templates_dir = os.path.join(current_app.root_path, '..', 'templates', 'documents')
    
    if not os.path.exists(templates_dir):
        return jsonify([])
    
    try:
        files = [f for f in os.listdir(templates_dir) if f.endswith('.html')]
        templates = []
        for f in files:
            name = f.replace('.html', '').replace('_', ' ').title()
            templates.append({'filename': f, 'name': name})
        return jsonify(templates)
    except Exception as e:
        return jsonify([])


@llm_bp.route('/api/template/<filename>')
def get_template(filename):
    """Zwraca zawartość szablonu HTML."""
    templates_dir = os.path.join(current_app.root_path, '..', 'templates', 'documents')
    template_path = os.path.join(templates_dir, filename)
    
    if not os.path.exists(template_path):
        return jsonify({'error': 'Szablon nie istnieje'}), 404
    
    try:
        with open(template_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Wyodrębnij nazwy pól input
        field_names = re.findall(r'name=["\']([^"\']+)["\']', content)
        field_names = list(set(field_names))  # Usuń duplikaty
        
        return jsonify({
            'content': content,
            'fields': field_names
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@llm_bp.route('/api/process_template', methods=['POST'])
def process_template():
    """
    Przetwarza wiele plików JSON i wypełnia szablon.
    Oczekuje: { "files": ["plik1.json", "plik2.json"], "fields": ["pole1", "pole2"] }
    """
    data = request.get_json()
    
    if not data or 'files' not in data or not data['files']:
        return jsonify({'success': False, 'error': 'Brak plików'}), 400
    
    if 'fields' not in data or not data['fields']:
        return jsonify({'success': False, 'error': 'Brak pól do ekstrakcji'}), 400
    
    files = data['files']
    fields = data['fields']
    
    # Zbierz ścieżki do plików
    json_paths = []
    for filename in files:
        json_path = os.path.join(current_app.config['OUTPUT_FOLDER'], filename)
        if os.path.exists(json_path):
            json_paths.append(json_path)
    
    if not json_paths:
        return jsonify({'success': False, 'error': 'Żaden z plików nie istnieje'}), 404
    
    # Przetwórz przez LLM
    result = extract_template_fields(json_paths, fields)
    
    if 'error' in result and 'success' not in result:
        return jsonify({'success': False, 'error': result['error']}), 500
    
    return jsonify(result)


@llm_bp.route('/api/process_multiple_invoices', methods=['POST'])
def process_multiple_invoices():
    """
    Przetwarza wiele plików JSON - każdy osobno przez LLM.
    Zapisuje wyniki do output/wezwania_faktury/
    Oczekuje: { "files": ["plik1.json", "plik2.json"], "fields": ["pole1", "pole2"] }
    """
    import json
    from datetime import datetime
    
    data = request.get_json()
    
    if not data or 'files' not in data or not data['files']:
        return jsonify({'success': False, 'error': 'Brak plików'}), 400
    
    if 'fields' not in data or not data['fields']:
        return jsonify({'success': False, 'error': 'Brak pól do ekstrakcji'}), 400
    
    files = data['files']
    fields = data['fields']
    
    # Folder na wyniki
    output_dir = os.path.join(current_app.config['OUTPUT_FOLDER'], 'wezwania_faktury')
    os.makedirs(output_dir, exist_ok=True)
    
    results = []
    all_invoices = []
    common_data = {}
    
    for filename in files:
        json_path = os.path.join(current_app.config['OUTPUT_FOLDER'], filename)
        if not os.path.exists(json_path):
            continue
        
        print(f"📄 Przetwarzanie faktury: {filename}")
        
        # Przetwórz każdy plik osobno
        result = extract_template_fields([json_path], fields)
        
        if result.get('success'):
            invoice_data = result.get('fields', {})
            
            # Zapisz wynik do osobnego pliku
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            base_name = os.path.splitext(filename)[0]
            output_filename = f"faktura_{base_name}_{timestamp}.json"
            output_path = os.path.join(output_dir, output_filename)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump({
                    'source_file': filename,
                    'extracted_data': invoice_data
                }, f, ensure_ascii=False, indent=2)
            
            print(f"💾 Zapisano: {output_filename}")
            
            # Funkcja pomocnicza do elastycznego wyszukiwania klucza
            def find_field(data, partial_key):
                """Znajdź pole po częściowym dopasowaniu nazwy klucza"""
                for key, value in data.items():
                    if partial_key.lower() in key.lower():
                        return value
                return ''
            
            # Zbierz dane faktury - elastyczne wyszukiwanie
            # Szukaj kwoty pod różnymi wariantami (LLM może użyć różnych odmian: kwota/kwote/kwoty)
            kwota_val = find_field(invoice_data, 'kwote_do_zaplaty')
            if not kwota_val:
                kwota_val = find_field(invoice_data, 'kwota_do_zaplaty')
            if not kwota_val:
                kwota_val = find_field(invoice_data, 'kwoty_do_zaplaty')
            
            invoice_info = {
                'source': filename,
                'numer': find_field(invoice_data, 'numer_faktury'),
                'data': find_field(invoice_data, 'date_wystawienia'),
                'kwota': kwota_val,
                'termin': find_field(invoice_data, 'terminu_platnosci')
            }
            all_invoices.append(invoice_info)
            
            # Zapisz wspólne dane (wierzyciel, dłużnik) z pierwszej faktury
            if not common_data:
                common_data = {k: v for k, v in invoice_data.items() 
                              if not k.startswith('faktura_') and not k.startswith('platnosc_')}
            
            results.append({
                'file': filename,
                'output': output_filename,
                'success': True
            })
        else:
            results.append({
                'file': filename,
                'success': False,
                'error': result.get('error', 'Nieznany błąd')
            })
    
    # Oblicz sumę kwot
    total = 0
    for inv in all_invoices:
        try:
            kwota_str = str(inv.get('kwota', '0')).replace(',', '.').replace(' ', '')
            kwota_str = ''.join(c for c in kwota_str if c.isdigit() or c == '.')
            total += float(kwota_str) if kwota_str else 0
        except:
            pass
    
    return jsonify({
        'success': True,
        'results': results,
        'invoices': all_invoices,
        'common_data': common_data,
        'total_amount': f"{total:.2f}",
        'output_folder': 'wezwania_faktury'
    })

