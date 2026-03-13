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
    """Zwraca listę plików z folderu input do biblioteki."""
    print("Wywołano funkcję: get_library (z main_bp)")
    input_folder = current_app.config['UPLOAD_FOLDER']
    if not os.path.exists(input_folder):
        return jsonify([])

    try:
        files = []
        for filename in os.listdir(input_folder):
            if filename.startswith('.'):
                continue
            filepath = os.path.join(input_folder, filename)
            if os.path.isfile(filepath):
                ext = os.path.splitext(filename)[1].lower()
                files.append({
                    'name': filename,
                    'url': f'/input/{filename}',
                    'ext': ext,
                    'size': os.path.getsize(filepath)
                })
        # Sortuj od najnowszych - zmiana na path.join(input_folder, ...)
        files.sort(key=lambda x: os.path.getmtime(os.path.join(input_folder, x['name'])), reverse=True)
        return jsonify(files)
    except Exception as e:
        return jsonify({'error': str(e)}), 500