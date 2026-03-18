"""
Endpointy API do analizy pozwu.
Mapuje dane z wezwania i KRS na pola formularza pozwu.
"""

import os
import re
import json
import logging
from flask import Blueprint, request, jsonify, current_app
from app.utils.helpers import parse_kwota, extract_city_from_address, extract_postal_code_city, extract_postal_code
from app.services.llm_service import call_llm

log = logging.getLogger(__name__)

pozew_bp = Blueprint('pozew', __name__)


def _map_wezwanie_fields(wezwanie: dict) -> dict:
    """Mapowanie danych z wezwania na pola pozwu (bez LLM)."""
    fields = {}

    fields['powod_nazwa_pelna'] = wezwanie.get('wierzyciel_nazwa', '')
    fields['powod_adres_pelny'] = wezwanie.get('wierzyciel_adres', '')

    powod_adres = fields['powod_adres_pelny']
    if powod_adres:
        fields['powod_siedziba_miasto'] = extract_city_from_address(powod_adres)

    fields['pozwany_nazwa_pelna'] = wezwanie.get('dluznik_nazwa', '')
    fields['pozwany_adres_pelny'] = wezwanie.get('dluznik_adres', '')

    pozwany_adres = fields['pozwany_adres_pelny']
    if pozwany_adres:
        kod_miasto = extract_postal_code_city(pozwany_adres)
        if kod_miasto:
            fields['pozwany_kod_pocztowy_miasto'] = kod_miasto

    fields['platnosc_kwota_glowna'] = wezwanie.get('kwota_do_zaplaty', '')
    fields['roszczenie_kwota_glowna'] = wezwanie.get('kwota_do_zaplaty', '')
    fields['dowod_faktura_numer'] = wezwanie.get('faktura_numer', '')
    fields['dowod_faktura_data_wystawienia'] = wezwanie.get('faktura_data_wystawienia', '')
    fields['uzasadnienie_faktura_data'] = wezwanie.get('faktura_data_wystawienia', '')
    fields['uzasadnienie_termin_platnosci'] = wezwanie.get('termin_platnosci', '')
    fields['roszczenie_odsetki_data_poczatkowa'] = wezwanie.get('termin_platnosci', '')

    return fields


def _find_krs_number(pozwany_nazwa: str, krs_list: list, model: str = None) -> str | None:
    """Wyszukuje numer KRS pozwanego w dokumencie KRS przez LLM."""
    if not krs_list or not pozwany_nazwa:
        return None

    krs_text = str(krs_list[0])[:2000]

    krs_prompt = f"""Z poniższego dokumentu KRS znajdź numer KRS dla firmy: "{pozwany_nazwa}"

DOKUMENT KRS:
{krs_text}

Sprawdź czy nazwa firmy w dokumencie zgadza się z podaną nazwą.
Odpowiedz TYLKO numerem KRS (same cyfry, np. "0000123456"). 
Jeśli nie znalazłeś numeru KRS lub nazwa firmy się nie zgadza, odpowiedz: "BRAK"."""

    try:
        krs_answer = call_llm(krs_prompt, system_prompt="Wyciągasz numery KRS z dokumentów. Odpowiadasz krótko - samym numerem KRS lub BRAK.", model=model)
        
        krs_match = re.search(r'\d{7,10}', krs_answer)
        if krs_match and 'BRAK' not in krs_answer.upper():
            return krs_match.group(0)
    except Exception as e:
        log.warning("KRS lookup failed: %s", e)

    return None


def _find_court(pozwany_kod_miasto: str, kwota_glowna: str) -> dict:
    """Wyszukuje właściwy sąd na podstawie kodu pocztowego pozwanego."""
    if not pozwany_kod_miasto:
        return {}

    kod_pocztowy = extract_postal_code(pozwany_kod_miasto)

    sady_path = os.path.join(current_app.root_path, '..', 'assets', 'sady.json')
    try:
        with open(sady_path, 'r', encoding='utf-8') as f:
            sady_data = json.load(f)
    except Exception:
        return {}

    wps = parse_kwota(kwota_glowna)
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
        return {
            'sad_nazwa_pelna': sad_info.get('sad_nazwa_pelna', ''),
            'sad_wydzial_gospodarczy': sad_info.get('sad_wydzial_gospodarczy', ''),
            'sad_adres_pelny': sad_info.get('sad_adres_pelny', ''),
        }
    return {}


@pozew_bp.route('/api/analyze_pozew', methods=['POST'])
def analyze_pozew():
    """Analizuje dane z wezwania i KRS, mapuje na pola pozwu."""
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': 'Brak danych'}), 400

    wezwanie = data.get('wezwanie', {})
    krs_list = data.get('krs', [])
    model_name = data.get('model')

    fields = _map_wezwanie_fields(wezwanie)

    krs_number = _find_krs_number(fields.get('pozwany_nazwa_pelna', ''), krs_list, model=model_name)
    if krs_number:
        fields['pozwany_numer_krs'] = krs_number

    court_data = _find_court(
        fields.get('pozwany_kod_pocztowy_miasto', ''),
        fields.get('platnosc_kwota_glowna', '0'),
    )
    fields.update(court_data)

    fields = {k: v for k, v in fields.items() if v}

    return jsonify({'success': True, 'fields': fields})
