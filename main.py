import streamlit as st
import os
from jinja2 import Template

# --- IMPORTY TWOICH MODUŁÓW ---
from ocr_function import przetworz_dokument      # Zakładka 1
from data_extractor import analyze_invoice_json  # Zakładka 2 (NOWOŚĆ)
from szablony import BIBLIOTEKA_SZABLONOW        # Szablony

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
    st.header("Kreator Pism")

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
            szablon_key = st.selectbox("2. Wybierz szablon:", list(BIBLIOTEKA_SZABLONOW.keys()))

        st.divider()

        # 2. UŻYCIE NOWEGO PLIKU DO ANALIZY DANYCH
        # To jedna linijka, która zastąpiła 50 linii kodu!
        dane_z_ocr = analyze_invoice_json(json_path)

        # 3. Formularz weryfikacji
        st.subheader("3. Zweryfikuj dane")
        with st.form("form_pisma"):
            c1, c2 = st.columns(2)
            with c1:
                nr_fv = st.text_input("Numer faktury", value=dane_z_ocr["nr_faktury"])
                data_fv = st.text_input("Data wystawienia", value=dane_z_ocr["data"])
                kwota = st.text_input("Kwota brutto", value=dane_z_ocr["kwota"])
            with c2:
                nip = st.text_input("NIP Dłużnika", value=dane_z_ocr["nip"])
                dluznik = st.text_input("Nazwa Dłużnika", value="Do uzupełnienia...")
                wierzyciel = st.text_input("Wierzyciel", value="Moja Firma Sp. z o.o.")

            if st.form_submit_button("🖨️ Generuj Dokument"):
                # Renderowanie szablonu
                context = {
                    "nr_faktury": nr_fv, "data_faktury": data_fv, 
                    "kwota_brutto": kwota, "wierzyciel_nip": "TWÓJ NIP",
                    "wierzyciel_nazwa": wierzyciel, "dluznik_nazwa": dluznik,
                    "dluznik_adres": "...", "miasto": "Warszawa", 
                    "data_biezaca": "2026-01-08", 
                    "nr_konta": "00...", "nazwa_banku": "Bank..."
                }
                
                tm = Template(BIBLIOTEKA_SZABLONOW[szablon_key])
                final_text = tm.render(context)
                
                st.success("Wygenerowano!")
                st.text_area("Podgląd", final_text, height=350)
                st.download_button("Pobierz .txt", final_text, file_name="pismo.txt")