import re

with open(r'd:\antygravity\ocr+dokumenty\DataExtractAI\app\services\ocr\service.py', 'r', encoding='utf-8') as f:
    code = f.read()

# Replace the imports
code = re.sub(r'from app\.prompts\.ocr_prompts import .*', 'from app.prompts.ocr_prompts import build_ocr_schema, get_ocr_system_prompt, build_ocr_prompt', code)

# Update _predict_text
new_predict_text = '''    def _predict_text(self, text_content, file_path, page_info=None):
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
            **self._common_params(),
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
        return self._send_to_llm(payload, file_path, source_type='text')'''
code = re.sub(r'    def _predict_text\(.*?return self\._send_to_llm\(payload, file_path, source_type=\'text\'\)', new_predict_text, code, flags=re.DOTALL)

# Update _predict_image
new_predict_image = '''    def _predict_image(self, image_path, source_path=None):
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
            **self._common_params(),
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
        return self._send_to_llm(payload, source_path or image_path, source_type='image')'''
code = re.sub(r'    def _predict_image\(.*?return self\._send_to_llm\(payload, source_path or image_path, source_type=\'image\'\)', new_predict_image, code, flags=re.DOTALL)

# Remove _response_format completely, change _common_params to use build_ocr_schema
new_common_params = '''    def _common_params(self):
        params = {
            "model": self.model,
            "temperature": 0.0,
            "max_tokens": 2048,
        }
        if self.fields:
            params["response_format"] = build_ocr_schema(self.fields, self._fields_source, self._field_key_map)
        return params'''
code = re.sub(r'    def _common_params.*?return params', new_common_params, code, flags=re.DOTALL)

# Delete the old _response_format and _build_prompt methods
code = re.sub(r'    def _response_format\(self\):.*?            \},$          \}', '', code, flags=re.DOTALL)
code = re.sub(r'    def _build_prompt\(self, is_text=False\):.*', '', code, flags=re.DOTALL)

with open(r'd:\antygravity\ocr+dokumenty\DataExtractAI\app\services\ocr\service.py', 'w', encoding='utf-8') as f:
    f.write(code)

print("Updated OCR service!")
