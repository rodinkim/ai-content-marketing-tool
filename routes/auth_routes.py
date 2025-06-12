# ai-content-marketing-tool/routes/auth_routes.py

from flask import render_template, request, jsonify, Blueprint, redirect, url_for, flash
from models import User # 절대 임포트
from flask_login import login_required, login_user, logout_user, current_user
from extensions import db # 절대 임포트
import logging

logger = logging.getLogger(__name__)

# 블루프린트 정의: auth_bp로 변경하고, 이름을 'auth_routes'로 설정합니다.
auth_bp = Blueprint('auth_routes', __name__) 

@auth_bp.route('/')
def index():
    """메인 페이지를 렌더링합니다."""
    return render_template('index.html')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """회원가입 페이지를 렌더링하고, 사용자 정보를 받아 새로운 계정을 생성합니다."""
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        if password != confirm_password:
            flash('비밀번호가 일치하지 않습니다.', 'danger')
            return render_template('register.html')
        
        existing_user = db.session.query(User).filter_by(username=username).first()
        if existing_user:
            flash('이미 존재하는 사용자 이름입니다.', 'danger')
            return render_template('register.html')

        existing_email = db.session.query(User).filter_by(email=email).first()
        if existing_email:
            flash('이미 존재하는 이메일입니다.', 'danger')
            return render_template('register.html')

        new_user = User(username=username, email=email)
        new_user.set_password(password)
        
        try:
            db.session.add(new_user)
            db.session.commit()
            flash('회원가입이 성공적으로 완료되었습니다. 로그인해주세요.', 'success')
            return redirect(url_for('auth_routes.login')) # <-- 'auth_routes.login'으로 변경
        except Exception as e:
            db.session.rollback()
            flash(f'회원가입 중 오류가 발생했습니다: {e}', 'danger')
            logger.error(f"회원가입 오류: {e}", exc_info=True)
            return render_template('register.html')

    return render_template('register.html')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """로그인 페이지를 렌더링하고, 사용자 자격 증명을 확인하여 로그인 세션을 관리합니다."""
    if current_user.is_authenticated:
        return redirect(url_for('auth_routes.index')) # <-- 'auth_routes.index'로 변경

    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        remember_me = request.form.get('remember_me') == 'on'

        user = db.session.query(User).filter_by(email=email).first()

        if user and user.check_password(password):
            login_user(user, remember=remember_me)
            flash('로그인 성공!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page or url_for('auth_routes.index')) # <-- 'auth_routes.index'로 변경
        else:
            flash('로그인 실패. 이메일 또는 비밀번호를 확인해주세요.', 'danger')
    
    return render_template('login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    """현재 로그인된 사용자의 세션을 종료(로그아웃)합니다."""
    logout_user()
    flash('로그아웃되었습니다.', 'info')
    return redirect(url_for('auth_routes.index')) # <-- 'auth_routes.index'로 변경