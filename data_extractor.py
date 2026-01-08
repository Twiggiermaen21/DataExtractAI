import json
import re
import os

def analyze_invoice_json(json_path):
    """
    Główna funkcja: otwiera JSON, wyciąga tekst i szuka danych.
    Zwraca słownik z gotowymi danymi do formularza.
    """
    # Domyślny wynik, gdyby coś poszło nie tak
    wynik = {
        "nr_faktury": "",
        "data": "",
        "kwota": "",
        "nip": "",
        "raw_text": "" # Dla debugowania
    }

    if not os.path.exists(json_path):
        return wynik

    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # 1. Wyciągnij czysty tekst (omijając metadane jak input_path)
        text = _extract_clean_text(data)
        wynik["raw_text"] = text

        if not text:
            return wynik

        # 2. Uruchom Regexy na tekście
        wynik.update(_run_regex_search(text))

    except Exception as e:
        print(f"Błąd analizy JSON: {e}")
    
    return wynik

def _extract_clean_text(json_data):
    """Pomocnicza funkcja wyciągająca tekst z różnych formatów PaddleOCR"""
    text_content = ""
    
    # Wariant A: PaddleOCRVL / Structure (Twoja wersja)
    if isinstance(json_data, dict) and "parsing_res_list" in json_data:
        for block in json_data["parsing_res_list"]:
            # Pobieramy tylko treść bloku, ignorujemy resztę
            text_content += block.get("block_content", "") + "\n"
            
    # Wariant B: Standardowa lista wyników
    elif isinstance(json_data, list):
        for element in json_data:
            if isinstance(element, dict) and "rec_text" in element:
                text_content += element["rec_text"] + "\n"
            else:
                # Ostateczność dla list, ale unikamy zrzutu całego słownika
                text_content += str(element) + "\n"
                
    return text_content

def _run_regex_search(text):
    """Szuka konkretnych danych w tekście"""
    found = {}

    # A. Numer Faktury
    # Szuka: Faktura ... (numer)
    fv_match = re.search(r'Faktura\s*(?:VAT)?\s*(?:nr\.?|numer)?\s*[:.]?\s*(\S+)', text, re.IGNORECASE)
    if fv_match:
        val = fv_match.group(1)
        # Filtrowanie śmieci
        if len(val) > 1 and val.lower() not in ['nr', 'numer', 'vat', 'data', 'oryginał']:
            found["nr_faktury"] = val

    # B. NIP
    nip_match = re.search(r'\d{3}[-\s]?\d{3}[-\s]?\d{2}[-\s]?\d{2}', text)
    if nip_match:
        found["nip"] = nip_match.group(0)

    # C. Data
    data_match = re.search(r'\d{4}[-.]\d{2}[-.]\d{2}|\d{2}[-.]\d{2}[-.]\d{4}', text)
    if data_match:
        found["data"] = data_match.group(0)

    # D. Kwota (Brutto - logika MAX po słowie Razem)
    # Szuka liczb w okolicy słowa "Razem"
    amounts_raw = re.findall(r'Razem.{0,40}?(\d[\d\s\.]*[,.]\d{2})', text, re.IGNORECASE)
    valid_floats = []
    
    for amount in amounts_raw:
        # Czyszczenie: 1 230,00 -> 1230.00
        clean = amount.replace(' ', '').replace('\xa0', '').replace(',', '.')
        if clean.count('.') > 1: # Usuń kropki tysięcy (np. 1.000.00)
            clean = clean.replace('.', '', clean.count('.') - 1)
        try:
            valid_floats.append(float(clean))
        except ValueError:
            pass

    if valid_floats:
        # Bierzemy największą (zazwyczaj brutto)
        found["kwota"] = f"{max(valid_floats):.2f}".replace('.', ',') + " PLN"

    return found