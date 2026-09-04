import copy
import json
import logging
import os
import time

from app.utils.ocr_utils import check_connection, get_mime_type, image_to_base64, extract_text_from_docx, extract_text_from_pdf_pages, extract_fields_from_template, llm_post
from app.utils.ocr_result import OCRResult

from .schemas import RESPONSE_SCHEMA
from .prompts import _field_description, _field_instructions

log = logging.getLogger(__name__)

def _preview(text, limit=500):
    if text is None:
        return None
    text = str(text).replace("\r", " ").replace("\n", " ")
    return text[:limit] + ("..." if len(text) > limit else "")

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
        """Ustawia pola bezpośrednio (np. z frontendu) bez parsowania szablonu HTML.
        
        Pola z frontendu to ludzkie opisy (np. 'Znajdź datę pozwoleń...').
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
            "model": self.model,
            "messages": [
                {"role": "system", "content": "Jestes asystentem. Wyodrebniasz dane z dokumentow i zwracasz je jako JSON."},
                {"role": "user",   "content": (
                    f"Przeanalizuj ponizszy tekst dokumentu i wyodrebnij dane.\n\n"
                    f"--- TEKST DOKUMENTU ---\n{text_content}\n--- KONIEC ---\n\n"
                    f"{self._build_prompt(is_text=True)}"
                )},
            ],
            **self._common_params(),
        }
        return self._send_to_llm(payload, file_path, source_type='text')

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
            "model": self.model,
            "messages": [
                {"role": "system", "content": "Jestes asystentem OCR. Wyodrebniasz dane z dokumentow i zwracasz je jako JSON."},
                {"role": "user",   "content": [
                    {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{image_base64}"}},
                    {"type": "text", "text": self._build_prompt(is_text=False)},
                ]},
            ],
            **self._common_params(),
        }
        return self._send_to_llm(payload, source_path or image_path, source_type='image')

    def _common_params(self):
        params = {
            "max_tokens": int(os.environ.get("LLM_MAX_TOKENS", 8000)),
            "temperature": 0.1,
            "response_format": self._response_format(),
        }
        log.debug("OCRService common params: max_tokens=%s response_format_type=%s", params["max_tokens"], params["response_format"].get("type"))
        return params

    def _response_format(self):
        if not self.fields:
            return RESPONSE_SCHEMA

        if self._fields_source == 'custom' and self._field_key_map:
            # Custom fields: użyj oryginalnych opisów z frontendu jako description
            properties = {
                field: {"type": "string", "description": self._field_key_map.get(field, field)}
                for field in self.fields
            }
        else:
            # Template fields: użyj _field_description do tłumaczenia nazw pól
            properties = {field: {"type": "string", "description": _field_description(field)} for field in self.fields}
        
        return {
            "type": "json_schema",
            "json_schema": {
                "name": "ekstrakcja_pol_szablonu",
                "schema": {
                    "type": "object",
                    "properties": properties,
                    "required": self.fields,
                    "additionalProperties": False,
                },
                "strict": True,
            },
        }

    def _send_to_llm(self, payload, result_path, source_type=None):
        safe_payload = self._debug_payload(payload)
        log.info(
            "LLM OCR request: source=%s result_path=%s api_url=%s model=%s messages=%s timeout=%s",
            source_type,
            result_path,
            self.api_url,
            payload.get("model"),
            len(payload.get("messages", [])),
            self.timeout,
        )
        log.debug("LLM OCR request payload: %s", json.dumps(safe_payload, ensure_ascii=False, default=str))

        started_at = time.monotonic()
        response = llm_post(
            self.api_url, json=payload,
            headers={"Content-Type": "application/json"},
            timeout=self.timeout,
        )
        elapsed_ms = int((time.monotonic() - started_at) * 1000)
        log.info(
            "LLM OCR response: source=%s status=%s elapsed_ms=%s response_chars=%s content_type=%s",
            source_type,
            response.status_code,
            elapsed_ms,
            len(response.text or ''),
            response.headers.get('Content-Type'),
        )

        if response.status_code == 200:
            try:
                response_json = response.json()
                output_text = response_json["choices"][0]["message"]["content"].strip()
            except Exception:
                log.exception("LLM OCR response parse failed: preview=%s", _preview(response.text, 1000))
                raise

            # Dla custom fields: zamień klucze pole_X z powrotem na oryginalne opisy z frontendu
            if self._fields_source == 'custom' and self._field_key_map:
                try:
                    parsed = json.loads(output_text)
                    if isinstance(parsed, dict):
                        remapped = {}
                        for key, value in parsed.items():
                            original_key = self._field_key_map.get(key, key)
                            remapped[original_key] = value
                        output_text = json.dumps(remapped, ensure_ascii=False, indent=2)
                        log.info("LLM OCR keys remapped: %s -> %s keys", len(parsed), len(remapped))
                except (json.JSONDecodeError, TypeError):
                    log.warning("LLM OCR key remap skipped: could not parse output as JSON")

            result = OCRResult(output_text, result_path)
            log.info(
                "LLM OCR parsed: source=%s output_chars=%s extracted_keys=%s output_preview=%s",
                source_type,
                len(output_text),
                list(result.extracted_data.keys()) if isinstance(result.extracted_data, dict) else [],
                _preview(output_text, 700),
            )
            return result

        log.warning("LLM OCR non-200: status=%s body_preview=%s", response.status_code, _preview(response.text, 1200))
        if "image input is not supported" in response.text.lower():
            raise Exception(
                "Serwer LLM dziala bez obslugi obrazow. Uruchom llama-server ponownie "
                "z pasujacym projektorem, np. --mmproj <plik-mmproj.gguf>, albo ustaw "
                "LLAMA_ARG_MMPROJ. Model i mmproj musza pochodzic z tego samego wydania."
            )
        raise Exception(f"API blad {response.status_code}: {response.text}")

    def _debug_payload(self, payload):
        debug_payload = copy.deepcopy(payload)
        for message in debug_payload.get("messages", []):
            content = message.get("content")
            if isinstance(content, str) and len(content) > 1200:
                message["content"] = f"{content[:1200]}... <truncated; {len(content)} chars>"
                continue
            if not isinstance(content, list):
                continue
            for item in content:
                image_url = item.get("image_url") if isinstance(item, dict) else None
                url = image_url.get("url") if isinstance(image_url, dict) else None
                if isinstance(url, str) and url.startswith("data:"):
                    header, _, data = url.partition(",")
                    image_url["url"] = f"{header},<base64 omitted; {len(data)} chars>"
                if isinstance(item, dict) and isinstance(item.get("text"), str) and len(item["text"]) > 1200:
                    item["text"] = f"{item['text'][:1200]}... <truncated; {len(item['text'])} chars>"
        return debug_payload

    def _build_prompt(self, is_text=False):
        action = "Przeanalizuj tekst" if is_text else "Przeanalizuj obraz"

        if self.fields and self._fields_source == 'custom' and self._field_key_map:
            # Custom fields z frontendu - ogólny prompt do dokumentu
            field_lines = "\n".join(
                f"- {key}: {self._field_key_map[key]}"
                for key in self.fields
            )
            return (
                f"{action} dokumentu i wypelnij JSON zgodny ze schema response_format.\n"
                "To jest ekstrakcja danych z dokumentu. "
                "Nie oceniaj prawnie dokumentu, tylko przepisz widoczne dane.\n\n"
                "POLA DO WYPELNIENIA (klucz: instrukcja):\n"
                f"{field_lines}\n\n"
                "ZASADY:\n"
                "- Zwracaj TYLKO obiekt JSON zgodny ze schema, bez markdown.\n"
                "- Nie dodawaj zadnych dodatkowych kluczy.\n"
                "- Kazde pole ma instrukcje co dokladnie znalezc - postepuj dokladnie wg niej.\n"
                "- Jesli instrukcja okresla format (np. YYYY-MM-DD), uzyj go.\n"
                "- Dla NIP usun spacje i myslniki.\n"
                "- Pusty string wpisuj dopiero wtedy, gdy danych naprawde nie da sie odczytac.\n"
                "- Nie zostawiaj wszystkich pol pustych, jesli w dokumencie widac jakiekolwiek dane."
            )

        if self.fields:
            return (
                f"{action} faktury i wypelnij JSON zgodny ze schema response_format.\n"
                "To jest ekstrakcja danych z faktury do wezwania do zaplaty. "
                "Nie oceniaj prawnie dokumentu, tylko przepisz widoczne dane.\n\n"
                "POLA DO WYPELNIENIA:\n"
                f"{_field_instructions(self.fields)}\n\n"
                "ZASADY:\n"
                "- Zwracaj TYLKO obiekt JSON zgodny ze schema, bez markdown.\n"
                "- Nie dodawaj zadnych dodatkowych kluczy.\n"
                "- Jesli widzisz na fakturze odpowiednik pola, wpisz go nawet gdy etykieta ma inna nazwe.\n"
                "- Dla kwoty wybierz koncowa kwote brutto/do zaplaty, zwykle na dole faktury.\n"
                "- Dla NIP usun spacje i myslniki.\n"
                "- Dla dat zachowaj format z faktury albo DD.MM.RRRR, jesli jest oczywisty.\n"
                "- Pusty string wpisuj dopiero wtedy, gdy danych naprawde nie da sie odczytac.\n"
                "- Nie zostawiaj wszystkich pol pustych, jesli na obrazie widac jakiekolwiek dane faktury."
            )

        return (
            f"{action} i wyodrebnij wszystkie kluczowe dane z dokumentu. "
            "Zwroc TYLKO ustrukturyzowany obiekt JSON (bez znacznikow markdown)."
        )