import re

with open(r'd:\antygravity\ocr+dokumenty\DataExtractAI\app\prompts\ocr_prompts.py', 'r', encoding='utf-8') as f:
    prompts_code = f.read()

new_functions = '''
def build_ocr_schema(fields, fields_source, field_key_map):
    if fields_source == 'custom' and field_key_map:
        properties = {
            field: {"type": "string", "description": field_key_map.get(field, field)}
            for field in fields
        }
    else:
        properties = {field: {"type": "string", "description": _field_description(field)} for field in fields}
    
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "ekstrakcja_pol_szablonu",
            "schema": {
                "type": "object",
                "properties": properties,
                "required": fields,
                "additionalProperties": False,
            },
            "strict": True,
        },
    }

def get_ocr_system_prompt(is_image=False):
    if is_image:
        return "Jestes asystentem OCR. Wyodrebniasz dane z dokumentow i zwracasz je jako JSON."
    return "Jestes asystentem. Wyodrebniasz dane z dokumentow i zwracasz je jako JSON."

def build_ocr_prompt(fields, fields_source, field_key_map, is_text=False):
    action = "Przeanalizuj tekst" if is_text else "Przeanalizuj obraz"

    if fields and fields_source == 'custom' and field_key_map:
        field_lines = "\\n".join(
            f"- {key}: {field_key_map[key]}"
            for key in fields
        )
        return (
            f"{action} dokumentu i wypelnij JSON zgodny ze schema response_format.\\n"
            "To jest ekstrakcja danych z dokumentu. "
            "Nie oceniaj prawnie dokumentu, tylko przepisz widoczne dane.\\n\\n"
            "POLA DO WYPELNIENIA (klucz: instrukcja):\\n"
            f"{field_lines}\\n\\n"
            "ZASADY:\\n"
            "- Zwracaj TYLKO obiekt JSON zgodny ze schema, bez markdown.\\n"
            "- Nie dodawaj zadnych dodatkowych kluczy.\\n"
            "- Kazde pole ma instrukcje co dokladnie znalezc - postepuj dokladnie wg niej.\\n"
            "- Jesli instrukcja okresla format (np. YYYY-MM-DD), uzyj go.\\n"
            "- Dla NIP usun spacje i myslniki.\\n"
            "- Pusty string wpisuj dopiero wtedy, gdy danych naprawde nie da sie odczytac.\\n"
            "- Nie zostawiaj wszystkich pol pustych, jesli w dokumencie widac jakiekolwiek dane."
        )

    if fields:
        return (
            f"{action} faktury i wypelnij JSON zgodny ze schema response_format.\\n"
            "To jest ekstrakcja danych z faktury do wezwania do zaplaty. "
            "Nie oceniaj prawnie dokumentu, tylko przepisz widoczne dane.\\n\\n"
            "POLA DO WYPELNIENIA:\\n"
            f"{_field_instructions(fields)}\\n\\n"
            "ZASADY:\\n"
            "- Zwracaj TYLKO obiekt JSON zgodny ze schema, bez markdown.\\n"
            "- Nie dodawaj zadnych dodatkowych kluczy.\\n"
            "- Jesli widzisz na fakturze odpowiednik pola, wpisz go nawet gdy etykieta ma inna nazwe.\\n"
            "- Dla kwoty wybierz koncowa kwote brutto/do zaplaty, zwykle na dole faktury.\\n"
            "- Dla NIP usun spacje i myslniki.\\n"
            "- Dla dat zachowaj format z faktury albo DD.MM.RRRR, jesli jest oczywisty.\\n"
            "- Pusty string wpisuj dopiero wtedy, gdy danych naprawde nie da sie odczytac.\\n"
            "- Nie zostawiaj wszystkich pol pustych, jesli na obrazie widac jakiekolwiek dane faktury."
        )

    return (
        f"{action} i wyodrebnij wszystkie kluczowe dane z dokumentu. "
        "Zwroc TYLKO ustrukturyzowany obiekt JSON (bez znacznikow markdown)."
    )
'''

with open(r'd:\antygravity\ocr+dokumenty\DataExtractAI\app\prompts\ocr_prompts.py', 'w', encoding='utf-8') as f:
    f.write(prompts_code + new_functions)
print("Updated ocr_prompts.py")
