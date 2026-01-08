import streamlit as st
import os
import base64  # <--- BIBLIOTEKA DO PODGLĄDU (WBUDOWANA, NIE TRZEBA INSTALOWAĆ)
from jinja2 import Template
from datetime import datetime

# --- IMPORTY TWOICH MODUŁÓW ---
from ocr_function import przetworz_dokument       # Zakładka 1
from data_extractor import analyze_invoice_json   # Zakładka 2
from szablony import BIBLIOTEKA_SZABLONOW         # Szablony
from pdf_generator import stworz_wezwanie_pdf     # Generator PDF

st.set_page_config(page_title="OCR & Generator", layout="wide")
st.title("🗃️ System Obsługi Faktur")

# --- KONFIGURACJA ---
UPLOAD_FOLDER = "input"
OUTPUT_ROOT = "output"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_ROOT, exist_ok=True)

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
        
        c1, c2 = st.columns([1, 2])
        with c1:
            st.image(uploaded_file, width=300, caption="Podgląd")
        with c2:
            st.info(f"Plik: `{uploaded_file.name}`")
            nazwa_bez_ext = os.path.splitext(uploaded_file.name)[0]
            folder_out = os.path.join(OUTPUT_ROOT, f"output_{nazwa_bez_ext}")
            
            if st.button("🚀 Uruchom przetwarzanie OCR", type="primary"):
                with st.spinner("Analiza w toku..."):
                    res = przetworz_dokument(file_path, folder_wynikowy=folder_out)
                    st.success("Gotowe!")
                    st.write(f"Wyniki: `{folder_out}`")

# =========================================================
# ZAKŁADKA 2: GENEROWANIE PISMA
# =========================================================
with tab2:
    st.header("Kreator Pism (PDF)")

    # 1. Lista dostępnych wyników (JSON)
    json_files = []
    for root, _, files in os.walk(OUTPUT_ROOT):
        for file in files:
            if file.endswith(".json"):
                json_files.append(os.path.join(root, file))

    if not json_files:
        st.warning("Brak przetworzonych faktur. Wróć do zakładki 1.")
    else:
        col_sel1, col_sel2 = st.columns(2)
        with col_sel1:
            json_path = st.selectbox("1. Wybierz fakturę (JSON):", json_files)
        with col_sel2:
            # Wybór szablonu (dla PDF mamy jeden główny wzór w pdf_generator.py)
            szablon_key = st.selectbox("2. Wybierz typ pisma:", list(BIBLIOTEKA_SZABLONOW.keys()))

        st.divider()

        # 2. UŻYCIE PLIKU DO ANALIZY DANYCH
        dane_z_ocr = analyze_invoice_json(json_path)

        # 3. Formularz weryfikacji
        st.subheader("Uzupełnij dane do wezwania")
        
        with st.form("form_pisma"):
            st.caption("Dane z faktury")
            c1, c2 = st.columns(2)
            with c1:
                nr_fv = st.text_input("Numer faktury", value=dane_z_ocr.get("nr_faktury", ""))
                data_fv = st.text_input("Data wystawienia", value=dane_z_ocr.get("data", ""))
                kwota = st.text_input("Kwota brutto (PLN)", value=dane_z_ocr.get("kwota", ""))
            with c2:
                nip_dluznika = st.text_input("NIP Dłużnika", value=dane_z_ocr.get("nip", ""))
                dluznik_nazwa = st.text_input("Nazwa Dłużnika", value="Firma XYZ (do uzupełnienia)")
                dluznik_adres = st.text_input("Adres Dłużnika", value="ul. Przykładowa 1, 00-001 Miasto")

            st.caption("Twoje dane i płatność")
            c3, c4 = st.columns(2)
            with c3:
                wierzyciel = st.text_input("Wierzyciel (Twoja firma)", value="Moja Firma Sp. z o.o.")
                nip_wierzyciela = st.text_input("Twój NIP", value="525-000-00-00")
                miasto = st.text_input("Miasto sporządzenia", value="Warszawa")
            with c4:
                nazwa_banku = st.text_input("Nazwa banku", value="mBank S.A.")
                nr_konta = st.text_input("Numer konta", value="00 0000 0000 0000 0000 0000 0000")
                data_pisma = st.date_input("Data pisma", value=datetime.now())

            # Przycisk wysyłania formularza
            submitted = st.form_submit_button("🖨️ Generuj PDF")

        # --- LOGIKA PO WYSŁANIU (POZA FORMULARZEM) ---
        if submitted:
            # 1. Przygotowanie słownika danych dla generatora PDF
            dane_do_pdf = {
                "nr_faktury": nr_fv,
                "data_faktury": data_fv,
                "kwota_brutto": kwota,
                "wierzyciel_nazwa": wierzyciel,
                "wierzyciel_nip": nip_wierzyciela,
                "dluznik_nazwa": dluznik_nazwa,
                "dluznik_adres": dluznik_adres,
                "dluznik_nip": nip_dluznika,
                "miasto": miasto,
                "data_biezaca": str(data_pisma),
                "nr_konta": nr_konta,
                "nazwa_banku": nazwa_banku
            }

            # 2. Generowanie PDF (otrzymujemy bajty)
            try:
                pdf_bytes = stworz_wezwanie_pdf(dane_do_pdf)
                
                # 3. Wyświetlenie sukcesu
                st.success("✅ Pismo zostało wygenerowane poprawnie!")
                
                # 4. Przycisk pobierania PDF
                file_name_pdf = f"Wezwanie_{nr_fv.replace('/', '_')}.pdf"
                
                st.download_button(
                    label="⬇️ POBIERZ WEZWANIE (PDF)",
                    data=bytes(pdf_bytes),
                    file_name=file_name_pdf,
                    mime="application/pdf"
                )

                # --- 5. PODGLĄD PDF W PRZEGLĄDARCE (IFRAME) ---
                st.markdown("---")
                st.subheader("👀 Podgląd dokumentu")
                
                # Kodowanie bajtów PDF do formatu Base64
                base64_pdf = base64.b64encode(bytes(pdf_bytes)).decode('utf-8')
                
                # Tworzenie tagu HTML <iframe> z osadzonym PDF
                # height="800" ustala wysokość okna podglądu
                pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="800" type="application/pdf"></iframe>'
                
                # Wyświetlenie HTML w Streamlit
                st.markdown(pdf_display, unsafe_allow_html=True)
            
            except Exception as e:
                st.error(f"Wystąpił błąd podczas generowania PDF: {e}")
                st.info("Sprawdź, czy masz plik czcionki (np. DejaVuSans.ttf) w folderze projektu!")