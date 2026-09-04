import re

with open(r'd:\antygravity\ocr+dokumenty\DataExtractAI\app\services\template\service.py', 'r', encoding='utf-8') as f:
    code = f.read()

# Extract TEMPLATE_FIELD_RESPONSE_SCHEMA and TEMPLATE_ANALYSIS_SYSTEM_PROMPT
schema_match = re.search(r'TEMPLATE_FIELD_RESPONSE_SCHEMA = \{.*?\n\}\n\n', code, re.DOTALL)
prompt_match = re.search(r'TEMPLATE_ANALYSIS_SYSTEM_PROMPT = """.*?\"\"\"\n', code, re.DOTALL)

schema = schema_match.group(0) if schema_match else ""
prompt = prompt_match.group(0) if prompt_match else ""

with open(r'd:\antygravity\ocr+dokumenty\DataExtractAI\app\prompts\template_prompts.py', 'w', encoding='utf-8') as f:
    f.write(schema + "\n" + prompt)

# Remove them from service.py and add import
code = code.replace(schema, "")
code = code.replace(prompt, "")
code = code.replace('from decimal import InvalidOperation', 'from decimal import InvalidOperation\nfrom app.prompts.template_prompts import TEMPLATE_FIELD_RESPONSE_SCHEMA, TEMPLATE_ANALYSIS_SYSTEM_PROMPT\n')

with open(r'd:\antygravity\ocr+dokumenty\DataExtractAI\app\services\template\service.py', 'w', encoding='utf-8') as f:
    f.write(code)

print("Done")
