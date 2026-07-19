import os
from flask import Blueprint, render_template, jsonify, current_app, request

from app.auth import require_auth

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    return render_template('index.html')


@main_bp.route('/login')
def login_page():
    return render_template('login.html')


@main_bp.route('/healthz')
def healthz():
    return jsonify({'status': 'ok'})


@main_bp.route('/api/slownie/<amount>')
@require_auth
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

