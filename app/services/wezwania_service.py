"""
Serwis do zarządzania wezwaniami do zapłaty.
Zapisuje i pobiera wezwania z folderu output/wezwania/.
"""

import os
import json
import uuid
from datetime import datetime


def get_wezwania_dir():
    """Zwraca ścieżkę do folderu z wezwaniami."""
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    wezwania_dir = os.path.join(project_root, "output", "wezwania")
    os.makedirs(wezwania_dir, exist_ok=True)
    return wezwania_dir


def save_wezwanie(data: dict) -> dict:
    """
    Zapisuje wezwanie do zapłaty.
    
    Args:
        data: Słownik z danymi wezwania (pola formularza)
        
    Returns:
        Słownik z id i ścieżką do zapisanego pliku
    """
    wezwanie_id = str(uuid.uuid4())[:8]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Pobierz dane dłużnika do nazwy pliku
    dluznik = data.get('dluznik_nazwa', 'nieznany')
    dluznik_clean = "".join(c for c in dluznik if c.isalnum() or c in (' ', '-', '_')).strip()[:30]
    
    filename = f"wezwanie_{timestamp}_{dluznik_clean}_{wezwanie_id}.json"
    
    wezwanie_data = {
        'id': wezwanie_id,
        'created_at': datetime.now().isoformat(),
        'fields': data
    }
    
    filepath = os.path.join(get_wezwania_dir(), filename)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(wezwanie_data, f, ensure_ascii=False, indent=2)
    
    return {
        'success': True,
        'id': wezwanie_id,
        'filename': filename,
        'filepath': filepath
    }


def get_all_wezwania() -> list:
    """
    Zwraca listę wszystkich zapisanych wezwań.
    
    Returns:
        Lista słowników z podstawowymi informacjami o wezwaniach
    """
    wezwania_dir = get_wezwania_dir()
    wezwania = []
    
    for filename in os.listdir(wezwania_dir):
        if filename.endswith('.json') and filename.startswith('wezwanie_'):
            filepath = os.path.join(wezwania_dir, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                fields = data.get('fields', {})
                wezwania.append({
                    'id': data.get('id'),
                    'filename': filename,
                    'created_at': data.get('created_at'),
                    'dluznik_nazwa': fields.get('dluznik_nazwa_pelna', fields.get('dluznik_nazwa', 'Nieznany')),
                    'dluznik_adres': fields.get('dluznik_adres_pelny', fields.get('dluznik_adres', '')),
                    'kwota': fields.get('platnosc_kwota_glowna', '0'),
                    'faktura_numer': fields.get('faktura_numer_referencyjny', '')
                })
            except Exception as e:
                print(f"Błąd odczytu {filename}: {e}")
    
    # Sortuj od najnowszych
    wezwania.sort(key=lambda x: x.get('created_at', ''), reverse=True)
    
    return wezwania



def get_wezwanie(wezwanie_id: str) -> dict:
    """
    Pobiera szczegóły wezwania po ID.
    
    Args:
        wezwanie_id: ID wezwania
        
    Returns:
        Słownik z pełnymi danymi wezwania lub None
    """
    wezwania_dir = get_wezwania_dir()
    
    for filename in os.listdir(wezwania_dir):
        if filename.endswith('.json') and wezwanie_id in filename:
            filepath = os.path.join(wezwania_dir, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Błąd odczytu {filename}: {e}")
                return None
    
    return None


def get_wezwania_by_ids(ids: list) -> list:
    """
    Pobiera wiele wezwań po liście ID.
    
    Args:
        ids: Lista ID wezwań
        
    Returns:
        Lista słowników z danymi wezwań
    """
    wezwania = []
    for wezwanie_id in ids:
        wezwanie = get_wezwanie(wezwanie_id)
        if wezwanie:
            wezwania.append(wezwanie)
    return wezwania


def calculate_summary(wezwania: list) -> dict:
    """
    Oblicza podsumowanie z wielu wezwań (suma kwot, lista faktur).
    
    Args:
        wezwania: Lista wezwań
        
    Returns:
        Słownik z podsumowaniem
    """
    total_amount = 0.0
    invoices = []
    
    for wezwanie in wezwania:
        fields = wezwanie.get('fields', {})
        
        # Parsuj kwotę
        kwota_str = fields.get('platnosc_kwota_glowna', '0')
        kwota_str = kwota_str.replace(' zł', '').replace(' ', '').replace(',', '.')
        try:
            kwota = float(kwota_str)
            total_amount += kwota
        except ValueError:
            pass
        
        # Zbierz dane faktury
        invoices.append({
            'numer': fields.get('faktura_numer_referencyjny', ''),
            'data': fields.get('faktura_data_wystawienia', ''),
            'kwota': fields.get('platnosc_kwota_glowna', ''),
            'termin': fields.get('platnosc_data_odsetek', '')
        })
    
    return {
        'total_amount': total_amount,
        'total_amount_formatted': f"{total_amount:,.2f}".replace(',', ' ').replace('.', ',') + ' zł',
        'invoices': invoices,
        'count': len(wezwania)
    }
