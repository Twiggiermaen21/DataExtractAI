from flask import Blueprint, render_template, jsonify
from flask_login import login_required

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

        slownie_text = num2words(zlotowki, lang='pl')

        reszta_100 = zlotowki % 100
        reszta_10 = zlotowki % 10

        if zlotowki == 1:
            waluta = "złoty"
        elif 2 <= reszta_10 <= 4 and not (12 <= reszta_100 <= 14):
            waluta = "złote"
        else:
            waluta = "złotych"

        final_text = f"{slownie_text} {waluta} {grosze:02d}/100"
        return jsonify({'slownie': final_text})
    except Exception:
        return jsonify({'error': 'Nieprawidłowa kwota'}), 400
