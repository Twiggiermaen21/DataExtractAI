import os
import re
import json
import logging
from io import BytesIO

import openpyxl
from openpyxl.styles import PatternFill, Font, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from flask import Blueprint, request, jsonify, current_app, send_file

excel_export_bp = Blueprint('excel_export', __name__)
log = logging.getLogger(__name__)

# Kolejność i etykiety wszystkich możliwych kolumn
COLUMN_DEFS = [
    ("sprzedawca",              "Sprzedawca",                False),
    ("data_wystawienia",        "Data wystawienia",           False),
    ("data_sprzedazy",          "Data sprzedaży",             False),
    ("wolumen_energii",         "Wolumen energii [kWh]",      True),
    ("kwota_netto",             "Kwota netto [zł]",           True),
    ("kwota_brutto",            "Kwota brutto [zł]",          True),
    ("kwota_vat",               "Kwota VAT [zł]",             True),
    ("sprzedaz_cena_netto",     "Sprzedaż netto [zł]",        True),
    ("sprzedaz_cena_brutto",    "Sprzedaż brutto [zł]",       True),
    ("dystrybucja_cena_netto",  "Dystrybucja netto [zł]",     True),
    ("dystrybucja_cena_brutto", "Dystrybucja brutto [zł]",    True),
    ("oplata_oze",              "Opłata OZE [zł]",            True),
    ("oplata_kogeneracyjna",    "Opłata kogeneracyjna [zł]",  True),
    ("naleznos_netto",          "Należność netto [zł]",       True),
    ("naleznos_brutto",         "Należność brutto [zł]",      True),
]

# Indeksy (key → (label, is_numeric))
COLUMN_MAP = {k: (label, numeric) for k, label, numeric in COLUMN_DEFS}


def _to_number(value):
    """Zwraca float z wartości która może zawierać jednostki (kWh, zł itp.)."""
    if value is None:
        return None
    s = str(value).strip()
    # Usuń jednostki na końcu
    s = re.sub(r'[\s\u00a0]*[a-zA-ZłzłŁZŁ%]+[\s\u00a0]*$', '', s).strip()
    # Usuń spacje i &nbsp; wewnątrz liczby
    s = s.replace('\u00a0', '').replace(' ', '')
    # Polski format: 1.234,56 → 1234.56
    if ',' in s and '.' in s:
        s = s.replace('.', '').replace(',', '.')
    elif ',' in s:
        s = s.replace(',', '.')
    try:
        return float(s)
    except (ValueError, TypeError):
        return None


def _find_json(output_dir, filename):
    """Szuka pliku JSON w OUTPUT_FOLDER i podfolderze wezwania_faktury."""
    for candidate in [
        os.path.join(output_dir, filename),
        os.path.join(output_dir, 'wezwania_faktury', filename),
    ]:
        if os.path.exists(candidate):
            return candidate

    # Fallback: szukaj po nazwie bazowej
    base = os.path.splitext(filename)[0]
    for f in os.listdir(output_dir):
        if f.endswith('.json') and base in f:
            return os.path.join(output_dir, f)
    return None


@excel_export_bp.route('/api/export_excel', methods=['POST'])
def export_excel():
    data = request.get_json()
    if not data or not data.get('files'):
        return jsonify({'success': False, 'error': 'Brak plików do eksportu'}), 400

    files = data['files']
    # Kolumny wybrane przez użytkownika (opcjonalne — jeśli brak, bierzemy wszystkie)
    selected = data.get('selected_columns') or [k for k, _, _ in COLUMN_DEFS]
    output_dir = current_app.config['OUTPUT_FOLDER']

    # Wyznacz aktywne kolumny zachowując kolejność z COLUMN_DEFS
    active_cols = [(k, label, numeric)
                   for k, label, numeric in COLUMN_DEFS
                   if k in selected]

    if not active_cols:
        return jsonify({'success': False, 'error': 'Nie wybrano żadnych kolumn'}), 400

    records = []  # lista (dict_of_values, is_vision)

    for filename in files:
        json_path = _find_json(output_dir, filename)
        if not json_path:
            log.warning("Nie znaleziono JSON dla: %s", filename)
            continue
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                doc = json.load(f)

            fields = doc.get('extracted_fields') or doc.get('extracted_data') or doc.get('fields') or {}
            if isinstance(fields, str):
                try:
                    fields = json.loads(fields)
                except Exception:
                    fields = {}

            is_vision = doc.get('is_vision', False)
            source = doc.get('source_file', filename)

            row = {'_source': source}
            for col_id, _, is_numeric in active_cols:
                raw = fields.get(col_id)
                if is_numeric:
                    row[col_id] = _to_number(raw)
                else:
                    row[col_id] = str(raw) if raw is not None else ''

            records.append((row, is_vision))
        except Exception:
            log.exception("Błąd odczytu JSON: %s", json_path)

    if not records:
        return jsonify({'success': False, 'error': 'Nie znaleziono poprawnych danych do eksportu'}), 404

    # ── Budowanie pliku Excel ────────────────────────────────────────
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = 'Faktury Energia'

    # Style
    header_fill = PatternFill(fill_type='solid', fgColor='1F2937')   # ciemny nagłówek
    header_font = Font(bold=True, color='FFFFFF', size=10)
    scan_fill   = PatternFill(fill_type='solid', fgColor='FFF9C4')   # żółty dla skanów
    sum_fill    = PatternFill(fill_type='solid', fgColor='D1FAE5')   # zielony dla SUM
    sum_font    = Font(bold=True, size=10)
    center      = Alignment(horizontal='center', vertical='center')
    thin        = Side(style='thin', color='D1D5DB')
    border      = Border(left=thin, right=thin, top=thin, bottom=thin)

    # ── Nagłówek ────────────────────────────────────────────────────
    headers = ['Plik źródłowy'] + [label for _, label, _ in active_cols] + ['Skan?']
    for col_idx, h in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col_idx, value=h)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = center
        cell.border = border
    ws.row_dimensions[1].height = 22

    # ── Dane ────────────────────────────────────────────────────────
    for row_idx, (row, is_vision) in enumerate(records, 2):
        fill = scan_fill if is_vision else None

        # Plik źródłowy
        c = ws.cell(row=row_idx, column=1, value=row.get('_source', ''))
        c.border = border
        c.alignment = Alignment(vertical='center')
        if fill:
            c.fill = fill

        for col_offset, (col_id, _, is_numeric) in enumerate(active_cols, 2):
            val = row.get(col_id)
            c = ws.cell(row=row_idx, column=col_offset, value=val)
            c.border = border
            c.alignment = Alignment(horizontal='right' if is_numeric else 'left', vertical='center')
            if fill:
                c.fill = fill
            if is_numeric and val is not None:
                c.number_format = '#,##0.00'

        # Kolumna "Skan?"
        skan_col = len(active_cols) + 2
        c = ws.cell(row=row_idx, column=skan_col, value='TAK' if is_vision else '')
        c.border = border
        c.alignment = center
        if fill:
            c.fill = fill

    # ── Wiersz SUM ──────────────────────────────────────────────────
    data_rows = len(records)
    sum_row = data_rows + 2

    ws.cell(row=sum_row, column=1, value='SUMA').font = sum_font

    for col_offset, (col_id, _, is_numeric) in enumerate(active_cols, 2):
        c = ws.cell(row=sum_row, column=col_offset)
        if is_numeric:
            col_letter = get_column_letter(col_offset)
            c.value = f'=SUM({col_letter}2:{col_letter}{data_rows + 1})'
            c.number_format = '#,##0.00'
            c.font = sum_font
        c.fill = sum_fill
        c.border = border
        c.alignment = Alignment(horizontal='right', vertical='center')

    # SUM w ostatniej kolumnie (Skan?) — puste
    skan_col = len(active_cols) + 2
    ws.cell(row=sum_row, column=skan_col).fill = sum_fill

    # ── Ostrzeżenie o skanach ────────────────────────────────────────
    scan_count = sum(1 for _, is_vision in records if is_vision)
    if scan_count > 0:
        note_row = sum_row + 2
        note = ws.cell(
            row=note_row, column=1,
            value=f'⚠ {scan_count} plik(ów) to skany (żółte wiersze) — wyższe ryzyko błędu OCR. Zweryfikuj ręcznie.'
        )
        note.font = Font(color='B45309', italic=True, size=9)
        ws.merge_cells(
            start_row=note_row, start_column=1,
            end_row=note_row, end_column=len(headers)
        )

    # ── Autodopasowanie szerokości ───────────────────────────────────
    for col_idx in range(1, len(headers) + 1):
        col_letter = get_column_letter(col_idx)
        max_len = len(str(ws.cell(row=1, column=col_idx).value or ''))
        for row_idx in range(2, data_rows + 2):
            val = ws.cell(row=row_idx, column=col_idx).value
            if val is not None:
                max_len = max(max_len, len(str(val)))
        ws.column_dimensions[col_letter].width = min(max_len + 3, 40)

    ws.freeze_panes = 'A2'

    # ── Zapis do pamięci i wysyłka ───────────────────────────────────
    output = BytesIO()
    wb.save(output)
    output.seek(0)

    return send_file(
        output,
        as_attachment=True,
        download_name='raport_faktury_energia.xlsx',
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
