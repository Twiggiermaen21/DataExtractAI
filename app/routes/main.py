import os
from flask import Blueprint, app, render_template, current_app, send_from_directory

main_bp = Blueprint('main', __name__)


# Konfiguracja folderu z szablonami
# Zakładam, że folder 'docs' jest w tym samym katalogu co app.py
DOCS_FOLDER = os.path.join(os.getcwd(), 'docs')

@main_bp.route('/')
def index():
    return render_template('index.html') # Twój plik HTML

# --- NOWY ENDPOINT ---
# Służy do pobierania plików .docx przez JavaScript
@main_bp.route('/get-template/<filename>')
def get_template(filename):
    try:
        # Zwraca plik z folderu docs
        return send_from_directory(DOCS_FOLDER, filename)
    except FileNotFoundError:
        return "File not found", 404





if __name__ == '__main__':
    app.run(debug=True)



# @main_bp.route('/')
# def index():
#     """
#     Główny widok Dashboardu.
#     Zbiera listy plików z folderów konfiguracyjnych, aby wyświetlić statystyki/listy na starcie.
#     """
#     # Pobieranie list plików (bezpiecznie, z obsługą błędów jeśli folder nie istnieje)
#     try:
#         files = os.listdir(current_app.config['UPLOAD_FOLDER'])
#     except OSError:
#         files = []

#     try:
#         processed_files = os.listdir(current_app.config['OUTPUT_FOLDER'])
#     except OSError:
#         processed_files = []

#     try:
#         # Pobieramy tylko gotowe szablony HTML
#         templates = [f for f in os.listdir(current_app.config['PROCESSED_TEMPLATES_FOLDER']) if f.endswith('.html')]
#     except OSError:
#         templates = []
    
#     return render_template('index.html', 
#                            files=files, 
#                            processed=processed_files, 
#                            templates=templates)

# @main_bp.route('/files_list_html')
# def files_list_html():
#     """
#     Zwraca fragment HTML z listą plików wejściowych (do dynamicznego odświeżania listy).
#     """
#     try:
#         files = os.listdir(current_app.config['UPLOAD_FOLDER'])
#     except OSError:
#         files = []
#     return render_template('components/file_list.html', files=files)