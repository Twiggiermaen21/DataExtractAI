import os
import glob
from app.utils.ocr_utils import get_mime_type, image_to_base64, extract_text_from_docx, extract_text_from_pdf_pages, extract_fields_from_template, extract_text_from_xml
from app.utils.ocr_result import OCRResult
from llm_config import ALL_COLUMNS,DEFAULT_COLUMNS,FIELD_INSTRUCTIONS,SYSTEM_PROMPT
import subprocess
import atexit
import time
import sys
from openai import OpenAI

# Usuwamy stare importy llama_cpp



def build_response_schema(selected_columns=None):
    """Buduje RESPONSE_SCHEMA — zawsze wyciąga WSZYSTKIE dostępne pola.
    Parametr selected_columns jest ignorowany przy ekstrakcji; filtrowanie
    do podglądu i Excela odbywa się po stronie frontendu / excel_export."""
    properties = dict(ALL_COLUMNS)

    return {
        "type": "json_schema",
        "json_schema": {
            "name": "ekstrakcja_danych_faktury_energia",
            "schema": {
                "type": "object",
                "properties": properties,
                "required": list(properties.keys()),
                "additionalProperties": False,
            },
            "strict": True,
        },
    }


# Usunięto lokalne uruchamianie serwera - teraz zarządza nim run.py globalnie

class OCRService:

    def __init__(self, api_url=None, model=None, selected_columns=None):
        self.fields = []
        self.selected_columns = selected_columns
        self.response_schema = build_response_schema(selected_columns)

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

        if ext == '.xml':
            text = extract_text_from_xml(file_path)
            if text:
                return [self._predict_text(text, file_path)]

        return [self._predict_image(file_path)]

    # ── PDF (wszystkie strony) ──────────────────────────────────

    def _predict_pdf(self, file_path):
        import fitz
        from app.utils.ocr_utils import extract_text_from_pdf_pages

        page_texts = extract_text_from_pdf_pages(file_path)
        num_pages = len(page_texts)
        print(f"[OCR] PDF: {num_pages} stron(y)")

        # Łączymy tekst ze wszystkich stron
        combined_text = "\n\n".join(
            [f"--- STRONA {i+1} ---\n{t}" for i, t in enumerate(page_texts) if t.strip()]
        )

        # Jeśli PDF ma wystarczająco dużo tekstu — wysyłamy jako tekst (wszystkie strony)
        if len(combined_text.strip()) > 100:
            print(f"[OCR] Przetwarzanie całego PDF jako tekst ({num_pages} stron).")
            return [self._predict_text(combined_text, file_path)]

        # PDF jest skanem — renderujemy WSZYSTKIE strony jako obrazy
        print(f"[OCR] PDF wygląda na skan. Renderowanie wszystkich {num_pages} stron jako obrazy.")
        img_paths = []
        try:
            doc = fitz.open(file_path)
            for i in range(len(doc)):
                img_path = f"{file_path}_page{i+1}.png"
                doc[i].get_pixmap(dpi=150).save(img_path)
                img_paths.append(img_path)
            doc.close()

            if not img_paths:
                return [self._predict_text(combined_text, file_path)]

            # Wysyłamy wszystkie strony w jednym wywołaniu LLM
            return [self._predict_images(img_paths, source_path=file_path)]
        except Exception as e:
            print(f"[OCR] Błąd renderowania stron PDF: {e}")
            return [self._predict_text(combined_text, file_path)]
        finally:
            for p in img_paths:
                if os.path.exists(p):
                    os.remove(p)

 

    # ── tekst → LLM ────────────────────────────────────────────

    def _predict_text(self, text_content, file_path, page_info=None):
        max_chars = int(os.environ.get("LLM_MAX_CHARS", 800000))
        if len(text_content) > max_chars:
            print(f"[OCR] Tekst za długi ({len(text_content)} znaków), przycinanie do {max_chars}.")
            text_content = text_content[:max_chars]

        log = __import__('logging').getLogger(__name__)
        log.info("[OCR] Tekst dokumentu (pierwsze 500 znaków): %s", text_content)

        llama_url = os.environ.get("LLAMA_SERVER_URL", "http://127.0.0.1:8080/v1")
        client = OpenAI(base_url=llama_url, api_key="local")

        user_msg = (
            "Przeanalizuj poniższy tekst faktury za energię elektryczną.\n\n"
            f"{FIELD_INSTRUCTIONS}\n\n"
            f"--- TEKST DOKUMENTU ---\n{text_content}\n--- KONIEC ---"
        )

        log.debug("[OCR] Prompt (tekst): %s", user_msg[:800])

        response = client.chat.completions.create(
            model="local-model",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": user_msg},
            ],
            response_format=self.response_schema,
            temperature=0.0,
            max_tokens=int(os.environ.get("LLM_MAX_TOKENS", 1000)),
            extra_body={
                "top_k": 1,
                "chat_template_kwargs": {"enable_thinking": False},
            },
        )

        output_text = response.choices[0].message.content
        log.info("[OCR] Odpowiedź LLM (tekst): %s", output_text)
        return OCRResult(output_text, file_path, is_vision=False)

    # ── obraz → LLM ────────────────────────────────────────────

    def _predict_image(self, image_path, source_path=None):
        log = __import__('logging').getLogger(__name__)
        log.info("[OCR] Przetwarzanie obrazu: %s", image_path)

        llama_url = os.environ.get("LLAMA_SERVER_URL", "http://127.0.0.1:8080/v1")
        client = OpenAI(base_url=llama_url, api_key="local")

        image_base64 = image_to_base64(image_path)
        mime_type = get_mime_type(image_path)

        user_msg = (
            "Przeanalizuj załączoną fakturę za energię elektryczną.\n\n"
            f"{FIELD_INSTRUCTIONS}"
        )

        log.debug("[OCR] Prompt (wizja): %s", user_msg[:800])

        response = client.chat.completions.create(
            model="local-model",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": [
                    {"type": "text",      "text": user_msg},
                    {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{image_base64}"}},
                ]},
            ],
            response_format=self.response_schema,
            temperature=0.0,
            max_tokens=int(os.environ.get("LLM_MAX_TOKENS", 1000)),
        )

        output_text = response.choices[0].message.content
        log.info("[OCR] Odpowiedź LLM (wizja): %s", output_text)
        return OCRResult(output_text, source_path or image_path, is_vision=True)

    # ── wiele obrazów (skany wielostronicowe) → LLM ────────────

    def _predict_images(self, image_paths, source_path=None):
        """Wysyła wiele obrazów stron w jednym wywołaniu LLM (dla skanowanych PDF)."""
        log = __import__('logging').getLogger(__name__)
        log.info("[OCR] Przetwarzanie %d stron jako obrazów: %s", len(image_paths), source_path)

        llama_url = os.environ.get("LLAMA_SERVER_URL", "http://127.0.0.1:8080/v1")
        client = OpenAI(base_url=llama_url, api_key="local")

        user_msg = (
            f"Przeanalizuj poniższy dokument składający się z {len(image_paths)} stron "
            f"(każdy obraz to jedna strona faktury za energię elektryczną).\n\n"
            f"{FIELD_INSTRUCTIONS}"
        )

        # Buduj content: tekst + wszystkie obrazy
        content = [{"type": "text", "text": user_msg}]
        for img_path in image_paths:
            image_base64 = image_to_base64(img_path)
            mime_type = get_mime_type(img_path)
            content.append({
                "type": "image_url",
                "image_url": {"url": f"data:{mime_type};base64,{image_base64}"}
            })

        response = client.chat.completions.create(
            model="local-model",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": content},
            ],
            response_format=self.response_schema,
            temperature=0.0,
            max_tokens=int(os.environ.get("LLM_MAX_TOKENS", 1000)),
        )

        output_text = response.choices[0].message.content
        log.info("[OCR] Odpowiedź LLM (multi-wizja): %s", output_text)
        return OCRResult(output_text, source_path or image_paths[0], is_vision=True)

    # ── wspólne elementy ────────────────────────────────────────

    def _build_prompt(self, is_text=False):
        action = "Przeanalizuj tekst" if is_text else "Przeanalizuj obraz"

        if self.fields:
            fields_list = "\n".join(
                f'{i+1}. "{f}": {f.replace("_", " ")}' for i, f in enumerate(self.fields)
            )
            return (
                f"{action} i wyodrębnij dane. Zwróć TYLKO obiekt JSON (bez markdown).\n\n"
                f"Pola do ekstrakcji:\n{fields_list}\n\n"
                "WAŻNE: Dla pól pewnosc_ocr_procent podaj szacunkową pewność odczytu jako liczbę 0-100.\n"
                "Jeśli wartości nie ma, użyj null."
            )
        return (
            f"{action} i wyodrębnij wszystkie kluczowe dane z dokumentu. "
            "Zwróć TYLKO ustrukturyzowany obiekt JSON (bez znaczników markdown)."
        )
