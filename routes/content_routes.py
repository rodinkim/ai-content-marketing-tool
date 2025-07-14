# ai-content-marketing-tool/routes/content_routes.py

import os
import uuid
from flask import render_template, request, jsonify, Blueprint, flash, current_app, send_from_directory
from services.ai_rag.ai_service import get_ai_content_generator
from models import Content 
from flask_login import login_required, current_user
from extensions import db
import logging

# Bedrock 모델 호출 Provider 임포트
# services.ai_rag.llm_invoker에서 Claude와 이미지 생성 Provider를 임포트합니다.
# BedrockStableDiffusionProvider 대신 BedrockImageGeneratorProvider를 임포트합니다.
from services.ai_rag.llm_invoker import BedrockClaudeProvider, BedrockImageGeneratorProvider 

logger = logging.getLogger(__name__)

content_bp = Blueprint('content_routes', __name__) 

# 생성된 이미지를 저장할 디렉토리 (Config에서 설정)
IMAGE_SAVE_DIR = "generated_images" 

# 정적 파일 서빙을 위한 라우트 (생성된 이미지 확인용)
@content_bp.route(f'/{IMAGE_SAVE_DIR}/<path:filename>')
def serve_generated_image(filename):
    """생성된 이미지를 정적 파일로 서빙합니다."""
    return send_from_directory(os.path.join(current_app.root_path, IMAGE_SAVE_DIR), filename)


@content_bp.route('/content')
@login_required
def content_page():
    """로그인한 사용자를 위한 메인 콘텐츠 생성 페이지를 렌더링합니다."""
    return render_template('content.html')

@content_bp.route('/generate_content', methods=['POST'])
@login_required
def generate_text_content():
    """사용자 입력 기반으로 RAG와 LLM을 활용하여 마케팅 콘텐츠를 생성하고 저장합니다."""
    user_id = current_user.id

    data = request.json
    topic = data.get('topic')
    industry = data.get('industry')
    content_type = data.get('content_type')
    tone = data.get('tone')
    length = data.get('length')
    seo_keywords = data.get('seo_keywords')

    blog_style = data.get('blog_style')
    email_subject = data.get('email_subject')
    target_audience = data.get('target_audience')
    email_type = data.get('email_type')
    key_points = data.get('key_points')
    landing_page_url = data.get('landing_page_url')

    if not all([topic, industry, content_type, tone, length]):
        logger.warning(f"콘텐츠 생성 필수 필드 누락: {data}")
        return jsonify({"error": "모든 필수 필드를 입력해주세요."}), 400
    
    final_content_type = content_type 

    if content_type == 'email':
        if not email_type:
            logger.warning(f"email_type is required for content_type 'email': {data}")
            return jsonify({"error": "이메일 유형(뉴스레터/프로모션)을 선택해주세요."}), 400
        
        final_content_type = f"email_{email_type}"
        
    elif content_type == 'blog':
        if not blog_style:
            return jsonify({"error": "블로그 스타일을 선택해주세요."}), 400
        final_content_type = f"blog_{blog_style}"
    elif content_type == 'sns_image':
        logger.warning(f"Unsupported content_type '{content_type}' for this endpoint.")
        return jsonify({"error": "이 엔드포인트는 텍스트 콘텐츠 생성만 지원합니다. 이미지 생성을 위해서는 /generate-image 엔드포인트를 사용해주세요."}), 400


    try:
        ai_generator = get_ai_content_generator()

        if ai_generator is None:
            logger.critical("AI Content Generator is not initialized. Cannot generate content.")
            return jsonify({"error": "AI 서비스 초기화 오류. 관리자에게 문의하세요."}), 503

        # Bedrock Claude Provider 인스턴스 생성 및 호출
        bedrock_runtime_client = current_app.extensions.get('rag_bedrock_runtime')
        if not bedrock_runtime_client:
            return jsonify({"error": "Bedrock client is not initialized. Please check server logs."}), 500
        
        claude_provider = BedrockClaudeProvider(bedrock_runtime_client)
        model_id = current_app.config.get('BEDROCK_CLAUDE_SONNET_MODEL_ID', 'anthropic.claude-3-5-sonnet-20240620-v1:0')

        generated_text = claude_provider.invoke(
            prompt=ai_generator.generate_prompt( # ai_generator의 프롬프트 생성 로직 사용
                topic=topic, industry=industry, content_type=final_content_type,
                blog_style=blog_style, tone=tone, length=length,
                seo_keywords=seo_keywords, email_subject=email_subject,
                target_audience=target_audience, email_type=email_type,
                key_points=key_points, landing_page_url=landing_page_url
            ),
            model_id=model_id,
            max_tokens=2000,
            temperature=0.7,
            top_p=0.9
        )
        
        new_content = Content(
            user_id=user_id,
            topic=topic,
            industry=industry,
            content_type=content_type, 
            blog_style=blog_style,
            tone=tone,
            length_option=length,
            seo_keywords=seo_keywords,
            generated_text=generated_text,
            email_subject=email_subject,
            target_audience=target_audience,
            email_type=email_type,
            key_points=key_points,
            landing_page_url=landing_page_url
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

@content_bp.route('/generate-image', methods=['POST'])
@login_required 
def generate_image_content():
    """
    Bedrock 이미지 생성 모델을 사용하여 SNS용 이미지를 생성합니다.
    """
    data = request.json
    if not data or 'prompt' not in data:
        return jsonify({"error": "Image prompt is required."}), 400

    prompt_text = data['prompt']
    
    width = data.get('width', 1024)
    height = data.get('height', 1024)

    # Bedrock 이미지 생성 Provider 인스턴스 생성
    bedrock_runtime_client = current_app.extensions.get('rag_bedrock_runtime')
    if not bedrock_runtime_client:
        return jsonify({"error": "Bedrock client is not initialized. Please check server logs."}), 500
    
    # BedrockStableDiffusionProvider 대신 BedrockImageGeneratorProvider를 사용합니다.
    image_generator_provider = BedrockImageGeneratorProvider(bedrock_runtime_client) 

    # 이미지 생성 모델 ID 설정 (config.py에서 가져옴)
    model_id = current_app.config.get('IMAGE_GENERATION_MODEL_ID', 'stability.stable-image-core-v1:1')

    logger.info(f"Generating image content for user {current_user.id} with prompt: {prompt_text[:50]}...")

    try:
        # 이미지 생성 Provider의 invoke 메서드 호출
        image_bytes = image_generator_provider.invoke(
            prompt=prompt_text, 
            model_id=model_id,
            width=width,
            height=height,
            # Stable Image Core에 맞는 추가 파라미터 (선택 사항)
            cfg_scale=7.0, 
            seed=0,
            steps=50,
            output_format='png',
            aspect_ratio='1:1'
        )

        if image_bytes:
            image_filename = f"sns_image_{uuid.uuid4().hex}.png"
            output_path = os.path.join(current_app.root_path, IMAGE_SAVE_DIR, image_filename)
            
            try:
                with open(output_path, 'wb') as f:
                    f.write(image_bytes)
                logger.info(f"Image saved to {output_path}")
            except IOError as e:
                logger.error(f"Failed to save image to disk: {e}", exc_info=True)
                return jsonify({"status": "error", "message": "Failed to save generated image to disk."}), 500

            image_url = f"/{IMAGE_SAVE_DIR}/{image_filename}"
            
            # DB에 이미지 정보 저장 (Content 모델에 이미지 URL 필드가 필요할 수 있습니다)
            # Content 모델에 generated_image_url 필드를 추가하는 것을 강력히 권장합니다.
            # 예시:
            # new_image_content = Content(
            #     user_id=current_user.id,
            #     content_type='sns_image',
            #     topic=prompt_text, 
            #     generated_image_url=image_url 
            # )
            # db.session.add(new_image_content)
            # db.session.commit()
            # logger.info(f"Image content saved to DB: ID {new_image_content.id}, URL {image_url}")

            return jsonify({
                "status": "success",
                "prompt_used": prompt_text,
                "image_url": image_url
            })
        else:
            return jsonify({"status": "error", "message": "Failed to generate image content: No image data returned."}), 500

    except RuntimeError as e:
        logger.error(f"Image generation failed: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500
    except Exception as e:
        logger.error(f"An unexpected error occurred during image generation: {e}", exc_info=True)
        return jsonify({"status": "error", "message": "An unexpected server error occurred."}), 500


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
            "blog_style": content.blog_style,
            "tone": content.tone,
            "length": content.length_option,
            "seo_keywords": content.seo_keywords,
            "content": content.generated_text,
            "timestamp": content.timestamp.isoformat(),
            "email_subject": content.email_subject,
            "target_audience": content.target_audience,
            "email_type": content.email_type,
            "key_points": content.key_points,
            "landing_page_url": content.landing_page_url,
            # "generated_image_url": content.generated_image_url # 이미지 URL 필드가 있다면 추가
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
        "blog_style": content.blog_style,
        "tone": content.tone,
        "length": content.length_option,
        "seo_keywords": content.seo_keywords,
        "content": content.generated_text,
        "timestamp": content.timestamp.isoformat(),
        "email_subject": content.email_subject,
        "target_audience": content.target_audience,
        "email_type": content.email_type,
        "key_points": content.key_points,
        "landing_page_url": content.landing_page_url,
        # "generated_image_url": content.generated_image_url # 이미지 URL 필드가 있다면 추가
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
        return jsonify({"error": "콘텐츠 업데이트 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요."}), 