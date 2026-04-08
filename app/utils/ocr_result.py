import json
import os
import time
import logging

from json_repair import repair_json

log = logging.getLogger(__name__)


class OCRResult:

    # Fields where many daily rows should be summed rather than listed.
    _SUM_IF_MANY = {"oplata_mocowa", "oplata_mocowa_brutto"}
    # Any pipe-separated field with more than this many parts gets summed.
    _PIPE_LIMIT = 10

    def __init__(self, text, input_path, is_vision=False):
        self.text = text
        self.input_path = input_path
        self.is_vision = is_vision
        self.extracted_data = self._postprocess(self._parse_json(text))
        self.parsing_res_list = [{"block_content": text}]

    def _postprocess(self, data):
        if not isinstance(data, dict):
            return data
        for key in self._SUM_IF_MANY:
            if key in data and isinstance(data[key], str):
                parts = [p.strip() for p in data[key].split("|") if p.strip()]
                if len(parts) > self._PIPE_LIMIT:
                    try:
                        data[key] = str(round(sum(float(p.replace(",", ".")) for p in parts), 2))
                    except ValueError:
                        pass
        return data

    def _parse_json(self, text):
        try:
            clean = text.strip()
            if clean.startswith("```"):
                lines = clean.split("\n")
                clean = "\n".join(lines[1:-1])
            return json.loads(clean)
        except Exception as e:
            log.warning("Nie udało się sparsować odpowiedzi LLM jako JSON: %s | Tekst: %.200s", e, text)
            try:
                repaired = repair_json(text, return_objects=True)
                if isinstance(repaired, dict) and repaired:
                    log.info("JSON naprawiony przez json_repair")
                    return repaired
            except Exception:
                pass
            return {"_parse_error": str(e)}

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
