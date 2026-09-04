import json
import logging
import os
import time

from app.utils.ocr_utils import check_connection, get_mime_type, image_to_base64, extract_text_from_docx, extract_text_from_pdf_pages, extract_fields_from_template, llm_post
from app.utils.ocr_result import OCRResult, _preview

from .schemas import RESPONSE_SCHEMA
from app.prompts.ocr_prompts import get_ocr_system_prompt, build_ocr_prompt
from .llm_client import OCRLLMClient

log = logging.getLogger(__name__)

class OCRService:

    def __init__(self, api_url=None, model=None):
        self.api_url = api_url or os.environ.get("LLM_API_URL")
        self.model = model or os.environ.get("LLM_MODEL")
        self.timeout = int(os.environ.get("LLM_TIMEOUT_SECONDS", os.environ.get("OCR_LLM_TIMEOUT", 600)))
        self.fields = []
        self._fields_source = None  # 'template' or 'custom'
        self._field_key_map = {}    # key -> original description (tylko dla custom fields)
        log.info("OCRService init: api_url=%s model=%s timeout=%s", self.api_url, self.model, self.timeout)
        check_connection(self.api_url)

    def set_template(self, template_path):
        """Pobiera pola z szablonu HTML (atrybuty name z inputow)."""
        self.fields = extract_fields_from_template(template_path)
        self._fields_source = 'template'
        log.info("OCRService template loaded: path=%s fields_count=%s fields=%s", template_path, len(self.fields), self.fields[:40])

    def set_fields(self, fields):
        """Ustawia pola bezpoĹ›rednio (np. z frontendu) bez parsowania szablonu HTML.
        
        Pola z frontendu to ludzkie opisy (np. 'ZnajdĹş datÄ™ pozwoleĹ„...').
        Tworzymy bezpieczne klucze JSON (pole_1, pole_2, ...) i mapujemy je na opisy.
        """
        self._fields_source = 'custom'
        self._field_key_map = {}
        self.fields = []
        
        for i, field_desc in enumerate(fields, start=1):
            key = f"pole_{i}"
            self.fields.append(key)
            self._field_key_map[key] = field_desc
        
        log.info("OCRService custom fields set: fields_count=%s keys=%s", len(self.fields), self.fields[:10])

    def predict(self, file_path):
        """Wysyla plik do API i zwraca liste OCRResult (po jednym na strone/dokument)."""
        started_at = time.monotonic()
        ext = os.path.splitext(file_path)[1].lower()
        size = os.path.getsize(file_path) if os.path.exists(file_path) else None
        log.info("OCRService predict start: path=%s ext=%s size=%s model=%s", file_path, ext, size, self.model)

        try:
            if ext == '.pdf':
                results = self._predict_pdf(file_path)
            elif ext in ('.docx', '.doc'):
                text = extract_text_from_docx(file_path)
                log.info("OCRService doc text extracted: path=%s chars=%s", file_path, len(text or ''))
                if text and len(text) >= 50:
                    results = [self._predict_text(text, file_path)]
                else:
                    log.info("OCRService doc text too short, falling back to image flow: path=%s chars=%s", file_path, len(text or ''))
                    results = [self._predict_image(file_path)]
            else:
                results = [self._predict_image(file_path)]

            log.info(
                "OCRService predict done: path=%s results=%s elapsed_ms=%d",
                file_path,
                len(results),
                int((time.monotonic() - started_at) * 1000),
            )
            return results
        except Exception:
            log.exception("OCRService predict failed: path=%s", file_path)
            raise

    def _predict_pdf(self, file_path):
        import fitz

        page_texts = extract_text_from_pdf_pages(file_path)
        num_pages = len(page_texts)
        log.info("OCRService PDF start: path=%s pages=%s", file_path, num_pages)

        results = []
        for idx, page_text in enumerate(page_texts):
            page_label = f"strona {idx + 1}/{num_pages}"
            text_chars = len(page_text or '')
            log.info("OCRService PDF page: path=%s page=%s text_chars=%s", file_path, page_label, text_chars)

            if page_text and text_chars >= 50:
                results.append(self._predict_text(page_text, file_path, page_info=page_label))
            else:
                img_path = f"{file_path}_page{idx + 1}.png"
                try:
                    render_started_at = time.monotonic()
                    doc = fitz.open(file_path)
                    doc[idx].get_pixmap(dpi=150).save(img_path)
                    doc.close()
                    log.info(
                        "OCRService PDF page rendered: source=%s image=%s size=%s render_ms=%d",
                        file_path,
                        img_path,
                        os.path.getsize(img_path) if os.path.exists(img_path) else None,
                        int((time.monotonic() - render_started_at) * 1000),
                    )
                    results.append(self._predict_image(img_path, source_path=file_path))
                except Exception:
                    log.exception("OCRService PDF page error: path=%s page=%s", file_path, page_label)
                finally:
                    try:
                        os.remove(img_path)
                        log.debug("OCRService temporary page image removed: %s", img_path)
                    except OSError:
                        pass

        if not results:
            raise Exception("Nie udalo sie przetworzyc zadnej strony PDF.")
        return results

    def _predict_text(self, text_content, file_path, page_info=None):
        original_chars = len(text_content or '')
        max_chars = int(os.environ.get("OCR_TEXT_MAX_CHARS", 3000))
        if original_chars > max_chars:
            text_content = text_content[:max_chars]
        log.info(
            "OCRService text request prepared: path=%s page=%s original_chars=%s sent_chars=%s truncated=%s preview=%s",
            file_path,
            page_info,
            original_chars,
            len(text_content or ''),
            original_chars > max_chars,
            _preview(text_content, 300),
        )

        payload = {
            **self._llm_client.get_common_params(self.fields, self._fields_source, self._field_key_map),
            "messages": [
                {"role": "system", "content": get_ocr_system_prompt(is_image=False)},
                {
                    "role": "user",
                    "content": (
                        f"{build_ocr_prompt(self.fields, self._fields_source, self._field_key_map, is_text=True)}\\n\\n"
                        f"TEKST:\\n{text_content}"
                    )
                }
            ]
        }
        return self._llm_client.send_to_llm(payload, file_path, self._fields_source, self._field_key_map, source_type='text')

    def _predict_image(self, image_path, source_path=None):
        started_at = time.monotonic()
        mime_type = get_mime_type(image_path)
        image_base64 = image_to_base64(image_path)
        log.info(
            "OCRService image request prepared: image=%s source=%s mime=%s file_size=%s base64_chars=%s encode_ms=%d",
            image_path,
            source_path or image_path,
            mime_type,
            os.path.getsize(image_path) if os.path.exists(image_path) else None,
            len(image_base64),
            int((time.monotonic() - started_at) * 1000),
        )

        payload = {
            **self._llm_client.get_common_params(self.fields, self._fields_source, self._field_key_map),
            "messages": [
                {"role": "system", "content": get_ocr_system_prompt(is_image=True)},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": build_ocr_prompt(self.fields, self._fields_source, self._field_key_map, is_text=False)},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{image_base64}"
                            },
                        },
                    ],
                }
            ]
        }
        return self._llm_client.send_to_llm(payload, source_path or image_path, self._fields_source, self._field_key_map, source_type='image')

