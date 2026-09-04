def _field_description(field):
    text = field.replace('_', ' ')
    replacements = {
        'Znajdz': 'Znajdz',
        'fakturze': 'fakturze',
        'pelna nazwa firmy sprzedawcy czyli wierzyciela wraz z forma prawna np Spolka Akcyjna else nazwa na gorze faktury': 'pelna nazwa sprzedawcy/wierzyciela wraz z forma prawna; zwykle nazwa firmy na gorze faktury',
        'pelny adres sprzedawcy zawierajacy tylko ulice numer domu kod pocztowy i miasto': 'adres sprzedawcy/wierzyciela: ulica, numer, kod pocztowy, miasto',
        'pelny adres sprzedawcy wierzyciela zawierajacy ulice numer domu kod pocztowy i miasto': 'pelny adres sprzedawcy/wierzyciela: ulica, numer, kod pocztowy, miasto',
        'numer NIP sprzedawcy wierzyciela bez myslnikow i spacji': 'NIP sprzedawcy/wierzyciela, tylko cyfry bez myslnikow i spacji',
        'numer faktury ktorej dotyczy to wezwanie do zaplaty': 'numer faktury',
        'pelna nazwa firmy nabywcy czyli dluznika ktory ma zaplacic za towar lub usluge': 'pelna nazwa nabywcy/dluznika',
        'dokladny adres siedziby nabywcy dluznika ulica kod miasto': 'adres nabywcy/dluznika: ulica, numer, kod pocztowy, miasto',
        'numer NIP nabywcy dluznika jesli jest podany': 'NIP nabywcy/dluznika, jesli widoczny',
        'date wystawienia dokumentu lub date sprzedazy': 'data wystawienia faktury albo data sprzedazy/uslugi',
        'koncowa kwote do zaplaty opisana czesto jako Razem lub Do zaplaty brutto wraz z waluta szukaj na koncu faktury': 'koncowa kwota brutto do zaplaty wraz z waluta; szukaj pol Razem, Do zaplaty, Suma brutto na dole faktury',
        'date terminu platnosci od ktorej beda liczone odsetki': 'termin platnosci faktury; data platnosci',
        'numer konta bankowego na ktory ma zostac dokonana wplata zazwyczaj na dole faktury': 'numer rachunku bankowego do zaplaty',
        'nazwe banku wierzyciela jesli jest podana obok numeru konta': 'nazwa banku przy numerze rachunku, jesli jest widoczna',
    }
    for source, target in replacements.items():
        text = text.replace(source, target)
    return text


def _field_instructions(fields):
    return "\n".join(f"- {field}: {_field_description(field)}" for field in fields)


