import re

with open(r'd:\antygravity\ocr+dokumenty\DataExtractAI\app\services\ocr\service.py', 'r', encoding='utf-8') as f:
    code = f.read()

client_code = '''import time
import json
import copy
import logging

from app.utils.ocr_utils import llm_post
from app.utils.ocr_result import OCRResult
from app.prompts.ocr_prompts import build_ocr_schema

log = logging.getLogger(__name__)

def _preview(text, limit=500):
    if text is None:
        return None
    text = str(text).replace("\\r", " ").replace("\\n", " ")
    return text[:limit] + ("..." if len(text) > limit else "")

class OCRLLMClient:
    def __init__(self, api_url, model, timeout=120):
        self.api_url = api_url
        self.model = model
        self.timeout = timeout

    def get_common_params(self, fields, fields_source, field_key_map):
        params = {
            "model": self.model,
            "temperature": 0.0,
            "max_tokens": 2048,
        }
        if fields:
            params["response_format"] = build_ocr_schema(fields, fields_source, field_key_map)
        return params

    def send_to_llm(self, payload, result_path, fields_source, field_key_map, source_type=None):
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

            if fields_source == 'custom' and field_key_map:
                try:
                    parsed = json.loads(output_text)
                    if isinstance(parsed, dict):
                        remapped = {}
                        for key, value in parsed.items():
                            original_key = field_key_map.get(key, key)
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
'''

with open(r'd:\antygravity\ocr+dokumenty\DataExtractAI\app\services\ocr\llm_client.py', 'w', encoding='utf-8') as f:
    f.write(client_code)

# Replace usage in service.py
code = code.replace("from app.utils.ocr_utils import extract_fields_from_template, get_llm_api_url, llm_post", "from app.utils.ocr_utils import extract_fields_from_template, get_llm_api_url")
code = code.replace("import copy\n", "")
code = code.replace("from app.prompts.ocr_prompts import build_ocr_schema, get_ocr_system_prompt, build_ocr_prompt", "from app.prompts.ocr_prompts import get_ocr_system_prompt, build_ocr_prompt\nfrom .llm_client import OCRLLMClient")

# replace _predict_text internal calls
code = code.replace("**self._common_params()", "**self._llm_client.get_common_params(self.fields, self._fields_source, self._field_key_map)")
code = code.replace("return self._send_to_llm(payload, file_path, source_type='text')", "return self._llm_client.send_to_llm(payload, file_path, self._fields_source, self._field_key_map, source_type='text')")
code = code.replace("return self._send_to_llm(payload, source_path or image_path, source_type='image')", "return self._llm_client.send_to_llm(payload, source_path or image_path, self._fields_source, self._field_key_map, source_type='image')")

# remove old methods
code = re.sub(r'    def _common_params\(self\):.*?    def _send_to_llm\(self, payload, result_path, source_type=None\):', '    def _send_to_llm(self, payload, result_path, source_type=None):', code, flags=re.DOTALL)
code = re.sub(r'    def _send_to_llm\(self, payload, result_path, source_type=None\):.*?    def _debug_payload\(self, payload\):', '    def _debug_payload(self, payload):', code, flags=re.DOTALL)
code = re.sub(r'    def _debug_payload\(self, payload\):.*', '', code, flags=re.DOTALL)
code = re.sub(r'def _preview\(text, limit=500\):.*?class OCRService:', 'class OCRService:', code, flags=re.DOTALL)

# Add client init
code = code.replace("self.api_url = get_llm_api_url(api_url)", "self.api_url = get_llm_api_url(api_url)\n        self._llm_client = OCRLLMClient(self.api_url, self.model, self.timeout)")

with open(r'd:\antygravity\ocr+dokumenty\DataExtractAI\app\services\ocr\service.py', 'w', encoding='utf-8') as f:
    f.write(code)

print("Updated OCR service to use LLMClient!")
