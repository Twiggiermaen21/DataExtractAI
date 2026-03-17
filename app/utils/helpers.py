"""
Współdzielone funkcje pomocnicze: parsowanie kwot, wyszukiwanie pól, obróbka adresów.
"""

import re


def parse_kwota(kwota_str: str) -> float:
    """Parsuje string z kwotą pieniężną na float. Zwraca 0.0 przy błędzie."""
    if not kwota_str:
        return 0.0
    cleaned = str(kwota_str).replace(',', '.').replace(' ', '').replace('zł', '')
    cleaned = ''.join(c for c in cleaned if c.isdigit() or c == '.')
    try:
        return float(cleaned) if cleaned else 0.0
    except ValueError:
        return 0.0


def find_field(data: dict, partial_key: str) -> str:
    """Szuka wartości po częściowym dopasowaniu klucza (case-insensitive)."""
    for key, value in data.items():
        if partial_key.lower() in key.lower():
            return value
    return ''


def extract_city_from_address(address: str) -> str:
    """Wyodrębnia miasto z adresu (po kodzie pocztowym XX-XXX)."""
    if not address:
        return ''
    match = re.search(r'\d{2}-\d{3}\s+(.+)', address)
    return match.group(1).strip() if match else ''


def extract_postal_code_city(address: str) -> str:
    """Wyodrębnia kod pocztowy + miasto z adresu."""
    if not address:
        return ''
    match = re.search(r'(\d{2}-\d{3}\s+\S+(?:\s+\S+)?)', address)
    return match.group(1).strip() if match else ''


def extract_postal_code(address: str) -> str:
    """Wyodrębnia sam kod pocztowy (XX-XXX) z adresu."""
    if not address:
        return ''
    match = re.search(r'\d{2}-\d{3}', address)
    return match.group(0) if match else address
