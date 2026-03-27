import os
import glob
from app.utils.ocr_utils import get_mime_type, image_to_base64, extract_text_from_docx, extract_text_from_pdf_pages, extract_fields_from_template, extract_text_from_xml
from app.utils.ocr_result import OCRResult

import subprocess
import atexit
import time
import sys
from openai import OpenAI

# Usuwamy stare importy llama_cpp

# Pełna definicja dostępnych kolumn (id → typ JSON Schema)
ALL_COLUMNS = {
    "sprzedawca":              {"type": "string"},
    "data_wystawienia":        {"type": "string"},
    "wolumen_energii":         {"type": "string"},
    "kwota_netto":             {"type": "number"},
    "kwota_brutto":            {"type": "number"},
    "kwota_vat":               {"type": "number"},
    "sprzedaz_cena_netto":     {"type": "number"},
    "sprzedaz_cena_brutto":    {"type": "number"},
    "dystrybucja_cena_netto":  {"type": "number"},
    "dystrybucja_cena_brutto": {"type": "number"},
}

# Kolumna pewności jest zawsze wymagana
CONFIDENCE_COL = {"pewnosc_ocr_procent": {"type": "integer"}}

# Domyślne kolumny (gdy frontend nie poda wyboru)
DEFAULT_COLUMNS = ["sprzedawca", "data_wystawienia", "wolumen_energii",
                   "kwota_netto", "kwota_brutto", "kwota_vat"]


def build_response_schema(selected_columns=None):
    """Buduje RESPONSE_SCHEMA dynamicznie na podstawie zaznaczonych checkboxów."""
    columns = selected_columns if selected_columns else DEFAULT_COLUMNS
    properties = {}
    for col_id in columns:
        if col_id in ALL_COLUMNS:
            properties[col_id] = ALL_COLUMNS[col_id]
    # Pewność OCR jest zawsze dodawana
    properties.update(CONFIDENCE_COL)

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

    # ── PDF (strona po stronie) ─────────────────────────────────

    def _predict_pdf(self, file_path):
        import fitz
        from app.utils.ocr_utils import extract_text_from_pdf_pages

        page_texts = extract_text_from_pdf_pages(file_path)
        num_pages = len(page_texts)
        print(f"[OCR] PDF: {num_pages} stron(y)")

        # Łączymy tekst ze wszystkich stron
        combined_text = "\n\n".join([f"--- STRONA {i+1} ---\n{t}" for i, t in enumerate(page_texts) if t.strip()])
        
        # Jeśli mamy wystarczająco dużo tekstu (>100 znaków), wysyłamy wszystko naraz
        if len(combined_text.strip()) > 100:
            print(f"[OCR] Przetwarzanie całego PDF jako jeden dokument (tekst).")
            return [self._predict_text(combined_text, file_path)]

        # Jeśli PDF to skan (mało tekstu), przetwarzamy pierwszą stronę jako obraz
        # (W fakturach za energię pierwsza strona zazwyczaj zawiera podsumowanie)
        print(f"[OCR] PDF wygląda na skan. Przetwarzanie pierwszej strony jako obraz.")
        img_path = f"{file_path}_page1.png"
        try:
            doc = fitz.open(file_path)
            if len(doc) > 0:
                doc[0].get_pixmap(dpi=150).save(img_path)
            doc.close()
            return [self._predict_image(img_path, source_path=file_path)]
        except Exception as e:
            print(f"[OCR] Błąd przetwarzania obrazu PDF: {e}")
            # Fallback do tekstu (nawet jeśli krótki)
            return [self._predict_text(combined_text, file_path)]
        finally:
            if os.path.exists(img_path):
                os.remove(img_path)

    # ── tekst → LLM ────────────────────────────────────────────

    def _predict_text(self, text_content, file_path, page_info=None):
        max_chars = 15000  # Zwiększamy limit, aby pomieścić multi-page PDF
        if len(text_content) > max_chars:
            text_content = text_content[:max_chars]
        
        # Opcjonalnie: skróć środek jeśli za długie (ale tu bierzemy początek)

        print(f"[OCR] --- ODPOWIEDŹ Z PLIKU/STRONY ---")
        print(f"{text_content[:1000]}{'...' if len(text_content) > 1000 else ''}")
        print(f"[OCR] ---------------------------------")

        print(f"[OCR] Wysyłanie zapytania tekstowego do wbudowanego serwera llama.cpp...")
        llama_url = os.environ.get("LLAMA_SERVER_URL", "http://127.0.0.1:8080/v1")
        client = OpenAI(base_url=llama_url, api_key="local")
        
        system_prompt = "Jesteś asystentem OCR. Analizujesz faktury za energię elektryczną i wyodrębniasz precyzyjne dane finansowe do wniosków o ulgę. Zwracasz WYŁĄCZNIE kod JSON."
        user_msg = (
            f"Przeanalizuj poniższy tekst faktury za energię elektryczną i wyodrębnij konkretne informacje liczbowe i tekstowe.\n\n"
            f"Zwróć uwagę, że 'wolumen_energii' określa zazwyczaj ilość zużytej energii czynnej (wyrażoną w kWh lub MWh, np. '1234 kWh'). Zwróć go jako string wraz z jednostką.\n\n"
            f"--- TEKST DOKUMENTU ---\n{text_content}\n--- KONIEC ---\n\n"
            f"{self._build_prompt(is_text=True)}"
        )
        
        print(f"[OCR] --- PROMPT DO LLM ---")
        print(user_msg)
        print(f"[OCR] ----------------------")
        
        response = client.chat.completions.create(
            model="local-model",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_msg}
            ],
            response_format=self.response_schema,
            temperature=0.99,
            max_tokens=int(os.environ.get("LLM_MAX_TOKENS", 1000)),
            extra_body={
        "top_k": 20,
        "chat_template_kwargs": {"enable_thinking": False},
    }, 
        )
        
        output_text = response.choices[0].message.content
        print(f"[OCR] --- ODPOWIEDŹ LLM ---")
        print(output_text)
        print(f"[OCR] ---------------------")
        return OCRResult(output_text, file_path, is_vision=False)

    # ── obraz → LLM ────────────────────────────────────────────

    def _predict_image(self, image_path, source_path=None):
        print(f"[OCR] Wysyłanie zapytania graficznego do wbudowanego serwera llama.cpp...")
        llama_url = os.environ.get("LLAMA_SERVER_URL", "http://127.0.0.1:8080/v1")
        client = OpenAI(base_url=llama_url, api_key="local")
        
        print(f"[OCR] Przetwarzanie obrazu: {image_path}")
        image_base64 = image_to_base64(image_path)
        mime_type = get_mime_type(image_path)
        user_msg = self._build_prompt(is_text=False)

        print(f"[OCR] --- PROMPT DO LLM (WIZJA) ---")
        print(user_msg)
        print(f"[OCR] -------------------------------")

        response = client.chat.completions.create(
            model="local-model",
            messages=[
                {"role": "system", "content": "Jesteś asystentem OCR. Czytasz faktury za energię elektryczną do celów podatkowych i zwracasz czysty JSON. Ignorujesz elementy nieregulowane. Pamiętaj, że wolumen energii (energii czynnej) ma zazwyczaj jednostkę kWh lub MWh."},
                {"role": "user", "content": [
                    {"type": "text", "text": user_msg},
                    {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{image_base64}"}}
                ]}
            ],
            response_format=self.response_schema,
            temperature=0.99,
            max_tokens=int(os.environ.get("LLM_MAX_TOKENS", 1000))
        )
        
        output_text = response.choices[0].message.content
        print(f"[OCR] --- ODPOWIEDŹ LLM (WIZJA) ---")
        print(output_text)
        print(f"[OCR] -----------------------------")
        return OCRResult(output_text, source_path or image_path, is_vision=True)

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
                "WAŻNE: Dla pól  pewnosc_ocr_procent podaj szacunkową pewność odczytu jako tekst z procentem.\n"
                "Jeśli wartości nie ma, użyj null."
            )
        return (
            f"{action} i wyodrębnij wszystkie kluczowe dane z dokumentu. "
            "Zwróć TYLKO ustrukturyzowany obiekt JSON (bez znaczników markdown)."
        )
