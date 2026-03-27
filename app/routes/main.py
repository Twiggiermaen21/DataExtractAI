import os
from flask import Blueprint, render_template, jsonify, current_app, request
from flask_login import login_required
from werkzeug.utils import secure_filename

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
@login_required
def index():
    return render_template('index.html')


@main_bp.route('/api/slownie/<amount>')
def slownie(amount):
    """Zamienia kwotę na słowa (logika gramatyczna)."""
    try:
        from num2words import num2words
        clean_amount = amount.replace(',', '.').replace(' ', '').replace('zł', '')

        kwota = float(clean_amount)
        zlotowki = int(kwota)
        grosze = int(round((kwota - zlotowki) * 100))

        slownie = num2words(zlotowki, lang='pl')

        reszta_100 = zlotowki % 100
        reszta_10 = zlotowki % 10

        if zlotowki == 1:
            waluta = "złoty"
        elif 2 <= reszta_10 <= 4 and not (12 <= reszta_100 <= 14):
            waluta = "złote"
        else:
            waluta = "złotych"

        final_text = f"{slownie} {waluta} {grosze:02d}/100"
        return jsonify({'slownie': final_text})
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@main_bp.route('/api/library')
def get_library():
    """Zwraca listę plików z folderów input i saved."""
    input_folder = current_app.config['UPLOAD_FOLDER']
    saved_folder = current_app.config.get('SAVED_FOLDER')

    files = []

    for folder, url_prefix in [(input_folder, '/input'), (saved_folder, '/saved')]:
        if not folder or not os.path.exists(folder):
            continue
        for filename in os.listdir(folder):
            if filename.startswith('.'):
                continue
            filepath = os.path.join(folder, filename)
            if os.path.isfile(filepath):
                files.append({
                    'name': filename,
                    'url': f'{url_prefix}/{filename}',
                    'ext': os.path.splitext(filename)[1].lower(),
                    'size': os.path.getsize(filepath),
                    'mtime': os.path.getmtime(filepath),
                })

    try:
        files.sort(key=lambda x: x['mtime'], reverse=True)
        return jsonify(files)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@main_bp.route('/api/library/save', methods=['POST'])
def save_to_library():
    """Zapisuje kod HTML jako plik w folderze saved."""
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
        os.makedirs(saved_folder, exist_ok=True)

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


@main_bp.route('/api/library/delete', methods=['POST'])
def delete_from_library():
    """Usuwa wybrane pliki z folderów input lub saved."""
    try:
        data = request.json
        urls = data.get('urls', [])

        if not urls:
            return jsonify({'success': False, 'error': 'Nie wybrano plików do usunięcia'}), 400

        deleted_count = 0
        errors = []

        # Mapowanie prefixów URL na ścieżki fizyczne
        folder_map = {
            'input': current_app.config['UPLOAD_FOLDER'],
            'saved': current_app.config['SAVED_FOLDER']
        }

        for url in urls:
            try:
                # Oczyszczamy URL z ewentualnych ukośników
                url_clean = url.lstrip('/')
                parts = url_clean.split('/')
                if len(parts) < 2:
                    continue
                
                prefix = parts[0]
                filename = parts[1]
                
                if prefix in folder_map:
                    base_folder = folder_map[prefix]
                    safe_name = secure_filename(filename)
                    if not safe_name:
                        errors.append(f"Nieprawidłowa nazwa pliku: {filename}")
                        continue
                    filepath = os.path.realpath(os.path.join(base_folder, safe_name))
                    if not filepath.startswith(os.path.realpath(base_folder)):
                        errors.append(f"Niedozwolona ścieżka: {filename}")
                        continue

                    if os.path.exists(filepath):
                        os.remove(filepath)
                        deleted_count += 1
                    else:
                        errors.append(f"Nie znaleziono pliku: {filename}")
            except Exception as e:
                errors.append(f"Błąd przy usuwaniu {url}: {str(e)}")

        return jsonify({
            'success': True, 
            'deleted_count': deleted_count,
            'errors': errors
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500