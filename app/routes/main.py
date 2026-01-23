import os
from flask import Blueprint, render_template, jsonify

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    """Główna strona aplikacji."""
    return render_template('index.html')


@main_bp.route('/api/slownie/<amount>')
def slownie(amount):
    """Zamienia kwotę na słowa używając niestandardowej logiki gramatycznej."""
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