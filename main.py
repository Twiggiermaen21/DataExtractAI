import streamlit as st
import os
from ocr_function import przetworz_dokument 

st.set_page_config(page_title="OCR Faktur")
st.title("📂 Wrzutnia + Funkcja")

# --- KONFIGURACJA FOLDERÓW ---
UPLOAD_FOLDER = "input"


# Tworzymy folder wejściowy
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# --- UI ---
uploaded_file = st.file_uploader("Wybierz plik faktury")

if uploaded_file is not None:
    file_path = os.path.join(UPLOAD_FOLDER, uploaded_file.name)
    
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    
    st.success(f"Zapisano plik w: {file_path}")
    st.image(uploaded_file, width=400)

    st.divider()
    # ZMIANA: Tu definiujemy ścieżkę zagnieżdżoną "output/output_faktura"
    OUTPUT_FOLDER = os.path.join("output", f"output_{uploaded_file.name}") 
    if st.button("Uruchom przetwarzanie OCR"):
        with st.spinner("Przetwarzanie..."):
            # Przekazujemy ścieżkę do zagnieżdżonego folderu wynikowego
            wynik = przetworz_dokument(file_path, folder_wynikowy=OUTPUT_FOLDER)
            
            st.success("Gotowe!")
            st.info(f"Komunikat: {wynik}")
            st.write(f"Wyniki zapisano w: `{OUTPUT_FOLDER}`")