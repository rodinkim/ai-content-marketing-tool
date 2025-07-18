import os
from flask import render_template, request, jsonify, Blueprint, current_app, send_from_directory, flash
from flask_login import login_required, current_user
import logging
from typing import Any, Dict, List, Optional

from models import Content
from extensions import db
from services.utils.constants import IMAGE_SAVE_PATH
from services.generation.translation_generator import TranslationPromptInput
from services.generation.image_generator import ImageGenerationInput
from services.generation.text_generator import TextGenerationInput
from services.content_service import create_text_content, create_image_content

logger = logging.getLogger(__name__)
content_bp = Blueprint('content_routes', __name__)

@content_bp.route('/generated_images/<path:filename>')
def serve_generated_image(filename: str):
    """
    생성된 이미지를 정적 파일로 서빙합니다.
    Args:
        filename (str): 이미지 파일명
    Returns:
        Response: 이미지 파일 응답
    """
    image_dir = os.path.join(current_app.root_path, IMAGE_SAVE_PATH)
    return send_from_directory(image_dir, filename)

@content_bp.route('/content')
@login_required
def content_page():
    """
    메인 콘텐츠 생성 페이지를 렌더링합니다.
    Returns:
        str: 렌더링된 HTML
    """
    return render_template('content.html')

@content_bp.route('/generate_content', methods=['POST'])
@login_required
def generate_text_content() -> Any:
    """
    텍스트 콘텐츠(블로그, 이메일)를 생성합니다.
    Returns:
        Response: 생성된 콘텐츠 또는 오류 메시지
    """
    data: Dict[str, Any] = request.json
    required_fields = ['topic', 'industry', 'content_type']
    # 필수 입력값 검증
    for field in required_fields:
        if not data.get(field):
            return jsonify({"error": f"{field}는 필수 입력값입니다."}), 400
    try:
        text_generator = current_app.extensions.get('text_generator')
        if not text_generator:
            raise RuntimeError("TextGenerator 서비스가 초기화되지 않았습니다.")
        input_data = TextGenerationInput(**data)
        generated_text = text_generator.generate_content(input_data)
        create_text_content(current_user.id, generated_text, data)
        return jsonify({"content": generated_text})
    except Exception as e:
        db.session.rollback()
        logger.error(f"Text content generation failed: {e}", exc_info=True)
        return jsonify({"error": "텍스트 콘텐츠 생성 중 오류가 발생했습니다."}), 500

@content_bp.route('/generate-image', methods=['POST'])
@login_required
def generate_image_content() -> Any:
    """
    SNS 콘텐츠(이미지)를 생성합니다. (번역 기능 포함)
    Returns:
        Response: 생성된 이미지 URL, 번역 프롬프트 또는 오류 메시지
    """
    data: Dict[str, Any] = request.json
    required_fields = ['topic', 'industry', 'content_type']
    # 필수 입력값 검증
    for field in required_fields:
        if not data.get(field):
            return jsonify({"error": f"{field}는 필수 입력값입니다."}), 400
    try:
        translation_generator = current_app.extensions.get('translation_generator')
        if not translation_generator:
            raise RuntimeError("TranslationGenerator 서비스가 초기화되지 않았습니다.")
        # 번역 프롬프트 입력값 구성
        translation_keys = [
            "topic", "brand_style_tone", "product_category", "target_audience",
            "ad_purpose", "key_points", "other_requirements"
        ]
        translation_input_dict = {key: data.get(key, "") for key in translation_keys}
        translation_input = TranslationPromptInput(**translation_input_dict)
        translation_result = translation_generator.translate_for_image_prompt(translation_input)
        image_prompt = translation_result['image_prompt']
        image_generator = current_app.extensions.get('image_generator')
        if not image_generator:
            raise RuntimeError("ImageGenerator 서비스가 초기화되지 않았습니다.")
        # 이미지 생성 입력값 구성
        image_request_data = data.copy()
        image_request_data['topic'] = image_prompt
        image_input = ImageGenerationInput(
            topic=image_request_data['topic'],
            cut_count=int(image_request_data.get('cut_count', 1))
        )
        image_urls: Optional[List[str]] = image_generator.create_image(image_input)
        if not image_urls:
            return jsonify({
                "status": "error",
                "message": "일시적인 오류가 발생했습니다. 잠시 후 다시 시도해 주세요."
            }), 500
        create_image_content(current_user.id, image_urls, data)
        return jsonify({
            "status": "success",
            "image_urls": image_urls,
            "translated_prompt": translation_result
        })
    except Exception as e:
        db.session.rollback()
        logger.error(f"Image content generation failed: {e}", exc_info=True)
        return jsonify({"status": "error", "message": "이미지 생성 중 오류가 발생했습니다."}), 500

@content_bp.route('/history', methods=['GET'])
@login_required
def get_history_page() -> str:
    """
    사용자가 생성한 콘텐츠 히스토리 페이지를 렌더링합니다.
    Returns:
        str: 렌더링된 HTML
    """
    return render_template('history.html')

@content_bp.route('/history-api', methods=['GET'])
@login_required
def get_history_api() -> Any:
    """
    현재 사용자의 모든 콘텐츠 기록을 JSON 형태로 반환합니다.
    Returns:
        Response: 콘텐츠 기록 리스트(JSON)
    """
    contents = db.session.query(Content).filter_by(user_id=current_user.id).order_by(Content.timestamp.desc()).all()
    return jsonify([content.to_dict() for content in contents])

@content_bp.route('/history/<int:content_id>', methods=['DELETE'])
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

@content_bp.route('/history/clear_all', methods=['DELETE'])
@login_required
def clear_all_history() -> Any:
    """
    현재 로그인된 사용자의 모든 콘텐츠 기록을 삭제합니다.
    Returns:
        Response: 삭제 결과 메시지
    """
    try:
        num_deleted = db.session.query(Content).filter_by(user_id=current_user.id).delete()
        db.session.commit()
        logger.info(f"User ID {current_user.id} cleared {num_deleted} history items.")
        return jsonify({"message": f"{num_deleted}개의 콘텐츠 기록이 성공적으로 삭제되었습니다."}), 200
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error clearing history for user ID {current_user.id}: {e}", exc_info=True)
        return jsonify({"error": "기록 삭제 중 오류가 발생했습니다."}), 500

@content_bp.route('/history/<int:content_id>', methods=['GET'])
@login_required
def get_content_detail(content_id: int) -> Any:
    """
    특정 content_id에 해당하는 콘텐츠의 상세 내용을 JSON 형태로 반환합니다.
    Args:
        content_id (int): 조회할 콘텐츠 ID
    Returns:
        Response: 콘텐츠 상세 정보(JSON)
    """
    content = db.session.query(Content).filter_by(id=content_id, user_id=current_user.id).first_or_404()
    return jsonify(content.to_dict())

@content_bp.route('/history/<int:content_id>', methods=['PUT'])
@login_required
def update_content(content_id: int) -> Any:
    """
    특정 content_id에 해당하는 콘텐츠의 내용을 업데이트합니다.
    Args:
        content_id (int): 업데이트할 콘텐츠 ID
    Returns:
        Response: 업데이트 결과 메시지
    """
    content = db.session.query(Content).filter_by(id=content_id, user_id=current_user.id).first_or_404()
    data: Dict[str, Any] = request.json
    updated_text: Optional[str] = data.get('generated_text')
    if not updated_text:
        return jsonify({"error": "업데이트할 콘텐츠 내용이 없습니다."}), 400
    content.generated_text = updated_text
    db.session.commit()
    flash('콘텐츠가 성공적으로 업데이트되었습니다.', 'success')
    return jsonify({"message": "콘텐츠가 성공적으로 업데이트되었습니다."}), 200