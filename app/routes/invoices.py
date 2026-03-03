"""
Endpointy API do batch-przetwarzania faktur.
Każda faktura przetwarzana jest osobno przez LLM,
wyniki zapisywane do output/wezwania_faktury/.
"""

import os
import json
from datetime import datetime
from flask import Blueprint, request, jsonify, current_app

from app.services.llm_service import extract_template_fields
from app.utils.helpers import parse_kwota, find_field

invoices_bp = Blueprint('invoices', __name__)


# ============================================================
# Endpoint: POST /api/process_multiple_invoices
# ============================================================

@invoices_bp.route('/api/process_multiple_invoices', methods=['POST'])
def process_multiple_invoices():
    """
    Przetwarza wiele plików JSON — każdą fakturę osobno przez LLM.
    Wyniki zapisywane są do output/wezwania_faktury/.
    
    Oczekuje JSON: { "files": ["plik1.json", ...], "fields": ["pole1", ...] }
    Zwraca JSON:   { "success": true, "results": [...], "invoices": [...],
                     "common_data": {...}, "total_amount": "0.00" }
    """
    print("Wywołano funkcję: process_multiple_invoices")
    data = request.get_json()

    # Walidacja danych wejściowych
    if not data or 'files' not in data or not data['files']:
        return jsonify({'success': False, 'error': 'Brak plików'}), 400

    if 'fields' not in data or not data['fields']:
        return jsonify({'success': False, 'error': 'Brak pól do ekstrakcji'}), 400

    files = data['files']
    fields = data['fields']
    model_name = data.get('model')

    # Folder na wyniki faktur
    output_dir = os.path.join(current_app.config['OUTPUT_FOLDER'], 'wezwania_faktury')
    os.makedirs(output_dir, exist_ok=True)

    results = []       # Status przetwarzania każdego pliku
    all_invoices = []   # Zebrane dane faktur (numer, kwota, termin)
    common_data = {}    # Wspólne dane (wierzyciel, dłużnik) — z pierwszej faktury

    for filename in files:
        json_path = os.path.join(current_app.config['OUTPUT_FOLDER'], filename)
        if not os.path.exists(json_path):
            continue

        pass  # usuniety print

        # Przetwórz każdy plik osobno przez LLM
        result = extract_template_fields([json_path], fields, model=model_name)

        if result.get('success'):
            invoice_data = result.get('fields', {})

            # Zapisz wynik do osobnego pliku JSON
            invoice_result = _save_invoice_result(filename, invoice_data, output_dir)
            pass  # usuniety print

            # Wyciągnij kluczowe dane faktury (numer, kwota, termin)
            invoice_info = _extract_invoice_summary(filename, invoice_data)
            all_invoices.append(invoice_info)

            # Zapamiętaj wspólne dane z pierwszej faktury (wierzyciel, dłużnik)
            if not common_data:
                common_data = {k: v for k, v in invoice_data.items()
                              if not k.startswith('faktura_') and not k.startswith('platnosc_')}

            results.append({
                'file': filename,
                'output': invoice_result['output_filename'],
                'success': True
            })
        else:
            results.append({
                'file': filename,
                'success': False,
                'error': result.get('error', 'Nieznany błąd')
            })

    # Oblicz łączną sumę kwot ze wszystkich faktur
    total = _calculate_total(all_invoices)

    return jsonify({
        'success': True,
        'results': results,
        'invoices': all_invoices,
        'common_data': common_data,
        'total_amount': f"{total:.2f}",
        'output_folder': 'wezwania_faktury'
    })


# ============================================================
# Funkcje pomocnicze
# ============================================================

def _save_invoice_result(filename: str, invoice_data: dict, output_dir: str) -> dict:
    """
    Zapisuje wynik ekstrakcji faktury do pliku JSON.
    
    Args:
        filename: Nazwa pliku źródłowego
        invoice_data: Wyekstrahowane dane faktury
        output_dir: Folder docelowy
        
    Returns:
        Słownik z nazwą i ścieżką pliku wyjściowego
    """
    print("Wywołano funkcję: _save_invoice_result")
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    base_name = os.path.splitext(filename)[0]
    output_filename = f"faktura_{base_name}_{timestamp}.json"
    output_path = os.path.join(output_dir, output_filename)

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump({
            'source_file': filename,
            'extracted_data': invoice_data
        }, f, ensure_ascii=False, indent=2)

    return {'output_filename': output_filename, 'output_path': output_path}


def _extract_invoice_summary(filename: str, invoice_data: dict) -> dict:
    """
    Wyciąga kluczowe pola z danych faktury do podsumowania.
    Używa elastycznego wyszukiwania kluczy (find_field) bo LLM
    może zwracać klucze z drobnymi różnicami w pisowni.
    
    Args:
        filename: Nazwa pliku źródłowego
        invoice_data: Wyekstrahowane dane faktury
        
    Returns:
        Słownik z: source, numer, data, kwota, termin
    """
    print("Wywołano funkcję: _extract_invoice_summary")
    # Szukaj kwoty — LLM może użyć różnych wariantów nazwy klucza
    kwota_val = (find_field(invoice_data, 'kwote_do_zaplaty')
                 or find_field(invoice_data, 'kwota_do_zaplaty')
                 or find_field(invoice_data, 'kwoty_do_zaplaty'))

    return {
        'source': filename,
        'numer': find_field(invoice_data, 'numer_faktury'),
        'data': find_field(invoice_data, 'date_wystawienia'),
        'kwota': kwota_val,
        'termin': find_field(invoice_data, 'terminu_platnosci')
    }


def _calculate_total(invoices: list) -> float:
    """
    Sumuje kwoty ze wszystkich faktur.
    Używa parse_kwota() do obsługi różnych formatów kwot.
    
    Args:
        invoices: Lista słowników z polem 'kwota'
        
    Returns:
        Łączna suma jako float
    """
    print("Wywołano funkcję: _calculate_total")
    total = 0.0
    for inv in invoices:
        total += parse_kwota(inv.get('kwota', '0'))
    return total
