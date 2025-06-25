# routes/knowledge_base_routes.py

from flask import request, jsonify, Blueprint, current_app, render_template
from flask_login import login_required, current_user 
import logging
import re
import boto3

# services/ 디렉토리 내의 모듈들을 임포트합니다.
from services.ai_rag.rag_system import get_rag_system 
from services.web_crawling.web_content_extractor import extract_text_from_url
from services.web_crawling.web_utils import sanitize_filename
from services.ai_rag.ai_constants import INDUSTRIES
from models import User
from services.ai_rag.pgvector_store import PgVectorStore

logger = logging.getLogger(__name__)

knowledge_base_bp = Blueprint('knowledge_base_routes', __name__)

def sanitize_industry_name(username_raw):
    """
    사용자 이름을 기반으로 S3 폴더 이름(산업명)을 생성합니다.
    특수 문자를 제거하고 안전한 폴더명으로 변환합니다.
    """
    if not username_raw: 
        return "default_industry"
    user_folder_name = re.sub(r'[^a-zA-Z0-9가-힣_-]', '', username_raw).strip()
    return user_folder_name if user_folder_name else "default_industry"

def get_s3_info():
    """
    Flask 애플리케이션의 S3 클라이언트와 버킷 이름을 가져옵니다.
    초기화 여부를 확인하여 안정성을 높입니다.
    """
    s3_client = current_app.extensions.get('s3_client')
    if not s3_client:
        logger.error("S3 클라이언트가 초기화되지 않았습니다.")
        raise RuntimeError("S3 클라이언트를 사용할 수 없습니다.")
    bucket_name = current_app.config.get('S3_BUCKET_NAME')
    if not bucket_name:
        logger.error("S3 버킷 이름이 설정되지 않았습니다.")
        raise RuntimeError("S3 버킷 이름을 사용할 수 없습니다.")
    return s3_client, bucket_name

# --- 페이지 렌더링 라우트 ---
@knowledge_base_bp.route('/', methods=['GET'])
@login_required
def manage_knowledge_base():
    """지식 베이스 관리 페이지를 렌더링합니다."""
    # 현재 로그인한 사용자가 관리자인지 확인하여 페이지에 전달합니다.
    is_admin = current_user.username == current_app.config.get('ADMIN_USERNAME')
    return render_template('knowledge_base_manager.html', is_admin=is_admin)

# --- API 라우트 ---
@knowledge_base_bp.route('/users', methods=['GET'])
@login_required
def list_all_users_for_admin():
    """
    관리자 전용: 시스템에 등록된 모든 사용자 목록을 조회합니다.
    """
    admin_username = current_app.config.get('ADMIN_USERNAME')
    
    # 현재 로그인한 사용자가 관리자인지 확인
    if current_user.username != admin_username:
        logger.warning(f"접근 권한 없음: 비관리자 '{current_user.username}'이(가) 사용자 목록 조회 시도.")
        return jsonify({"error": "접근 권한이 없습니다. 관리자만 이 기능을 사용할 수 있습니다."}), 403
    
    try:
        # User 모델을 통해 모든 사용자의 사용자명(username)을 조회
        # 데이터베이스 접근 시 발생할 수 있는 예외를 처리합니다.
        all_usernames = [user.username for user in User.query.all()]
        all_usernames.sort() # 사용자명을 알파벳순으로 정렬하여 일관된 순서 제공

        logger.info(f"관리자 '{current_user.username}'이(가) 등록된 사용자 목록을 성공적으로 조회했습니다. (총 {len(all_usernames)}명)")
        
        # 실제 사용자 목록임을 나타내기 위해 'is_industry_list'를 False로 설정
        return jsonify({"users": all_usernames, "is_industry_list": False }), 200
    
    except Exception as e:
        logger.error(f"등록된 사용자 목록 조회 중 예기치 않은 오류 발생: {e}", exc_info=True)
        return jsonify({"error": "사용자 목록 조회 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요."}), 500


@knowledge_base_bp.route('/files', methods=['GET'])
@login_required
def list_knowledge_base_files():
    """
    지식 베이스 파일 목록을 조회합니다.
    관리자는 특정 산업 또는 특정 사용자가 업로드한 파일 목록을 필터링하여 조회할 수 있습니다.
    일반 사용자는 현재 자신의 파일만 조회하도록 확장할 수 있습니다 (현재는 관리자만 필터링).
    """
    s3_client, bucket_name = get_s3_info()
    is_admin = current_user.username == current_app.config.get('ADMIN_USERNAME')
    
    # S3 프리픽스 필터와 PgVector user_id 필터를 초기화합니다.
    s3_filter_prefix = ''
    pgvector_filter_user_id = None 

    # 반환할 파일 데이터 목록을 초기화합니다.
    retrieved_files_data = []

    # --- 파일 조회 필터링 로직 (관리자 전용) ---
    if is_admin:
        target_filter_type = request.args.get('target_type') # 'industry' 또는 'user'
        target_filter_name = request.args.get('target_username') # 조회할 산업명 또는 사용자명

        if target_filter_type == 'industry':
            # 산업명으로 S3 프리픽스 필터를 설정합니다.
            s3_filter_prefix = f"{target_filter_name}/"
            logger.info(f"관리자 '{current_user.username}'이(가) 산업 '{target_filter_name}'의 파일을 조회합니다. (S3 프리픽스 필터링)")
        
        elif target_filter_type == 'user':
            # 사용자명으로 PgVector DB에서 user_id를 찾아 필터링합니다.
            target_user_object = User.query.filter_by(username=target_filter_name).first()
            
            if target_user_object:
                pgvector_filter_user_id = target_user_object.id
                logger.info(f"관리자 '{current_user.username}'이(가) 사용자 '{target_filter_name}' (ID: {pgvector_filter_user_id})의 파일을 조회합니다. (PgVector DB 필터링)")
                # 사용자별 조회 시에는 S3 프리픽스 필터를 사용하지 않고, PgVector에서 직접 필터링합니다.
                s3_filter_prefix = '' 
            else:
                # 존재하지 않는 사용자를 조회하려 할 때 빈 목록을 반환하고 경고를 기록합니다.
                logger.warning(f"관리자 '{current_user.username}'이(가) 존재하지 않는 사용자 '{target_filter_name}'의 파일 조회를 시도했습니다. 빈 목록을 반환합니다.")
                return jsonify({"files": []}), 200 # 조회할 사용자가 없으면 바로 빈 목록 반환
        
        else:
            # 유효하지 않은 필터 타입인 경우 경고를 기록하고 S3 전체 파일 조회로 폴백합니다.
            logger.warning(f"관리자 '{current_user.username}'이(가) 유효하지 않은 필터 타입 '{target_filter_type}'으로 파일 조회를 시도했습니다. S3 버킷의 모든 파일을 조회합니다.")
            s3_filter_prefix = '' # 기본값 유지
            
    # --- 파일 조회 실행 로직 ---
    # PgVector user_id 필터가 설정된 경우 (즉, 관리자가 특정 사용자를 선택한 경우)
    if pgvector_filter_user_id is not None:
        try:
            # PgVectorStore 인스턴스를 가져와서 특정 user_id의 벡터 데이터를 조회합니다.
            pg_store = PgVectorStore() # PgVectorStore는 RAGSystem.pgvector_store로 접근하는 것이 더 일관적일 수 있습니다.
                                       # 하지만 이 라우트에서 직접 임포트하여 사용하는 것도 가능합니다.
            user_specific_vectors = pg_store.get_vectors_by_user_id(pgvector_filter_user_id)
            
            # 조회된 벡터 객체에서 파일 정보(s3_key, original_filename)를 추출합니다.
            for vector_entry in user_specific_vectors:
                # vector_entry는 models_vector.py의 KnowledgeBaseVector 인스턴스입니다.
                display_filename = re.sub(r'_[0-9a-fA-F]{8}\.txt$', '.txt', vector_entry.original_filename)
                retrieved_files_data.append({"display_name": display_filename, "s3_key": vector_entry.s3_key})
            
            logger.info(f"PgVector DB에서 사용자 ID '{pgvector_filter_user_id}'에 해당하는 {len(retrieved_files_data)}개의 파일을 성공적으로 조회했습니다.")

        except Exception as e:
            logger.error(f"PgVector DB에서 사용자 파일 목록 조회 중 예기치 않은 오류 발생: {e}", exc_info=True)
            return jsonify({"error": "사용자 파일 목록 조회 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요."}), 500
    
    else:
        # PgVector 필터가 없는 경우 (즉, 산업 필터링 또는 모든 S3 파일 조회)
        # 기존처럼 S3에서 직접 파일 목록을 가져옵니다.
        try:
            paginator = s3_client.get_paginator('list_objects_v2')
            pages = paginator.paginate(Bucket=bucket_name, Prefix=s3_filter_prefix)
            files_from_s3_keys = []
            for page in pages:
                for obj in page.get('Contents', []):
                    key = obj['Key']
                    if not key.endswith('/'): # 폴더 항목은 제외
                        files_from_s3_keys.append(key)
            
            for s3_key in files_from_s3_keys:
                display_filename = re.sub(r'_[0-9a-fA-F]{8}\.txt$', '.txt', s3_key.split('/')[-1])
                retrieved_files_data.append({"display_name": display_filename, "s3_key": s3_key})
            
            logger.info(f"S3에서 {len(retrieved_files_data)}개의 지식 베이스 파일 목록을 성공적으로 조회했습니다. (프리픽스: '{s3_filter_prefix}')")

        except Exception as e:
            logger.error(f"S3 파일 목록 조회 중 예기치 않은 오류 발생: {e}", exc_info=True)
            return jsonify({"error": "파일 목록 조회 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요."}), 500
    
    # 조회된 파일 데이터를 S3 키 기준으로 정렬하고 반환합니다.
    retrieved_files_data.sort(key=lambda x: x['s3_key'])
    return jsonify({"files": retrieved_files_data}), 200


@knowledge_base_bp.route('/delete/<path:s3_key>', methods=['DELETE'])
@login_required
def delete_knowledge_base_file(s3_key):
    """
    지식 베이스 파일 삭제 라우트.
    관리자만 S3에서 파일을 삭제하고, 연결된 벡터 DB 데이터(PgVector, FAISS)를 제거할 수 있습니다.
    """
    is_admin = current_user.username == current_app.config.get('ADMIN_USERNAME')
    
    if not is_admin:
        logger.warning(f"권한 없음: 비관리자 '{current_user.username}'이(가) S3 키 '{s3_key}' 삭제 시도.")
        return jsonify({"error": "파일을 삭제할 권한이 없습니다."}), 403

    s3_client, bucket_name = get_s3_info()
    logger.info(f"관리자 '{current_user.username}'이(가) S3 키 '{s3_key}' 삭제를 시도합니다.")

    try:
        # 1. S3에서 파일 삭제
        s3_client.delete_object(Bucket=bucket_name, Key=s3_key)
        logger.info(f"S3 객체 '{s3_key}'이(가) 성공적으로 삭제되었습니다.")
        
        # 2. RAG 시스템(PgVector DB 및 FAISS 인덱스)에서 문서 제거 함수 호출
        rag_system_instance = get_rag_system()
        if rag_system_instance:
            rag_system_instance.remove_document_from_rag_system(s3_key)
            logger.info(f"RAG 시스템에서 S3 키 '{s3_key}'에 해당하는 벡터를 성공적으로 삭제했습니다.")
        else:
            logger.error("RAGSystem 인스턴스를 찾을 수 없습니다. 벡터 DB에서 파일을 삭제할 수 없습니다.")
            return jsonify({"error": "RAG 시스템 오류로 파일 삭제에 실패했습니다."}), 500

        # 사용자에게 반환할 파일명 (UUID 제거)
        filename = re.sub(r'_[0-9a-fA-F]{8}\.txt$', '.txt', s3_key.split('/')[-1])
        return jsonify({"message": f"파일 '{filename}'이(가) 성공적으로 삭제되었습니다."}), 200
    except boto3.exceptions.Boto3Error as e:
        logger.error(f"S3 파일 삭제 중 오류 발생: {e}", exc_info=True)
        return jsonify({"error": "S3에서 파일 삭제 중 오류가 발생했습니다."}), 500
    except Exception as e:
        logger.error(f"파일 또는 벡터 삭제 중 예기치 않은 오류 발생: {e}", exc_info=True)
        return jsonify({"error": "파일 삭제 중 예기치 않은 오류가 발생했습니다."}), 500


# NOTE: `clear_all_files` 라우트는 요청에 따라 제거되었습니다.


@knowledge_base_bp.route('/add_from_url', methods=['POST'])
@login_required
def add_knowledge_base_from_url():
    """
    지식 베이스에 URL로부터 콘텐츠를 추가하는 라우트.
    로그인된 사용자가 URL을 통해 콘텐츠를 추가하고, 해당 데이터를 RAG 시스템에 반영합니다.
    """
    s3_client, bucket_name = get_s3_info()

    data = request.json
    url = data.get('url')
    industry = data.get('industry', None) 

    if not url or not industry:
        logger.warning(f"URL 또는 산업 정보가 누락되었습니다. URL: '{url}', Industry: '{industry}'")
        return jsonify({"error": "URL과 산업(industry)이 필요합니다."}), 400

    # `@login_required` 데코레이터가 이미 인증을 처리하므로 명시적 `is_authenticated` 체크는 제거합니다.
    
    industry_folder_name = sanitize_industry_name(industry)

    logger.info(f"URL로부터 지식 베이스 추가 시도: '{url}' (대상 산업 폴더: '{industry_folder_name}') (S3) by user '{current_user.username}' (ID: {current_user.id})")

    try:
        article_content_data = extract_text_from_url(url)
        if not article_content_data:
            logger.warning(f"URL '{url}'에서 콘텐츠를 추출할 수 없습니다. 유효하지 않은 URL이거나 파싱 오류입니다.")
            return jsonify({"error": "URL에서 콘텐츠를 추출할 수 없습니다. 유효한 URL인지 확인해주세요."}), 400
        
        article_title = article_content_data.get('title')
        article_content_str = article_content_data.get('content')
        
        logger.info(f"URL: '{url}'에서 'extract_text_from_url'로 추출된 원본 제목: '{article_title}'")
        if not article_title:
            logger.warning(f"경고: URL '{url}'에서 유효한 기사 제목을 추출하지 못했습니다. 파일명이 예상과 다를 수 있습니다.")

        base_filename = sanitize_filename(article_title, url) # 안전한 파일명 생성
        
        # S3 객체 키 생성 (예: 'Beauty/제목_uuid.txt')
        final_s3_object_key = f"{industry_folder_name}/{base_filename}" 

        message_prefix = "URL에서 콘텐츠를 가져와 지식 베이스에 추가했습니다."
        
        try:
            logger.debug(f"S3 HeadObject 호출 시도: Bucket='{bucket_name}', Key='{final_s3_object_key}'")
            # S3에 이미 파일이 존재하는지 확인하여 응답 메시지 결정
            s3_client.head_object(Bucket=bucket_name, Key=final_s3_object_key)
            logger.info(f"S3 객체 '{final_s3_object_key}'이(가) 이미 존재합니다. 새 콘텐츠로 덮어씁니다.")
            message_prefix = "이미 등록된 URL입니다. 최신 정보로 업데이트했습니다." 
        except s3_client.exceptions.ClientError as e:
            http_status = e.response.get('ResponseMetadata', {}).get('HTTPStatusCode')
            if http_status == 404:
                logger.info(f"S3 객체 '{final_s3_object_key}'을(를) 찾을 수 없습니다 (HTTP 404). 새로운 파일로 업로드 진행합니다.")
            else: 
                logger.error(f"S3 HeadObject 호출 중 알 수 없는 ClientError 발생 (HTTP {http_status}): {e}", exc_info=True)
                raise # 다른 S3 오류는 재발생
        except Exception as e:
            logger.error(f"S3 HeadObject 호출 중 예상치 못한 오류 발생: {e}", exc_info=True)
            raise

        # S3에 콘텐츠 업로드 (파일 내용, 인코딩)
        s3_client.put_object(Bucket=bucket_name, Key=final_s3_object_key, Body=article_content_str.encode('utf-8'))
        logger.info(f"URL '{url}'의 콘텐츠가 S3에 '{bucket_name}/{final_s3_object_key}'으로 성공적으로 업로드되었습니다.")

        # RAG 시스템에 문서 추가 함수 호출
        rag_system_instance = get_rag_system()
        if rag_system_instance:
            rag_system_instance.add_document_to_rag_system(
                s3_key=final_s3_object_key, 
                user_id=current_user.id
            )
            logger.info(f"S3 키 '{final_s3_object_key}'에 대한 벡터가 RAG 시스템에 성공적으로 추가/업데이트되었습니다. (User ID: {current_user.id})")
        else:
            logger.error("RAGSystem 인스턴스를 찾을 수 없습니다. 벡터 DB에 파일을 추가할 수 없습니다.")
            return jsonify({"error": "RAG 시스템 오류로 파일 추가에 실패했습니다."}), 500
        
        return jsonify({"message": message_prefix}), 200

    except Exception as e:
        logger.error(f"URL로부터 지식 베이스 추가 중 예기치 않은 오류 발생 (URL: '{url}'): {e}", exc_info=True)
        return jsonify({"error": f"URL에서 콘텐츠를 가져오는 중 오류가 발생했습니다: {e}"}), 500


@knowledge_base_bp.route('/industries', methods=['GET'])
@login_required
def get_industries():
    """AI 상수 파일에 정의된 산업 목록을 반환합니다."""
    logger.info(f"'{current_user.username}' 사용자에게 상수 파일에 정의된 산업 목록을 제공합니다.")
    return jsonify({"industries": INDUSTRIES}), 200