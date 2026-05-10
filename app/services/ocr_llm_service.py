import os
from openai import OpenAI

from app.utils.ocr_utils import (
    get_mime_type,
    image_to_base64,
    extract_text_from_docx,
    extract_text_from_pdf_pages,
    extract_fields_from_template,
    extract_text_from_xml,
    enhance_image_for_ocr,
)
from app.utils.ocr_result import OCRResult
from llm_config import ALL_COLUMNS, FIELD_INSTRUCTIONS, SYSTEM_PROMPT


def build_response_schema(selected_columns=None):
    """Buduje RESPONSE_SCHEMA - zawsze wyciaga wszystkie pola."""
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


class OCRService:
    def __init__(self, api_url=None, model=None, selected_columns=None):
        self.fields = []
        self.selected_columns = selected_columns
        self.response_schema = build_response_schema(selected_columns)

    def set_template(self, template_path):
        self.fields = extract_fields_from_template(template_path)

    def predict(self, file_path):
        ext = os.path.splitext(file_path)[1].lower()

        if ext == ".pdf":
            return self._predict_pdf(file_path)

        if ext in (".docx", ".doc"):
            text = extract_text_from_docx(file_path)
            if text and len(text) >= 50:
                return [self._predict_text(text, file_path)]

        if ext == ".xml":
            text = extract_text_from_xml(file_path)
            if text:
                return [self._predict_text(text, file_path)]

        return [self._predict_image(file_path)]

    def _predict_pdf(self, file_path):
        import fitz

        page_texts = extract_text_from_pdf_pages(file_path)
        num_pages = len(page_texts)
        print(f"[OCR] PDF: {num_pages} stron(y)")

        combined_text = "\n\n".join(
            [f"--- STRONA {i+1} ---\n{t}" for i, t in enumerate(page_texts) if t.strip()]
        )

        if len(combined_text.strip()) > 100:
            print(f"[OCR] Przetwarzanie calego PDF jako tekst ({num_pages} stron).")
            return [self._predict_text(combined_text, file_path)]

        print(f"[OCR] PDF wyglada na skan. Renderowanie wszystkich {num_pages} stron jako obrazy.")
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

            return [self._predict_images(img_paths, source_path=file_path)]
        except Exception as e:
            print(f"[OCR] Blad renderowania stron PDF: {e}")
            return [self._predict_text(combined_text, file_path)]
        finally:
            for p in img_paths:
                if os.path.exists(p):
                    os.remove(p)

    def _predict_text(self, text_content, file_path, page_info=None):
        max_chars = int(os.environ.get("LLM_MAX_CHARS", 800000))
        if len(text_content) > max_chars:
            print(f"[OCR] Tekst za dlugi ({len(text_content)} znakow), przycinanie do {max_chars}.")
            text_content = text_content[:max_chars]

        log = __import__("logging").getLogger(__name__)
        log.info("[OCR] Tekst dokumentu (pierwsze 500 znakow): %s", text_content)

        llama_url = os.environ.get("LLAMA_SERVER_URL", "http://127.0.0.1:8080/v1")
        client = OpenAI(base_url=llama_url, api_key="local")

        user_msg = (
            "Przeanalizuj ponizszy tekst faktury za energie elektryczna.\n\n"
            f"{FIELD_INSTRUCTIONS}\n\n"
            f"--- TEKST DOKUMENTU ---\n{text_content}\n--- KONIEC ---"
        )

        response = client.chat.completions.create(
            model="local-model",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_msg},
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
        log.info("[OCR] Odpowiedz LLM (tekst): %s", output_text)
        return OCRResult(output_text, file_path, is_vision=False)

    def _predict_image(self, image_path, source_path=None):
        log = __import__("logging").getLogger(__name__)
        log.info("[OCR] Przetwarzanie obrazu: %s", image_path)

        llama_url = os.environ.get("LLAMA_SERVER_URL", "http://127.0.0.1:8080/v1")
        client = OpenAI(base_url=llama_url, api_key="local")

        enhanced_path, is_temp = enhance_image_for_ocr(image_path)
        image_base64 = image_to_base64(enhanced_path)
        mime_type = get_mime_type(enhanced_path)

        user_msg = (
            "Przeanalizuj zalaczona fakture za energie elektryczna.\n\n"
            f"{FIELD_INSTRUCTIONS}"
        )

        try:
            response = client.chat.completions.create(
                model="local-model",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": user_msg},
                            {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{image_base64}"}},
                        ],
                    },
                ],
                response_format=self.response_schema,
                temperature=0.0,
                max_tokens=int(os.environ.get("LLM_MAX_TOKENS", 1000)),
            )

            output_text = response.choices[0].message.content
            log.info("[OCR] Odpowiedz LLM (wizja): %s", output_text)
            return OCRResult(output_text, source_path or image_path, is_vision=True)
        finally:
            if is_temp and os.path.exists(enhanced_path):
                os.remove(enhanced_path)

    def _predict_images(self, image_paths, source_path=None):
        log = __import__("logging").getLogger(__name__)
        log.info("[OCR] Przetwarzanie %d stron jako obrazow: %s", len(image_paths), source_path)

        llama_url = os.environ.get("LLAMA_SERVER_URL", "http://127.0.0.1:8080/v1")
        client = OpenAI(base_url=llama_url, api_key="local")

        user_msg = (
            f"Przeanalizuj ponizszy dokument skladajacy sie z {len(image_paths)} stron "
            f"(kazdy obraz to jedna strona faktury za energie elektryczna).\n\n"
            f"{FIELD_INSTRUCTIONS}"
        )

        temp_paths = []
        try:
            content = [{"type": "text", "text": user_msg}]
            for img_path in image_paths:
                enhanced_path, is_temp = enhance_image_for_ocr(img_path)
                if is_temp:
                    temp_paths.append(enhanced_path)

                image_base64 = image_to_base64(enhanced_path)
                mime_type = get_mime_type(enhanced_path)
                content.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:{mime_type};base64,{image_base64}"},
                })

            response = client.chat.completions.create(
                model="local-model",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": content},
                ],
                response_format=self.response_schema,
                temperature=0.0,
                max_tokens=int(os.environ.get("LLM_MAX_TOKENS", 1000)),
            )

            output_text = response.choices[0].message.content
            log.info("[OCR] Odpowiedz LLM (multi-wizja): %s", output_text)
            return OCRResult(output_text, source_path or image_paths[0], is_vision=True)
        finally:
            for p in temp_paths:
                if os.path.exists(p):
                    os.remove(p)

    def _build_prompt(self, is_text=False):
        action = "Przeanalizuj tekst" if is_text else "Przeanalizuj obraz"

        if self.fields:
            fields_list = "\n".join(
                f'{i+1}. "{f}": {f.replace("_", " ")}' for i, f in enumerate(self.fields)
            )
            return (
                f"{action} i wyodrebnij dane. Zwroc TYLKO obiekt JSON (bez markdown).\n\n"
                f"Pola do ekstrakcji:\n{fields_list}\n\n"
                "WAZNE: Dla pol pewnosc_ocr_procent podaj szacunkowa pewnosc odczytu jako liczbe 0-100.\n"
                "Jesli wartosci nie ma, uzyj null."
            )
        return (
            f"{action} i wyodrebnij wszystkie kluczowe dane z dokumentu. "
            "Zwroc TYLKO ustrukturyzowany obiekt JSON (bez znacznikow markdown)."
        )
