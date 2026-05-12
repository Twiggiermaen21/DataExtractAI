import json
import os
import time
import logging
import re
from datetime import date

try:
    from json_repair import repair_json
except ImportError:
    repair_json = None

log = logging.getLogger(__name__)


class OCRResult:

    # Fields where many daily rows should be summed rather than listed.
    _SUM_IF_MANY = {"oplata_mocowa", "oplata_mocowa_brutto"}
    # Any pipe-separated field with more than this many parts gets summed.
    _PIPE_LIMIT = 10
    _DATE_PATTERN = re.compile(r"\d{4}[./-]\d{1,2}[./-]\d{1,2}|\d{1,2}[./-]\d{1,2}[./-]\d{4}")

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
        if isinstance(data.get("data_sprzedazy"), str):
            data["data_sprzedazy"] = self._normalize_data_sprzedazy(data["data_sprzedazy"])
        return data

    @classmethod
    def _normalize_data_sprzedazy(cls, value):
        raw = value.strip()
        if not raw:
            return raw

        lower = raw.lower()
        matches = cls._DATE_PATTERN.findall(raw)
        if len(matches) >= 2 and ("od" in lower or "do" in lower):
            first_date = cls._to_iso_date(matches[0])
            return first_date or matches[0]

        return cls._to_iso_date(raw) or raw

    @staticmethod
    def _to_iso_date(value):
        clean = value.strip().replace("/", "-").replace(".", "-")
        parts = clean.split("-")
        if len(parts) != 3:
            return None

        try:
            p1, p2, p3 = (int(part) for part in parts)
        except ValueError:
            return None

        if len(parts[0]) == 4:
            year, month, day = p1, p2, p3
        elif len(parts[2]) == 4:
            day, month, year = p1, p2, p3
        else:
            return None

        try:
            return date(year, month, day).isoformat()
        except ValueError:
            return None

    def _parse_json(self, text):
        try:
            if text is None:
                log.warning("LLM zwrocil None zamiast JSON.")
                return {"_parse_error": "empty LLM response (None)"}

            if not isinstance(text, str):
                text = str(text)

            clean = text.strip()
            if not clean:
                log.warning("LLM zwrocil pusty tekst zamiast JSON.")
                return {"_parse_error": "empty LLM response"}

            if clean.startswith("```"):
                lines = clean.split("\n")
                clean = "\n".join(lines[1:-1])
            return json.loads(clean)
        except Exception as e:
            log.warning("Nie udalo sie sparsowac odpowiedzi LLM jako JSON: %s | Tekst: %.200s", e, text)
            if repair_json is not None:
                try:
                    repaired = repair_json(text, return_objects=True)
                    if isinstance(repaired, dict) and repaired:
                        log.info("JSON naprawiony przez json_repair")
                        return repaired
                except Exception:
                    pass
            else:
                log.warning("Brak biblioteki json_repair - pomijam probe naprawy JSON.")
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
            log.error("Blad zapisu JSON: %s", e)
            return None
