"""
Współdzielone funkcje pomocnicze używane w wielu routach.
Zawiera parsowanie kwot, wyszukiwanie w słownikach i obróbkę adresów.
"""

import re


def parse_kwota(kwota_str: str) -> float:
    """
    Parsuje string z kwotą pieniężną na liczbę float.
    Obsługuje formaty: "1 234,56 zł", "1234.56", "1 234,56" itp.
    
    Args:
        kwota_str: String z kwotą do sparsowania
        
    Returns:
        Wartość kwoty jako float, 0.0 jeśli nie udało się sparsować
    """
    print("Wywołano funkcję: parse_kwota")
    if not kwota_str:
        return 0.0
    
    # Usuń spacje, symbol waluty, zamień przecinek na kropkę
    cleaned = str(kwota_str).replace(',', '.').replace(' ', '').replace('zł', '')
    # Zostaw tylko cyfry i kropkę
    cleaned = ''.join(c for c in cleaned if c.isdigit() or c == '.')
    
    try:
        return float(cleaned) if cleaned else 0.0
    except ValueError:
        return 0.0


def find_field(data: dict, partial_key: str) -> str:
    """
    Szuka wartości w słowniku po częściowym dopasowaniu nazwy klucza.
    Przydatne gdy LLM zwraca klucze z drobnymi różnicami w pisowni.
    
    Args:
        data: Słownik z danymi
        partial_key: Fragment nazwy klucza do wyszukania (case-insensitive)
        
    Returns:
        Wartość pierwszego pasującego klucza lub pusty string
    """
    print("Wywołano funkcję: find_field")
    for key, value in data.items():
        if partial_key.lower() in key.lower():
            return value
    return ''


def extract_city_from_address(address: str) -> str:
    """
    Wyodrębnia nazwę miasta z polskiego adresu.
    Szuka wzorca: kod pocztowy (XX-XXX) + nazwa miasta.
    
    Args:
        address: Pełny adres z kodem pocztowym
        
    Returns:
        Nazwa miasta lub pusty string
    """
    print("Wywołano funkcję: extract_city_from_address")
    if not address:
        return ''
    
    match = re.search(r'\d{2}-\d{3}\s+(.+)', address)
    return match.group(1).strip() if match else ''


def extract_postal_code_city(address: str) -> str:
    """
    Wyodrębnia kod pocztowy + miasto z adresu.
    Szuka wzorca: "XX-XXX Miasto" (+ ewentualnie drugie słowo).
    
    Args:
        address: Pełny adres
        
    Returns:
        String "XX-XXX Miasto" lub pusty string
    """
    print("Wywołano funkcję: extract_postal_code_city")
    if not address:
        return ''
    
    match = re.search(r'(\d{2}-\d{3}\s+\S+(?:\s+\S+)?)', address)
    return match.group(1).strip() if match else ''


def extract_postal_code(address: str) -> str:
    """
    Wyodrębnia sam kod pocztowy (XX-XXX) z adresu.
    
    Args:
        address: String zawierający kod pocztowy
        
    Returns:
        Kod pocztowy lub oryginalny string jeśli nie znaleziono
    """
    print("Wywołano funkcję: extract_postal_code")
    if not address:
        return ''
    
    match = re.search(r'\d{2}-\d{3}', address)
    return match.group(0) if match else address
