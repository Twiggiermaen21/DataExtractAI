"""
Settings API routes for account management with email confirmation.
"""
import logging
from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from app.extensions import db, limiter
from app.models import User
from app.services.email_service import (
    send_password_reset_email,
    send_name_change_email,
    send_email_change_email,
    SALT_NAME_CHANGE,
    SALT_EMAIL_CHANGE,
)
from app.utils.token_utils import verify_token

log = logging.getLogger(__name__)
settings_bp = Blueprint('settings', __name__)


@settings_bp.route('/api/settings/profile', methods=['GET'])
@login_required
def get_profile():
    """Return the current user's profile data."""
    return jsonify({
        'username': current_user.username,
        'email': current_user.email,
    })


@settings_bp.route('/api/settings/change-name', methods=['POST'])
@login_required
@limiter.limit("5 per hour", methods=["POST"])
def change_name():
    """Initiate account name change — sends confirmation email."""
    data = request.get_json(silent=True) or {}
    new_name = (data.get('new_name') or '').strip()

    if not new_name:
        return jsonify({'success': False, 'error': 'Nazwa nie może być pusta.'}), 400

    if len(new_name) < 3 or len(new_name) > 80:
        return jsonify({'success': False, 'error': 'Nazwa musi mieć od 3 do 80 znaków.'}), 400

    if new_name == current_user.username:
        return jsonify({'success': False, 'error': 'Nowa nazwa jest taka sama jak obecna.'}), 400

    existing = User.query.filter_by(username=new_name).first()
    if existing and existing.id != current_user.id:
        return jsonify({'success': False, 'error': 'Ta nazwa użytkownika jest już zajęta.'}), 400

    try:
        send_name_change_email(current_user, new_name)
        return jsonify({
            'success': True,
            'message': 'Link potwierdzający zmianę nazwy został wysłany na Twój adres e-mail.',
        })
    except Exception as e:
        log.error("Error sending name change email: %s", e)
        return jsonify({'success': False, 'error': 'Nie udało się wysłać e-maila. Spróbuj ponownie.'}), 500


@settings_bp.route('/api/settings/change-email', methods=['POST'])
@login_required
@limiter.limit("5 per hour", methods=["POST"])
def change_email():
    """Initiate email address change — sends confirmation to the NEW email."""
    data = request.get_json(silent=True) or {}
    new_email = (data.get('new_email') or '').strip().lower()

    if not new_email:
        return jsonify({'success': False, 'error': 'Adres e-mail nie może być pusty.'}), 400

    if new_email == current_user.email:
        return jsonify({'success': False, 'error': 'Nowy e-mail jest taki sam jak obecny.'}), 400

    existing = User.query.filter_by(email=new_email).first()
    if existing:
        return jsonify({'success': False, 'error': 'Ten adres e-mail jest już zarejestrowany.'}), 400

    try:
        send_email_change_email(current_user, new_email)
        return jsonify({
            'success': True,
            'message': f'Link potwierdzający został wysłany na adres {new_email}.',
        })
    except Exception as e:
        log.error("Error sending email change email: %s", e)
        return jsonify({'success': False, 'error': 'Nie udało się wysłać e-maila. Spróbuj ponownie.'}), 500


@settings_bp.route('/api/settings/request-password-reset', methods=['POST'])
@login_required
@limiter.limit("3 per hour", methods=["POST"])
def request_password_reset():
    """Send a password reset email to the current user."""
    try:
        send_password_reset_email(current_user)
        return jsonify({
            'success': True,
            'message': 'Link do resetowania hasła został wysłany na Twój adres e-mail.',
        })
    except Exception as e:
        log.error("Error sending password reset email: %s", e)
        return jsonify({'success': False, 'error': 'Nie udało się wysłać e-maila. Spróbuj ponownie.'}), 500


@settings_bp.route('/api/settings/confirm/<token>', methods=['GET'])
def confirm_change(token):
    """Confirm a name or email change via the token from the email link."""
    from flask import render_template
    action = request.args.get('action', '')

    if action == 'name':
        data = verify_token(token, salt=SALT_NAME_CHANGE)
        if not data:
            return render_template('confirm_result.html',
                                   success=False,
                                   message='Link wygasł lub jest nieprawidłowy. Spróbuj ponownie zmienić nazwę w ustawieniach.')

        user = User.query.get(data['user_id'])
        if not user:
            return render_template('confirm_result.html', success=False, message='Nie znaleziono użytkownika.')

        old_name = user.username
        user.username = data['new_name']
        db.session.commit()
        log.info("User %d name changed: %s -> %s", user.id, old_name, user.username)
        return render_template('confirm_result.html',
                               success=True,
                               message=f'Nazwa konta została zmieniona na „{user.username}".')

    elif action == 'email':
        data = verify_token(token, salt=SALT_EMAIL_CHANGE)
        if not data:
            return render_template('confirm_result.html',
                                   success=False,
                                   message='Link wygasł lub jest nieprawidłowy. Spróbuj ponownie zmienić e-mail w ustawieniach.')

        user = User.query.get(data['user_id'])
        if not user:
            return render_template('confirm_result.html', success=False, message='Nie znaleziono użytkownika.')

        old_email = user.email
        user.email = data['new_email']
        db.session.commit()
        log.info("User %d email changed: %s -> %s", user.id, old_email, user.email)
        return render_template('confirm_result.html',
                               success=True,
                               message=f'Adres e-mail został zmieniony na „{user.email}".')

    return render_template('confirm_result.html', success=False, message='Nieznana akcja.')
