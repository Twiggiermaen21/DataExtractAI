from fpdf import FPDF
import os

class PDF(FPDF):
    def header(self):
        # Opcjonalnie logo
        pass

    def footer(self):
        # --- KLUCZOWA POPRAWKA: RESET MARGINESÓW W STOPCE ---
        # Zapisujemy obecny lewy margines, żeby go nie zepsuć, jeśli stopka wywoła się w środku
        current_left_margin = self.l_margin
        
        # Ustawiamy standardowy margines dla stopki (np. 10mm)
        self.set_left_margin(10)
        
        self.set_y(-15)
        # Używamy tej samej czcionki co w reszcie dokumentu
        # Sprawdzamy, czy czcionka jest już zarejestrowana, żeby uniknąć błędu
        if 'PolskąCzcionka' in self.fonts:
             self.set_font('PolskąCzcionka', '', 8)
        else:
             self.set_font('Helvetica', '', 8)
             
        self.cell(0, 10, 'Wygenerowano automatycznie w systemie OCR Faktury', align='C')
        
        # Przywracamy margines, jaki był przed wejściem do stopki
        self.set_left_margin(current_left_margin)

def stworz_wezwanie_pdf(dane):
    pdf = PDF()
    pdf.add_page()

    # --- 1. ŁADOWANIE CZCIONKI (DejaVuSans lub inna Unicode) ---
    font_name = 'DejaVuSans.ttf' 
    
    # Sprawdzamy czy plik istnieje, jak nie to szukamy Arial
    if not os.path.exists(font_name):
        if os.path.exists('arial.ttf'):
            font_name = 'arial.ttf'
        else:
            # Krytyczny błąd - bez czcionki nie zrobimy polskich znaków
            # Tworzymy PDF z błędem zamiast wyrzucać wyjątek, żeby aplikacja nie padła
            pdf.set_font("Helvetica", size=14)
            pdf.cell(0, 10, "BŁĄD: Brak pliku czcionki (DejaVuSans.ttf) w folderze projektu!", ln=True)
            return pdf.output(dest='S')

    # Rejestracja czcionek
    pdf.add_font('PolskąCzcionka', '', font_name)
    pdf.add_font('PolskąCzcionka', 'B', font_name)
    pdf.set_font('PolskąCzcionka', '', 12)

    # --- 2. NAGŁÓWEK (Miejscowość) ---
    pdf.cell(0, 10, f"{dane.get('miasto', 'Warszawa')}, dnia {dane.get('data_biezaca', '')}", align='R', new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)

    # --- 3. WIERZYCIEL (Lewa strona) ---
    pdf.set_font('PolskąCzcionka', 'B', 12)
    pdf.cell(0, 6, "WIERZYCIEL:", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font('PolskąCzcionka', '', 12)
    pdf.cell(0, 6, dane.get('wierzyciel_nazwa', ''), new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, f"NIP: {dane.get('wierzyciel_nip', '')}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(10)

    # --- 4. DŁUŻNIK (Prawa strona) ---
    # Zmieniamy margines na 100mm (prawa połowa strony)
    pdf.set_left_margin(100)
    
    pdf.set_font('PolskąCzcionka', 'B', 12)
    # width=90 to bezpieczna szerokość (210mm strona - 100mm margines - 10mm prawy margines = 100mm)
    pdf.cell(90, 6, "DŁUŻNIK:", new_x="LMARGIN", new_y="NEXT")
    
    pdf.set_font('PolskąCzcionka', '', 12)
    
    # Używamy width=90 zamiast 0, żeby mieć pewność, że się zmieści
    dluznik_nazwa = dane.get('dluznik_nazwa', '')
    dluznik_adres = dane.get('dluznik_adres', '')
    
    pdf.multi_cell(90, 6, dluznik_nazwa)
    pdf.multi_cell(90, 6, dluznik_adres)
    pdf.cell(90, 6, f"NIP: {dane.get('dluznik_nip', '-')}", new_x="LMARGIN", new_y="NEXT")
    
    # --- PRZYWRACAMY MARGINES ---
    pdf.set_left_margin(10)
    pdf.ln(20)

    # --- 5. TREŚĆ PISMA ---
    pdf.set_font('PolskąCzcionka', 'B', 14)
    pdf.cell(0, 10, "PRZEDSĄDOWE WEZWANIE DO ZAPŁATY", align='C', new_x="LMARGIN", new_y="NEXT")
    pdf.ln(10)

    pdf.set_font('PolskąCzcionka', '', 11)
    
    kwota = dane.get('kwota_brutto', '0,00')
    nr_fv = dane.get('nr_faktury', 'brak')
    
    tresc = (
        f"W związku z upływem terminu płatności faktury VAT nr {nr_fv} "
        f"z dnia {dane.get('data_faktury', 'brak')}, wzywam do natychmiastowej zapłaty należności.\n\n"
        f"Kwota do zapłaty: {kwota} PLN\n\n"
        f"Płatności należy dokonać w terminie 7 dni od daty otrzymania niniejszego wezwania "
        f"na rachunek bankowy:\n"
        f"{dane.get('nazwa_banku', '')}\n"
        f"Nr konta: {dane.get('nr_konta', '')}\n\n"
        f"Brak wpłaty w wyznaczonym terminie spowoduje skierowanie sprawy na drogę postępowania sądowego, "
        f"co narazi Państwa na dodatkowe koszty procesowe oraz koszty zastępstwa procesowego."
    )
    
    pdf.multi_cell(0, 8, tresc)
    pdf.ln(20)

    # --- 6. PODPIS ---
    pdf.cell(0, 10, "Z poważaniem,", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(15)
    pdf.cell(0, 10, "." * 40, new_x="LMARGIN", new_y="NEXT")
    pdf.set_font('PolskąCzcionka', '', 10)
    pdf.cell(0, 5, "(Podpis wierzyciela)", new_x="LMARGIN", new_y="NEXT")

    return pdf.output(dest='S')