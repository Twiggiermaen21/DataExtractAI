import os
import json
import uuid
from datetime import datetime

import logging

log = logging.getLogger(__name__)

# Mapowanie długich nazw pól z szablonu na krótkie nazwy
FIELD_NAME_MAP = {
    'Znajdz_na_fakturze_pelna_nazwa_firmy_sprzedawcy_czyli_wierzyciela_wraz_z_forma_prawna_np_Spolka_Akcyjna_czesto_na_gorze_faktury': 'wierzyciel_nazwa',
    'Znajdz_na_fakturze_pelny_adres_sprzedawcy_zawierajacy_tylko_ulice_numer_domu_kod_pocztowy_i_miasto': 'wierzyciel_adres',
    'Znajdz_na_fakturze_pelny_adres_sprzedawcy_wierzyciela_zawierajacy_ulice_numer_domu_kod_pocztowy_i_miasto': 'wierzyciel_adres',
    'Znajdz_na_fakturze_numer_NIP_sprzedawcy_wierzyciela_bez_myslnikow_i_spacji': 'wierzyciel_nip',
    'Znajdz_na_fakturze_pelna_nazwa_firmy_nabywcy_czyli_dluznika_ktory_ma_zaplacic_za_towar_lub_usluge': 'dluznik_nazwa',
    'Znajdz_na_fakturze_dokladny_adres_siedziby_nabywcy_dluznika_ulica_kod_miasto': 'dluznik_adres',
    'Znajdz_na_fakturze_numer_NIP_nabywcy_dluznika_jesli_jest_podany': 'dluznik_nip',
    'Znajdz_i_przepisz_numer_faktury_ktorej_dotyczy_to_wezwanie_do_zaplaty': 'faktura_numer',
    'Znajdz_na_fakturze_date_wystawienia_dokumentu_lub_date_sprzedazy': 'faktura_data_wystawienia',
    'Znajdz_na_fakturze_koncowa_kwote_do_zaplaty_opisana_czesto_jako_Razem_lub_Do_zaplaty_brutto_wraz_z_waluta': 'kwota_do_zaplaty',
    'Znajdz_na_fakturze_date_terminu_platnosci_od_ktorej_beda_liczone_odsetki': 'termin_platnosci',
    'Znajdz_numer_konta_bankowego_na_ktory_ma_zostac_dokonana_wplata_zazwyczaj_na_dole_faktury': 'numer_konta',
    'Znajdz_nazwe_banku_wierzyciela_jesli_jest_podana_obok_numeru_konta': 'nazwa_banku',
}


def _remap_fields(data: dict) -> dict:
    """Zamienia długie nazwy pól z szablonu na krótkie, czytelne nazwy."""
    remapped = {}
    for key, value in data.items():
        if not value or str(value).strip() == '':
            continue
        short_name = FIELD_NAME_MAP.get(key, key)
        if short_name not in remapped:
            remapped[short_name] = value
    return remapped


def get_wezwania_dir():
    """Zwraca ścieżkę do folderu z wezwaniami (tworzy jeśli nie istnieje)."""
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    wezwania_dir = os.path.join(project_root, "output", "wezwania")
    os.makedirs(wezwania_dir, exist_ok=True)
    return wezwania_dir


def save_wezwanie(data: dict) -> dict:
    data = _remap_fields(data)
    wezwanie_id = str(uuid.uuid4())[:8]

    dluznik = data.get('dluznik_nazwa') or data.get('dluznik_nazwa_pelna') or 'nieznany'
    dluznik_clean = "".join(c for c in dluznik if c.isalnum() or c in (' ', '-', '_')).strip()[:40]
    dluznik_clean = dluznik_clean.replace(' ', '_')

    filename = f"wezwanie_do_zaplaty_{dluznik_clean}_{wezwanie_id}.json"
    wezwanie_data = {
        'id': wezwanie_id,
        'created_at': datetime.now().isoformat(),
        'fields': data,
    }

    filepath = os.path.join(get_wezwania_dir(), filename)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(wezwanie_data, f, ensure_ascii=False, indent=2)

    return {'success': True, 'id': wezwanie_id, 'filename': filename, 'filepath': filepath}


def get_all_wezwania() -> list:
    wezwania_dir = get_wezwania_dir()
    wezwania = []

    for filename in os.listdir(wezwania_dir):
        if not (filename.endswith('.json') and filename.startswith('wezwanie_do_zaplaty_')):
            continue
        filepath = os.path.join(wezwania_dir, filename)
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)

            fields = data.get('fields', {})

            dluznik_nazwa = (
                fields.get('dluznik_nazwa')
                or fields.get('Znajdz_na_fakturze_pelna_nazwa_firmy_nabywcy_czyli_dluznika_ktory_ma_zaplacic_za_towar_lub_usluge')
                or 'Nieznany'
            )
            dluznik_adres = (
                fields.get('dluznik_adres')
                or fields.get('Znajdz_na_fakturze_dokladny_adres_siedziby_nabywcy_dluznika_ulica_kod_miasto')
                or ''
            )
            faktura_numer = (
                fields.get('faktura_numer')
                or fields.get('Znajdz_i_przepisz_numer_faktury_ktorej_dotyczy_to_wezwanie_do_zaplaty')
                or ''
            )
            kwota = (
                fields.get('kwota_do_zaplaty')
                or fields.get('Znajdz_na_fakturze_koncowa_kwote_do_zaplaty_opisana_czesto_jako_Razem_lub_Do_zaplaty_brutto_wraz_z_waluta')
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
                'fields': fields,
            })
        except Exception:
            log.exception("Błąd odczytu wezwania: %s", filename)

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
            except Exception:
                return None
    return None


def get_wezwania_by_ids(ids: list) -> list:
    return [w for wid in ids if (w := get_wezwanie(wid)) is not None]


def calculate_summary(wezwania: list) -> dict:
    total_amount = 0.0
    invoices = []

    for wezwanie in wezwania:
        fields = wezwanie.get('fields', {})
        kwota_str = fields.get('kwota_do_zaplaty') or fields.get('platnosc_kwota_glowna', '0')
        kwota_str = kwota_str.replace(' zł', '').replace(' ', '').replace(',', '.')
        try:
            total_amount += float(kwota_str)
        except ValueError:
            pass

        invoices.append({
            'numer': fields.get('faktura_numer') or fields.get('faktura_numer_referencyjny', ''),
            'data': fields.get('faktura_data_wystawienia', ''),
            'kwota': fields.get('kwota_do_zaplaty') or fields.get('platnosc_kwota_glowna', ''),
            'termin': fields.get('termin_platnosci') or fields.get('platnosc_data_odsetek', ''),
        })

    return {
        'total_amount': total_amount,
        'total_amount_formatted': f"{total_amount:,.2f}".replace(',', ' ').replace('.', ',') + ' zł',
        'invoices': invoices,
        'count': len(wezwania),
    }
