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

    def __init__(self, text, input_path=None):
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