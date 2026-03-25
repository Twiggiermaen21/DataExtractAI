from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app.extensions import db, limiter
from app.models import User
from app.forms import LoginForm, RegistrationForm

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['GET', 'POST'])
@limiter.limit("5 per minute", methods=["POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')
            flash('Zalogowano pomyślnie!', 'success')
            return redirect(next_page or url_for('main.index'))
        flash('Nieprawidłowy email lub hasło.', 'danger')
    return render_template('login.html', form=form)


@auth_bp.route('/register', methods=['GET', 'POST'])
@limiter.limit("3 per minute", methods=["POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Konto zostało utworzone! Możesz się zalogować.', 'success')
        return redirect(url_for('auth.login'))
    return render_template('register.html', form=form)


@auth_bp.route('/logout')
def logout():
    logout_user()
    flash('Wylogowano pomyślnie.', 'info')
    return redirect(url_for('auth.login'))


@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
@limiter.limit("3 per minute", methods=["POST"])
def forgot_password():
    """Public page to request a password reset email."""
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        email = (request.form.get('email') or '').strip().lower()
        user = User.query.filter_by(email=email).first()
        if user:
            from app.services.email_service import send_password_reset_email
            try:
                send_password_reset_email(user)
            except Exception:
                pass  # nie ujawniamy błędów
        # Zawsze ten sam komunikat — nie ujawniamy czy email istnieje
        flash('Jeśli podany adres e-mail jest zarejestrowany, otrzymasz wiadomość z linkiem do resetowania hasła.', 'success')
        return redirect(url_for('auth.forgot_password'))

    return render_template('forgot_password.html')


@auth_bp.errorhandler(429)
def ratelimit_error(e):
    flash('Zbyt wiele prób logowania. Spróbuj ponownie za minutę.', 'danger')
    return render_template('login.html', form=LoginForm()), 429


@auth_bp.route('/auth/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    """Handle password reset via email link."""
    from app.utils.token_utils import verify_token
    from app.services.email_service import SALT_PASSWORD_RESET

    data = verify_token(token, salt=SALT_PASSWORD_RESET)
    if not data:
        return render_template('confirm_result.html',
                               success=False,
                               message='Link do resetowania hasła wygasł lub jest nieprawidłowy. Spróbuj ponownie.')

    user = User.query.get(data['user_id'])
    if not user:
        return render_template('confirm_result.html',
                               success=False,
                               message='Nie znaleziono użytkownika.')

    if request.method == 'POST':
        password = request.form.get('password', '')
        confirm = request.form.get('confirm_password', '')

        if len(password) < 8:
            flash('Hasło musi mieć minimum 8 znaków.', 'danger')
            return render_template('reset_password.html', token=token)

        if password != confirm:
            flash('Hasła nie są identyczne.', 'danger')
            return render_template('reset_password.html', token=token)

        user.set_password(password)
        db.session.commit()
        flash('Hasło zostało zmienione! Możesz się zalogować.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('reset_password.html', token=token)
