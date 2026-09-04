with open(r'd:\antygravity\ocr+dokumenty\DataExtractAI\app\services\ocr\service.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
skip = False
for line in lines:
    if line.startswith('    def _response_format'):
        skip = True
    elif line.startswith('    def _send_to_llm'):
        skip = False
    
    if not skip:
        new_lines.append(line)

with open(r'd:\antygravity\ocr+dokumenty\DataExtractAI\app\services\ocr\service.py', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)
