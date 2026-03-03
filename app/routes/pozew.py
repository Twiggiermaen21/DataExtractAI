"""
Endpointy API do analizy pozwu.
Mapuje dane z wezwania i KRS na pola formularza pozwu,
wyszukuje numer KRS pozwanego przez LLM i dopasowuje właściwy sąd.
"""

import os
import re
import json
import requests
from flask import Blueprint, request, jsonify, current_app
from dotenv import load_dotenv

from app.utils.helpers import parse_kwota, extract_city_from_address, extract_postal_code_city, extract_postal_code

load_dotenv()

pozew_bp = Blueprint('pozew', __name__)


# ============================================================
# Mapowanie pól wezwania → pól pozwu (bez LLM)
# ============================================================

def _map_wezwanie_fields(wezwanie: dict) -> dict:
    """
    Bezpośrednie mapowanie danych z wezwania do zapłaty na pola pozwu.
    Nie wymaga LLM — to proste przypisanie pól.
    
    Args:
        wezwanie: Słownik z danymi wezwania (wierzyciel, dłużnik, kwoty, daty)
        
    Returns:
        Słownik z polami pozwu
    """
    fields = {}

    # --- Powód (wierzyciel / sprzedawca) ---
    fields['powod_nazwa_pelna'] = wezwanie.get('wierzyciel_nazwa', '')
    fields['powod_adres_pelny'] = wezwanie.get('wierzyciel_adres', '')

    # Wyodrębnij miasto siedziby powoda z adresu (np. "00-123 Warszawa" → "Warszawa")
    powod_adres = fields['powod_adres_pelny']
    if powod_adres:
        fields['powod_siedziba_miasto'] = extract_city_from_address(powod_adres)

    # --- Pozwany (dłużnik / nabywca) ---
    fields['pozwany_nazwa_pelna'] = wezwanie.get('dluznik_nazwa', '')
    fields['pozwany_adres_pelny'] = wezwanie.get('dluznik_adres', '')

    # Wyodrębnij kod pocztowy + miasto pozwanego
    pozwany_adres = fields['pozwany_adres_pelny']
    if pozwany_adres:
        kod_miasto = extract_postal_code_city(pozwany_adres)
        if kod_miasto:
            fields['pozwany_kod_pocztowy_miasto'] = kod_miasto

    # --- Kwoty i daty ---
    fields['platnosc_kwota_glowna'] = wezwanie.get('kwota_do_zaplaty', '')
    fields['roszczenie_kwota_glowna'] = wezwanie.get('kwota_do_zaplaty', '')
    fields['dowod_faktura_numer'] = wezwanie.get('faktura_numer', '')
    fields['dowod_faktura_data_wystawienia'] = wezwanie.get('faktura_data_wystawienia', '')
    fields['uzasadnienie_faktura_data'] = wezwanie.get('faktura_data_wystawienia', '')
    fields['uzasadnienie_termin_platnosci'] = wezwanie.get('termin_platnosci', '')
    fields['roszczenie_odsetki_data_poczatkowa'] = wezwanie.get('termin_platnosci', '')

    return fields


# ============================================================
# Wyszukiwanie numeru KRS pozwanego przez LLM
# ============================================================

def _find_krs_number(pozwany_nazwa: str, krs_list: list, model: str = None) -> str | None:
    """
    Wysyła krótkie zapytanie do LLM, aby znaleźć numer KRS pozwanego
    w dokumencie KRS. Przycina dokument do 2000 znaków.
    
    Args:
        pozwany_nazwa: Pełna nazwa firmy pozwanego
        krs_list: Lista dokumentów KRS (używany jest pierwszy element)
        
    Returns:
        Numer KRS (string z cyframi) lub None jeśli nie znaleziono
    """
    if not krs_list or not pozwany_nazwa:
        return None

    # Przygotuj tekst KRS (przytnij do 2000 znaków)
    krs_text = str(krs_list[0])
    if len(krs_text) > 2000:
        print(f"✂️  KRS: przycięto {len(krs_text) - 2000} znaków")
        krs_text = krs_text[:2000]

    krs_prompt = f"""Z poniższego dokumentu KRS znajdź numer KRS dla firmy: "{pozwany_nazwa}"

DOKUMENT KRS:
{krs_text}

Sprawdź czy nazwa firmy w dokumencie zgadza się z podaną nazwą.
Odpowiedz TYLKO numerem KRS (same cyfry, np. "0000123456"). 
Jeśli nie znalazłeś numeru KRS lub nazwa firmy się nie zgadza, odpowiedz: "BRAK"."""

    print(f"🔍 Szukam KRS dla pozwanego: {pozwany_nazwa}")

    try:
        # Zapytanie do LLM — krótka odpowiedź (max 50 tokenów)
        response = requests.post(
            os.environ.get("LLM_API_URL"),
            json={
                "model": model or os.environ.get("LLM_MODEL"),
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

            # Wyciągnij sam numer (7-10 cyfr)
            krs_match = re.search(r'\d{7,10}', krs_answer)
            if krs_match and 'BRAK' not in krs_answer.upper():
                print(f"✅ KRS pozwanego: {krs_match.group(0)}")
                return krs_match.group(0)
            else:
                print(f"⚠️ Nie znaleziono KRS dla: {pozwany_nazwa}")
        else:
            print(f"❌ Błąd API KRS: {response.status_code}: {response.text}")

    except Exception as e:
        print(f"❌ Błąd zapytania KRS: {e}")

    return None


# ============================================================
# Wyszukiwanie właściwego sądu wg kodu pocztowego pozwanego
# ============================================================

def _find_court(pozwany_kod_miasto: str, kwota_glowna: str) -> dict:
    """
    Wyszukuje właściwy sąd na podstawie kodu pocztowego pozwanego.
    Typ sądu (rejonowy/okręgowy) zależy od WPS — wartości przedmiotu sporu.
    
    Args:
        pozwany_kod_miasto: Kod pocztowy + miasto pozwanego (np. "00-123 Warszawa")
        kwota_glowna: Kwota roszczenia jako string
        
    Returns:
        Słownik z danymi sądu lub pusty słownik
    """
    if not pozwany_kod_miasto:
        return {}

    kod_pocztowy = extract_postal_code(pozwany_kod_miasto)

    # Wczytaj bazę sądów z pliku JSON
    sady_path = os.path.join(current_app.root_path, '..', 'assets', 'sady.json')
    try:
        with open(sady_path, 'r', encoding='utf-8') as f:
            sady_data = json.load(f)
    except Exception as e:
        print(f"❌ Błąd wczytywania sady.json: {e}")
        return {}

    # Ustal typ sądu na podstawie WPS (wartości przedmiotu sporu)
    # WPS > 100 000 zł → sąd okręgowy, w przeciwnym razie rejonowy
    wps = parse_kwota(kwota_glowna)
    sad_typ = 'okregowy' if wps > 100000 else 'rejonowy'

    # Szukaj sądu: najpierw po pełnym kluczu, potem po samym kodzie pocztowym
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
        print(f"✅ Znaleziono sąd: {sad_info.get('sad_nazwa_pelna')}")
        return {
            'sad_nazwa_pelna': sad_info.get('sad_nazwa_pelna', ''),
            'sad_wydzial_gospodarczy': sad_info.get('sad_wydzial_gospodarczy', ''),
            'sad_adres_pelny': sad_info.get('sad_adres_pelny', '')
        }
    else:
        print(f"⚠️ Nie znaleziono sądu dla kodu: {pozwany_kod_miasto}")
        return {}


# ============================================================
# Endpoint: POST /api/analyze_pozew
# ============================================================

@pozew_bp.route('/api/analyze_pozew', methods=['POST'])
def analyze_pozew():
    """
    Analizuje dane z wezwania i KRS, mapuje je na pola formularza pozwu.
    
    Przebieg:
      1. Mapowanie pól z wezwania → pola pozwu (bez LLM)
      2. Wyszukanie numeru KRS pozwanego (krótkie zapytanie do LLM)
      3. Wyszukanie właściwego sądu wg kodu pocztowego pozwanego
    
    Oczekuje JSON: { "wezwanie": {...}, "krs": [...] }
    Zwraca JSON:   { "success": true, "fields": {...} }
    """
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': 'Brak danych'}), 400

    wezwanie = data.get('wezwanie', {})
    krs_list = data.get('krs', [])
    model_name = data.get('model')

    # KROK 1: Bezpośrednie mapowanie pól z wezwania (bez LLM)
    fields = _map_wezwanie_fields(wezwanie)

    print(f"📋 KROK 1: Zmapowano {len(fields)} pól z wezwania (bez LLM)")

    # KROK 2: Szukanie numeru KRS pozwanego (krótkie zapytanie LLM)
    krs_number = _find_krs_number(fields.get('pozwany_nazwa_pelna', ''), krs_list, model=model_name)
    if krs_number:
        fields['pozwany_numer_krs'] = krs_number

    # KROK 3: Wyszukanie sądu wg kodu pocztowego pozwanego
    court_data = _find_court(
        fields.get('pozwany_kod_pocztowy_miasto', ''),
        fields.get('platnosc_kwota_glowna', '0')
    )
    fields.update(court_data)

    # Usuń puste pola z wyniku
    fields = {k: v for k, v in fields.items() if v}

    print(f"📝 KROK 4: Finalne pola pozwu: {len(fields)} pól gotowych")

    return jsonify({'success': True, 'fields': fields})
