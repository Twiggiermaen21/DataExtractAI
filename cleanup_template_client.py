import re

with open(r'd:\antygravity\ocr+dokumenty\DataExtractAI\app\services\template\service.py', 'r', encoding='utf-8') as f:
    code = f.read()

# Remove _build_payload entirely
code = re.sub(r'    def _build_payload\(self.*?        return \{.*?        \}\n', '', code, flags=re.DOTALL)

# Remove _read_llm_payload entirely
code = re.sub(r'    def _read_llm_payload\(self.*?        return payload\n', '', code, flags=re.DOTALL)

with open(r'd:\antygravity\ocr+dokumenty\DataExtractAI\app\services\template\service.py', 'w', encoding='utf-8') as f:
    f.write(code)
