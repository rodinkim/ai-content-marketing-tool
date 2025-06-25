# forms.py

from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, Length, ValidationError
from models import User

class RegistrationForm(FlaskForm):
    """회원가입 폼을 정의합니다."""
    username = StringField('사용자 이름', validators=[DataRequired(), Length(min=2, max=20)])
    email = StringField('이메일', validators=[DataRequired(), Email()])
    password = PasswordField('비밀번호', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('비밀번호 확인', validators=[DataRequired(), EqualTo('password', message='비밀번호가 일치해야 합니다.')])
    submit = SubmitField('계정 생성')

    def validate_username(self, username):
        """사용자 이름 중복을 확인합니다."""
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('이미 존재하는 사용자 이름입니다. 다른 이름을 사용해주세요.')

    def validate_email(self, email):
        """이메일 중복을 확인합니다."""
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('이미 등록된 이메일입니다. 다른 이메일을 사용해주세요.')


class LoginForm(FlaskForm):
    """로그인 폼을 정의합니다."""
    email = StringField('이메일', validators=[DataRequired(), Email()])
    password = PasswordField('비밀번호', validators=[DataRequired()])
    remember_me = BooleanField('로그인 상태 유지')
    submit = SubmitField('로그인')