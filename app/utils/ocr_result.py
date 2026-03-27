import json
import os
import time
import logging

log = logging.getLogger(__name__)


class OCRResult:

    def __init__(self, text, input_path, is_vision=False):
        self.text = text
        self.input_path = input_path
        self.is_vision = is_vision
        self.extracted_data = self._parse_json(text)
        self.parsing_res_list = [{"block_content": text}]

    def _parse_json(self, text):
        try:
            clean = text.strip()
            if clean.startswith("```"):
                lines = clean.split("\n")
                clean = "\n".join(lines[1:-1])
            return json.loads(clean)
        except Exception as e:
            log.warning("Nie udało się sparsować odpowiedzi LLM jako JSON: %s | Tekst: %.200s", e, text)
            return {}

    def save_to_json(self, save_path):
        filename = os.path.basename(self.input_path)
        base_name = os.path.splitext(filename)[0]
        output_filename = f"{base_name}_{int(time.time())}.json"
        full_path = os.path.join(save_path, output_filename)

        data = {
            "input_path": self.input_path,
            "is_vision": self.is_vision,
            "parsing_res_list": self.parsing_res_list,
            "full_text": self.text,
            "extracted_fields": self.extracted_data,
        }

        try:
            with open(full_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return full_path
        except Exception as e:
            log.error("Błąd zapisu JSON: %s", e)
            return None
