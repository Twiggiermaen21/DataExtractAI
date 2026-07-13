import json
import os
import time
import logging

log = logging.getLogger(__name__)


def _preview(text, limit=500):
    if text is None:
        return None
    text = str(text).replace("\r", " ").replace("\n", " ")
    return text[:limit] + ("..." if len(text) > limit else "")


class OCRResult:

    def __init__(self, text, input_path):
        self.text = text
        self.input_path = input_path
        self.extracted_data = self._parse_json(text)
        self.parsing_res_list = [{"block_content": text}]
        log.info(
            "OCRResult created: input=%s text_chars=%s extracted_type=%s extracted_keys=%s",
            input_path,
            len(text or ''),
            type(self.extracted_data).__name__,
            list(self.extracted_data.keys()) if isinstance(self.extracted_data, dict) else [],
        )

    def _parse_json(self, text):
        try:
            clean = (text or '').strip()
            if clean.startswith("```"):
                lines = clean.split("\n")
                clean = "\n".join(lines[1:-1])
            parsed = json.loads(clean)
            log.info(
                "OCRResult JSON parsed: type=%s keys=%s",
                type(parsed).__name__,
                list(parsed.keys()) if isinstance(parsed, dict) else None,
            )
            return parsed
        except Exception:
            log.exception("OCRResult JSON parse failed: text_preview=%s", _preview(text, 1000))
            return {}

    def save_to_json(self, save_path):
        filename = os.path.basename(self.input_path)
        base_name = os.path.splitext(filename)[0]
        output_filename = f"{base_name}_{int(time.time())}.json"
        full_path = os.path.join(save_path, output_filename)

        data = {
            "input_path": self.input_path,
            "parsing_res_list": self.parsing_res_list,
            "full_text": self.text,
            "extracted_fields": self.extracted_data,
        }

        try:
            os.makedirs(save_path, exist_ok=True)
            with open(full_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            log.info(
                "OCRResult saved JSON: path=%s size=%s extracted_keys=%s",
                full_path,
                os.path.getsize(full_path) if os.path.exists(full_path) else None,
                list(self.extracted_data.keys()) if isinstance(self.extracted_data, dict) else [],
            )
            return full_path
        except Exception:
            log.exception("OCRResult JSON save failed: path=%s", full_path)
            return None