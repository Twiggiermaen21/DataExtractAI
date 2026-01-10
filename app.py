import os
import uuid
from flask import Flask, json, render_template, request, redirect, url_for, send_from_directory, jsonify,make_response
from paddleocr import PaddleOCRVL

app = Flask(__name__)

# --- KONFIGURACJA FOLDERÓW ---
UPLOAD_FOLDER = "input"
OUTPUT_FOLDER = "output"
TEMPLATES_FOLDER = "docs"               # Tutaj lądują surowe pliki .docx (szablony źródłowe)
PROCESSED_TEMPLATES_FOLDER = "templates_db" # Tutaj zapisujemy gotowe szablony HTML po edycji

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['OUTPUT_FOLDER'] = OUTPUT_FOLDER
app.config['TEMPLATES_FOLDER'] = TEMPLATES_FOLDER
app.config['PROCESSED_TEMPLATES_FOLDER'] = PROCESSED_TEMPLATES_FOLDER

# Tworzenie folderów jeśli nie istnieją
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)
os.makedirs(TEMPLATES_FOLDER, exist_ok=True)
os.makedirs(PROCESSED_TEMPLATES_FOLDER, exist_ok=True)

# --- INICJALIZACJA MODELU AI ---
try:
    pipeline = PaddleOCRVL()
    print("Model PaddleOCR załadowany pomyślnie.")
except Exception as e:
    print(f"Błąd ładowania modelu: {e}")
    pipeline = None


# --- TRASY GŁÓWNE (DASHBOARD) ---

@app.route('/')
def index():
    files = os.listdir(app.config['UPLOAD_FOLDER'])
    processed_files = os.listdir(OUTPUT_FOLDER)
    templates = os.listdir(app.config['PROCESSED_TEMPLATES_FOLDER']) # Lista gotowych szablonów HTML
    return render_template('index.html', files=files, processed=processed_files, templates=templates)

@app.route('/files_list_html')
def files_list_html():
    files = os.listdir(app.config['UPLOAD_FOLDER'])
    return render_template('file_list.html', files=files)

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'Brak pliku'}), 400
    
    files = request.files.getlist('file')
    saved_count = 0
    
    for file in files:
        if file.filename != '':
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], file.filename))
            saved_count += 1
            
    return jsonify({'success': True, 'count': saved_count})

# --- TRASY PRZETWARZANIA OCR (BEZ ZMIAN) ---

@app.route('/process/<filename>')
def process_single_file(filename):
    if pipeline is None:
        return "Model nie został załadowany.", 500

    file_path = os.path.join(UPLOAD_FOLDER, filename)
    
    if os.path.exists(file_path):
        try:
            output = pipeline.predict(file_path)
            for res in output:
                res.save_to_json(save_path=OUTPUT_FOLDER)
                res.save_to_markdown(save_path=OUTPUT_FOLDER)
            print(f"Sukces: {filename}")
        except Exception as e:
            print(f"Błąd przy przetwarzaniu {filename}: {e}")
            
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


# --- NOWE TRASY DLA EDYTORA SZABLONÓW ---

@app.route('/editor')
def template_editor():
    """Otwiera stronę edytora wizualnego."""
    return render_template('editor.html')

@app.route('/save_template_html', methods=['POST'])
def save_template_html():
    """Zapisuje wyedytowany szablon jako plik HTML gotowy do użycia."""
    try:
        data = request.get_json()
        html_content = data.get('html')
        template_name = data.get('name', f"szablon_{uuid.uuid4().hex[:8]}")
        
        # Dodajemy rozszerzenie .html jeśli go nie ma
        if not template_name.endswith('.html'):
            template_name += '.html'

        save_path = os.path.join(app.config['PROCESSED_TEMPLATES_FOLDER'], template_name)
        
        with open(save_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
            
        return jsonify({'success': True, 'filename': template_name})
    except Exception as e:
        print(f"Błąd zapisu szablonu: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/templates_list_html')
def templates_list_html():
    # Zwraca listę surowych plików DOCX
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
            file.save(os.path.join(app.config['TEMPLATES_FOLDER'], file.filename))
            saved_count += 1
            
    return jsonify({'success': True, 'count': saved_count})

# --- NOWE TRASY DLA ZAKŁADKI GENEROWANIE ---

@app.route('/api/get_templates_json')
def get_templates_json():
    """Zwraca listę dostępnych szablonów HTML jako JSON."""
    try:
        files = [f for f in os.listdir(app.config['PROCESSED_TEMPLATES_FOLDER']) if f.endswith('.html')]
        return jsonify(files)
    except Exception as e:
        return jsonify([])

@app.route('/get_template_content/<filename>')
def get_template_content(filename):
    """Zwraca czystą treść HTML wybranego szablonu."""
    try:
        path = os.path.join(app.config['PROCESSED_TEMPLATES_FOLDER'], filename)
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        return f"Błąd: {e}", 404

@app.route('/generate_document', methods=['POST'])
def generate_document():
    data = request.get_json()
    template_name = data.get('template')
    form_data = data.get('data')
    
    path = os.path.join(app.config['PROCESSED_TEMPLATES_FOLDER'], template_name)
    
    if not os.path.exists(path):
        return jsonify({'success': False, 'error': 'Szablon nie istnieje'}), 404

    with open(path, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    from flask import render_template_string
    filled_html = render_template_string(html_content, **form_data)
    
    # Dodajemy mały skrypt JS do wygenerowanego HTML, żeby sam wywołał drukowanie
    auto_print_script = """
    <script>
        window.onload = function() { 
            setTimeout(function(){ window.print(); }, 500); 
        }
    </script>
    """
    final_html = filled_html + auto_print_script

    # Zwracamy HTML jako tekst
    response = make_response(final_html)
    response.headers['Content-Type'] = 'text/html; charset=utf-8'
    return response







@app.route('/api/get_output_data')
def get_output_data():
    # UWAGA: Tutaj wpisz dokładną nazwę swojego pliku JSON!
    # Czy Twój plik nazywa się 'dane.json', 'output.json' czy 'wyniki.json'?
    filename = 'dane.json' 
    
    file_path = os.path.join('output', filename)
    
    if not os.path.exists(file_path):
        print(f"BŁĄD: Nie znaleziono pliku {file_path}")
        return jsonify([]) # Zwracamy pustą listę

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # Jeśli JSON to pojedynczy obiekt (np. {...}), zamieniamy go w listę [{...}]
            if isinstance(data, dict):
                data = [data]
            return jsonify(data)
    except Exception as e:
        print(f"BŁĄD JSON: {e}")
        return jsonify([])

if __name__ == '__main__':
    app.run(debug=True)