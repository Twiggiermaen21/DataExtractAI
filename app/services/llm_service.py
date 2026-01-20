"""
Serwis LLM do ekstrakcji danych z wyników OCR.
Łączy się z zewnętrznym serwerem llama-server przez API HTTP.
"""

import os
import json
import requests

# Adres serwera llama-server
LLAMA_SERVER_URL = "http://localhost:8080"


def extract_invoice_data(ocr_json_path: str, custom_attributes: str = '') -> dict:
    """
    Ekstrahuje dane z dokumentu na podstawie wyników OCR.
    
    Args:
        ocr_json_path: Ścieżka do pliku JSON z wynikami OCR
        custom_attributes: Opcjonalna lista atrybutów do wyodrębnienia
        
    Returns:
        Słownik z wyekstrahowanymi danymi
    """
    try:
        # Wczytaj dane OCR
        with open(ocr_json_path, 'r', encoding='utf-8') as f:
            ocr_data = json.load(f)
        
        # Zbierz tekst z bloków
        text_blocks = []
        for block in ocr_data.get('parsing_res_list', []):
            content = block.get('block_content', '').strip()
            if content and block.get('block_label') not in ['image']:
                text_blocks.append(content)
        
        full_text = '\n'.join(text_blocks)
        
        # Przygotuj listę atrybutów
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
        
        # Przygotuj prompt
        prompt = f"""Wyodrębnij następujące dane z tego dokumentu i zwróć TYLKO jako JSON (bez żadnego innego tekstu):
{attributes_list}

Tekst dokumentu:
{full_text}"""
        
        print("🤖 Wysyłanie zapytania do llama-server...")
        
        # Wyślij zapytanie do llama-server (OpenAI-compatible API)
        response = requests.post(
            f"{LLAMA_SERVER_URL}/v1/chat/completions",
            json={
                "messages": [
                    {"role": "system", "content": "Jesteś asystentem do ekstrakcji danych z dokumentów. Zwracaj TYLKO JSON, bez żadnego dodatkowego tekstu."},
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": 1500,
                "temperature": 0.1
            },
            timeout=120
        )
        
        if response.status_code != 200:
            return {'error': f'Błąd serwera LLM: {response.status_code} - {response.text}'}
        
        result = response.json()
        generated_text = result['choices'][0]['message']['content'].strip()
        
        # Wyczyść odpowiedź z markdown code blocks
        if generated_text.startswith('```'):
            lines = generated_text.split('\n')
            # Usuń pierwszą linię (```json) i ostatnią (```)
            if lines[0].startswith('```'):
                lines = lines[1:]
            if lines and lines[-1].strip() == '```':
                lines = lines[:-1]
            generated_text = '\n'.join(lines)
        
        # Próba parsowania JSON
        try:
            extracted_data = json.loads(generated_text)
        except json.JSONDecodeError:
            extracted_data = {'raw_response': generated_text}
        
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
