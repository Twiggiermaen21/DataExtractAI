import os
import requests
from app.utils.ocr_utils import check_connection, get_mime_type, image_to_base64, extract_text_from_docx, extract_text_from_pdf, extract_fields_from_template
from app.utils.ocr_result import OCRResult

class OCRService:
    
    def __init__(self, api_url=None, model=None):
        print("Wywołano funkcję: __init__")
        self.api_url = api_url or os.environ.get("LLM_API_URL")
        self.model = model or os.environ.get("LLM_MODEL")
        self.timeout = 600
        self.fields = []  # Pola pobrane z szablonu HTML
        
        pass  # usuniety print
        pass  # usuniety print
        check_connection(self.api_url)
    
    def load_model(self):
        print("Wywołano funkcję: load_model")
        pass
    
    def unload_model(self):
        print("Wywołano funkcję: unload_model")
        pass  # usuniety print
    
    def set_template(self, template_path):
        """Pobiera pola z szablonu HTML (atrybuty name z inputów)."""
        print("Wywołano funkcję: set_template")
        self.fields = extract_fields_from_template(template_path)
    
    def predict(self, file_path):
        """Wysyła plik do API i zwraca wynik."""
        print("Wywołano funkcję: predict")
        pass  # usuniety print
        
        ext = os.path.splitext(file_path)[1].lower()
        
        # Dla plików tekstowych (DOCX, PDF) - wyciągnij tekst
        text_content = None
        is_scanned_pdf = False
        
        if ext in ['.docx', '.doc']:
            pass  # usuniety print
            text_content = extract_text_from_docx(file_path)
        elif ext == '.pdf':
            pass  # usuniety print
            text_content = extract_text_from_pdf(file_path)
            if not text_content or len(text_content) < 50:
                pass  # usuniety print
                is_scanned_pdf = True
                # Konwertuj pierwszą stronę PDF na obraz
                try:
                    import fitz
                    doc = fitz.open(file_path)
                    page = doc[0]
                    pix = page.get_pixmap(dpi=150)
                    img_path = file_path + ".png"
                    pix.save(img_path)
                    doc.close()
                    file_path = img_path  # Użyj obrazu zamiast PDF
                    ext = '.png'
                except Exception as e:
                    raise Exception(f"Nie można skonwertować PDF na obraz: {e}")
                text_content = None  # Wymuś ścieżkę obrazu
        
        if text_content and len(text_content) >= 50:
            # Ogranicz tekst żeby nie przekroczyć kontekstu LLM 
            if len(text_content) > 3000:
                pass  # usuniety print
                raise Exception("Dokument jest zbyt długi do przetworzenia przez LLM.")
            
            # Dla dokumentów tekstowych
            payload = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": "Jesteś asystentem. Wyodrębniasz dane z dokumentów i zwracasz je jako JSON."},
                    {
                        "role": "user",
                        "content": f"Przeanalizuj poniższy tekst dokumentu i wyodrębnij dane.\n\n--- TEKST DOKUMENTU ---\n{text_content}\n--- KONIEC ---\n\n{self._build_prompt(is_text=True)}"
                    }
                ],
                "max_tokens": int(os.environ.get("LLM_MAX_TOKENS", 8000)),
                "temperature": 0.1
            }
        else:
            # Dla obrazów - wyślij jako base64
            image_base64 = image_to_base64(file_path)
            mime_type = get_mime_type(file_path)
            
            payload = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": "Jesteś asystentem OCR. Wyodrębniasz dane z dokumentów i zwracasz je jako JSON."},
                    {
                        "role": "user",
                        "content": [
                            {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{image_base64}"}},
                            {"type": "text", "text": self._build_prompt(is_text=False)}
                        ]
                    }
                ],
                "max_tokens": int(os.environ.get("LLM_MAX_TOKENS", 8000)),
                "temperature": 0.1
            }
        
        # DEBUG: Wyświetl dane wysyłane do LLM
        print("\n" + "="*80)
        print("[OCR_LLM] WYSYŁANIE ZAPYTANIA DO LLM")
        print("="*80)
        print(f"[OCR_LLM] Model: {self.model}")
        print(f"[OCR_LLM] API URL: {self.api_url}")
        print(f"[OCR_LLM] System prompt: {payload['messages'][0]['content']}")
        user_msg = payload['messages'][1]['content']
        if isinstance(user_msg, list):
            # Wiadomość z obrazem - wyświetl tylko tekst
            for part in user_msg:
                if part.get('type') == 'text':
                    print(f"[OCR_LLM] User prompt (tekst): {part['text']}")
                elif part.get('type') == 'image_url':
                    print(f"[OCR_LLM] User prompt zawiera obraz base64 (długość: {len(part['image_url']['url'])} znaków)")
        else:
            print(f"[OCR_LLM] User prompt: {user_msg}")
        print(f"[OCR_LLM] Max tokens: {payload.get('max_tokens')}")
        print(f"[OCR_LLM] Temperature: {payload.get('temperature')}")
        print(f"[OCR_LLM] Pola do ekstrakcji: {self.fields}")
        print("="*80 + "\n")
        
        response = requests.post(self.api_url, json=payload, headers={"Content-Type": "application/json"}, timeout=self.timeout)
        
        if response.status_code == 200:
            result = response.json()
            output_text = result["choices"][0]["message"]["content"]
            print(f"[OCR_LLM] ODPOWIEDŹ LLM (pierwsze 500 znaków): {output_text[:500]}")
            return [OCRResult(output_text, file_path)]
        else:
            raise Exception(f"API błąd {response.status_code}: {response.text}")
    
    def _build_prompt(self, is_text=False):
        """Buduje prompt z pól szablonu HTML lub używa domyślnych."""
        print("Wywołano funkcję: _build_prompt")
        action = "Przeanalizuj tekst" if is_text else "Przeanalizuj obraz"
        
        if self.fields:
            fields_list = "\n".join([f'{i+1}. "{f}": {f.replace("_", " ")}' for i, f in enumerate(self.fields)])
            return f"""{action} i wyodrębnij dane. Zwróć TYLKO obiekt JSON (bez markdown).

Pola do ekstrakcji:
{fields_list}

Jeśli wartości nie ma, użyj null."""
        else:
            return f"""{action} i wyodrębnij wszystkie kluczowe dane z dokumentu. 
Zwróć TYLKO ustrukturyzowany obiekt JSON (bez znaczników markdown)."""
