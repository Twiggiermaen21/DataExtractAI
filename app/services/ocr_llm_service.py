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
    "numer_faktury":            {"type": "string"},
    "sprzedawca":               {"type": "string"},
    "data_wystawienia":         {"type": "string"},
    "data_sprzedazy":           {"type": "string"},
    "wolumen_energii":          {"type": "number"},
    "kwota_netto":              {"type": "number"},
    "kwota_brutto":             {"type": "number"},
    "kwota_vat":                {"type": "number"},
    "sprzedaz_cena_netto":      {"type": "number"},
    "sprzedaz_cena_brutto":     {"type": "number"},
    "dystrybucja_cena_netto":   {"type": "number"},
    "dystrybucja_cena_brutto":  {"type": "number"},
    # Opłaty dodatkowe — typ string: LLM zwraca liczbę lub wiele wartości rozdzielonych "|"
    "oplata_abonamentowa":             {"type": "string"},
    "oplata_abonamentowa_brutto":      {"type": "string"},
    "oplata_sieciowa_stala":           {"type": "string"},
    "oplata_sieciowa_stala_brutto":    {"type": "string"},
    "oplata_sieciowa_zmienna":         {"type": "string"},
    "oplata_sieciowa_zmienna_brutto":  {"type": "string"},
    "oplata_jakosciowa":               {"type": "string"},
    "oplata_jakosciowa_brutto":        {"type": "string"},
    "oplata_oze":                      {"type": "string"},
    "oplata_oze_brutto":               {"type": "string"},
    "oplata_kogeneracyjna":            {"type": "string"},
    "oplata_kogeneracyjna_brutto":     {"type": "string"},
    "oplata_przejsciowa":              {"type": "string"},
    "oplata_przejsciowa_brutto":       {"type": "string"},
    "oplata_mocowa":                   {"type": "string"},
    "oplata_mocowa_brutto":            {"type": "string"},
    "naleznos_netto":           {"type": "number"},
    "naleznos_brutto":          {"type": "number"},
}

# Kolumna pewności jest zawsze wymagana
CONFIDENCE_COL = {"pewnosc_ocr_procent": {"type": "integer"}}

# Domyślne kolumny (gdy frontend nie poda wyboru)
DEFAULT_COLUMNS = ["sprzedawca", "data_wystawienia", "data_sprzedazy",
                   "wolumen_energii", "kwota_netto", "kwota_brutto", "kwota_vat"]


def build_response_schema(selected_columns=None):
    """Buduje RESPONSE_SCHEMA — zawsze wyciąga WSZYSTKIE dostępne pola.
    Parametr selected_columns jest ignorowany przy ekstrakcji; filtrowanie
    do podglądu i Excela odbywa się po stronie frontendu / excel_export."""
    properties = dict(ALL_COLUMNS)
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

    # ── Wspólny prompt systemowy ────────────────────────────────

    SYSTEM_PROMPT = (
        "Jesteś ekspertem OCR specjalizującym się w polskich fakturach za energię elektryczną "
        "(PGE, Tauron, Enea, Energa, E.ON i innych operatorów). "
        "Każdy operator stosuje inne nazewnictwo i układ tabel. "
        "Twoim zadaniem jest znalezienie konkretnych wartości niezależnie od układu dokumentu.\n\n"
        "ZASADY BEZWZGLĘDNE — MUSISZ ICH PRZESTRZEGAĆ:\n"
        "1. Przepisuj WYŁĄCZNIE wartości widoczne w dokumencie. "
        "NIE wolno Ci niczego obliczać, szacować, interpolować ani domyślać się.\n"
        "2. Jeśli danej LICZBOWEJ wartości NIE MA w dokumencie — zwróć null. "
        "Jeśli danej TEKSTOWEJ (string) wartości NIE MA w dokumencie — zwróć pusty string ''. "
        "Nigdy nie wstawiaj własnych szacunków ani 0 zamiast pustego stringa.\n"
        "3. NIE wolno Ci 'poprawiać' ani 'uzupełniać' danych na podstawie wiedzy o typowych fakturach.\n"
        "4. Wartości numeryczne przepisuj dokładnie tak jak stoją w dokumencie, "
        "zamieniając tylko separator dziesiętny na kropkę i usuwając symbole walut/jednostek.\n"
        "5. Zwróć WYŁĄCZNIE czysty obiekt JSON — bez żadnego komentarza, wyjaśnienia ani markdown."
    )

    FIELD_INSTRUCTIONS = (
        "KRYTYCZNA ZASADA — TABELE Z OPŁATAMI:\n"
        "Faktury za energię mają tabele z kolumnami: Lp. | Nazwa | Ilość | Cena jed. netto | Wartość netto | Wartość brutto.\n"
        "- ZAWSZE bierz wartość z kolumny 'Wartość netto' (nie z 'Cena jed.', 'Stawka', 'zł/kWh').\n"
        "- Kolumna 'Cena jed. netto' to cena za 1 kWh/kW/mc — to NIE jest kwota do zapłaty.\n"
        "- Kolumna 'Wartość netto' to kwota do zapłaty — tej szukasz.\n"
        "- Jeśli opłata ma kilka wierszy (strefy, dni, taryfy) — zwróć WSZYSTKIE wartości oddzielone '|', np. '0.00|115.21'.\n"
        "- WAŻNE: Zwracaj WSZYSTKIE wiersze tej samej opłaty — nawet jeśli wartość wynosi 0.00. "
        "Wiersze z zerem to osobne pozycje rozliczeniowe (np. inna taryfa lub mnożnik), nie brak opłaty.\n\n"
        "Gdzie szukać poszczególnych pól (jeśli NIE ZNAJDZIESZ — zwróć null dla liczb, '' dla stringów):\n"
        '1. "numer_faktury": Numer faktury. Frazy: "Nr faktury", "Numer faktury", "Faktura VAT nr", "FV/", "FA/". Przepisz dokładnie z dokumentu.\n'
        '2. "sprzedawca": Nazwa firmy wystawiającej fakturę widoczna w nagłówku lub stopce (np. PGE Obrót S.A., Tauron Sprzedaż). Ignoruj dane Nabywcy/Odbiorcy.\n'
        '3. "data_wystawienia": Frazy: "Data wystawienia", "Wystawiono dnia". Format YYYY-MM-DD.\n'
        '4. "data_sprzedazy": Frazy: "Data sprzedaży", "Miesiąc sprzedaży", lub końcowa data z "Okres rozliczeniowy od ... do ...". Format YYYY-MM-DD.\n'
        '5. "wolumen_energii": Całkowite zużycie energii czynnej. Frazy: "Ilość", "Wolumen", suma tabeli odczytów licznika. Tylko liczba bez jednostki.\n'
        '6. "naleznos_netto": Całkowita należność netto przed VAT. Nie mylić z kwotą bieżącej faktury.\n'
        '7. "naleznos_brutto": Kwota ostateczna do zapłaty przez klienta. Frazy: "Do zapłaty", "Razem do zapłaty", "Należność ogółem", "Kwota do zapłaty".\n'
        '8. "kwota_netto": Suma netto z tabeli stawek VAT lub głównego podsumowania za bieżący okres rozliczeniowy.\n'
        '9. "kwota_brutto": Suma brutto z tabeli stawek VAT lub głównego podsumowania za bieżący okres.\n'
        '10. "kwota_vat": Podatek VAT za bieżący okres. Frazy: "Kwota VAT", "Podatek VAT", "Suma VAT".\n'
        '11. "sprzedaz_cena_netto": Suma netto sekcji SPRZEDAŻY (energia czynna, opłata handlowa). Frazy: "Sprzedaż energii elektrycznej".\n'
        '12. "sprzedaz_cena_brutto": Suma brutto sekcji SPRZEDAŻY energii.\n'
        '13. "dystrybucja_cena_netto": Suma netto sekcji DYSTRYBUCJI. Frazy: "Dystrybucja", "Usługi dystrybucyjne".\n'
        '14. "dystrybucja_cena_brutto": Suma brutto sekcji DYSTRYBUCJI.\n'
        'OPŁATY DODATKOWE (pola 15–30): Pobieraj z kolumny "Wartość netto" (NIE "Cena jed."). '
        'Jeśli opłata ma wiele wierszy — zwróć WSZYSTKIE wartości oddzielone "|" (np. "0.00|115.21"), '
        'WŁĄCZNIE z wierszami gdzie wartość wynosi 0.00 — to osobne pozycje, nie brak opłaty. '
        'Jeśli opłata ma jeden wiersz — zwróć samą liczbę jako string (np. "12.34"). '
        'Jeśli opłaty w ogóle NIE MA w dokumencie — zwróć "" (pusty string).\n'
        '15. "oplata_abonamentowa": "Opłata abonamentowa", "abonament". Wartość(i) netto.\n'
        '16. "oplata_abonamentowa_brutto": wartość(i) brutto opłaty abonamentowej.\n'
        '17. "oplata_sieciowa_stala": "Składnik stały stawki sieciowej", "opłata sieciowa stała". Wartość netto.\n'
        '18. "oplata_sieciowa_stala_brutto": wartość brutto tej opłaty.\n'
        '19. "oplata_sieciowa_zmienna": "Składnik zmienny stawki sieciowej", "opłata sieciowa zmienna". Wartość netto.\n'
        '20. "oplata_sieciowa_zmienna_brutto": wartość brutto tej opłaty.\n'
        '21. "oplata_jakosciowa": "Opłata jakościowa", "stawka jakościowa". Wartość netto.\n'
        '22. "oplata_jakosciowa_brutto": wartość brutto tej opłaty.\n'
        '23. "oplata_oze": "Opłata OZE". Wartość netto.\n'
        '24. "oplata_oze_brutto": wartość brutto opłaty OZE.\n'
        '25. "oplata_kogeneracyjna": "Opłata kogeneracyjna". Wartość netto.\n'
        '26. "oplata_kogeneracyjna_brutto": wartość brutto tej opłaty.\n'
        '27. "oplata_przejsciowa": "Opłata przejściowa", "stawka opłaty przejściowej". Wartość netto.\n'
        '28. "oplata_przejsciowa_brutto": wartość brutto tej opłaty.\n'
        '29. "oplata_mocowa": "Opłata mocowa". Wartość netto — może być bardzo wiele wierszy dziennych, zwróć wszystkie oddzielone "|".\n'
        '30. "oplata_mocowa_brutto": wartość brutto wszystkich wierszy opłaty mocowej, oddzielone "|".\n'
        '31. "pewnosc_ocr_procent": Liczba całkowita 0-100 — Twoja pewność że odczytane wartości są dokładnie takie jak w dokumencie (nie domysły).'
    )

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
            f"{self.FIELD_INSTRUCTIONS}\n\n"
            f"--- TEKST DOKUMENTU ---\n{text_content}\n--- KONIEC ---"
        )

        log.debug("[OCR] Prompt (tekst): %s", user_msg[:800])

        response = client.chat.completions.create(
            model="local-model",
            messages=[
                {"role": "system", "content": self.SYSTEM_PROMPT},
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
            f"{self.FIELD_INSTRUCTIONS}"
        )

        log.debug("[OCR] Prompt (wizja): %s", user_msg[:800])

        response = client.chat.completions.create(
            model="local-model",
            messages=[
                {"role": "system", "content": self.SYSTEM_PROMPT},
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
            f"{self.FIELD_INSTRUCTIONS}"
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
                {"role": "system", "content": self.SYSTEM_PROMPT},
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
