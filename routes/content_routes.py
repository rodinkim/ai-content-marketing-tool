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
