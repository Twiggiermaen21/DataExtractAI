with open(r'd:\antygravity\ocr+dokumenty\DataExtractAI\app\services\template\service.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
skip = False
for line in lines:
    if line.startswith('def _strip_json_code_fence('):
        skip = True
    elif line.startswith('class IusfullyTemplateAnalysisService'):
        skip = False
    
    if not skip:
        new_lines.append(line)

with open(r'd:\antygravity\ocr+dokumenty\DataExtractAI\app\services\template\service.py', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)
