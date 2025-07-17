import os
from flask import render_template, request, jsonify, Blueprint, current_app, send_from_directory, flash
from flask_login import login_required, current_user
import logging

from models import Content 
from extensions import db
from services.ai_rag.text_generator import get_text_generator
from services.ai_rag.image_generator import get_image_generator
from services.ai_rag.translation_generator import get_translation_generator

logger = logging.getLogger(__name__)
content_bp = Blueprint('content_routes', __name__) 

@content_bp.route('/generated_images/<path:filename>')
def serve_generated_image(filename):
    """생성된 이미지를 정적 파일로 서빙합니다."""
    image_dir = os.path.join(current_app.root_path, current_app.config.get('IMAGE_SAVE_PATH'))
    return send_from_directory(image_dir, filename)


@content_bp.route('/content')
@login_required
def content_page():
    """메인 콘텐츠 생성 페이지를 렌더링합니다."""
    return render_template('content.html')


@content_bp.route('/generate_content', methods=['POST'])
@login_required
def generate_text_content():
    """텍스트 콘텐츠(블로그, 이메일)를 생성하고 DB에 저장합니다."""
    data = request.json

    # 공통 필수 필드만 검증
    required_fields = ['topic', 'industry', 'content_type']
    for field in required_fields:
        if not data.get(field):
            return jsonify({"error": f"{field}는 필수 입력값입니다."}), 400

    try:
        text_generator = get_text_generator()
        if not text_generator:
            raise RuntimeError("TextGenerator 서비스가 초기화되지 않았습니다.")
        
        generated_text = text_generator.generate_content(**data)

        new_content = Content(
            user_id=current_user.id,
            generated_text=generated_text,
            topic=data.get('topic'),
            industry=data.get('industry'),
            content_type=data.get('content_type'),
            target_audience=data.get('target_audience'),
            key_points=data.get('key_points'),
            landing_page_url=data.get('landing_page_url'),
            tone=data.get('tone'),
            length_option=data.get('length_option'),
            seo_keywords=data.get('seo_keywords'),
            blog_style=data.get('blog_style'),
            email_subject=data.get('email_subject'),
            email_type=data.get('email_type'),
            brand_style_tone=data.get('brand_style_tone'),
            product_category=data.get('product_category'),
            ad_purpose=data.get('ad_purpose')
        )
        db.session.add(new_content)
        db.session.commit()
        
        return jsonify({"content": generated_text})
    except Exception as e:
        db.session.rollback()
        logger.error(f"Text content generation failed: {e}", exc_info=True)
        return jsonify({"error": "텍스트 콘텐츠 생성 중 오류가 발생했습니다."}), 500


@content_bp.route('/generate-image', methods=['POST'])
@login_required
def generate_image_content():
    """SNS 콘텐츠(이미지)를 생성합니다. (번역 기능 포함)"""
    # 1. 입력 데이터 파싱
    data = request.json

    # 2. 필수 입력값 검증
    required_fields = ['topic', 'industry', 'content_type']
    for field in required_fields:
        if not data.get(field):
            return jsonify({"error": f"{field}는 필수 입력값입니다."}), 400

    try:
        # 3. 번역 서비스 준비 및 번역 프롬프트 생성
        translation_generator = get_translation_generator()
        if not translation_generator:
            raise RuntimeError("TranslationGenerator 서비스가 초기화되지 않았습니다.")

        # 번역에 필요한 필드만 추출
        translation_keys = [
            "topic", "brand_style_tone", "product_category", "target_audience",
            "ad_purpose", "key_points", "cut_count", "aspect_ratio_sns", "other_requirements"
        ]
        translation_input = {key: data.get(key, "") for key in translation_keys}
        translation_result = translation_generator.translate_for_image_prompt(**translation_input)
        image_prompt = translation_result['image_prompt']

        # 4. 고급 설정 입력값 개수 체크 (사용자 안내)
        advanced_fields = ["brand_style_tone", "product_category", "target_audience", "ad_purpose", "key_points"]
        advanced_filled = sum(1 for field in advanced_fields if data.get(field))
        if advanced_filled < 2:
            return jsonify({
                "status": "info",
                "message": (
                    "<div style='font-family: \"Noto Sans KR\", sans-serif; font-size:17px; line-height:1.9; color:#222;'>"
                    "조금 더 구체적으로 입력해 주시면,<br>"
                    "<span style='color:#0052cc; font-weight:600;'>AI가 더욱 완성도 높은 이미지를 만들어 드릴 수 있어요 🌿</span><br><br>"
                    "<b>아래 항목 중 2개 이상</b> 입력해 주세요:<br>"
                    "<span style='color:#1976d2;'>· 타겟 고객 · 브랜드 스타일 · 제품 카테고리<br>· 광고 목적 · 핵심 메시지</span><br><br>"
                    "<span style='font-size:14px; color:#888;'>* 정보가 풍부할수록 이미지도 더 좋아집니다 :)</span>"
                    "</div>"
                )
            }), 200

        # 5. 이미지 생성 서비스 준비
        image_generator = get_image_generator()
        if not image_generator:
            raise RuntimeError("ImageGenerator 서비스가 초기화되지 않았습니다.")

        # 6. 이미지 생성 요청 (프롬프트는 번역 결과 사용)
        image_request_data = data.copy()
        image_request_data['topic'] = image_prompt
        image_urls = image_generator.create_image(**image_request_data)

        if not image_urls:
            return jsonify({
                "status": "error",
                "message": "일시적인 오류가 발생했습니다. 잠시 후 다시 시도해 주세요."
            }), 500

        # 7. 생성 결과 DB 저장
        new_content = Content(
            user_id=current_user.id,
            content_type=data.get('content_type'),
            generated_image_url=", ".join(image_urls),
            topic=data.get('topic'),
            industry=data.get('industry'),
            target_audience=data.get('target_audience'),
            brand_style_tone=data.get('brand_style_tone'),
            product_category=data.get('product_category'),
            ad_purpose=data.get('ad_purpose'),
            key_points=data.get('key_points'),
            cut_count=data.get('cut_count'),
            aspect_ratio_sns=data.get('aspect_ratio_sns'),
            other_requirements=data.get('other_requirements')
        )
        db.session.add(new_content)
        db.session.commit()

        # 8. 성공 응답 반환
        return jsonify({
            "status": "success",
            "image_urls": image_urls,
            "translated_prompt": translation_result
        })

    except RuntimeError as e:
        db.session.rollback()
        logger.error(f"Service initialization error: {e}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500
    except Exception as e:
        db.session.rollback()
        logger.error(f"Image content generation failed: {e}", exc_info=True)
        return jsonify({"status": "error", "message": "이미지 생성 중 오류가 발생했습니다."}), 500


@content_bp.route('/history', methods=['GET'])
@login_required
def get_history_page():
    """사용자가 생성한 콘텐츠 히스토리 페이지를 렌더링합니다."""
    return render_template('history.html')


@content_bp.route('/history-api', methods=['GET'])
@login_required
def get_history_api():
    """현재 사용자의 모든 콘텐츠 기록을 JSON 형태로 반환합니다."""
    contents = db.session.query(Content).filter_by(user_id=current_user.id).order_by(Content.timestamp.desc()).all()
    # Content 모델에 to_dict() 메서드가 구현되어 있다고 가정합니다.
    # 구현되어 있지 않다면, 이전처럼 수동으로 딕셔너리를 만들어야 합니다.
    return jsonify([content.to_dict() for content in contents])


@content_bp.route('/history/<int:content_id>', methods=['DELETE'])
@login_required
def delete_content(content_id):
    """특정 content_id에 해당하는 콘텐츠를 데이터베이스에서 삭제합니다."""
    content = db.session.query(Content).filter_by(id=content_id, user_id=current_user.id).first_or_404()
    db.session.delete(content)
    db.session.commit()
    flash('콘텐츠가 성공적으로 삭제되었습니다.', 'success')
    return jsonify({"message": f"Content with ID {content_id} deleted."}), 200


@content_bp.route('/history/clear_all', methods=['DELETE'])
@login_required
def clear_all_history():
    """현재 로그인된 사용자의 모든 콘텐츠 기록을 삭제합니다."""
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
def get_content_detail(content_id):
    """특정 content_id에 해당하는 콘텐츠의 상세 내용을 JSON 형태로 반환합니다."""
    content = db.session.query(Content).filter_by(id=content_id, user_id=current_user.id).first_or_404()
    return jsonify(content.to_dict())


@content_bp.route('/history/<int:content_id>', methods=['PUT'])
@login_required
def update_content(content_id):
    """특정 content_id에 해당하는 콘텐츠의 내용을 업데이트합니다."""
    content = db.session.query(Content).filter_by(id=content_id, user_id=current_user.id).first_or_404()
    data = request.json
    updated_text = data.get('generated_text')
    
    if not updated_text:
        return jsonify({"error": "업데이트할 콘텐츠 내용이 없습니다."}), 400

    content.generated_text = updated_text
    db.session.commit()
    flash('콘텐츠가 성공적으로 업데이트되었습니다.', 'success')
    return jsonify({"message": "콘텐츠가 성공적으로 업데이트되었습니다."}), 200