import streamlit as st
import os
import json
import re
from jinja2 import Template

# Importy Twoich funkcji
from ocr_function import przetworz_dokument
from szablony import BIBLIOTEKA_SZABLONOW

st.set_page_config(page_title="OCR & Generator", layout="wide")
st.title("🗃️ System Obsługi Faktur")

# --- KONFIGURACJA FOLDERÓW ---
UPLOAD_FOLDER = "input"
OUTPUT_ROOT = "output"

# Upewniamy się, że foldery istnieją
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_ROOT, exist_ok=True)

# --- TWORZENIE ZAKŁADEK ---
tab1, tab2 = st.tabs(["📥 1. Pobieranie danych (OCR)", "📝 2. Generuj pismo"])

# =========================================================
# ZAKŁADKA 1: SKANOWANIE
# =========================================================
with tab1:
    st.header("Wgraj fakturę i uruchom OCR")
    
    uploaded_file = st.file_uploader("Wybierz plik faktury", key="ocr_upload")

    if uploaded_file is not None:
        file_path = os.path.join(UPLOAD_FOLDER, uploaded_file.name)
        
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        col_img, col_action = st.columns([1, 2])
        
        with col_img:
            st.image(uploaded_file, width=300, caption="Podgląd pliku")
        
        with col_action:
            st.info(f"Plik zapisano w: `{file_path}`")
            st.divider()
            
            nazwa_bez_ext = os.path.splitext(uploaded_file.name)[0]
            folder_dla_tego_pliku = os.path.join(OUTPUT_ROOT, f"output_{nazwa_bez_ext}")
            
            if st.button("🚀 Uruchom przetwarzanie OCR", type="primary"):
                with st.spinner("Model AI analizuje dokument..."):
                    wynik = przetworz_dokument(file_path, folder_wynikowy=folder_dla_tego_pliku)
                    
                    st.success("Gotowe!")
                    st.write(f"📂 Wyniki zapisano w folderze: `{folder_dla_tego_pliku}`")
                    st.json({"Status": "OK", "Folder": folder_dla_tego_pliku})


# =========================================================
# ZAKŁADKA 2: GENEROWANIE PISMA
# =========================================================
with tab2:
    st.header("Generowanie pisma na podstawie wyników")

    # 1. Przeszukujemy folder 'output'
    json_files = []
    for root, dirs, files in os.walk(OUTPUT_ROOT):
        for file in files:
            if file.endswith(".json"):
                json_files.append(os.path.join(root, file))

    if not json_files:
        st.warning("Nie znaleziono żadnych plików JSON. Najpierw przetwórz fakturę w zakładce 1.")
    else:
        col_sel1, col_sel2 = st.columns(2)
        with col_sel1:
            wybrany_plik_json = st.selectbox("1. Wybierz wynik OCR (plik JSON):", json_files)
        with col_sel2:
            wybrany_szablon = st.selectbox("2. Wybierz szablon pisma:", list(BIBLIOTEKA_SZABLONOW.keys()))

        st.divider()

       # 2. Wczytanie danych z JSON (POPRAWIONE)
        tekst_z_faktury = ""
        
        if wybrany_plik_json:
            try:
                with open(wybrany_plik_json, "r", encoding="utf-8") as f:
                    zawartosc = json.load(f)
                    
                    # --- LOGIKA EKSTRAKCJI TEKSTU ---
                    # Zamiast zamieniać całość na string, wyciągamy tylko pola tekstowe.
                    # Ignorujemy 'input_path', 'model_settings' itp.
                    
                    # Wariant 1: Struktura PaddleOCRVL (którą pokazywałeś wcześniej)
                    if isinstance(zawartosc, dict) and "parsing_res_list" in zawartosc:
                        print(">>> Wykryto strukturę PaddleOCRVL")
                        lista_blokow = zawartosc["parsing_res_list"]
                        for blok in lista_blokow:
                            # Pobieramy tylko 'block_content' (treść)
                            tresc = blok.get("block_content", "")
                            if tresc:
                                tekst_z_faktury += tresc + "\n"
                                
                    # Wariant 2: Standardowy PaddleOCR (lista list)
                    elif isinstance(zawartosc, list):
                        print(">>> Wykryto listę (standardowy OCR)")
                        # Często struktura to [ [box, (text, score)], ... ]
                        for element in zawartosc:
                            # Próba wyciągnięcia tekstu z różnych dziwnych struktur
                            if isinstance(element, dict) and "rec_text" in element:
                                tekst_z_faktury += element["rec_text"] + "\n"
                            else:
                                tekst_z_faktury += str(element) + "\n"
                    
                    # Wariant 3: Ostateczność (jeśli struktura jest inna)
                    else:
                        print(">>> Struktura nieznana, używam surowego zrzutu (ryzyko błędów)")
                        tekst_z_faktury = str(zawartosc)

            except Exception as e:
                st.error(f"Błąd odczytu JSON: {e}")

        # 3. Automatyczne szukanie danych (Regex)
        znalezione_dane = {"nr_faktury": "", "data": "", "kwota": "", "nip": ""}
        
        if tekst_z_faktury:
            # A. Szukanie NR FAKTURY
            fv_match = re.search(r'Faktura\s*(?:VAT)?\s*(?:nr\.?|numer)?\s*[:.]?\s*(\S+)', tekst_z_faktury, re.IGNORECASE)
            if fv_match: 
                ciag = fv_match.group(1)
                # Prosta walidacja, czy nie złapaliśmy śmiecia
                if len(ciag) > 1 and ciag.lower() not in ['nr', 'numer', 'vat', 'data']:
                    znalezione_dane['nr_faktury'] = ciag

            # B. Szukanie KWOTY (Największa liczba po słowie "Razem")
            mozliwe_kwoty = re.findall(r'Razem.{0,40}?(\d[\d\s\.]*[,.]\d{2})', tekst_z_faktury, re.IGNORECASE)
            
            liczby = []
            for k in mozliwe_kwoty:
                # Zamiana: "1 230,50" -> 1230.50
                clean = k.replace(' ', '').replace('\xa0', '').replace(',', '.')
                # Usuwanie nadmiarowych kropek (np. 1.000.00 -> 1000.00)
                if clean.count('.') > 1:
                    clean = clean.replace('.', '', clean.count('.') - 1)
                try:
                    liczby.append(float(clean))
                except:
                    pass
            
            if liczby:
                max_kwota = max(liczby)
                znalezione_dane['kwota'] = f"{max_kwota:.2f}".replace('.', ',') + " PLN"

            # C. Szukanie NIP
            nip_match = re.search(r'\d{3}[-\s]?\d{3}[-\s]?\d{2}[-\s]?\d{2}', tekst_z_faktury)
            if nip_match: znalezione_dane['nip'] = nip_match.group(0)
            
            # D. Szukanie DATY
            data_match = re.search(r'\d{4}[-.]\d{2}[-.]\d{2}|\d{2}[-.]\d{2}[-.]\d{4}', tekst_z_faktury)
            if data_match: znalezione_dane['data'] = data_match.group(0)

        # 4. Formularz edycji
        st.subheader("3. Zweryfikuj dane")
        with st.form("formularz_generowania"):
            c1, c2 = st.columns(2)
            with c1:
                input_nr_fv = st.text_input("Numer faktury", value=znalezione_dane['nr_faktury'])
                input_data = st.text_input("Data faktury", value=znalezione_dane['data'])
                input_kwota = st.text_input("Kwota (Brutto)", value=znalezione_dane['kwota'])
            with c2:
                input_nip = st.text_input("NIP Dłużnika", value=znalezione_dane['nip'])
                input_dluznik = st.text_input("Nazwa Dłużnika", value="Do uzupełnienia...")
                input_wierzyciel = st.text_input("Wierzyciel (Ty)", value="Moja Firma Sp. z o.o.")

            submit_btn = st.form_submit_button("🖨️ Generuj Dokument")

            if submit_btn:
                context = {
                    "nr_faktury": input_nr_fv,
                    "data_faktury": input_data,
                    "kwota_brutto": input_kwota,
                    "wierzyciel_nip": "TWÓJ NIP",
                    "wierzyciel_nazwa": input_wierzyciel,
                    "dluznik_nazwa": input_dluznik,
                    "dluznik_adres": "Adres...",
                    "miasto": "Warszawa",
                    "data_biezaca": "2026-01-08",
                    "nr_konta": "00 0000 0000...",
                    "nazwa_banku": "Bank..."
                }

                szablon_str = BIBLIOTEKA_SZABLONOW[wybrany_szablon]
                tm = Template(szablon_str)
                gotowy_tekst = tm.render(context)

                st.success("Dokument wygenerowany!")
                st.text_area("Podgląd:", gotowy_tekst, height=300)
                st.download_button("Pobierz .txt", gotowy_tekst, file_name="pismo.txt")