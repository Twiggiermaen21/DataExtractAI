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


def _call_llm(prompt: str, system_prompt: str = None) -> str:
    """Wysyła zapytanie do llama-server i zwraca odpowiedź."""
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})
    
    response = requests.post(
        f"{LLAMA_SERVER_URL}/v1/chat/completions",
        json={
            "messages": messages,
            "max_tokens": 2000,
            "temperature": 0.1
        },
        timeout=120
    )
    
    if response.status_code != 200:
        raise Exception(f'Błąd serwera LLM: {response.status_code}')
    
    result = response.json()
    return result['choices'][0]['message']['content'].strip()


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


def extract_invoice_data(ocr_json_path: str, custom_attributes: str = '') -> dict:
    """
    Ekstrahuje dane z dokumentu na podstawie wyników OCR.
    """
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
        
        prompt = f"""Wyodrębnij następujące dane z tego dokumentu i zwróć TYLKO jako JSON:
{attributes_list}

Tekst dokumentu:
{full_text}"""
        
        print("🤖 Wysyłanie zapytania do llama-server...")
        
        generated_text = _call_llm(
            prompt,
            "Jesteś asystentem do ekstrakcji danych z dokumentów. Zwracaj TYLKO JSON."
        )
        
        extracted_data = _parse_json_response(generated_text)
        
        print("✅ Ekstrakcja zakończona.")
        
        return {
            'success': True,
            'source_file': os.path.basename(ocr_json_path),
            'extracted_data': extracted_data
        }
        
    except requests.exceptions.ConnectionError:
        return {'error': 'Nie można połączyć się z llama-server. Upewnij się że serwer działa na http://localhost:8080'}
    except requests.exceptions.Timeout:
        return {'error': 'Przekroczono czas oczekiwania na odpowiedź od llama-server'}
    except Exception as e:
        print(f"❌ Błąd ekstrakcji: {e}")
        return {'error': str(e)}


def extract_template_fields(json_paths: list, field_names: list) -> dict:
    """
    Ekstrahuje wartości pól szablonu z wielu plików JSON OCR.
    
    Args:
        json_paths: Lista ścieżek do plików JSON z wynikami OCR
        field_names: Lista nazw pól do wyodrębnienia (z input[name])
        
    Returns:
        Słownik z wyekstrahowanymi wartościami pól
    """
    try:
        # Zbierz tekst ze wszystkich plików
        all_texts = []
        for path in json_paths:
            text = _get_text_from_ocr_json(path)
            filename = os.path.basename(path)
            all_texts.append(f"=== Dokument: {filename} ===\n{text}")
        
        combined_text = '\n\n'.join(all_texts)
        
        # Przygotuj listę pól do ekstrakcji
        fields_list = '\n'.join(f'- {field}' for field in field_names)
        
        prompt = f"""Przeanalizuj poniższe dokumenty i wyodrębnij wartości dla następujących pól.
Zwróć TYLKO JSON gdzie klucze to nazwy pól, a wartości to wyodrębnione dane.
Jeśli nie możesz znaleźć wartości dla pola, ustaw wartość na pusty string "".

Pola do wyodrębnienia:
{fields_list}

Dokumenty:
{combined_text}"""
        
        print(f"🤖 Przetwarzanie {len(json_paths)} plików przez LLM...")
        
        generated_text = _call_llm(
            prompt,
            "Jesteś asystentem do ekstrakcji danych z dokumentów. Dopasuj dane z dokumentów do podanych pól. Zwracaj TYLKO JSON."
        )
        
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
