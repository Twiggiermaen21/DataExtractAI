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
   
    wezwanie_id = str(uuid.uuid4())[:8]
    
    # Pobierz dane dłużnika (pozwanego) do nazwy pliku
    dluznik = (data.get('Znajdz_na_fakturze_pelna_nazwa_firmy_nabywcy_czyli_dluznika_ktory_ma_zaplacic_za_towar_lub_usluge') 
               or data.get('dluznik_nazwa') 
               or data.get('dluznik_nazwa_pelna')
               or 'nieznany')
    # Oczyść nazwę - zostaw tylko dozwolone znaki
    dluznik_clean = "".join(c for c in dluznik if c.isalnum() or c in (' ', '-', '_')).strip()[:40]
    dluznik_clean = dluznik_clean.replace(' ', '_')
    
    filename = f"wezwanie_do_zaplaty_{dluznik_clean}_{wezwanie_id}.json"
    
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
   
    wezwania_dir = get_wezwania_dir()
    wezwania = []
    
    for filename in os.listdir(wezwania_dir):
        if filename.endswith('.json') and filename.startswith('wezwanie_do_zaplaty_'):
            filepath = os.path.join(wezwania_dir, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                fields = data.get('fields', {})
                
                # Pobierz dane z długich nazw kluczy lub z uproszczonych
                dluznik_nazwa = (
                    fields.get('Znajdz_na_fakturze_pelna_nazwa_firmy_nabywcy_czyli_dluznika_ktory_ma_zaplacic_za_towar_lub_usluge')
                    or fields.get('dluznik_nazwa_pelna')
                    or fields.get('dluznik_nazwa')
                    or 'Nieznany'
                )
                dluznik_adres = (
                    fields.get('Znajdz_na_fakturze_dokladny_adres_siedziby_nabywcy_dluznika_ulica_kod_miasto')
                    or fields.get('dluznik_adres_pelny')
                    or fields.get('dluznik_adres')
                    or ''
                )
                faktura_numer = (
                    fields.get('Znajdz_i_przepisz_numer_faktury_ktorej_dotyczy_to_wezwanie_do_zaplaty')
                    or fields.get('faktura_numer_referencyjny')
                    or ''
                )
                kwota = (
                    fields.get('Znajdz_na_fakturze_koncowa_kwote_do_zaplaty_opisana_czesto_jako_Razem_lub_Do_zaplaty_brutto_wraz_z_waluta')
                    or fields.get('platnosc_kwota_glowna')
                    or '0'
                )
                
                wezwania.append({
                    'id': data.get('id'),
                    'filename': filename,
                    'created_at': data.get('created_at'),
                    'dluznik_nazwa': dluznik_nazwa,
                    'dluznik_adres': dluznik_adres,
                    'kwota': kwota,
                    'faktura_numer': faktura_numer,
                    'fields': fields  # Dodaj pełne fields dla pozwu
                })
            except Exception as e:
                print(f"Błąd odczytu {filename}: {e}")
    
    # Sortuj od najnowszych
    wezwania.sort(key=lambda x: x.get('created_at', ''), reverse=True)
    
    return wezwania



def get_wezwanie(wezwanie_id: str) -> dict:
   
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

    wezwania = []
    for wezwanie_id in ids:
        wezwanie = get_wezwanie(wezwanie_id)
        if wezwanie:
            wezwania.append(wezwanie)
    return wezwania


def calculate_summary(wezwania: list) -> dict:
   
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
