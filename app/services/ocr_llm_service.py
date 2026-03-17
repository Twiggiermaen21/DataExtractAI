import os
import requests
from app.utils.ocr_utils import check_connection, get_mime_type, image_to_base64, extract_text_from_docx, extract_text_from_pdf, extract_text_from_pdf_pages, extract_fields_from_template
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
        """Wysyła plik do API i zwraca wynik. Dla PDF-ów przetwarza każdą stronę osobno."""
        print("Wywołano funkcję: predict")
        
        ext = os.path.splitext(file_path)[1].lower()
        
        # ── PDF: przetwarzaj każdą stronę osobno ──
        if ext == '.pdf':
            return self._predict_pdf(file_path)
        
        # ── DOCX / DOC ──
        if ext in ['.docx', '.doc']:
            text_content = extract_text_from_docx(file_path)
            if text_content and len(text_content) >= 50:
                return [self._predict_text(text_content, file_path)]
        
        # ── Obrazy i inne pliki ──
        return [self._predict_image(file_path)]
    
    def _predict_pdf(self, file_path):
        """Przetwarza PDF — każdą stronę osobno. Zwraca listę OCRResult."""
        print("Wywołano funkcję: _predict_pdf")
        import fitz
        
        # Wyciągnij tekst z każdej strony osobno
        page_texts = extract_text_from_pdf_pages(file_path)
        num_pages = len(page_texts)
        print(f"[OCR_LLM] PDF ma {num_pages} stron(y)")
        
        all_results = []
        
        for page_num in range(num_pages):
            page_text = page_texts[page_num]
            print(f"\n[OCR_LLM] === Przetwarzanie strony {page_num + 1}/{num_pages} ===")
            
            if page_text and len(page_text) >= 50:
                # Strona z tekstem — wyślij tekst do LLM
                result = self._predict_text(
                    page_text, file_path,
                    page_info=f"strona {page_num + 1}/{num_pages}"
                )
                all_results.append(result)
            else:
                # Strona bez tekstu (skan) — konwertuj na obraz
                try:
                    doc = fitz.open(file_path)
                    page = doc[page_num]
                    pix = page.get_pixmap(dpi=150)
                    img_path = f"{file_path}_page{page_num + 1}.png"
                    pix.save(img_path)
                    doc.close()
                    
                    result = self._predict_image(img_path, source_path=file_path)
                    all_results.append(result)
                    
                    # Usuń tymczasowy obraz
                    try:
                        os.remove(img_path)
                    except:
                        pass
                except Exception as e:
                    print(f"[OCR_LLM] Błąd strony {page_num + 1}: {e}")
        
        if not all_results:
            raise Exception("Nie udało się przetworzyć żadnej strony PDF.")
        
        return all_results
    
    def _predict_text(self, text_content, file_path, page_info=None):
        """Wysyła tekst dokumentu do LLM i zwraca OCRResult."""
        label = f" ({page_info})" if page_info else ""
        print(f"[OCR_LLM] Przetwarzanie tekstu{label}, długość: {len(text_content)} znaków")
        
        if len(text_content) > 3000:
            print(f"[OCR_LLM] Tekst za długi ({len(text_content)} znaków), przycinanie do 3000")
            text_content = text_content[:3000]
        
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
        
        return self._send_to_llm(payload, file_path)
    
    def _predict_image(self, image_path, source_path=None):
        """Wysyła obraz do LLM i zwraca OCRResult."""
        print(f"[OCR_LLM] Przetwarzanie obrazu: {image_path}")
        
        image_base64 = image_to_base64(image_path)
        mime_type = get_mime_type(image_path)
        
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
        
        return self._send_to_llm(payload, source_path or image_path)
    
    def _send_to_llm(self, payload, result_path):
        """Wysyła payload do API LLM i zwraca OCRResult."""
        # DEBUG: Wyświetl dane wysyłane do LLM
        print("\n" + "="*80)
        print("[OCR_LLM] WYSYŁANIE ZAPYTANIA DO LLM")
        print("="*80)
        print(f"[OCR_LLM] Model: {self.model}")
        print(f"[OCR_LLM] API URL: {self.api_url}")
        print(f"[OCR_LLM] System prompt: {payload['messages'][0]['content']}")
        user_msg = payload['messages'][1]['content']
        if isinstance(user_msg, list):
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
            return OCRResult(output_text, result_path)
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

WAŻNE: Dla pól kończących się na "_procent" (np. pewnosc_ocr_procent), podaj szacunkową pewność odczytu jako tekst z procentem (np. "95%").
Dla pola "komentarz_ocr", podaj krótki komentarz (max 10 słów) o tym, jak dobrze udało się odczytać dane (np. "Wszystkie dane czytelne" lub "Brak NIP nabywcy").
Jeśli wartości nie ma, użyj null."""
        else:
            return f"""{action} i wyodrębnij wszystkie kluczowe dane z dokumentu. 
Zwróć TYLKO ustrukturyzowany obiekt JSON (bez znaczników markdown)."""
