import os
from flask import Flask, render_template, request, redirect, url_for, send_from_directory, jsonify
from paddleocr import PaddleOCRVL

app = Flask(__name__)

# Konfiguracja folderów
UPLOAD_FOLDER = "input"
OUTPUT_FOLDER = "output"
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Inicjalizacja modelu (ładuje się raz przy starcie aplikacji)
# Upewnij się, że masz zainstalowane odpowiednie biblioteki do PaddleOCR
try:
    pipeline = PaddleOCRVL()
    print("Model PaddleOCR załadowany pomyślnie.")
except Exception as e:
    print(f"Błąd ładowania modelu: {e}")
    pipeline = None

# Tworzenie folderów jeśli nie istnieją
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# --- TRASY (ROUTES) ---

@app.route('/')
def index():
    files = os.listdir(app.config['UPLOAD_FOLDER'])
    processed_files = os.listdir(OUTPUT_FOLDER)
    return render_template('index.html', files=files, processed=processed_files)

# [NOWOŚĆ] Trasa zwracająca tylko fragment HTML z listą plików (dla AJAX)
@app.route('/files_list_html')
def files_list_html():
    files = os.listdir(app.config['UPLOAD_FOLDER'])
    # Renderujemy ten mały plik szablonu, który stworzyliśmy w poprzednim kroku
    return render_template('file_list.html', files=files)

# [AKTUALIZACJA] Upload obsługujący wiele plików i zwracający JSON
@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'Brak pliku'}), 400
    
    files = request.files.getlist('file') # Pobiera listę plików
    saved_count = 0
    
    for file in files:
        if file.filename != '':
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], file.filename))
            saved_count += 1
            
    # Zwracamy JSON do JavaScriptu, zamiast przeładowywać stronę
    return jsonify({'success': True, 'count': saved_count})

@app.route('/process/<filename>')
def process_single_file(filename):
    if pipeline is None:
        return "Model nie został załadowany.", 500

    file_path = os.path.join(UPLOAD_FOLDER, filename)
    
    if os.path.exists(file_path):
        try:
            output = pipeline.predict(file_path)
            for res in output:
                # PaddleOCR zapisuje wyniki, tutaj zakładamy, że metoda save_to... działa poprawnie
                res.save_to_json(save_path=OUTPUT_FOLDER)
                res.save_to_markdown(save_path=OUTPUT_FOLDER)
            print(f"Sukces: {filename}")
        except Exception as e:
            print(f"Błąd przy przetwarzaniu {filename}: {e}")
            
    return redirect(url_for('index'))

@app.route('/process_all')
def process_all():
    for filename in os.listdir(UPLOAD_FOLDER):
        if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.pdf')):
            # Wywołujemy logikę przetwarzania (zauważ: process_single_file zwraca redirect, 
            # więc w pętli to ignorujemy i robimy robotę)
            
            file_path = os.path.join(UPLOAD_FOLDER, filename)
            if pipeline and os.path.exists(file_path):
                try:
                    output = pipeline.predict(file_path)
                    for res in output:
                        res.save_to_json(save_path=OUTPUT_FOLDER)
                        res.save_to_markdown(save_path=OUTPUT_FOLDER)
                    print(f"Przetworzono w pętli: {filename}")
                except Exception as e:
                    print(f"Błąd pętli dla {filename}: {e}")

    return redirect(url_for('index'))

@app.route('/input/<filename>')
def serve_input_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


@app.route('/delete_selected', methods=['POST'])
def delete_selected():
    data = request.get_json()
    files_to_delete = data.get('files', [])
    
    deleted_count = 0
    for filename in files_to_delete:
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        if os.path.exists(file_path):
            os.remove(file_path)
            deleted_count += 1
            
    return jsonify({'success': True, 'count': deleted_count})

@app.route('/process_selected', methods=['POST'])
def process_selected():
    data = request.get_json()
    files_to_process = data.get('files', [])
    
    if pipeline is None:
        return jsonify({'success': False, 'error': 'Model AI nie jest załadowany'}), 500

    processed_count = 0
    for filename in files_to_process:
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        if os.path.exists(file_path):
            try:
                output = pipeline.predict(file_path)
                for res in output:
                    res.save_to_json(save_path=OUTPUT_FOLDER)
                    res.save_to_markdown(save_path=OUTPUT_FOLDER)
                processed_count += 1
            except Exception as e:
                print(f"Błąd AI dla {filename}: {e}")

    return jsonify({'success': True, 'count': processed_count})

# --- KONFIGURACJA SZABLONÓW ---
TEMPLATES_FOLDER = "docs"
app.config['TEMPLATES_FOLDER'] = TEMPLATES_FOLDER
os.makedirs(TEMPLATES_FOLDER, exist_ok=True)

# --- TRASY DLA SZABLONÓW ---

@app.route('/templates_list_html')
def templates_list_html():
    # Pobieramy pliki z folderu szablonów
    files = os.listdir(app.config['TEMPLATES_FOLDER'])
    return render_template('template_list.html', files=files)

@app.route('/upload_template', methods=['POST'])
def upload_template():
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'Brak pliku'}), 400
    
    files = request.files.getlist('file')
    saved_count = 0
    
    for file in files:
        if file.filename != '':
            # Tutaj lądują szablony
            file.save(os.path.join(app.config['TEMPLATES_FOLDER'], file.filename))
            saved_count += 1
            
    return jsonify({'success': True, 'count': saved_count})

if __name__ == '__main__':
    app.run(debug=True)