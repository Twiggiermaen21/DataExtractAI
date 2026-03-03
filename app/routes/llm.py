import os
import re
from flask import Blueprint, request, jsonify, current_app
from dotenv import load_dotenv

load_dotenv()

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
    - Dane z wezwania -> mapowane bezposrednio (bez LLM)
    - Dane z KRS -> krotkie zapytanie do LLM: znajdz numer KRS pozwanego
    Oczekuje: { "wezwanie": {...}, "krs": [...] }
    """
    import requests
    import json
    
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': 'Brak danych'}), 400
    
    wezwanie = data.get('wezwanie', {})
    krs_list = data.get('krs', [])
    
    # === KROK 1: Bezposrednie mapowanie pol z wezwania (bez LLM) ===
    fields = {}
    
    # Powod (wierzyciel/sprzedawca)
    fields['powod_nazwa_pelna'] = wezwanie.get('wierzyciel_nazwa', '')
    fields['powod_adres_pelny'] = wezwanie.get('wierzyciel_adres', '')
    
    # Wyodrebnij miasto siedziby powoda z adresu
    powod_adres = fields['powod_adres_pelny']
    if powod_adres:
        miasto_match = re.search(r'\d{2}-\d{3}\s+(.+)', powod_adres)
        fields['powod_siedziba_miasto'] = miasto_match.group(1).strip() if miasto_match else ''
    
    # Pozwany (dluznik/nabywca)
    fields['pozwany_nazwa_pelna'] = wezwanie.get('dluznik_nazwa', '')
    fields['pozwany_adres_pelny'] = wezwanie.get('dluznik_adres', '')
    
    # Wyodrebnij kod pocztowy + miasto pozwanego
    pozwany_adres = fields['pozwany_adres_pelny']
    if pozwany_adres:
        kod_miasto_match = re.search(r'(\d{2}-\d{3}\s+\S+(?:\s+\S+)?)', pozwany_adres)
        if kod_miasto_match:
            fields['pozwany_kod_pocztowy_miasto'] = kod_miasto_match.group(1).strip()
    
    # Kwoty i daty
    fields['platnosc_kwota_glowna'] = wezwanie.get('kwota_do_zaplaty', '')
    fields['roszczenie_kwota_glowna'] = wezwanie.get('kwota_do_zaplaty', '')
    fields['dowod_faktura_numer'] = wezwanie.get('faktura_numer', '')
    fields['dowod_faktura_data_wystawienia'] = wezwanie.get('faktura_data_wystawienia', '')
    fields['uzasadnienie_faktura_data'] = wezwanie.get('faktura_data_wystawienia', '')
    fields['uzasadnienie_termin_platnosci'] = wezwanie.get('termin_platnosci', '')
    fields['roszczenie_odsetki_data_poczatkowa'] = wezwanie.get('termin_platnosci', '')
    
    print(f"\n{'='*60}")
    print(f"📋 KROK 1: Zmapowane pola z wezwania (bez LLM):")
    print(json.dumps(fields, indent=2, ensure_ascii=False))
    print(f"{'='*60}")
    
    # === KROK 2: Zapytanie LLM o numer KRS pozwanego (krotki prompt) ===
    pozwany_nazwa = fields.get('pozwany_nazwa_pelna', '')
    
    if krs_list and pozwany_nazwa:
        krs_text = str(krs_list[0]) if krs_list else ''
        original_len = len(krs_text)
        
        if original_len > 2000:
            cut = original_len - 2000
            krs_text = krs_text[:2000]
            print(f"\n✂️  KRS: PRZYCIĘTO {cut} znaków (oryginał: {original_len} → po przycięciu: 2000 znaków)")
        else:
            print(f"\n✅ KRS: OK ({original_len} znaków, mieści się w limicie)")
        
        krs_prompt = f"""Z poniższego dokumentu KRS znajdź numer KRS dla firmy: "{pozwany_nazwa}"

DOKUMENT KRS:
{krs_text}

Sprawdź czy nazwa firmy w dokumencie zgadza się z podaną nazwą.
Odpowiedz TYLKO numerem KRS (same cyfry, np. "0000123456"). 
Jeśli nie znalazłeś numeru KRS lub nazwa firmy się nie zgadza, odpowiedz: "BRAK"."""

        print(f"🔍 KROK 2: Szukam KRS dla pozwanego: {pozwany_nazwa}")
        
        try:
            response = requests.post(
                os.environ.get("LLM_API_URL"),
                json={
                    "model": os.environ.get("LLM_MODEL"),
                    "messages": [
                        {"role": "system", "content": "Wyciągasz numery KRS z dokumentów. Odpowiadasz krótko - samym numerem KRS lub BRAK."},
                        {"role": "user", "content": krs_prompt}
                    ],
                    "max_tokens": 50,
                    "temperature": 0.1
                },
                timeout=120
            )
            
            if response.status_code == 200:
                result = response.json()
                krs_answer = result["choices"][0]["message"]["content"].strip()
                print(f"🏢 LLM odpowiedź KRS: {krs_answer}")
                
                # Wyciagnij sam numer (cyfry)
                krs_match = re.search(r'\d{7,10}', krs_answer)
                if krs_match and 'BRAK' not in krs_answer.upper():
                    fields['pozwany_numer_krs'] = krs_match.group(0)
                    print(f"✅ KRS pozwanego znaleziony: {fields['pozwany_numer_krs']}")
                else:
                    print(f"⚠️ Nie znaleziono KRS dla: {pozwany_nazwa}")
            else:
                error_text = response.text
                print(f"❌ Błąd API KRS: {response.status_code}: {error_text}")
                
        except Exception as e:
            print(f"❌ Błąd zapytania KRS: {e}")
    else:
        if not krs_list:
            print("\n⚠️ Brak dokumentów KRS - pomijam wyszukiwanie numeru KRS")
        if not pozwany_nazwa:
            print("\n⚠️ Brak nazwy pozwanego - pomijam wyszukiwanie numeru KRS")
    
    # === KROK 3: Wyszukiwanie sadu na podstawie kodu pocztowego pozwanego ===
    pozwany_kod_miasto = fields.get('pozwany_kod_pocztowy_miasto', '')
    if pozwany_kod_miasto:
        kod_match = re.search(r'\d{2}-\d{3}', pozwany_kod_miasto)
        kod_pocztowy = kod_match.group(0) if kod_match else pozwany_kod_miasto
        
        sady_path = os.path.join(current_app.root_path, '..', 'assets', 'sady.json')
        try:
            with open(sady_path, 'r', encoding='utf-8') as f:
                sady_data = json.load(f)
            
            # Typ sadu na podstawie WPS
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
            
            sad_info = None
            if sad_typ in sady_data:
                if pozwany_kod_miasto in sady_data[sad_typ]:
                    sad_info = sady_data[sad_typ][pozwany_kod_miasto]
                else:
                    for klucz, dane in sady_data[sad_typ].items():
                        if klucz.startswith(kod_pocztowy):
                            sad_info = dane
                            break
            
            if sad_info:
                fields['sad_nazwa_pelna'] = sad_info.get('sad_nazwa_pelna', '')
                fields['sad_wydzial_gospodarczy'] = sad_info.get('sad_wydzial_gospodarczy', '')
                fields['sad_adres_pelny'] = sad_info.get('sad_adres_pelny', '')
                print(f"\n✅ KROK 3: Znaleziono sąd dla {pozwany_kod_miasto}: {sad_info.get('sad_nazwa_pelna')}")
            else:
                print(f"\n⚠️ KROK 3: Nie znaleziono sądu dla kodu: {pozwany_kod_miasto}")
        except Exception as e:
            print(f"\n❌ Błąd wczytywania sady.json: {e}")
    
    # Usun puste pola
    fields = {k: v for k, v in fields.items() if v}
    
    print(f"\n{'='*60}")
    print(f"📝 FINALNE pola pozwu:")
    print(json.dumps(fields, indent=2, ensure_ascii=False))
    print(f"{'='*60}\n")
    
    return jsonify({'success': True, 'fields': fields})


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
