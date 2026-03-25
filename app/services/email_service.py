"""
Email-sending service for account settings confirmation flows.
"""
import logging
from flask import render_template, url_for, current_app
from flask_mail import Message
from app.extensions import mail
from app.utils.token_utils import generate_token

log = logging.getLogger(__name__)

SALT_PASSWORD_RESET = 'password-reset'
SALT_NAME_CHANGE = 'name-change'
SALT_EMAIL_CHANGE = 'email-change'


def _send(msg: Message):
    """Send an email, logging to console when MAIL_SUPPRESS_SEND is on."""
    try:
        mail.send(msg)
        log.info("Email sent to %s (subject: %s)", msg.recipients, msg.subject)
    except Exception as e:
        log.error("Failed to send email: %s", e)
        raise


def _base_url() -> str:
    """Get the base URL for confirmation links."""
    return current_app.config.get('BASE_URL', 'http://localhost:5000')


def send_password_reset_email(user):
    """Send a password reset link to the user's email."""
    token = generate_token({'user_id': user.id}, salt=SALT_PASSWORD_RESET)
    reset_url = f"{_base_url()}/auth/reset-password/{token}"

    msg = Message(
        subject='iusfully – Resetowanie hasła',
        recipients=[user.email],
    )
    msg.html = render_template(
        'emails/reset_password_email.html',
        user=user,
        reset_url=reset_url,
    )

    log.info("Password reset URL for %s: %s", user.email, reset_url)
    _send(msg)


def send_name_change_email(user, new_name: str):
    """Send a name-change confirmation link to the user's email."""
    token = generate_token(
        {'user_id': user.id, 'new_name': new_name},
        salt=SALT_NAME_CHANGE,
    )
    confirm_url = f"{_base_url()}/api/settings/confirm/{token}?action=name"

    msg = Message(
        subject='iusfully – Potwierdź zmianę nazwy konta',
        recipients=[user.email],
    )
    msg.html = render_template(
        'emails/confirm_name_email.html',
        user=user,
        new_name=new_name,
        confirm_url=confirm_url,
    )

    log.info("Name change URL for %s: %s", user.email, confirm_url)
    _send(msg)


def send_email_change_email(user, new_email: str):
    """Send an email-change confirmation link to the NEW email address."""
    token = generate_token(
        {'user_id': user.id, 'new_email': new_email},
        salt=SALT_EMAIL_CHANGE,
    )
    confirm_url = f"{_base_url()}/api/settings/confirm/{token}?action=email"

    msg = Message(
        subject='iusfully – Potwierdź nowy adres e-mail',
        recipients=[new_email],  # Send to the NEW email
    )
    msg.html = render_template(
        'emails/confirm_email_email.html',
        user=user,
        new_email=new_email,
        confirm_url=confirm_url,
    )

    log.info("Email change URL for %s (new: %s): %s", user.email, new_email, confirm_url)
    _send(msg)
