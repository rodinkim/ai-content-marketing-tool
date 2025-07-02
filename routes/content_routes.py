# ai-content-marketing-tool/routes/content_routes.py

from flask import render_template, request, jsonify, Blueprint, flash
from services.ai_rag.ai_service import get_ai_content_generator
from models import Content 
from flask_login import login_required, current_user
from extensions import db
import logging

logger = logging.getLogger(__name__)

content_bp = Blueprint('content_routes', __name__) 

### ▼▼▼ 여기에 새로운 라우트 추가 ▼▼▼ ###
@content_bp.route('/content')
@login_required
def content_page():
    """로그인한 사용자를 위한 메인 콘텐츠 생성 페이지를 렌더링합니다."""
    return render_template('content.html')
### ▲▲▲ 추가된 라우트 끝 ▲▲▲ ###


@content_bp.route('/generate_content', methods=['POST'])
@login_required
def generate_content_api():
    """사용자 입력 기반으로 RAG와 LLM을 활용하여 마케팅 콘텐츠를 생성하고 저장합니다."""
    user_id = current_user.id

    data = request.json
    topic = data.get('topic')
    industry = data.get('industry')
    content_type = data.get('content_type')
    tone = data.get('tone')
    length = data.get('length')
    seo_keywords = data.get('seo_keywords')

    if not all([topic, industry, content_type, tone, length]):
        logger.warning(f"콘텐츠 생성 필수 필드 누락: {data}")
        return jsonify({"error": "모든 필수 필드를 입력해주세요."}), 400

    try:
        ai_generator = get_ai_content_generator()

        if ai_generator is None:
            logger.critical("AI Content Generator is not initialized. Cannot generate content.")
            return jsonify({"error": "AI 서비스 초기화 오류. 관리자에게 문의하세요."}), 503

        generated_text = ai_generator.generate_content(
            topic=topic,
            industry=industry,
            content_type=content_type,
            tone=tone,
            length=length,
            seo_keywords=seo_keywords
        )
        
        new_content = Content(
            user_id=user_id,
            topic=topic,
            industry=industry,
            content_type=content_type,
            tone=tone,
            length_option=length,
            seo_keywords=seo_keywords,
            generated_text=generated_text
        )
        db.session.add(new_content)
        db.session.commit()
        logger.info(f"Content successfully saved to DB: ID {new_content.id}, Topic '{new_content.topic}' by User ID {user_id}")

        return jsonify({
            "content": generated_text,
            "id": new_content.id,
            "timestamp": new_content.timestamp.isoformat()
        })

    except RuntimeError as e:
        logger.error(f"AI Service Runtime Error: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 503
    except Exception as e:
        db.session.rollback()
        logger.error(f"콘텐츠 생성 API 호출 실패 또는 DB 저장 오류: {e}", exc_info=True)
        return jsonify({"error": "콘텐츠 생성 또는 저장 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요."}), 500

@content_bp.route('/history', methods=['GET'])
@login_required
def get_history_page():
    """사용자가 생성한 콘텐츠 히스토리 페이지를 렌더링합니다."""
    return render_template('history.html')

@content_bp.route('/history-api', methods=['GET'])
@login_required
def get_history_api():
    """현재 사용자의 모든 콘텐츠 기록을 JSON 형태로 반환합니다."""
    all_contents = db.session.query(Content).filter_by(user_id=current_user.id).order_by(Content.timestamp.desc()).all()
    
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
            "content": content.generated_text,
            "timestamp": content.timestamp.isoformat()
        })
    return jsonify(history_data)

@content_bp.route('/history/<int:content_id>', methods=['DELETE'])
@login_required
def delete_content(content_id):
    """특정 content_id에 해당하는 콘텐츠를 데이터베이스에서 삭제합니다."""
    content_to_delete = db.session.query(Content).filter_by(id=content_id, user_id=current_user.id).first()
    
    if content_to_delete:
        db.session.delete(content_to_delete)
        db.session.commit()
        logger.info(f"Content ID {content_id} deleted from DB by User ID {current_user.id}.")
        flash('콘텐츠가 성공적으로 삭제되었습니다.', 'success')
        return jsonify({"message": f"Content with ID {content_id} deleted."}), 200
    
    flash('콘텐츠를 찾을 수 없거나 삭제 권한이 없습니다.', 'danger')
    return jsonify({"error": f"Content with ID {content_id} not found or not authorized."}), 404

# 기록 전체 삭제 라우트 추가
@content_bp.route('/history/clear_all', methods=['DELETE'])
@login_required
def clear_all_history():
    """현재 로그인된 사용자의 모든 콘텐츠 기록을 삭제합니다."""
    try:
        num_deleted = db.session.query(Content).filter_by(user_id=current_user.id).delete(synchronize_session='fetch')
        db.session.commit()
        
        logger.info(f"User ID {current_user.id}가 {num_deleted}개의 기록을 성공적으로 삭제했습니다.")
        
        return jsonify({"message": f"{num_deleted}개의 콘텐츠 기록이 성공적으로 삭제되었습니다."}), 200
    except Exception as e:
        db.session.rollback()
        logger.error(f"User ID {current_user.id}의 모든 기록 삭제 중 오류 발생: {e}", exc_info=True)
        return jsonify({"error": "모든 기록 삭제 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요."}), 500


@content_bp.route('/history/<int:content_id>', methods=['GET'])
@login_required
def get_content_detail(content_id):
    """특정 content_id에 해당하는 콘텐츠의 상세 내용을 JSON 형태로 반환합니다."""
    content = db.session.query(Content).filter_by(id=content_id, user_id=current_user.id).first()
    if not content:
        return jsonify({"error": "콘텐츠를 찾을 수 없거나 접근 권한이 없습니다."}), 404
    
    return jsonify({
        "id": content.id,
        "topic": content.topic,
        "industry": content.industry,
        "content_type": content.content_type,
        "tone": content.tone,
        "length": content.length_option,
        "seo_keywords": content.seo_keywords,
        "content": content.generated_text,
        "timestamp": content.timestamp.isoformat()
    })

@content_bp.route('/history/<int:content_id>', methods=['PUT'])
@login_required
def update_content(content_id):
    """특정 content_id에 해당하는 콘텐츠의 내용을 업데이트합니다."""
    content_to_update = db.session.query(Content).filter_by(id=content_id, user_id=current_user.id).first()
    
    if not content_to_update:
        return jsonify({"error": "콘텐츠를 찾을 수 없거나 업데이트 권한이 없습니다."}), 404

    data = request.json
    updated_text = data.get('generated_text') # 수정된 콘텐츠 텍스트

    if not updated_text:
        return jsonify({"error": "업데이트할 콘텐츠 내용이 없습니다."}), 400

    try:
        content_to_update.generated_text = updated_text
        db.session.commit()
        logger.info(f"Content ID {content_id} updated by User ID {current_user.id}.")
        flash('콘텐츠가 성공적으로 업데이트되었습니다.', 'success')
        return jsonify({"message": "콘텐츠가 성공적으로 업데이트되었습니다.", "id": content_to_update.id}), 200
    except Exception as e:
        db.session.rollback()
        logger.error(f"콘텐츠 ID {content_id} 업데이트 중 오류 발생: {e}", exc_info=True)
        return jsonify({"error": "콘텐츠 업데이트 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요."}), 500