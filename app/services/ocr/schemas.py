# Schema JSON wysylany do LLM (structured output)
RESPONSE_SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "ekstrakcja_danych_faktury",
        "schema": {
            "type": "object",
            "properties": {
                "nabywca":              {"type": "string"},
                "pewnosc_ocr_procent":  {"type": "integer"},
                "kwota_do_zaplaty":     {"type": "number"},
                "komentarz_ocr":       {"type": "string"},
                "sprzedawca":          {"type": "string"},
                "numer_faktury":       {"type": "string"},
            },
            "required": [
                "nabywca", "pewnosc_ocr_procent", "kwota_do_zaplaty",
                "komentarz_ocr", "sprzedawca", "numer_faktury"
            ],
            "additionalProperties": False,
        },
        "strict": True,
    },
}
