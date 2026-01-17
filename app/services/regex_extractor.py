import re


def extract_data_regex(json_data):
    # 1. Łączenie wszystkich bloków w jeden tekst (dla łatwiejszego przeszukiwania)
    blocks = [b.get("block_content", "") for b in json_data.get("parsing_res_list", [])]
    full_text = "\n".join(blocks)
    
    # Słownik wynikowy (musi pasować kluczami do JS: templatesData -> fields -> id)
    extracted = {
        "doc_place_date": "",
        # "creditor_name": "",
        # "creditor_address": "",
        # "creditor_nip": "",
        # "creditor_krs": "",
        # "debtor_name": "",
        # "debtor_address": "",
        "fv_nr": "",
        "fv_date": "",
        "debt_amount": "",
        "interest_date": "",
        # "bank_account": "",
        # "bank_name": ""
    }

    # ==========================================
    # LOGIKA EKSTRAKCJI (REGEX)
    # ==========================================

    # 1. MIEJSCOWOŚĆ I DATA (Szukamy na początku dokumentu wzorca: Miasto, DD.MM.YYYY)
    # Wyjaśnienie: ^ = początek linii, .*? = dowolne znaki, \d{2} = dwie cyfry
    place_date_match = re.search(r'(?m)^.*?,?\s*\d{2}[\.-]\d{2}[\.-]\d{4}\s*r?\.?', full_text)
    if place_date_match:
        extracted['doc_place_date'] = place_date_match.group(0).strip()

    # 2. NUMER FAKTURY
    # Szukamy słów "Faktury nr", "Faktura nr", "nr" i pobieramy to co jest dalej (bez spacji)
    fv_match = re.search(r'(?i)(?:faktur[ay]\s+nr|nr\s+faktury)\s*([a-zA-Z0-9/_]+)', full_text)
    if fv_match:
        extracted['fv_nr'] = fv_match.group(1)

    # 3. DATA FAKTURY
    # Szukamy daty, która występuje po słowie "z dnia" lub w pobliżu faktury
    fv_date_match = re.search(r'(?i)faktur.*?z\s+dnia\s+(\d{2}[\.-]\d{2}[\.-]\d{4})', full_text)
    if fv_date_match:
        extracted['fv_date'] = fv_date_match.group(1)

    # 4. KWOTA DO ZAPŁATY (Zaktualizowane)
    # Wyjaśnienie Regexa:
    # (?i) - ignoruj wielkość liter
    # (?: ... ) - grupa, która sprawdza alternatywy (słowa kluczowe), ale ich nie "wycina" do wyniku
    # kwot[yę]  - łapie "kwoty" lub "kwotę"
    # |razem(?:\s+do\s+zapłaty)? - łapie samo "razem" LUB "razem do zapłaty"
    # |do\s+zapłaty - łapie samo "do zapłaty"
    # |suma - warto dodać też "suma"
    # \s*:?\s* - pozwala na spacje i opcjonalny dwukropek po słowie kluczowym (np. "Razem:")
    # ([\d\s]+(?:[\.,]\d{2})?) - to jest grupa (1), która łapie samą liczbę
    
    amount_match = re.search(r'(?i)(?:kwot[yę]|razem(?:\s+do\s+zapłaty)?|do\s+zapłaty|suma)\s*:?\s*([\d\s]+(?:[\.,]\d{2})?)', full_text)

    if amount_match:
        # Pobieramy grupę z liczbą (group(1), bo group(0) to cały znaleziony tekst)
        raw_amount = amount_match.group(1)
        
        # Usuwamy spacje (np. z "1 200") i zamieniamy przecinek na kropkę
        clean_amount = raw_amount.replace(" ", "").replace(",", ".")
        
        # Opcjonalnie: usuwamy kropkę na końcu jeśli regex złapał ją przypadkiem z końca zdania
        clean_amount = clean_amount.rstrip('.')
        
        extracted['debt_amount'] = clean_amount
    # 5. DATA ODSETEK / TERMIN PŁATNOŚCI
    # Wyjaśnienie Regexa:
    # (?i) - ignoruj wielkość liter
    # (?: ... ) - grupa alternatywna (nie przechwytująca)
    # od\s+dnia - łapie "od dnia"
    # |termin(?:\s+płatności)? - łapie "termin" LUB "termin płatności"
    # |do\s+dnia - łapie "do dnia"
    # \s*:?\s* - pozwala na spacje i opcjonalny dwukropek (np. "Termin: 20.01.2026")
    
    interest_match = re.search(r'(?i)(?:od\s+dnia|termin(?:\s+p[lł]atno[sś]ci)?|do\s+dnia)\s*:?\s*(\d{2}[\.-]\d{2}[\.-]\d{4})', full_text)
    
    if interest_match:
        extracted['interest_date'] = interest_match.group(1)
    # 6. NUMER KONTA (IBAN)
    # Szukamy ciągu 26 cyfr (z opcjonalnymi spacjami)
    # Wzorzec: \d{2} to 2 cyfry, (?:\s*\d{4}){6} to 6 grup po 4 cyfry
    iban_match = re.search(r'\d{2}(?:\s*\d{4}){6}', full_text)
    if iban_match:
        extracted['bank_account'] = iban_match.group(0).replace(" ", "")

    # 7. NIP
    # Szukamy słowa NIP i 10 cyfr
    nip_match = re.search(r'(?i)NIP:?\s*([\d-]+)', full_text)
    if nip_match:
        extracted['creditor_nip'] = nip_match.group(1).replace("-", "")

    # 8. KRS
    krs_match = re.search(r'(?i)KRS:?\s*(\d+)', full_text)
    if krs_match:
        extracted['creditor_krs'] = krs_match.group(1)

    # 9. NAZWY FIRM (WIERZYCIEL I DŁUŻNIK) - To jest najtrudniejsze bez AI
    # Prosta heurystyka: Bierzemy całe linie na podstawie ich kolejności lub słów kluczowych "Spółka"
    
    lines = full_text.split('\n')
    
    # Wierzyciel: Zazwyczaj linia nr 2 (indeks 1) w wezwaniach, lub ta co ma "Spółka" pierwsza
    for line in lines[:5]: # Sprawdzamy pierwsze 5 linii
        if "Spółka" in line or "S.A." in line or "Sp. z o.o." in line:
            extracted['creditor_name'] = line.strip()
            break
            
    # Adres wierzyciela: Często zawiera "ul." i jest blisko NIPu
    # W tym przykładzie szukamy linii zawierającej "Ul." lub "ul." w górnej części
    for line in lines[:6]:
        if ("ul." in line.lower() or "al." in line.lower()) and extracted['creditor_name'] not in line:
            # Czyścimy z KRS/NIP jeśli są w tej samej linii
            address_part = line.split("KRS")[0].strip().strip(",")
            extracted['creditor_address'] = address_part
            break

    # Dłużnik: Szukamy drugiej firmy (drugie wystąpienie "Spółka" lub podobne)
    found_first_company = False
    for line in lines:
        if "Spółka" in line or "S.A." in line or "Sp. z o.o." in line:
            if not found_first_company:
                found_first_company = True # To był wierzyciel
                continue
            else:
                # To jest dłużnik (druga firma w tekście)
                extracted['debtor_name'] = line.strip()
                # Zakładamy, że linia pod dłużnikiem to jego adres
                try:
                    next_line_index = lines.index(line) + 1
                    if next_line_index < len(lines):
                        extracted['debtor_address'] = lines[next_line_index].strip()
                except:
                    pass
                break

    # Bank Name - szukamy w ostatnich liniach słowa "Bank"
    for line in lines[-5:]:
        if "BANK" in line.upper():
            extracted['bank_name'] = line.strip()

    return extracted
