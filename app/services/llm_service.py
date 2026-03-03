"""
Serwis LLM do ekstrakcji danych z wyników OCR.
Łączy się z zewnętrznym serwerem llama-server przez API HTTP.
"""

import os
import json
import requests

# Adres serwera llama-server
LLAMA_SERVER_URL = "http://localhost:8080"


def _get_text_from_ocr_json(json_path: str) -> str:
    """Wyciąga tekst z pliku JSON OCR."""
    with open(json_path, 'r', encoding='utf-8') as f:
        ocr_data = json.load(f)
    
    text_blocks = []
    for block in ocr_data.get('parsing_res_list', []):
        content = block.get('block_content', '').strip()
        if content and block.get('block_label') not in ['image']:
            text_blocks.append(content)
    
    return '\n'.join(text_blocks)


def _call_llm(prompt: str, system_prompt: str = None, model: str = None) -> str:
    """Wysyła zapytanie do llama-server i zwraca odpowiedź."""
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})
    
    # === LOGOWANIE PROMPTÓW (Skrócone) ===
    print(f"📤 WYSYŁANIE DO LLM...")
    
    response = requests.post(
        f"{LLAMA_SERVER_URL}/v1/chat/completions",
        json={
            "model": model or os.environ.get("LLM_MODEL", "default"),
            "messages": messages,
            "max_tokens": 8000,
            "temperature": 0.1
        },
        timeout=120
    )
    
    if response.status_code != 200:
        raise Exception(f'Błąd serwera LLM: {response.status_code}')
    
    result = response.json()
    llm_response = result['choices'][0]['message']['content'].strip()
    
    # === LOGOWANIE ODPOWIEDZI (Skrócone) ===
    print("📥 POBRANO ODPOWIEDŹ LLM")
    
    return llm_response



def _parse_json_response(text: str) -> dict:
    """Parsuje odpowiedź JSON z LLM, usuwając markdown code blocks."""
    if text.startswith('```'):
        lines = text.split('\n')
        if lines[0].startswith('```'):
            lines = lines[1:]
        if lines and lines[-1].strip() == '```':
            lines = lines[:-1]
        text = '\n'.join(lines)
    
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {'raw_response': text}


def extract_invoice_data(ocr_json_path: str, custom_attributes: str = '', model: str = None) -> dict:
    """
    Ekstrahuje dane z dokumentu na podstawie wyników OCR.
    Wynik zapisywany jest automatycznie do output/extract_data/.
    """
    
    # System role - jasna rola dla LLM
    SYSTEM_ROLE = """Jesteś specjalistycznym asystentem do ekstrakcji danych z dokumentów.

TWOJA ROLA:
- Analizujesz tekst dokumentów (faktury, paragony, umowy, itp.)
- Wyodrębniasz TYLKO konkretne dane określone przez użytkownika
- Zwracasz dane WYŁĄCZNIE w formacie JSON

ZASADY:
1. Odpowiadaj TYLKO kodem JSON - bez żadnych komentarzy, wyjaśnień czy tekstu
2. Jeśli nie możesz znaleźć danej wartości, wstaw null lub pusty string ""
3. Zachowaj oryginalne formatowanie liczb i dat z dokumentu
4. Dla list (np. pozycje faktury) użyj tablicy JSON []
5. Używaj polskich nazw kluczy jeśli tak podano w atrybutach"""

    try:
        full_text = _get_text_from_ocr_json(ocr_json_path)
        
        if custom_attributes:
            attrs = [a.strip() for a in custom_attributes.replace('\n', ',').split(',') if a.strip()]
            attributes_list = '\n'.join(f'- {attr}' for attr in attrs)
        else:
            attributes_list = """- numer_faktury
- data_wystawienia
- data_platnosci
- sprzedawca (nazwa, nip, adres)
- nabywca (nazwa, nip, adres)
- pozycje (lista z: nazwa, ilosc, cena_netto, wartosc_netto, vat_procent, wartosc_brutto)
- suma_netto
- suma_vat
- suma_brutto
- sposob_platnosci
- numer_konta"""
        
        prompt = f"""Wyodrębnij następujące dane z dokumentu i zwróć jako JSON:

DANE DO WYODRĘBNIENIA:
{attributes_list}

TEKST DOKUMENTU:
{full_text}

Zwróć TYLKO JSON:"""
        
        print("🤖 Wysyłanie zapytania do llama-server...")
        
        generated_text = _call_llm(prompt, SYSTEM_ROLE, model=model)
        
        extracted_data = _parse_json_response(generated_text)
        
        # --- ZAPIS DO PLIKU JSON ---
        source_filename = os.path.basename(ocr_json_path)
        source_name = os.path.splitext(source_filename)[0]
        
        # Folder output/extract_data
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        extract_dir = os.path.join(project_root, "output", "extract_data")
        os.makedirs(extract_dir, exist_ok=True)
        
        # Nazwa pliku: extracted_[oryginalna_nazwa].json
        output_filename = f"extracted_{source_name}.json"
        output_path = os.path.join(extract_dir, output_filename)
        
        # Zapisz wyekstrahowane dane
        output_data = {
            'source_file': source_filename,
            'extracted_data': extracted_data
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
        
        print(f"✅ Ekstrakcja zakończona. Zapisano: {output_path}")
        
        return {
            'success': True,
            'source_file': source_filename,
            'output_file': output_filename,
            'output_path': output_path,
            'extracted_data': extracted_data
        }
        
    except requests.exceptions.ConnectionError:
        return {'error': 'Nie można połączyć się z llama-server. Upewnij się że serwer działa na http://localhost:8080'}
    except requests.exceptions.Timeout:
        return {'error': 'Przekroczono czas oczekiwania na odpowiedź od llama-server'}
    except Exception as e:
        print(f"❌ Błąd ekstrakcji: {e}")
        return {'error': str(e)}


def extract_template_fields(json_paths: list, field_names: list, model: str = None) -> dict:
    """
    Ekstrahuje wartości pól szablonu z wielu plików JSON OCR.
    
    Args:
        json_paths: Lista ścieżek do plików JSON z wynikami OCR
        field_names: Lista nazw pól do wyodrębnienia (z input[name])
        
    Returns:
        Słownik z wyekstrahowanymi wartościami pól
    """
    
    # System role - precyzyjny dla Llama 3.2
    SYSTEM_ROLE = """Jesteś precyzyjnym systemem ekstrakcji danych z dokumentów.
Twoim zadaniem jest przeanalizowanie dostarczonej treści i wygenerowanie poprawnego obiektu JSON.

ZASADY:
1. Odpowiadaj WYŁĄCZNIE kodem JSON - bez żadnych komentarzy, wyjaśnień czy tekstu przed/po
2. Ignoruj numery stron, stopki i nagłówki dokumentów
3. Jeśli dane różnią się między dokumentami, wybierz te z najnowszą datą (np. "Stan na dzień...")
4. Jeśli nie możesz znaleźć wartości dla pola, wstaw pusty string ""
5. Zachowaj oryginalne formatowanie dat i liczb
6. Dla adresów łącz wszystkie elementy w jeden string (ulica, numer, kod, miasto)
7. Używaj dokładnie tych samych nazw kluczy jakie podano w schemacie
8. ZACHOWAJ POLSKIE ZNAKI - nie usuwaj ani nie zamieniaj: ą, ę, ś, ć, ź, ż, ó, ł, ń, Ą, Ę, Ś, Ć, Ź, Ż, Ó, Ł, Ń
9. Odpowiadaj po polsku - wszystkie wartości tekstowe mają być w języku polskim"""

    try:
        # Zbierz tekst ze wszystkich plików
        all_texts = []
        for path in json_paths:
            text = _get_text_from_ocr_json(path)
            filename = os.path.basename(path)
            all_texts.append(f"--- DOKUMENT: {filename} ---\n{text}")
        
        combined_text = '\n\n'.join(all_texts)
        
        # Przygotuj schemat JSON
        schema_fields = ',\n  '.join(f'"{field}": "string"' for field in field_names)
        
        prompt = f"""Na podstawie poniższych dokumentów wypełnij schemat JSON.
Wybierz najbardziej aktualne i kompletne dane.

WYMAGANY FORMAT ODPOWIEDZI (wypełnij wartości):
{{
  {schema_fields}
}}

TREŚĆ DOKUMENTÓW:
{combined_text}

Zwróć TYLKO wypełniony JSON:"""
        
        print(f"🤖 Przetwarzanie {len(json_paths)} plików przez LLM...")
        
        generated_text = _call_llm(prompt, SYSTEM_ROLE, model=model)
        
        extracted_data = _parse_json_response(generated_text)
        
        print("✅ Ekstrakcja szablonu zakończona.")
        
        return {
            'success': True,
            'source_files': [os.path.basename(p) for p in json_paths],
            'fields': extracted_data
        }
        
    except requests.exceptions.ConnectionError:
        return {'error': 'Nie można połączyć się z llama-server. Upewnij się że serwer działa na http://localhost:8080'}
    except requests.exceptions.Timeout:
        return {'error': 'Przekroczono czas oczekiwania na odpowiedź od llama-server'}
    except Exception as e:
        print(f"❌ Błąd ekstrakcji szablonu: {e}")
        return {'error': str(e)}
