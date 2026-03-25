from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Email, Length, EqualTo, ValidationError
from app.models import User


class RegistrationForm(FlaskForm):
    username = StringField('Nazwa użytkownika', validators=[
        DataRequired(), Length(min=3, max=80)
    ])
    email = StringField('Email', validators=[
        DataRequired(), Email(), Length(max=120)
    ])
    password = PasswordField('Hasło', validators=[
        DataRequired(), Length(min=8, message='Hasło musi mieć min. 8 znaków.')
    ])
    confirm_password = PasswordField('Potwierdź hasło', validators=[
        DataRequired(), EqualTo('password', message='Hasła muszą się zgadzać.')
    ])
    submit = SubmitField('Zarejestruj się')

    def validate_username(self, username):
        if User.query.filter_by(username=username.data).first():
            raise ValidationError('Ta nazwa użytkownika jest już zajęta.')

    def validate_email(self, email):
        if User.query.filter_by(email=email.data).first():
            raise ValidationError('Ten adres email jest już zarejestrowany.')


class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Hasło', validators=[DataRequired()])
    remember = BooleanField('Zapamiętaj mnie')
    submit = SubmitField('Zaloguj się')
