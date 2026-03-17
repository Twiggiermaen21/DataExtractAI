import os
import requests
from app.utils.ocr_utils import check_connection, get_mime_type, image_to_base64, extract_text_from_docx, extract_text_from_pdf_pages, extract_fields_from_template
from app.utils.ocr_result import OCRResult

# Schema JSON wysyłany do LLM (structured output)
RESPONSE_SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "ekstrakcja_danych_faktury",
        "schema": {
            "type": "object",
            "properties": {
                "nabywca":              {"type": "string"},
                "pewnosc_ocr_procent":  {"type": "integer"},
                "kwota_do_zaplaty":     {"type": "number"},
                "komentarz_ocr":       {"type": "string"},
                "sprzedawca":          {"type": "string"},
                "numer_faktury":       {"type": "string"},
            },
            "required": [
                "nabywca", "pewnosc_ocr_procent", "kwota_do_zaplaty",
                "komentarz_ocr", "sprzedawca", "numer_faktury"
            ],
            "additionalProperties": False,
        },
        "strict": True,
    },
}


class OCRService:

    def __init__(self, api_url=None, model=None):
        self.api_url = api_url or os.environ.get("LLM_API_URL")
        self.model = model or os.environ.get("LLM_MODEL")
        self.timeout = 600
        self.fields = []
        check_connection(self.api_url)

    # ── public API ──────────────────────────────────────────────

    def set_template(self, template_path):
        """Pobiera pola z szablonu HTML (atrybuty name z inputów)."""
        self.fields = extract_fields_from_template(template_path)

    def predict(self, file_path):
        """Wysyła plik do API i zwraca listę OCRResult (po jednym na stronę/dokument)."""
        ext = os.path.splitext(file_path)[1].lower()

        if ext == '.pdf':
            return self._predict_pdf(file_path)

        if ext in ('.docx', '.doc'):
            text = extract_text_from_docx(file_path)
            if text and len(text) >= 50:
                return [self._predict_text(text, file_path)]

        return [self._predict_image(file_path)]

    # ── PDF (strona po stronie) ─────────────────────────────────

    def _predict_pdf(self, file_path):
        import fitz

        page_texts = extract_text_from_pdf_pages(file_path)
        num_pages = len(page_texts)
        print(f"[OCR] PDF: {num_pages} stron(y)")

        results = []
        for idx, page_text in enumerate(page_texts):
            page_label = f"strona {idx + 1}/{num_pages}"
            print(f"[OCR] {page_label}")

            if page_text and len(page_text) >= 50:
                results.append(self._predict_text(page_text, file_path, page_info=page_label))
            else:
                img_path = f"{file_path}_page{idx + 1}.png"
                try:
                    doc = fitz.open(file_path)
                    doc[idx].get_pixmap(dpi=150).save(img_path)
                    doc.close()
                    results.append(self._predict_image(img_path, source_path=file_path))
                except Exception as e:
                    print(f"[OCR] Błąd {page_label}: {e}")
                finally:
                    try:
                        os.remove(img_path)
                    except OSError:
                        pass

        if not results:
            raise Exception("Nie udało się przetworzyć żadnej strony PDF.")
        return results

    # ── tekst → LLM ────────────────────────────────────────────

    def _predict_text(self, text_content, file_path, page_info=None):
        max_chars = 3000
        if len(text_content) > max_chars:
            text_content = text_content[:max_chars]

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "Jesteś asystentem. Wyodrębniasz dane z dokumentów i zwracasz je jako JSON."},
                {"role": "user",   "content": (
                    f"Przeanalizuj poniższy tekst dokumentu i wyodrębnij dane.\n\n"
                    f"--- TEKST DOKUMENTU ---\n{text_content}\n--- KONIEC ---\n\n"
                    f"{self._build_prompt(is_text=True)}"
                )},
            ],
            **self._common_params(),
        }
        return self._send_to_llm(payload, file_path)

    # ── obraz → LLM ────────────────────────────────────────────

    def _predict_image(self, image_path, source_path=None):
        image_base64 = image_to_base64(image_path)
        mime_type = get_mime_type(image_path)

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "Jesteś asystentem OCR. Wyodrębniasz dane z dokumentów i zwracasz je jako JSON."},
                {"role": "user",   "content": [
                    {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{image_base64}"}},
                    {"type": "text", "text": self._build_prompt(is_text=False)},
                ]},
            ],
            **self._common_params(),
        }
        return self._send_to_llm(payload, source_path or image_path)

    # ── wspólne elementy ────────────────────────────────────────

    def _common_params(self):
        return {
            "max_tokens": int(os.environ.get("LLM_MAX_TOKENS", 8000)),
            "temperature": 0.1,
            "response_format": RESPONSE_SCHEMA,
        }

    def _send_to_llm(self, payload, result_path):
        response = requests.post(
            self.api_url, json=payload,
            headers={"Content-Type": "application/json"},
            timeout=self.timeout,
        )
        if response.status_code == 200:
            output_text = response.json()["choices"][0]["message"]["content"]
            print(f"[OCR] Odpowiedź LLM (500 zn.): {output_text[:500]}")
            return OCRResult(output_text, result_path)
        raise Exception(f"API błąd {response.status_code}: {response.text}")

    def _build_prompt(self, is_text=False):
        action = "Przeanalizuj tekst" if is_text else "Przeanalizuj obraz"

        if self.fields:
            fields_list = "\n".join(
                f'{i+1}. "{f}": {f.replace("_", " ")}' for i, f in enumerate(self.fields)
            )
            return (
                f"{action} i wyodrębnij dane. Zwróć TYLKO obiekt JSON (bez markdown).\n\n"
                f"Pola do ekstrakcji:\n{fields_list}\n\n"
                "WAŻNE: Dla pól kończących się na \"_procent\" (np. pewnosc_ocr_procent), "
                "podaj szacunkową pewność odczytu jako tekst z procentem (np. \"95%\").\n"
                "Dla pola \"komentarz_ocr\", podaj krótki komentarz (max 10 słów) o tym, "
                "jak dobrze udało się odczytać dane.\n"
                "Jeśli wartości nie ma, użyj null."
            )
        return (
            f"{action} i wyodrębnij wszystkie kluczowe dane z dokumentu. "
            "Zwróć TYLKO ustrukturyzowany obiekt JSON (bez znaczników markdown)."
        )
