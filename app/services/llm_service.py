"""
Serwis LLM do ekstrakcji danych z wyników OCR.
Łączy się z zewnętrznym serwerem LLM przez API HTTP.
"""

import os
import json
import logging
from openai import OpenAI

log = logging.getLogger(__name__)


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


def call_llm(prompt: str, system_prompt: str = None, model: str = None) -> str:
    """Generuje odpowiedź przy użyciu lokalnego serwera llama.cpp na porcie 8080."""
    client = OpenAI(base_url="http://localhost:8080/v1", api_key="local")
    
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    log.debug("LLM request using OpenAI client to llama-server.exe")

    response = client.chat.completions.create(
        model="local-model",
        messages=messages,
        temperature=0.99,
        max_tokens=int(os.environ.get("LLM_MAX_TOKENS", 1000)),
    )

    llm_response = response.choices[0].message.content.strip()
    log.info("LLM odpowiedź (%d zn.): %.200s", len(llm_response), llm_response)
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
    """Ekstrahuje dane z dokumentu na podstawie wyników OCR."""
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

        generated_text = call_llm(prompt, SYSTEM_ROLE, model=model)
        extracted_data = _parse_json_response(generated_text)

        # Zapis do output/extract_data/
        source_filename = os.path.basename(ocr_json_path)
        source_name = os.path.splitext(source_filename)[0]

        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        extract_dir = os.path.join(project_root, "output", "extract_data")
        os.makedirs(extract_dir, exist_ok=True)

        output_filename = f"extracted_{source_name}.json"
        output_path = os.path.join(extract_dir, output_filename)

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump({'source_file': source_filename, 'extracted_data': extracted_data},
                      f, ensure_ascii=False, indent=2)

        return {
            'success': True,
            'source_file': source_filename,
            'output_file': output_filename,
            'output_path': output_path,
            'extracted_data': extracted_data,
        }

    except Exception as e:
        log.exception("extract_invoice_data error")
        return {'error': str(e)}


def extract_template_fields(json_paths: list, field_names: list, model: str = None) -> dict:
    """Ekstrahuje wartości pól szablonu z wielu plików JSON OCR."""
    SYSTEM_ROLE = """Jesteś precyzyjnym systemem ekstrakcji danych z dokumentów.
Twoim zadaniem jest przeanalizowanie dostarczonej treści i wygenerowanie poprawnego obiektu JSON.

ZASADY:
1. Odpowiadaj WYŁĄCZNIE kodem JSON - bez żadnych komentarzy, wyjaśnień czy tekstu przed/po
2. Ignoruj numery stron, stopki i nagłówki dokumentów
3. Jeśli dane różnią się między dokumentami, wybierz te z najnowszą datą
4. Jeśli nie możesz znaleźć wartości dla pola, wstaw pusty string ""
5. Zachowaj oryginalne formatowanie dat i liczb
6. Dla adresów łącz wszystkie elementy w jeden string
7. Używaj dokładnie tych samych nazw kluczy jakie podano w schemacie
8. ZACHOWAJ POLSKIE ZNAKI
9. Odpowiadaj po polsku"""

    try:
        all_texts = []
        for path in json_paths:
            text = _get_text_from_ocr_json(path)
            all_texts.append(f"--- DOKUMENT: {os.path.basename(path)} ---\n{text}")

        combined_text = '\n\n'.join(all_texts)
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

        generated_text = call_llm(prompt, SYSTEM_ROLE, model=model)
        extracted_data = _parse_json_response(generated_text)

        return {
            'success': True,
            'source_files': [os.path.basename(p) for p in json_paths],
            'fields': extracted_data,
        }

    except Exception as e:
        log.exception("extract_template_fields error")
        return {'error': str(e)}
