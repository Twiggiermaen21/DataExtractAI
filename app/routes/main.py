import os
from flask import Blueprint, render_template, jsonify, current_app, request

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    """Główna strona aplikacji."""
    print("Wywołano funkcję: index")
    return render_template('index.html')


@main_bp.route('/api/slownie/<amount>')
def slownie(amount):
    """Zamienia kwotę na słowa używając niestandardowej logiki gramatycznej."""
    print("Wywołano funkcję: slownie")
    try:
        from num2words import num2words
        # Zamień przecinek na kropkę i usuń spacje
        clean_amount = amount.replace(',', '.').replace(' ', '').replace('zł', '')
        
        # 1. Rozdzielamy złotówki i grosze
        kwota = float(clean_amount)
        zlotowki = int(kwota)
        grosze = int(round((kwota - zlotowki) * 100))
        
        # 2. Zamieniamy liczbę całkowitą na słowa
        slownie = num2words(zlotowki, lang='pl')
        
        # 3. Logika gramatyczna dla słowa "złoty"
        # 1 złoty, 2 złote, 5 złotych, 12 złotych, 22 złote etc.
        reszta_100 = zlotowki % 100
        reszta_10 = zlotowki % 10
        
        if zlotowki == 1:
            waluta = "złoty"
        elif 2 <= reszta_10 <= 4 and not (12 <= reszta_100 <= 14):
            waluta = "złote"
        else:
            waluta = "złotych"
            
        # 4. Złożenie całości w żądany format
        # Pominąłem nawiasy i tekst "(słownie: )", ponieważ są już w HTML
        final_text = f"{slownie} {waluta} {grosze:02d}/100"
        
        return jsonify({'slownie': final_text})
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@main_bp.route('/api/library')
def get_library():
    """Zwraca listę plików z folderów input i saved do biblioteki."""
    print("Wywołano funkcję: get_library (z main_bp)")
    input_folder = current_app.config['UPLOAD_FOLDER']
    saved_folder = current_app.config.get('SAVED_FOLDER')
    
    files = []
    
    # 1. Skanuj folder input
    if os.path.exists(input_folder):
        for filename in os.listdir(input_folder):
            if filename.startswith('.'): continue
            filepath = os.path.join(input_folder, filename)
            if os.path.isfile(filepath):
                ext = os.path.splitext(filename)[1].lower()
                files.append({
                    'name': filename,
                    'url': f'/input/{filename}',
                    'ext': ext,
                    'size': os.path.getsize(filepath),
                    'mtime': os.path.getmtime(filepath)
                })
                
    # 2. Skanuj folder saved
    if saved_folder and os.path.exists(saved_folder):
        for filename in os.listdir(saved_folder):
            if filename.startswith('.'): continue
            filepath = os.path.join(saved_folder, filename)
            if os.path.isfile(filepath):
                ext = os.path.splitext(filename)[1].lower()
                files.append({
                    'name': filename,
                    'url': f'/saved/{filename}',
                    'ext': ext,
                    'size': os.path.getsize(filepath),
                    'mtime': os.path.getmtime(filepath)
                })

    try:
        # Sortuj od najnowszych
        files.sort(key=lambda x: x['mtime'], reverse=True)
        return jsonify(files)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@main_bp.route('/api/library/save', methods=['POST'])
def save_to_library():
    """Zapisuje otrzymany kod HTML jako plik w folderze saved."""
    print("Wywołano funkcję: save_to_library")
    try:
        data = request.json
        content = data.get('content')
        filename = data.get('filename', 'document.html')

        if not content:
            return jsonify({'success': False, 'error': 'Brak treści dokumentu'}), 400

        from werkzeug.utils import secure_filename
        filename = secure_filename(filename)
        
        if not filename.endswith('.html'):
            filename += '.html'

        saved_folder = current_app.config['SAVED_FOLDER']
        if not os.path.exists(saved_folder):
            os.makedirs(saved_folder)

        filepath = os.path.join(saved_folder, filename)
        
        if os.path.exists(filepath):
            import time
            name, ext = os.path.splitext(filename)
            filename = f"{name}_{int(time.time())}{ext}"
            filepath = os.path.join(saved_folder, filename)

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)

        return jsonify({'success': True, 'filename': filename})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500