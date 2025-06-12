# ai-content-marketing-tool/routes/knowledge_base_routes.py

from flask import request, jsonify, Blueprint, current_app, render_template
from flask_login import login_required
import numpy as np
import os
import logging

# services/ 디렉토리 내의 모듈들의 임포트 경로를 수정합니다.
from services.ai_rag.rag_system import get_rag_system, init_rag_system
from services.ai_rag.ai_service import get_ai_content_generator
from services.web_crawling.web_content_extractor import extract_text_from_url
from services.web_crawling.web_utils import sanitize_filename
from services.web_crawling.crawler_tasks import perform_marketing_crawl_task

logger = logging.getLogger(__name__)

knowledge_base_bp = Blueprint('knowledge_base_routes', __name__)


# --- API 라우트 구현 ---

@knowledge_base_bp.route('/', methods=['GET'])
@login_required
def manage_knowledge_base():
    """지식 베이스 관리 페이지를 렌더링합니다."""
    return render_template('knowledge_base_manager.html')


@knowledge_base_bp.route('/files', methods=['GET'])
@login_required
def list_knowledge_base_files():
    """현재 지식 베이스 디렉토리 내의 파일 목록을 조회하여 JSON 형태로 반환합니다."""
    KNOWLEDGE_BASE_DIR = os.path.join(current_app.root_path, 'knowledge_base')
    
    files = []
    if not os.path.exists(KNOWLEDGE_BASE_DIR):
        return jsonify({"files": [], "message": "지식 베이스 디렉토리가 존재하지 않습니다."}), 200

    try:
        for root, _, filenames in os.walk(KNOWLEDGE_BASE_DIR):
            for filename in filenames:
                if filename.endswith(".txt"):
                    relative_path = os.path.relpath(os.path.join(root, filename), KNOWLEDGE_BASE_DIR)
                    files.append(relative_path)
        return jsonify({"files": files}), 200
    except Exception as e:
        logger.error(f"지식 베이스 파일 목록 조회 오류: {e}", exc_info=True)
        return jsonify({"error": "지식 베이스 파일 목록을 가져오는 중 오류가 발생했습니다."}), 500

@knowledge_base_bp.route('/delete/<path:filename>', methods=['DELETE'])
@login_required
def delete_knowledge_base_file(filename):
    """특정 filename에 해당하는 지식 베이스 파일을 삭제하고, RAG 시스템을 재로드합니다."""
    KNOWLEDGE_BASE_DIR = os.path.join(current_app.root_path, 'knowledge_base')
    
    target_filepath = os.path.abspath(os.path.join(KNOWLEDGE_BASE_DIR, filename))
    if not os.path.commonpath([KNOWLEDGE_BASE_DIR, target_filepath]) == KNOWLEDGE_BASE_DIR:
        logger.warning(f"경로 조작 시도 감지: {filename}")
        return jsonify({"error": "잘못된 파일명입니다."}), 400

    if not os.path.exists(target_filepath):
        return jsonify({"error": "파일을 찾을 수 없습니다."}), 404
    
    try:
        os.remove(target_filepath)
        logger.info(f"File '{filename}' deleted from {target_filepath}.")

        bedrock_runtime_client = current_app.extensions['rag_bedrock_runtime']
        init_rag_system(bedrock_runtime_client)
        
        return jsonify({"message": f"파일 '{filename}'이 삭제되고 지식 베이스가 업데이트되었습니다."}), 200
    except Exception as e:
        logger.error(f"지식 베이스 파일 삭제 및 RAG 재로드 오류: {e}", exc_info=True)
        return jsonify({"error": f"파일 삭제 및 지식 베이스 업데이트 중 오류가 발생했습니다: {e}"}), 500

# --- 새로운 라우트 추가: 모든 지식 베이스 파일 삭제 ---
@knowledge_base_bp.route('/clear_all_files', methods=['DELETE'])
@login_required
def clear_all_knowledge_base_files():
    """현재 모든 지식 베이스 파일(텍스트 파일만)을 삭제하고, RAG 시스템을 재로드합니다."""
    KNOWLEDGE_BASE_DIR = os.path.join(current_app.root_path, 'knowledge_base')
    
    deleted_count = 0
    try:
        if os.path.exists(KNOWLEDGE_BASE_DIR):
            for root, dirs, files in os.walk(KNOWLEDGE_BASE_DIR, topdown=False):
                for file in files:
                    if file.endswith(".txt"):
                        filepath = os.path.join(root, file)
                        os.remove(filepath)
                        deleted_count += 1
                for dir_name in dirs:
                    dir_path = os.path.join(root, dir_name)
                    if not os.listdir(dir_path):
                        os.rmdir(dir_path)

        logger.info(f"{deleted_count}개의 지식 베이스 파일이 성공적으로 삭제되었습니다.")

        bedrock_runtime_client = current_app.extensions['rag_bedrock_runtime']
        init_rag_system(bedrock_runtime_client)

        return jsonify({"message": f"모든 지식 베이스 파일({deleted_count}개)이 성공적으로 삭제되고 지식 베이스가 업데이트되었습니다."}), 200
    except Exception as e:
        logger.error(f"모든 지식 베이스 파일 삭제 중 오류 발생: {e}", exc_info=True)
        return jsonify({"error": "모든 지식 베이스 파일 삭제 중 오류가 발생했습니다."}), 500


@knowledge_base_bp.route('/add_from_url', methods=['POST'])
@login_required
def add_knowledge_base_from_url():
    """주어진 URL에서 기사 내용을 추출하고 지식 베이스 디렉토리에 .txt 파일로 저장합니다.
    가장 가까운 업종 디렉토리를 찾아 저장합니다. 이후 RAG 시스템을 재로드합니다.
    """
    KNOWLEDGE_BASE_DIR = os.path.join(current_app.root_path, 'knowledge_base')
    os.makedirs(KNOWLEDGE_BASE_DIR, exist_ok=True)

    data = request.json
    url = data.get('url')

    if not url:
        return jsonify({"error": "URL이 필요합니다."}), 400
    
    logger.info(f"URL로부터 지식 베이스 추가 시도: {url}")
    try:
        # 1. URL에서 기사 내용 추출
        article_content_data = extract_text_from_url(url)
        if not article_content_data:
            return jsonify({"error": "URL에서 콘텐츠를 추출할 수 없습니다. 유효한 URL인지 확인해주세요."}), 400
        
        article_title = article_content_data['title']
        article_content_str = article_content_data['content']
        
        base_filename = sanitize_filename(article_title, url)
        
        # 2. AIContentGenerator 인스턴스 가져오기 (업종 임베딩 비교용)
        ai_generator = get_ai_content_generator()
        if ai_generator is None:
            logger.error("AIContentGenerator 인스턴스를 가져올 수 없습니다. 업종 분류 기능이 작동하지 않습니다.")
            closest_industry_folder = "" # AI 서비스 초기화 실패 시 기본 디렉토리에 저장
        else:
            # 3. 추출된 콘텐츠의 임베딩 생성
            content_embedding = ai_generator.rag_system.get_embedding(article_content_str)
            if content_embedding is None:
                logger.warning(f"콘텐츠 임베딩 생성 실패: {url}. 업종 분류 대신 기본 디렉토리에 저장합니다.")
                closest_industry_folder = ""
            else:
                # 4. 가장 가까운 업종 찾기
                closest_industry = ""
                max_similarity = -1.0
                

                if hasattr(ai_generator, 'embedding_manager') and ai_generator.embedding_manager.industry_embeddings:
                    for industry_name, industry_emb in ai_generator.embedding_manager.industry_embeddings.items():
                        if industry_emb is not None:
                            similarity = np.dot(content_embedding, industry_emb) / \
                                         (np.linalg.norm(content_embedding) * np.linalg.norm(industry_emb))
                            
                            if similarity > max_similarity:
                                max_similarity = similarity
                                closest_industry = industry_name
                    
                    if max_similarity < 0.5:
                        logger.info(f"업종 분류 유사도 낮음 ({max_similarity:.2f}) for URL: {url}. 기본 디렉토리에 저장합니다.")
                        closest_industry_folder = ""
                    else:
                        closest_industry_folder = closest_industry
                        logger.info(f"URL '{url}'의 콘텐츠가 '{closest_industry}' 업종으로 분류되었습니다 (유사도: {max_similarity:.2f}).")
                else:
                    logger.warning("AIContentGenerator의 embedding_manager가 초기화되지 않았거나 업종 임베딩이 없습니다. 기본 디렉토리에 저장합니다.")
                    closest_industry_folder = ""


        # 5. 파일 저장 경로 결정 및 저장
        target_dir = os.path.join(KNOWLEDGE_BASE_DIR, closest_industry_folder)
        os.makedirs(target_dir, exist_ok=True)

        final_filename = base_filename
        filepath = os.path.join(target_dir, final_filename)

        counter = 1
        while os.path.exists(filepath):
            name, ext = os.path.splitext(base_filename)
            final_filename = f"{name}_{counter}{ext}"
            filepath = os.path.join(target_dir, final_filename)
            counter += 1

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(article_content_str)
        
        logger.info(f"URL '{url}'의 콘텐츠가 '{closest_industry_folder}/{final_filename}'으로 저장되었습니다.")

        # 6. RAG 시스템 재로드
        bedrock_runtime_client = current_app.extensions['rag_bedrock_runtime']
        init_rag_system(bedrock_runtime_client)
        
        return jsonify({"message": f"URL '{url}'에서 콘텐츠를 가져와 지식 베이스에 추가했습니다 ('{closest_industry_folder}/{final_filename}'). 지식 베이스가 업데이트되었습니다."}), 200

    except Exception as e:
        logger.error(f"URL로부터 지식 베이스 추가 오류: {e}", exc_info=True)
        return jsonify({"error": f"URL에서 콘텐츠를 가져오는 중 오류가 발생했습니다: {e}"}), 500
    
@knowledge_base_bp.route('/crawl_marketing_news/manual', methods=['POST'])
#@login_required # 운영자가 UI에서 클릭할 것이므로 로그인 필요
def crawl_marketing_news_manual():
    """
    수동으로 마케팅 뉴스 크롤링 작업을 즉시 트리거하는 API 엔드포인트.
    """
    logger.info("API 요청으로 수동 뉴스 크롤링 작업 트리거됨.")
    
    result = perform_marketing_crawl_task()
    
    if "error" in result:
        return jsonify(result), 500
    else:
        return jsonify(result), 200