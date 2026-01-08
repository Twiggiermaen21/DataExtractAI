import json
import re
import os

def analyze_invoice_json(json_path):
    """
    Główna funkcja analizująca fakturę.
    """
    wynik = {
        "nr_faktury": "",
        "data": "",
        "kwota": "",
        "nip": "",
        "raw_text": ""
    }

    if not os.path.exists(json_path):
        print(f"Brak pliku: {json_path}")
        return wynik

    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        text = _extract_clean_text(data)
        wynik["raw_text"] = text

        if text:
            wynik.update(_run_regex_search(text))

    except Exception as e:
        print(f"Błąd: {e}")
    
    return wynik

def _extract_clean_text(json_data):
    """Wyciąga tekst z JSONa (PaddleOCR)"""
    text_content = ""
    if isinstance(json_data, dict) and "parsing_res_list" in json_data:
        for block in json_data["parsing_res_list"]:
            text_content += block.get("block_content", "") + "\n"
    elif isinstance(json_data, list):
        for element in json_data:
            if isinstance(element, dict) and "rec_text" in element:
                text_content += element["rec_text"] + "\n"
            else:
                text_content += str(element) + "\n"
    return text_content

def _run_regex_search(text):
    """Agresywne szukanie danych"""
    found = {}

    # 1. Numer Faktury
    fv_match = re.search(r'Faktura\s*(?:VAT)?\s*(?:nr\.?|numer)?\s*[:.]?\s*(\S+)', text, re.IGNORECASE)
    if fv_match:
        val = fv_match.group(1)
        if len(val) > 1 and val.lower() not in ['nr', 'numer', 'vat', 'data']:
            found["nr_faktury"] = val

    # 2. NIP
    nip_match = re.search(r'\d{3}[-\s]?\d{3}[-\s]?\d{2}[-\s]?\d{2}', text)
    if nip_match:
        found["nip"] = nip_match.group(0)

    # 3. Data
    data_match = re.search(r'\d{4}[-.]\d{2}[-.]\d{2}|\d{2}[-.]\d{2}[-.]\d{4}', text)
    if data_match:
        found["data"] = data_match.group(0)

    # -------------------------------------------------------------
    # 4. KWOTA BRUTTO - Logika "Znajdź wszystkie i weź MAX"
    # -------------------------------------------------------------
    candidates = []

    # A. Szukanie kontekstowe (Słowo kluczowe + dowolne znaki + liczba)
    # (?s) oznacza, że kropka . pasuje też do nowej linii (\n)
    # Szukamy liczby do 100 znaków po słowie kluczowym
    keywords = r'(?:Do\s?zapłaty|Do\s?zaplaty|Razem|Brutto|Suma|Wartość|Total)'
    
    context_matches = re.findall(rf'(?s){keywords}.{{0,100}}?(\d[\d\s\.,]*\d{{2}})', text, re.IGNORECASE)
    
    for amount in context_matches:
        val = _parse_amount(amount)
        if val is not None:
            candidates.append(val)

    # B. Szukanie po walucie (na wypadek gdyby słowa kluczowe nie zadziałały)
    # Szukamy liczby stojącej bezpośrednio przed PLN/ZŁ
    currency_matches = re.findall(r'(\d[\d\s\.,]*\d{2})\s*(?:PLN|ZŁ|ZL)', text, re.IGNORECASE)
    
    for amount in currency_matches:
        val = _parse_amount(amount)
        if val is not None:
            candidates.append(val)

    # C. Wybór największej (Brutto)
    if candidates:
        # Usuwamy duplikaty i sortujemy
        unique_candidates = sorted(list(set(candidates)))
        
        # Filtrowanie nierealnych kwot (np. rok 2023 jako kwota, jeśli są inne opcje)
        # Jeśli mamy kwotę > 3000 i kwotę przypominającą rok (np. 2023, 2024), usuń rok
        final_candidates = []
        for c in unique_candidates:
            # Jeśli liczba wygląda jak bieżący rok (np. 2020-2030) i jest to jedna z mniejszych liczb,
            # a mamy w zbiorze wyraźnie większe liczby, to pewnie data wpadła przez pomyłkę.
            if 2020 <= c <= 2030 and max(unique_candidates) > 3000:
                continue
            final_candidates.append(c)

        if final_candidates:
            max_amount = max(final_candidates)
            found["kwota"] = f"{max_amount:.2f}".replace('.', ',') + " PLN"

    return found

def _parse_amount(amount_str):
    """
    Zamienia tekst na float, odporny na formaty typu:
    '1 200,00', '1.200,00', '1200.00', '1 200.00'
    """
    if not amount_str:
        return None
    
    # Wstępne czyszczenie
    clean = amount_str.replace(' ', '').replace('\xa0', '').strip()
    
    # Odrzucamy, jeśli to nie wygląda na liczbę (np. sam przecinek)
    if len(clean) < 2:
        return None

    try:
        # Jeśli mamy format '1.234,56' (kropka wcześniej niż przecinek) -> Polski/Niemiecki
        if '.' in clean and ',' in clean:
            if clean.find('.') < clean.find(','):
                clean = clean.replace('.', '').replace(',', '.')
            else:
                # Format '1,234.56' -> Angielski
                clean = clean.replace(',', '')
        
        # Jeśli tylko przecinek -> zamień na kropkę
        elif ',' in clean:
            clean = clean.replace(',', '.')
        
        # Jeśli tylko kropka -> sprawdź czy to nie separator tysięcy (np. 1.200)
        # Ale zazwyczaj w Pythonie float() łyka kropkę jako dziesiętną.
        # Przyjmujemy, że OCR daje 2 miejsca po przecinku.
        
        val = float(clean)
        return val
    except ValueError:
        return None

# --- TESTOWANIE ---
if __name__ == "__main__":
    # Test na "trudnym" tekście symulującym problem z OCR
    test_text = """
    Sprzedawca: Firma X
    Data: 2024-01-01
    Netto: 1000.00
    VAT: 230.00
    
    Razem ................................. 
    ....................... 1 230,00 PLN
    
    Do zapłaty:
    1 230,00
    """
    
    print("Symulacja OCR:")
    # Aby przetestować, podmieniamy funkcję extract na taką, która zwraca nasz test_text
    # Normalnie używasz analyze_invoice_json(plik)
    wynik = _run_regex_search(test_text)
    print(wynik)