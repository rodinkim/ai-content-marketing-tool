import logging
from flask import render_template, request, jsonify, Blueprint, flash
from flask_login import login_required, current_user
from typing import Any
from models import Content
from extensions import db

logger = logging.getLogger(__name__)
history_bp = Blueprint('history_routes', __name__)

@history_bp.route('/history', methods=['GET'])
@login_required
def get_history_page() -> str:
    """
    사용자가 생성한 콘텐츠 히스토리 페이지를 렌더링합니다.
    Returns:
        str: 렌더링된 HTML
    """
    return render_template('history.html')

# 전체 히스토리 목록
@history_bp.route('/history-api', methods=['GET'])
@login_required
def get_history_api() -> Any:
    """
    현재 사용자의 모든 콘텐츠 기록을 JSON 형태로 반환합니다.
    Returns:
        Response: 콘텐츠 기록 리스트(JSON)
    """
    contents = db.session.query(Content).filter_by(user_id=current_user.id).order_by(Content.timestamp.desc()).all()
    return jsonify([content.to_dict() for content in contents])

# 개별 콘텐츠 상세 조회
@history_bp.route('/history-api/<int:content_id>', methods=['GET'])
@login_required
def get_history_detail_api(content_id: int) -> Any:
    content = db.session.query(Content).filter_by(id=content_id, user_id=current_user.id).first_or_404()
    return jsonify(content.to_dict())

@history_bp.route('/history/<int:content_id>', methods=['GET'])
@login_required
def get_history_detail_page(content_id: int) -> str:
    # 상세 페이지 렌더링 (템플릿에서 content_id를 넘김)
    return render_template('history_detail.html', content_id=content_id)

@history_bp.route('/history/<int:content_id>', methods=['DELETE'])
@login_required
def delete_content(content_id: int) -> Any:
    """
    특정 content_id에 해당하는 콘텐츠를 데이터베이스에서 삭제합니다.
    Args:
        content_id (int): 삭제할 콘텐츠 ID
    Returns:
        Response: 삭제 결과 메시지
    """
    content = db.session.query(Content).filter_by(id=content_id, user_id=current_user.id).first_or_404()
    db.session.delete(content)
    db.session.commit()
    flash('콘텐츠가 성공적으로 삭제되었습니다.', 'success')
    return jsonify({"message": f"Content with ID {content_id} deleted."}), 200 