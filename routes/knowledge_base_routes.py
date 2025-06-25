# routes/knowledge_base_routes.py

from flask import request, jsonify, Blueprint, current_app, render_template
from flask_login import login_required, current_user 
import logging
import re
import boto3

# services/ 디렉토리 내의 모듈들을 임포트합니다.
from services.ai_rag.rag_system import init_rag_system, get_rag_system
from services.web_crawling.web_content_extractor import extract_text_from_url
from services.web_crawling.web_utils import sanitize_filename
from services.ai_rag.ai_constants import INDUSTRIES

logger = logging.getLogger(__name__)

knowledge_base_bp = Blueprint('knowledge_base_routes', __name__)

# --- 헬퍼 함수 (변경 없음) ---
def get_user_folder_name(username_raw):
    """사용자 이름을 기반으로 S3 폴더 이름을 생성하는 헬퍼 함수."""
    if not username_raw: return "default_user"
    user_folder_name = re.sub(r'[^a-zA-Z0-9가-힣_-]', '', username_raw).strip()
    return user_folder_name if user_folder_name else "default_user"

def get_s3_info():
    """S3 클라이언트와 버킷 이름을 가져오는 헬퍼 함수."""
    # 현재 Flask 애플리케이션의 S3 클라이언트와 버킷 이름을 가져옵니다.
    s3_client = current_app.extensions.get('s3_client')
    if not s3_client:
        logger.error("S3 client is not initialized.")
        raise RuntimeError("S3 client not available.")
    bucket_name = current_app.config.get('S3_BUCKET_NAME')
    if not bucket_name:
        logger.error("S3 bucket name is not configured.")
        raise RuntimeError("S3 bucket name not available.")
    return s3_client, bucket_name

# --- 페이지 렌더링 라우트 ---
@knowledge_base_bp.route('/', methods=['GET'])
@login_required
def manage_knowledge_base():
    """지식 베이스 관리 페이지 렌더링 라우트."""
    # 현재 사용자가 관리자 권한을 가지고 있는지 확인합니다.
    is_admin = current_user.username == current_app.config.get('ADMIN_USERNAME')
    return render_template('knowledge_base_manager.html', is_admin=is_admin)

# --- API 라우트 ---
@knowledge_base_bp.route('/users', methods=['GET'])
@login_required
def list_all_users_for_admin():
    """관리자만 접근할 수 있는 사용자 목록 조회 라우트."""
    admin_username = current_app.config.get('ADMIN_USERNAME')
    if current_user.username != admin_username:
        return jsonify({"error": "접근 권한이 없습니다."}), 403
    
    # 현재는 산업 목록을 관리 대상으로 반환합니다.
    return jsonify({"users": INDUSTRIES, "is_industry_list": True }), 200


@knowledge_base_bp.route('/files', methods=['GET'])
@login_required
def list_knowledge_base_files():
    """지식 베이스 파일 목록 조회 라우트."""
    """관리자 또는 사용자가 자신의 산업 폴더의 파일 목록을 조회합니다."""
    s3_client, bucket_name = get_s3_info()
    is_admin = current_user.username == current_app.config.get('ADMIN_USERNAME')
    prefix = ''

    # 관리자가 특정 대상을 필터링하는 경우
    if is_admin:
        target_type = request.args.get('target_type') # 'industry' 또는 'user'
        target_name = request.args.get('target_username') # js에서 보낸 이름
        
        if target_type == 'industry':
            prefix = f"{target_name}/"
            logger.info(f"관리자 '{current_user.username}'이(가) 산업 '{target_name}'의 파일을 조회합니다.")
        elif target_type == 'user':
            # 사용자 폴더가 없다는 전제하에, 이 로직은 거의 사용되지 않거나
            # 특정 사용자가 올린 파일을 DB 조회 후 필터링해야 하지만, 지금은 S3 prefix로만 처리합니다.
            # 이 부분은 사용자 폴더가 없으므로 사실상 빈 결과를 반환할 수 있습니다.
            prefix = f"{get_user_folder_name(target_name)}/"
            logger.info(f"관리자 '{current_user.username}'이(가) 사용자 '{target_name}'의 파일을 조회합니다.")

    try:
        paginator = s3_client.get_paginator('list_objects_v2')
        pages = paginator.paginate(Bucket=bucket_name, Prefix=prefix)
        files_from_s3 = []
        for page in pages:
            for obj in page.get('Contents', []):
                key = obj['Key']
                if not key.endswith('/'): # 폴더 자체는 제외
                    files_from_s3.append(key)
        
        returned_files_data = []
        for s3_key in files_from_s3:
            display_name = re.sub(r'_[0-9a-fA-F]{8}\.txt$', '.txt', s3_key.split('/')[-1])
            returned_files_data.append({"display_name": display_name, "s3_key": s3_key})
        
        returned_files_data.sort(key=lambda x: x['s3_key'])
        return jsonify({"files": returned_files_data}), 200
    except Exception as e:
        logger.error(f"S3 파일 목록 조회 오류: {e}", exc_info=True)
        return jsonify({"error": "파일 목록 조회 중 오류 발생"}), 500


@knowledge_base_bp.route('/delete/<path:s3_key>', methods=['DELETE'])
@login_required
def delete_knowledge_base_file(s3_key):
    """지식 베이스 파일 삭제 라우트."""
    """관리자만 S3에서 파일을 삭제할 수 있습니다."""
    is_admin = current_user.username == current_app.config.get('ADMIN_USERNAME')
    
    if not is_admin:
        logger.warning(f"권한 없음: 비관리자 '{current_user.username}'이(가) '{s3_key}' 삭제 시도.")
        return jsonify({"error": "파일을 삭제할 권한이 없습니다."}), 403

    s3_client, bucket_name = get_s3_info()
    logger.info(f"관리자 '{current_user.username}'이(가) S3 키 '{s3_key}' 삭제를 시도합니다.")

    try:
        # 1. S3에서 파일 삭제
        s3_client.delete_object(Bucket=bucket_name, Key=s3_key)
        logger.info(f"S3 객체 '{s3_key}'이(가) 성공적으로 삭제되었습니다.")
        
        # 2. RAG 시스템에서 문서 제거 함수 호출
        rag_system_instance = get_rag_system()
        if rag_system_instance:
            rag_system_instance.remove_document_from_rag_system(s3_key)
        else:
            logger.error("RAGSystem 인스턴스를 찾을 수 없습니다. 벡터 DB에서 파일을 삭제할 수 없습니다.")
            return jsonify({"error": "RAG 시스템 오류로 파일 삭제에 실패했습니다."}), 500

        filename = s3_key.split('/')[-1]
        return jsonify({"message": f"파일 '{filename}'이(가) 성공적으로 삭제되었습니다."}), 200
    except boto3.exceptions.Boto3Error as e:
        logger.error(f"S3 파일 삭제 중 오류 발생: {e}", exc_info=True)
        return jsonify({"error": "파일 삭제 중 S3 오류가 발생했습니다."}), 500
    except Exception as e:
        logger.error(f"파일 또는 벡터 삭제 중 예기치 않은 오류 발생: {e}", exc_info=True)
        return jsonify({"error": "파일 삭제 중 예기치 않은 오류가 발생했습니다."}), 500


@knowledge_base_bp.route('/add_from_url', methods=['POST'])
@login_required
def add_knowledge_base_from_url():
    """지식 베이스에 URL로부터 콘텐츠를 추가하는 라우트."""
    """사용자가 URL을 통해 콘텐츠를 추가할 수 있습니다."""
    s3_client, bucket_name = get_s3_info()

    data = request.json
    url = data.get('url')
    industry = data.get('industry', None) 

    if not url or not industry:
        return jsonify({"error": "URL과 산업(industry)이 필요합니다."}), 400

    if not current_user.is_authenticated:
        return jsonify({"error": "로그인이 필요합니다."}), 401
    
    industry_folder_name = get_user_folder_name(industry)

    logger.info(f"URL로부터 지식 베이스 추가 시도: {url} (대상 산업 폴더: {industry_folder_name}) (S3)")

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
        
        final_s3_object_key = f"{industry_folder_name}/{base_filename}" 

        message_prefix = "URL에서 콘텐츠를 가져와 지식 베이스에 추가했습니다."
        
        try:
            logger.debug(f"S3 HeadObject 호출 시도: Bucket={bucket_name}, Key={final_s3_object_key}")
            s3_client.head_object(Bucket=bucket_name, Key=final_s3_object_key)
            logger.info(f"S3 객체 '{final_s3_object_key}'이(가) 이미 존재합니다. 새 콘텐츠로 덮어씁니다.")
            message_prefix = "이미 등록된 URL입니다. 최신 정보로 업데이트했습니다." 
        except s3_client.exceptions.ClientError as e:
            http_status = e.response.get('ResponseMetadata', {}).get('HTTPStatusCode')
            if http_status == 404:
                logger.info(f"S3 객체 '{final_s3_object_key}'을(를) 찾을 수 없습니다 (HTTP 404). 새로운 파일로 업로드 진행합니다.")
            else: 
                logger.error(f"S3 HeadObject 알 수 없는 ClientError 발생 (HTTP {http_status}): {e}", exc_info=True)
                raise
        except Exception as e:
            logger.error(f"S3 HeadObject 예상치 못한 오류 발생: {e}", exc_info=True)
            raise

        s3_client.put_object(Bucket=bucket_name, Key=final_s3_object_key, Body=article_content_str.encode('utf-8'))
        logger.info(f"URL '{url}'의 콘텐츠가 S3에 '{bucket_name}/{final_s3_object_key}'으로 업로드되었습니다. (S3)")

        bedrock_runtime_client = current_app.extensions['rag_bedrock_runtime']
        
        print("\n--- current_user 객체 속성 확인 시작 ---")
        print(f"current_user.is_authenticated: {current_user.is_authenticated}")
        print(f"current_user.is_active: {current_user.is_active}")
        print(f"current_user.is_anonymous: {current_user.is_anonymous}")
        
        try:
            print(f"current_user.id: {current_user.id}")
        except AttributeError:
            print("current_user.id 속성을 찾을 수 없습니다.")
        
        try:
            print(f"current_user.username: {current_user.username}")
        except AttributeError:
            print("current_user.username 속성을 찾을 수 없습니다.")

        try:
            print(f"current_user.email: {current_user.email}")
        except AttributeError:
            print("current_user.email 속성을 찾을 수 없습니다.")
        print("--- current_user 객체 속성 확인 종료 ---\n")

        # RAG 시스템에 문서 추가 함수 호출
        rag_system_instance = get_rag_system()
        if rag_system_instance:
            rag_system_instance.add_document_to_rag_system(
                s3_key=final_s3_object_key, 
                user_id=current_user.id
            )
        else:
            logger.error("RAGSystem 인스턴스를 찾을 수 없습니다. 벡터 DB에 파일을 추가할 수 없습니다.")
            return jsonify({"error": "RAG 시스템 오류로 파일 추가에 실패했습니다."}), 500
        
        return jsonify({"message": message_prefix}), 200

    except Exception as e:
        logger.error(f"URL로부터 지식 베이스 추가 오류 (S3): {e}", exc_info=True)
        return jsonify({"error": f"URL에서 콘텐츠를 가져오는 중 오류가 발생했습니다: {e}"}), 500


@knowledge_base_bp.route('/industries', methods=['GET'])
@login_required
def get_industries():
    """ai_constants.py에 정의된 산업 목록을 반환합니다."""
    logger.info(f"'{current_user.username}' 사용자에게 상수 파일에 정의된 산업 목록을 제공합니다.")
    # 상수 파일에서 직접 INDUSTRIES 리스트를 가져와 사용합니다.
    return jsonify({"industries": INDUSTRIES}), 200