import re
import unicodedata
from datetime import date
from decimal import Decimal, InvalidOperation

POLISH_MONTHS = {
    'stycznia': 1,
    'lutego': 2,
    'marca': 3,
    'kwietnia': 4,
    'maja': 5,
    'czerwca': 6,
    'lipca': 7,
    'sierpnia': 8,
    'wrzesnia': 9,
    'września': 9,
    'pazdziernika': 10,
    'października': 10,
    'listopada': 11,
    'grudnia': 12,
}

def _collapse_whitespace(value: str) -> str:
    return ' '.join(unicodedata.normalize('NFKC', value).split())


def _normalize_number(value: str) -> str:
    normalized = unicodedata.normalize('NFKC', value).strip()
    normalized = normalized.replace('\u00a0', '').replace('\u202f', '')
    normalized = re.sub(r'[\s\']', '', normalized)

    sign = ''
    if normalized.startswith(('+', '-')):
        sign, normalized = normalized[0], normalized[1:]

    if not normalized or not re.fullmatch(r'[0-9.,]+', normalized):
        raise ValueError('Niepoprawny format liczby')
    if not normalized[0].isdigit() or not normalized[-1].isdigit():
        raise ValueError('Liczba musi zaczynac i konczyc sie cyfra')

    if ',' in normalized and '.' in normalized:
        if normalized.rfind(',') > normalized.rfind('.'):
            normalized = normalized.replace('.', '').replace(',', '.')
        else:
            normalized = normalized.replace(',', '')
    elif ',' in normalized:
        normalized = normalized.replace('.', '').replace(',', '.')
    elif normalized.count('.') > 1:
        parts = normalized.split('.')
        if all(len(part) == 3 for part in parts[1:]):
            normalized = ''.join(parts)
        else:
            normalized = ''.join(parts[:-1]) + '.' + parts[-1]
    elif normalized.count('.') == 1:
        integer_part, fraction_part = normalized.split('.')
        if len(fraction_part) == 3 and 1 <= len(integer_part) <= 3:
            normalized = integer_part + fraction_part

    try:
        number = Decimal(sign + normalized)
    except InvalidOperation as exc:
        raise ValueError('Niepoprawny format liczby') from exc
    if not number.is_finite():
        raise ValueError('Liczba musi byc skonczona')
    return format(number, 'f')


def _source_replacement_expression(source: str, field_type: str) -> str:
    """Build an exact-match expression without replacing inside larger tokens."""
    escaped_source = re.escape(source)

    if field_type == 'number':
        prefix = (
            r'(?<!\d)(?<![+-])(?<!\d[\s.,\'])'
            if source[0].isdigit()
            else ''
        )
        suffix = (
            r'(?!\d)(?![.,]\d)(?![\s\']\d{3}(?!\d))'
            if source[-1].isdigit()
            else ''
        )
        return prefix + escaped_source + suffix

    if field_type == 'date':
        prefix = r'(?<!\d)' if source[0].isdigit() else ''
        suffix = r'(?!\d)' if source[-1].isdigit() else ''
        return prefix + escaped_source + suffix

    prefix = (
        r"(?<!\w)(?<!\w[-/.'’])"
        if source[0].isalnum() or source[0] == '_'
        else ''
    )
    suffix = (
        r"(?!\w)(?![-/.'’]\w)"
        if source[-1].isalnum() or source[-1] == '_'
        else ''
    )
    return prefix + escaped_source + suffix


def _normalize_date(value: str) -> str:
    normalized = _collapse_whitespace(value)

    iso_match = re.fullmatch(r'(\d{4})[-./](\d{1,2})[-./](\d{1,2})', normalized)
    if iso_match:
        year, month, day = map(int, iso_match.groups())
        return date(year, month, day).isoformat()

    numeric_match = re.fullmatch(r'(\d{1,2})[-./](\d{1,2})[-./](\d{4})', normalized)
    if numeric_match:
        day, month, year = map(int, numeric_match.groups())
        return date(year, month, day).isoformat()

    words_match = re.fullmatch(r'(\d{1,2})\s+([A-Za-zĄĆĘŁŃÓŚŹŻąćęłńóśźż]+)\s+(\d{4})', normalized)
    if words_match:
        day = int(words_match.group(1))
        month_name = words_match.group(2).lower()
        year = int(words_match.group(3))
        month = POLISH_MONTHS.get(month_name)
        if month is None:
            raise ValueError('Nieznana nazwa miesiaca')
        return date(year, month, day).isoformat()

    raise ValueError('Niepoprawny format daty')


def _normalize_text(value: str, field_key: str) -> str:
    collapsed = _collapse_whitespace(value)
    identifier_kind = next(
        (
            identifier
            for identifier in ('nip', 'regon', 'krs', 'pesel')
            if identifier in field_key
        ),
        None,
    )
    if identifier_kind is not None:
        if not re.fullmatch(r'\d(?:[\d\s.-]*\d)?', collapsed):
            raise ValueError('Identyfikator zawiera niedozwolone znaki')
        digits = re.sub(r'\D', '', collapsed)
        expected_lengths = {
            'nip': {10},
            'regon': {9, 14},
            'krs': {10},
            'pesel': {11},
        }
        if len(digits) not in expected_lengths[identifier_kind]:
            raise ValueError('Identyfikator ma niepoprawna dlugosc')
        return digits
    bank_account_markers = (
        'iban',
        'rachunek_bankowy',
        'bankowy_rachunek',
        'konto_bankowe',
        'bankowe_konto',
        'konta_bankowego',
        'rachunku_bankowego',
        'numer_konta_bankowego',
        'numer_rachunku_bankowego',
    )
    if any(marker in field_key for marker in bank_account_markers):
        if not re.fullmatch(r'[A-Za-z0-9](?:[A-Za-z0-9\s-]*[A-Za-z0-9])?', collapsed):
            raise ValueError('Numer rachunku zawiera niedozwolone znaki')
        account = re.sub(r'[\s-]+', '', collapsed).upper()
        is_local_account = bool(re.fullmatch(r'\d{16,34}', account))
        is_iban = bool(re.fullmatch(r'[A-Z]{2}\d{2}[A-Z0-9]{11,30}', account))
        if not is_local_account and not is_iban:
            raise ValueError('Numer rachunku ma niepoprawny format')
        return account
    return collapsed


def _normalize_field_value(value: str, field_type: str, field_key: str) -> str:
    if field_type == 'number':
        return _normalize_number(value)
    if field_type == 'date':
        return _normalize_date(value)
    return _normalize_text(value, field_key)


