# ai-content-marketing-tool/routes/knowledge_base_routes.py

from flask import request, jsonify, Blueprint, current_app, render_template
from flask_login import login_required, current_user 
import numpy as np
import os
import logging
import re

# services/ 디렉토리 내의 모듈들의 임포트 경로를 수정합니다.
from services.ai_rag.rag_system import get_rag_system, init_rag_system
from services.ai_rag.ai_service import get_ai_content_generator
from services.web_crawling.web_content_extractor import extract_text_from_url
from services.web_crawling.web_utils import sanitize_filename
from services.web_crawling.crawler_tasks import perform_marketing_crawl_task

logger = logging.getLogger(__name__)

knowledge_base_bp = Blueprint('knowledge_base_routes', __name__)

# --- 헬퍼 함수: 사용자 폴더 이름 가져오기 ---
def get_user_folder_name(username_raw):
    """주어진 사용자 이름을 파일 시스템에 안전한 폴더 이름으로 반환합니다."""
    if not username_raw:
        return "default_user"
    user_folder_name = re.sub(r'[^a-zA-Z0-9가-힣_-]', '', username_raw).strip()
    return user_folder_name if user_folder_name else "default_user"


# --- API 라우트 구현 ---

@knowledge_base_bp.route('/', methods=['GET'])
@login_required
def manage_knowledge_base():
    """지식 베이스 관리 페이지를 렌더링합니다. 관리자 여부를 템플릿에 전달합니다."""
    is_admin = current_user.username == current_app.config.get('ADMIN_USERNAME')
    return render_template('knowledge_base_manager.html', is_admin=is_admin)



@knowledge_base_bp.route('/users', methods=['GET'])
@login_required
def list_all_users_for_admin():
    """
    관리자 계정만 모든 사용자의 지식 베이스 폴더 목록을 조회할 수 있도록 합니다.
    각 폴더 이름은 사용자를 의미합니다.
    """
    admin_username = current_app.config.get('ADMIN_USERNAME')
    
    if current_user.username != admin_username:
        logger.warning(f"비관리자 계정 '{current_user.username}'이(가) 사용자 목록 조회를 시도했습니다.")
        return jsonify({"error": "접근 권한이 없습니다."}), 403

    KNOWLEDGE_BASE_DIR = os.path.join(current_app.root_path, 'knowledge_base')
    users = []
    
    if not os.path.exists(KNOWLEDGE_BASE_DIR):
        logger.info("지식 베이스 루트 디렉토리가 존재하지 않아 사용자 목록이 비어 있습니다.")
        return jsonify({"users": [], "message": "지식 베이스 디렉토리가 존재하지 않습니다."}), 200

    try:
        for item_name in os.listdir(KNOWLEDGE_BASE_DIR):
            item_path = os.path.join(KNOWLEDGE_BASE_DIR, item_name)
            if os.path.isdir(item_path):
                users.append(item_name) # 폴더 이름 (사용자명)만 반환
        
        logger.info(f"관리자 '{current_user.username}'이(가) 모든 사용자 폴더 목록({len(users)}개)을 조회했습니다.")
        return jsonify({"users": users}), 200
    except Exception as e:
        logger.error(f"관리자 사용자 목록 조회 오류: {e}", exc_info=True)
        return jsonify({"error": "사용자 목록을 가져오는 중 오류가 발생했습니다."}), 500



@knowledge_base_bp.route('/files', methods=['GET'])
@knowledge_base_bp.route('/files/<string:target_username>', methods=['GET']) 
@login_required
def list_knowledge_base_files(target_username=None):
    """
    현재 로그인한 사용자의 지식 베이스 루트 폴더 ('knowledge_base/<username>/') 내의
    .txt 파일 목록을 조회합니다. 관리자 계정일 경우, target_username을 통해
    다른 사용자의 지식 베이스를 조회하거나 (target_username 지정 시),
    모든 사용자의 파일을 통합하여 조회할 수 있습니다 (target_username이 None일 때).
    """
    KNOWLEDGE_BASE_DIR = os.path.join(current_app.root_path, 'knowledge_base')
    
    current_user_name = str(current_user.username)
    admin_username = current_app.config.get('ADMIN_USERNAME')

    files = [] # 최종 반환될 파일 목록

    # 관리자 여부 확인
    is_current_user_admin = (current_user_name == admin_username)

    if is_current_user_admin and not target_username:
        # 관리자가 특정 사용자 지정 없이 '/files'를 요청했을 때, 모든 사용자의 파일 조회
        logger.info(f"관리자 '{current_user_name}'이(가) 모든 사용자의 지식 베이스 파일을 통합 조회합니다.")
        
        if not os.path.exists(KNOWLEDGE_BASE_DIR):
            logger.info("지식 베이스 루트 디렉토리가 존재하지 않아 모든 파일 목록이 비어 있습니다.")
            return jsonify({"files": [], "message": "지식 베이스 디렉토리가 존재하지 않습니다."}), 200

        try:
            # knowledge_base/ 바로 아래 모든 사용자 폴더를 탐색
            for user_folder_item in os.listdir(KNOWLEDGE_BASE_DIR):
                user_folder_path = os.path.join(KNOWLEDGE_BASE_DIR, user_folder_item)
                
                if os.path.isdir(user_folder_path): # 이게 사용자 폴더인 경우
                    # 해당 사용자 폴더 내의 .txt 파일들만 가져옵니다.
                    for item_name in os.listdir(user_folder_path):
                        item_path = os.path.join(user_folder_path, item_name)
                        if os.path.isfile(item_path) and item_name.endswith(".txt"):
                            # 파일 목록에 '사용자명/파일명.txt' 형태로 추가
                            files.append(os.path.join(user_folder_item, item_name))
            
            logger.info(f"관리자 '{current_user_name}'의 통합 지식 베이스 파일 목록 조회: {len(files)}개 파일 발견.")
            return jsonify({"files": files}), 200

        except Exception as e:
            logger.error(f"관리자 통합 지식 베이스 파일 목록 조회 오류: {e}", exc_info=True)
            return jsonify({"error": "통합 지식 베이스 파일 목록을 가져오는 중 오류가 발생했습니다."}), 500

    else:
        # 일반 사용자 또는 관리자가 특정 사용자를 지정하여 조회
        # target_username이 있다면 그 사용자, 없다면 현재 사용자의 파일을 조회
        actual_username_for_path = target_username if target_username else current_user_name

        # 관리자가 아니면서 다른 사용자를 지정하려고 시도하는 경우 차단
        if not is_current_user_admin and target_username and target_username != current_user_name:
            logger.warning(f"비관리자 계정 '{current_user_name}'이(가) '{target_username}'의 파일 조회를 시도했습니다. (권한 없음)")
            return jsonify({"error": "다른 사용자의 파일을 조회할 권한이 없습니다."}), 403
        
        logger.info(f"사용자 '{current_user_name}'이(가) '{actual_username_for_path}'의 지식 베이스를 조회합니다.")

        user_folder_name = get_user_folder_name(actual_username_for_path)
        user_knowledge_base_dir = os.path.join(KNOWLEDGE_BASE_DIR, user_folder_name)
        
        if not os.path.exists(user_knowledge_base_dir):
            logger.info(f"조회 대상 사용자 '{user_folder_name}'의 지식 베이스 디렉토리가 존재하지 않습니다.")
            return jsonify({"files": [], "message": f"'{user_folder_name}' 사용자의 지식 베이스 디렉토리가 존재하지 않습니다."}), 200

        try:
            for item_name in os.listdir(user_knowledge_base_dir):
                item_path = os.path.join(user_knowledge_base_dir, item_name)
                if os.path.isfile(item_path) and item_name.endswith(".txt"):
                    # 관리자 통합 조회와는 다르게, 여기서는 '제목.txt' 형태로 반환
                    # 프론트엔드에서 adminFileList와 fileList의 렌더링 로직을 통일하기 위함
                    if is_current_user_admin and target_username: # 관리자가 특정 유저 조회 시
                        files.append(os.path.join(user_folder_name, item_name)) # 'username/filename.txt'
                    else: # 일반 사용자 자신의 조회 시
                        files.append(item_name) # 'filename.txt'
            
            logger.info(f"사용자 '{user_folder_name}'의 지식 베이스 파일 목록 조회: {len(files)}개 파일 발견.")
            return jsonify({"files": files}), 200
        except Exception as e:
            logger.error(f"'{user_folder_name}' 사용자의 지식 베이스 파일 목록 조회 오류: {e}", exc_info=True)
            return jsonify({"error": "지식 베이스 파일 목록을 가져오는 중 오류가 발생했습니다."}), 500



@knowledge_base_bp.route('/delete/<path:filename>', methods=['DELETE'])
@knowledge_base_bp.route('/delete/<string:target_username>/<path:filename>', methods=['DELETE'])
@login_required
def delete_knowledge_base_file(filename, target_username=None):
    """
    특정 filename에 해당하는 지식 베이스 파일을 삭제합니다.
    관리자는 target_username을 지정하여 다른 사용자의 파일을 삭제할 수 있습니다.
    filename은 '제목.txt' 또는 'username/제목.txt' 형태일 수 있습니다.
    """
    KNOWLEDGE_BASE_DIR = os.path.join(current_app.root_path, 'knowledge_base')
    
    current_user_name = str(current_user.username)
    admin_username = current_app.config.get('ADMIN_USERNAME')
    is_current_user_admin = (current_user_name == admin_username)

    actual_filepath = "" # 실제로 삭제할 파일의 전체 경로
    
    if is_current_user_admin and target_username:
        # 관리자가 특정 사용자 파일 삭제 요청
        actual_username_for_path = target_username
        logger.info(f"관리자 '{current_user_name}'이(가) 사용자 '{target_username}'의 파일 '{filename}' 삭제를 시도합니다.")
    elif is_current_user_admin and not target_username and '/' in filename:
        # 관리자가 통합 목록에서 직접 'user/file.txt' 형태의 파일을 삭제 요청
        parts = filename.split('/', 1) # 'username/filename.txt'를 분리
        actual_username_for_path = parts[0]
        filename = parts[1] # 순수 파일명만 남김
        logger.info(f"관리자 '{current_user_name}'이(가) 통합 목록에서 사용자 '{actual_username_for_path}'의 파일 '{filename}' 삭제를 시도합니다.")
    else:
        # 일반 사용자 또는 관리자 자신의 파일 삭제 요청
        actual_username_for_path = current_user_name
        logger.info(f"사용자 '{current_user_name}'이(가) 자신의 파일 '{filename}' 삭제를 시도합니다.")

    # 일반 사용자가 다른 사용자 파일을 삭제 시도하는 경우 차단
    if not is_current_user_admin and actual_username_for_path != current_user_name:
        logger.warning(f"비관리자 계정 '{current_user_name}'이(가) '{actual_username_for_path}'의 파일 삭제를 시도했습니다. (권한 없음)")
        return jsonify({"error": "다른 사용자의 파일을 삭제할 권한이 없습니다."}), 403

    user_folder_name = get_user_folder_name(actual_username_for_path)
    user_specific_knowledge_base_dir = os.path.abspath(os.path.join(KNOWLEDGE_BASE_DIR, user_folder_name))
    requested_filepath = os.path.abspath(os.path.join(user_specific_knowledge_base_dir, filename))

    # 보안 검증: 요청된 파일 경로가 해당 사용자의 지식 베이스 디렉토리 내에 있는지 확인
    if not requested_filepath.startswith(user_specific_knowledge_base_dir + os.sep):
        logger.warning(f"경로 조작 또는 권한 없는 파일 삭제 시도: '{actual_username_for_path}' 폴더 외부 파일 '{filename}' 삭제 시도. (대상: {requested_filepath})")
        return jsonify({"error": "잘못된 파일명입니다."}), 400

    if not os.path.exists(requested_filepath):
        return jsonify({"error": "파일을 찾을 수 없습니다."}), 404
    
    try:
        os.remove(requested_filepath)
        logger.info(f"파일 '{requested_filepath}'이(가) 성공적으로 삭제되었습니다.")

        bedrock_runtime_client = current_app.extensions['rag_bedrock_runtime']
        init_rag_system(bedrock_runtime_client)
        
        return jsonify({"message": f"파일 '{filename}'이 삭제되고 지식 베이스가 업데이트되었습니다."}), 200
    except Exception as e:
        logger.error(f"지식 베이스 파일 삭제 및 RAG 재로드 오류: {e}", exc_info=True)
        return jsonify({"error": f"파일 삭제 및 지식 베이스 업데이트 중 오류가 발생했습니다: {e}"}), 500



@knowledge_base_bp.route('/clear_all_files', methods=['DELETE'])
@knowledge_base_bp.route('/clear_all_files/<string:target_username>', methods=['DELETE']) 
@login_required
def clear_all_knowledge_base_files(target_username=None):
    """
    현재 로그인한 사용자의 지식 베이스 루트 폴더 내의 모든 .txt 파일을 삭제합니다.
    관리자는 target_username을 지정하여 다른 사용자의 모든 .txt 파일을 삭제할 수 있습니다.
    하위 디렉토리는 삭제하지 않습니다.
    """
    KNOWLEDGE_BASE_DIR = os.path.join(current_app.root_path, 'knowledge_base')
    
    current_user_name = str(current_user.username)
    admin_username = current_app.config.get('ADMIN_USERNAME')
    is_current_user_admin = (current_user_name == admin_username)

    # 삭제 대상 사용자 이름 결정 및 권한 확인
    if target_username:
        # target_username이 명시되었지만 현재 사용자가 관리자가 아니라면 접근 거부
        if not is_current_user_admin:
            logger.warning(f"비관리자 계정 '{current_user_name}'이(가) '{target_username}'의 모든 파일 삭제를 시도했습니다. (권한 없음)")
            return jsonify({"error": "다른 사용자의 모든 파일을 삭제할 권한이 없습니다."}), 403
        actual_username_for_path = target_username
        logger.info(f"관리자 '{current_user_name}'이(가) 사용자 '{target_username}'의 모든 파일을 삭제합니다.")
    else:
        # target_username이 없으면 일반 사용자 또는 관리자 자신의 모든 파일 삭제
        actual_username_for_path = current_user_name
        logger.info(f"사용자 '{current_user_name}'이(가) 자신의 모든 파일을 삭제합니다.")

    user_folder_name = get_user_folder_name(actual_username_for_path)
    user_knowledge_base_dir = os.path.join(KNOWLEDGE_BASE_DIR, user_folder_name)

    deleted_count = 0
    try:
        if os.path.exists(user_knowledge_base_dir):
            for item_name in os.listdir(user_knowledge_base_dir):
                item_path = os.path.join(user_knowledge_base_dir, item_name)
                if os.path.isfile(item_path) and item_name.endswith(".txt"):
                    os.remove(item_path)
                    deleted_count += 1
                elif os.path.isdir(item_path):
                    logger.info(f"사용자 '{user_folder_name}' 폴더 내 하위 디렉토리 '{item_name}'은(는) 삭제하지 않고 건너뜁니다.")

        logger.info(f"사용자 '{actual_username_for_path}'의 지식 베이스 파일 {deleted_count}개가 성공적으로 삭제되었습니다.")

        bedrock_runtime_client = current_app.extensions['rag_bedrock_runtime']
        init_rag_system(bedrock_runtime_client)

        return jsonify({"message": f"사용자 '{actual_username_for_path}'의 모든 지식 베이스 파일({deleted_count}개)이 성공적으로 삭제되고 지식 베이스가 업데이트되었습니다."}), 200
    except Exception as e:
        logger.error(f"사용자 '{actual_username_for_path}'의 모든 지식 베이스 파일 삭제 중 오류 발생: {e}", exc_info=True)
        return jsonify({"error": "모든 지식 베이스 파일 삭제 중 오류가 발생했습니다."}), 500



@knowledge_base_bp.route('/add_from_url', methods=['POST'])
@login_required
def add_knowledge_base_from_url():
    """
    주어진 URL에서 기사 내용을 추출하고 지식 베이스 디렉토리에 .txt 파일로 저장합니다.
    파일은 'knowledge_base/<username>/' 경로에 직접 저장됩니다.
    """
    KNOWLEDGE_BASE_DIR = os.path.join(current_app.root_path, 'knowledge_base')
    os.makedirs(KNOWLEDGE_BASE_DIR, exist_ok=True) 

    data = request.json
    url = data.get('url')

    if not url:
        return jsonify({"error": "URL이 필요합니다."}), 400
    
    if not current_user.is_authenticated:
        return jsonify({"error": "로그인이 필요합니다."}), 401
    
    username_raw = str(current_user.username)
    user_folder_name = get_user_folder_name(username_raw)
        
    logger.info(f"URL로부터 지식 베이스 추가 시도: {url} (대상 사용자 폴더: {user_folder_name})")

    try:
        article_content_data = extract_text_from_url(url)
        if not article_content_data:
            return jsonify({"error": "URL에서 콘텐츠를 추출할 수 없습니다. 유효한 URL인지 확인해주세요."}), 400
        
        article_title = article_content_data.get('title')
        article_content_str = article_content_data.get('content')
        
        logger.info(f"URL: {url} 에서 'extract_text_from_url'로 추출된 원본 제목: '{article_title}'")
        if not article_title:
            logger.warning(f"경고: URL '{url}'에서 유효한 기사 제목을 추출하지 못했습니다. 파일명이 예상과 다를 수 있습니다.")

        base_filename = sanitize_filename(article_title, url) 
        
        target_dir = os.path.join(KNOWLEDGE_BASE_DIR, user_folder_name)
        os.makedirs(target_dir, exist_ok=True) # 사용자 폴더가 없으면 생성

        final_filename = base_filename
        filepath = os.path.join(target_dir, final_filename)

        counter = 1
        while os.path.exists(filepath):
            name, ext = os.path.splitext(base_filename)
            if len(name) + len(str(counter)) + len(ext) > 255:
                name = name[:(255 - len(str(counter)) - len(ext) - 5)] + "..."
            final_filename = f"{name}_{counter}{ext}"
            filepath = os.path.join(target_dir, final_filename)
            counter += 1

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(article_content_str)
        
        logger.info(f"URL '{url}'의 콘텐츠가 '{user_folder_name}/{final_filename}'으로 저장되었습니다.")

        bedrock_runtime_client = current_app.extensions['rag_bedrock_runtime']
        init_rag_system(bedrock_runtime_client)
        
        return jsonify({"message": f"URL '{url}'에서 콘텐츠를 가져와 지식 베이스에 추가했습니다 ('{user_folder_name}/{final_filename}'). 지식 베이스가 업데이트되었습니다."}), 200

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