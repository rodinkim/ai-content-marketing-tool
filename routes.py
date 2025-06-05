# ai-content-marketing-tool/routes.py
from flask import render_template, request, jsonify, Blueprint, current_app, redirect, url_for, flash
# from services import ai_service # <--- 이 임포트 방식 변경
from services.ai_service import get_ai_content_generator # <--- 변경: ai_service 모듈에서 get_ai_content_generator 임포트
from models import Content, User
from flask_login import login_required, login_user, logout_user, current_user
from extensions import db # <--- 추가: db 객체 임포트
import logging # <--- 추가: 로깅 모듈 임포트

# 라우트 모듈 전용 로거 인스턴스 생성
logger = logging.getLogger(__name__)

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    return render_template('index.html')

@main_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        # db_session = current_app.extensions['sqlalchemy'].session # <--- db.session으로 변경
        
        if password != confirm_password:
            flash('비밀번호가 일치하지 않습니다.', 'danger')
            return render_template('register.html')
        
        existing_user = db.session.query(User).filter_by(username=username).first() # <--- db.session 사용
        if existing_user:
            flash('이미 존재하는 사용자 이름입니다.', 'danger')
            return render_template('register.html')

        existing_email = db.session.query(User).filter_by(email=email).first() # <--- db.session 사용
        if existing_email:
            flash('이미 존재하는 이메일입니다.', 'danger')
            return render_template('register.html')

        new_user = User(username=username, email=email)
        new_user.set_password(password)
        
        try:
            db.session.add(new_user) # <--- db.session 사용
            db.session.commit() # <--- db.session 사용
            flash('회원가입이 성공적으로 완료되었습니다. 로그인해주세요.', 'success')
            return redirect(url_for('main.login'))
        except Exception as e:
            db.session.rollback() # <--- db.session 사용
            flash(f'회원가입 중 오류가 발생했습니다: {e}', 'danger')
            logger.error(f"회원가입 오류: {e}", exc_info=True) # <--- print 대신 로깅
            return render_template('register.html')

    return render_template('register.html')

@main_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        remember_me = request.form.get('remember_me') == 'on'

        # db_session = current_app.extensions['sqlalchemy'].session # <--- db.session으로 변경
        user = db.session.query(User).filter_by(email=email).first() # <--- db.session 사용

        if user and user.check_password(password):
            login_user(user, remember=remember_me)
            flash('로그인 성공!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page or url_for('main.index'))
        else:
            flash('로그인 실패. 이메일 또는 비밀번호를 확인해주세요.', 'danger')
    
    return render_template('login.html')

@main_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('로그아웃되었습니다.', 'info')
    return redirect(url_for('main.index'))


@main_bp.route('/generate_content', methods=['POST'])
@login_required
def generate_content():
    user_id = current_user.id

    data = request.json # AJAX 요청에서 JSON 데이터를 받습니다.
    topic = data.get('topic')
    industry = data.get('industry')
    content_type = data.get('content_type')
    tone = data.get('tone')
    length = data.get('length')
    seo_keywords = data.get('seo_keywords')
    email_subject_input = data.get('email_subject')

    if not all([topic, industry, content_type, tone, length]):
        logger.warning(f"콘텐츠 생성 필수 필드 누락: {data}") # <--- 로깅 추가
        return jsonify({"error": "모든 필수 필드를 입력해주세요."}), 400

    try:
        # AIContentGenerator 인스턴스 가져오기
        ai_generator = get_ai_content_generator() # <--- 변경

        if ai_generator is None:
            logger.critical("AI Content Generator is not initialized. Cannot generate content.") # <--- 로깅
            return jsonify({"error": "AI 서비스 초기화 오류. 관리자에게 문의하세요."}), 503

        # AIContentGenerator 클래스의 generate_content 메서드 호출
        generated_text = ai_generator.generate_content( # <--- 변경
            topic=topic,
            industry=industry,
            content_type=content_type,
            tone=tone,
            length=length,
            seo_keywords=seo_keywords,
            email_subject_input=email_subject_input
        )
        
        # db_session = current_app.extensions['sqlalchemy'].session # <--- db.session으로 변경
        new_content = Content(
            user_id=user_id,
            topic=topic,
            industry=industry,
            content_type=content_type,
            tone=tone,
            length_option=length,
            seo_keywords=seo_keywords,
            # 이메일 뉴스레터가 아닐 경우 email_subject는 None으로 저장
            email_subject=email_subject_input if content_type == "이메일 뉴스레터" else None, 
            generated_text=generated_text
        )
        db.session.add(new_content) # <--- db.session 사용
        db.session.commit() # <--- db.session 사용
        logger.info(f"Content successfully saved to DB: ID {new_content.id}, Topic '{new_content.topic}' by User ID {user_id}") # <--- print 대신 로깅
        
        return jsonify({
            "content": generated_text,
            "id": new_content.id,
            "timestamp": new_content.timestamp.isoformat()
        })

    except RuntimeError as e: # ai_service에서 발생시킬 수 있는 특정 오류
        logger.error(f"AI Service Runtime Error: {e}", exc_info=True) # <--- 로깅
        return jsonify({"error": str(e)}), 503
    except Exception as e:
        logger.error(f"콘텐츠 생성 API 호출 실패 또는 DB 저장 오류: {e}", exc_info=True) # <--- 로깅
        # db_session = current_app.extensions['sqlalchemy'].session # <--- db.session으로 변경
        db.session.rollback() # <--- db.session 사용
        return jsonify({"error": "콘텐츠 생성 또는 저장 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요."}), 500

# --- /history 라우트 변경: HTML 템플릿 렌더링으로 변경 ---
@main_bp.route('/history', methods=['GET'])
@login_required
def get_history():
    # db_session = current_app.extensions['sqlalchemy'].session # <--- db.session으로 변경
    # 현재 사용자의 콘텐츠만 조회
    all_contents = db.session.query(Content).filter_by(user_id=current_user.id).order_by(Content.timestamp.desc()).all() # <--- db.session 사용
    
    # 템플릿에 전달할 데이터를 딕셔너리 리스트로 변환
    history_items = []
    for content in all_contents:
        history_items.append({
            "id": content.id,
            "topic": content.topic,
            "industry": content.industry,
            "content_type": content.content_type,
            "tone": content.tone,
            "length": content.length_option,
            "seo_keywords": content.seo_keywords,
            "email_subject": content.email_subject,
            "content": content.generated_text,
            "timestamp": content.timestamp # datetime 객체 그대로 전달 (Jinja2에서 format 가능)
        })
    
    # history.html 템플릿 렌더링 시 history_items 데이터를 전달
    return render_template('history.html', history_items=history_items)

# --- 새로운 API 엔드포인트 추가: history 페이지에서 AJAX로 데이터를 가져올 때 사용 ---
@main_bp.route('/history-api', methods=['GET'])
@login_required
def get_history_api():
    # db_session = current_app.extensions['sqlalchemy'].session # <--- db.session으로 변경
    all_contents = db.session.query(Content).filter_by(user_id=current_user.id).order_by(Content.timestamp.desc()).all() # <--- db.session 사용
    
    history_data = []
    for content in all_contents:
        history_data.append({
            "id": content.id,
            "topic": content.topic,
            "industry": content.industry,
            "content_type": content.content_type,
            "tone": content.tone,
            "length": content.length_option,
            "seo_keywords": content.seo_keywords,
            "email_subject": content.email_subject,
            "content": content.generated_text,
            "timestamp": content.timestamp.isoformat() # JS에서 처리하기 위해 ISO 포맷으로 변환
        })
    return jsonify(history_data)


@main_bp.route('/history/<int:content_id>', methods=['DELETE'])
@login_required
def delete_content(content_id):
    # db_session = current_app.extensions['sqlalchemy'].session # <--- db.session으로 변경
    content_to_delete = db.session.query(Content).filter_by(id=content_id, user_id=current_user.id).first() # <--- db.session 사용
    
    if content_to_delete:
        db.session.delete(content_to_delete) # <--- db.session 사용
        db.session.commit() # <--- db.session 사용
        logger.info(f"Content ID {content_id} deleted from DB by User ID {current_user.id}.") # <--- print 대신 로깅
        flash('콘텐츠가 성공적으로 삭제되었습니다.', 'success')
        return jsonify({"message": f"Content with ID {content_id} deleted."}), 200
    
    flash('콘텐츠를 찾을 수 없거나 삭제 권한이 없습니다.', 'danger')
    return jsonify({"error": f"Content with ID {content_id} not found or not authorized."}), 404