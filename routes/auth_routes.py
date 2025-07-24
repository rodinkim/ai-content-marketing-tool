from flask import render_template, request, redirect, url_for, flash, Blueprint
from flask_login import login_required, login_user, logout_user, current_user
from models import User
from extensions import db
from forms import RegistrationForm, LoginForm
import logging

logger = logging.getLogger(__name__)
auth_bp = Blueprint('auth_routes', __name__)

@auth_bp.route('/')
def index():
    """
    메인 페이지 렌더링
    Returns:
        str: index.html 렌더링 결과
    """
    return render_template('index.html')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """
    회원가입 페이지 렌더링 및 가입 처리
    Returns:
        Response: 회원가입 폼 또는 처리 결과
    """
    if current_user.is_authenticated:
        return redirect(url_for('content_routes.content_page'))
    form = RegistrationForm()
    if form.validate_on_submit():
        new_user = User(username=form.username.data, email=form.email.data)
        new_user.set_password(form.password.data)
        try:
            db.session.add(new_user)
            db.session.commit()
            flash('성공적으로 가입되었습니다! 로그인해주세요.', 'success')
            return redirect(url_for('auth_routes.login'))
        except Exception as e:
            db.session.rollback()
            flash(f'회원가입 중 오류가 발생했습니다: {e}', 'danger')
            logger.error(f"회원가입 오류: {e}", exc_info=True)
    return render_template('register.html', form=form)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """
    로그인 페이지 렌더링 및 로그인 처리
    Returns:
        Response: 로그인 폼 또는 처리 결과
    """
    if current_user.is_authenticated:
        return redirect(url_for('content_routes.content_page'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember_me.data)
            flash('성공적으로 로그인되었습니다.', 'success')
            next_page = request.args.get('next')
            return redirect(next_page or url_for('content_routes.content_page'))
        else:
            flash('로그인 실패. 이메일 또는 비밀번호를 확인해주세요.', 'danger')
    return render_template('login.html', form=form)

@auth_bp.route('/logout')
@login_required
def logout():
    """
    현재 로그인된 사용자를 로그아웃
    Returns:
        Response: 로그아웃 후 메인 페이지 리다이렉트
    """
    logout_user()
    flash('성공적으로 로그아웃되었습니다.', 'info')
    return redirect(url_for('auth_routes.index'))