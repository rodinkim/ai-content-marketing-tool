# ai-content-marketing-tool/routes/knowledge_base_routes.py

from flask import request, jsonify, Blueprint, current_app, render_template
from flask_login import login_required, current_user 
import numpy as np
import os
import logging
import re
import boto3

# services/ 디렉토리 내의 모듈들의 임포트 경로를 수정합니다.
from services.ai_rag.rag_system import get_rag_system, init_rag_system
from services.ai_rag.ai_service import get_ai_content_generator
from services.web_crawling.web_content_extractor import extract_text_from_url
from services.web_crawling.web_utils import sanitize_filename
from services.web_crawling.crawler_tasks import perform_marketing_crawl_task

logger = logging.getLogger(__name__)

knowledge_base_bp = Blueprint('knowledge_base_routes', __name__)

# --- 헬퍼 함수: 사용자 폴더 이름 가져오기 (이 부분이 누락되어 있었습니다!) ---
def get_user_folder_name(username_raw):
    """주어진 사용자 이름을 파일 시스템에 안전한 폴더 이름으로 반환합니다."""
    if not username_raw:
        return "default_user"
    user_folder_name = re.sub(r'[^a-zA-Z0-9가-힣_-]', '', username_raw).strip()
    return user_folder_name if user_folder_name else "default_user"

# --- 헬퍼 함수: S3 클라이언트 및 버킷 정보 가져오기 ---
def get_s3_info():
    """앱 확장(app.extensions)에서 S3 클라이언트와 버킷 이름을 가져와 반환합니다."""
    s3_client = current_app.extensions.get('s3_client')
    if not s3_client:
        logger.error("S3 client is not initialized in app.extensions.")
        raise RuntimeError("S3 client not available.")
    
    bucket_name = current_app.config.get('S3_BUCKET_NAME')
    if not bucket_name:
        logger.error("S3 bucket name is not configured.")
        raise RuntimeError("S3 bucket name not available.")
    
    return s3_client, bucket_name

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
    각 폴더 이름은 S3 버킷의 최상위 접두사(사용자명)를 의미합니다.
    """
    admin_username = current_app.config.get('ADMIN_USERNAME')
    
    if current_user.username != admin_username:
        logger.warning(f"비관리자 계정 '{current_user.username}'이(가) 사용자 목록 조회를 시도했습니다.")
        return jsonify({"error": "접근 권한이 없습니다."}), 403

    s3_client, bucket_name = get_s3_info()
    users = set() # 중복 방지를 위해 set 사용

    try:
        # S3 버킷의 모든 객체를 나열하여 사용자 폴더(접두사)를 추출합니다.
        # Delimiter='/'를 지정하면 S3의 '폴더' 목록을 CommonPrefixes로 얻을 수 있습니다.
        paginator = s3_client.get_paginator('list_objects_v2')
        pages = paginator.paginate(Bucket=bucket_name, Delimiter='/') 

        for page in pages:
            if 'CommonPrefixes' in page:
                for prefix_info in page['CommonPrefixes']:
                    folder_name = prefix_info['Prefix'].rstrip('/') # 마지막 '/' 제거
                    # 'default_user' 같은 폴더가 없다면, 여기에 'admin' 사용자를 제외하는 로직 추가 가능
                    users.add(folder_name)
        
        # set을 list로 변환하여 정렬
        sorted_users = sorted(list(users))

        logger.info(f"관리자 '{current_user.username}'이(가) 모든 사용자 폴더 목록({len(sorted_users)}개)을 조회했습니다. (S3)")
        return jsonify({"users": sorted_users}), 200
    except Exception as e:
        logger.error(f"관리자 사용자 목록 조회 오류 (S3): {e}", exc_info=True)
        return jsonify({"error": "사용자 목록을 가져오는 중 오류가 발생했습니다."}), 500


@knowledge_base_bp.route('/files', methods=['GET'])
@knowledge_base_bp.route('/files/<string:target_username>', methods=['GET']) 
@login_required
def list_knowledge_base_files(target_username=None):
    """
    현재 로그인한 사용자의 지식 베이스 파일 목록을 조회합니다.
    관리자 계정일 경우, target_username을 통해 다른 사용자의 지식 베이스를 조회하거나
    (target_username 지정 시), 모든 사용자의 파일을 통합하여 조회할 수 있습니다 (target_username이 None일 때).
    """
    s3_client, bucket_name = get_s3_info() # S3 클라이언트 및 버킷 정보 가져오기
    
    current_user_name = str(current_user.username)
    admin_username = current_app.config.get('ADMIN_USERNAME')
    is_current_user_admin = (current_user_name == admin_username)

    files = [] # 최종 반환될 파일 목록

    # 관리자 여부 확인
    # is_current_user_admin = (current_user_name == admin_username) # <-- 중복 코드 제거 (함수 상단에 이미 선언됨)

    if is_current_user_admin and not target_username:
        # 관리자가 특정 사용자 지정 없이 '/files'를 요청했을 때, 모든 사용자의 파일 통합 조회
        logger.info(f"관리자 '{current_user_name}'이(가) 모든 사용자의 지식 베이스 파일을 통합 조회합니다. (S3)")
        try:
            paginator = s3_client.get_paginator('list_objects_v2')
            # 접두사(Prefix) 없이 모든 객체를 조회합니다.
            pages = paginator.paginate(Bucket=bucket_name) 

            for page in pages:
                if 'Contents' in page:
                    for obj in page['Contents']:
                        key = obj['Key'] # S3 객체 키 (예: 'user1/file1.txt')
                        # .txt 파일이고 사용자 폴더 내에 있는 파일만 포함 (최상위 파일이나 빈 폴더 객체 등 제외)
                        if key.endswith(".txt") and '/' in key: 
                            files.append(key) # 'username/filename.txt' 형태로 반환
            
            logger.info(f"관리자 '{current_user_name}'의 통합 지식 베이스 파일 목록 조회: {len(files)}개 파일 발견. (S3)")
            return jsonify({"files": files}), 200

        except Exception as e:
            logger.error(f"관리자 통합 지식 베이스 파일 목록 조회 오류 (S3): {e}", exc_info=True)
            return jsonify({"error": "통합 지식 베이스 파일 목록을 가져오는 중 오류가 발생했습니다."}), 500

    else:
        # 일반 사용자 또는 관리자가 특정 사용자를 지정하여 조회
        actual_username_for_path = target_username if target_username else current_user_name

        # 관리자가 아니면서 다른 사용자를 지정하려고 시도하는 경우 차단
        if not is_current_user_admin and target_username and target_username != current_user_name:
            logger.warning(f"비관리자 계정 '{current_user_name}'이(가) '{target_username}'의 파일 조회를 시도했습니다. (권한 없음)")
            return jsonify({"error": "다른 사용자의 파일을 조회할 권한이 없습니다."}), 403
        
        logger.info(f"사용자 '{current_user_name}'이(가) '{actual_username_for_path}'의 지식 베이스를 조회합니다. (S3)")

        user_folder_name = get_user_folder_name(actual_username_for_path) # <-- 이 함수 호출이 문제였습니다.
        # S3 객체 키 접두사 (예: 'ohsung/')
        s3_prefix = f"{user_folder_name}/"
        
        try:
            paginator = s3_client.get_paginator('list_objects_v2')
            # 해당 접두사로 시작하는 객체만 조회합니다.
            pages = paginator.paginate(Bucket=bucket_name, Prefix=s3_prefix) 

            for page in pages:
                if 'Contents' in page:
                    for obj in page['Contents']:
                        key = obj['Key'] # 'ohsung/file1.txt'
                        if key.endswith(".txt"):
                            # 파일명만 반환 ('ohsung/file1.txt' -> 'file1.txt')
                            file_name_only = key.replace(s3_prefix, '')
                            if file_name_only: # 빈 파일명 방지 (폴더 자체의 키 등)
                                files.append(file_name_only)
            
            logger.info(f"사용자 '{user_folder_name}'의 지식 베이스 파일 목록 조회: {len(files)}개 파일 발견. (S3)")
            return jsonify({"files": files}), 200
        except Exception as e:
            logger.error(f"'{user_folder_name}' 사용자의 지식 베이스 파일 목록 조회 오류 (S3): {e}", exc_info=True)
            return jsonify({"error": "지식 베이스 파일 목록을 가져오는 중 오류가 발생했습니다."}), 500


@knowledge_base_bp.route('/delete/<path:filename>', methods=['DELETE'])
@knowledge_base_bp.route('/delete/<string:target_username>/<path:filename>', methods=['DELETE'])
@login_required
def delete_knowledge_base_file(filename, target_username=None):
    """
    특정 filename에 해당하는 지식 베이스 파일을 S3에서 삭제합니다.
    관리자는 target_username을 지정하여 다른 사용자의 파일을 삭제할 수 있습니다.
    filename은 '제목.txt' (일반 사용자/관리자 특정 조회 시) 또는 'username/제목.txt' (관리자 통합 조회 시) 형태일 수 있습니다.
    이후 RAG 시스템을 재로드합니다.
    """
    s3_client, bucket_name = get_s3_info() # S3 클라이언트 및 버킷 정보 가져오기
    
    current_user_name = str(current_user.username)
    admin_username = current_app.config.get('ADMIN_USERNAME')
    is_current_user_admin = (current_user_name == admin_username)

    actual_s3_key = "" # 실제로 S3에서 삭제할 객체 키
    
    if is_current_user_admin and target_username:
        # 관리자가 특정 사용자 파일 삭제 요청 (프론트에서 target_username과 filename을 따로 보냄)
        actual_username_for_path = target_username
        # filename은 '제목.txt' 형태
        s3_key = f"{get_user_folder_name(actual_username_for_path)}/{filename}"
        logger.info(f"관리자 '{current_user_name}'이(가) 사용자 '{target_username}'의 파일 '{filename}' (S3 키: {s3_key}) 삭제를 시도합니다. (S3)")
    elif is_current_user_admin and not target_username and '/' in filename:
        # 관리자가 통합 목록에서 직접 'user/file.txt' 형태의 파일을 삭제 요청
        s3_key = filename # filename 자체가 'username/filename.txt' 형태의 S3 키
        parts = filename.split('/', 1)
        actual_username_for_path = parts[0]
        filename = parts[1] # 순수 파일명
        logger.info(f"관리자 '{current_user_name}'이(가) 통합 목록에서 사용자 '{actual_username_for_path}'의 파일 '{filename}' (S3 키: {s3_key}) 삭제를 시도합니다. (S3)")
    else:
        # 일반 사용자 또는 관리자 자신의 파일 삭제 요청
        actual_username_for_path = current_user_name
        # filename은 '제목.txt' 형태
        s3_key = f"{get_user_folder_name(actual_username_for_path)}/{filename}"
        logger.info(f"사용자 '{current_user_name}'이(가) 자신의 파일 '{filename}' (S3 키: {s3_key}) 삭제를 시도합니다. (S3)")

    # 일반 사용자가 다른 사용자 파일을 삭제 시도하는 경우 차단
    if not is_current_user_admin and actual_username_for_path != current_user_name:
        logger.warning(f"비관리자 계정 '{current_user_name}'이(가) '{actual_username_for_path}'의 파일 삭제를 시도했습니다. (권한 없음)")
        return jsonify({"error": "다른 사용자의 파일을 삭제할 권한이 없습니다."}), 403

    try:
        s3_client.delete_object(Bucket=bucket_name, Key=s3_key)
        logger.info(f"S3 객체 '{s3_key}'이(가) 성공적으로 삭제되었습니다. (S3)")

        bedrock_runtime_client = current_app.extensions['rag_bedrock_runtime']
        init_rag_system(bedrock_runtime_client) # RAG 시스템 재로드
        
        return jsonify({"message": f"파일 '{filename}'이 S3에서 삭제되고 지식 베이스가 업데이트되었습니다."}), 200
    except s3_client.exceptions.ClientError as e:
        if e.response['Error']['Code'] == 'NoSuchKey':
            logger.warning(f"S3에서 객체 '{s3_key}'을(를) 찾을 수 없어 삭제 실패.")
            return jsonify({"error": "파일을 S3에서 찾을 수 없습니다."}), 404
        logger.error(f"S3 파일 삭제 오류: {e}", exc_info=True)
        return jsonify({"error": f"파일 삭제 중 오류가 발생했습니다: {e}"}), 500
    except Exception as e:
        logger.error(f"지식 베이스 파일 삭제 및 RAG 재로드 오류: {e}", exc_info=True)
        return jsonify({"error": f"파일 삭제 및 지식 베이스 업데이트 중 오류가 발생했습니다: {e}"}), 500


@knowledge_base_bp.route('/clear_all_files', methods=['DELETE'])
@knowledge_base_bp.route('/clear_all_files/<string:target_username>', methods=['DELETE']) 
@login_required
def clear_all_knowledge_base_files(target_username=None):
    """
    현재 로그인한 사용자의 지식 베이스 루트 폴더 내의 모든 .txt 파일을 S3에서 삭제합니다.
    관리자는 target_username을 지정하여 다른 사용자의 모든 .txt 파일을 삭제할 수 있습니다.
    하위 디렉토리는 삭제하지 않습니다. 이후 RAG 시스템을 재로드합니다.
    """
    s3_client, bucket_name = get_s3_info() # S3 클라이언트 및 버킷 정보 가져오기
    
    current_user_name = str(current_user.username)
    admin_username = current_app.config.get('ADMIN_USERNAME')
    is_current_user_admin = (current_user_name == admin_username)

    # 삭제 대상 사용자 이름 결정 및 권한 확인
    if target_username:
        if not is_current_user_admin:
            logger.warning(f"비관리자 계정 '{current_user_name}'이(가) '{target_username}'의 모든 파일 삭제를 시도했습니다.")
            return jsonify({"error": "다른 사용자의 모든 파일을 삭제할 권한이 없습니다."}), 403
        actual_username_for_path = target_username
        logger.info(f"관리자 '{current_user_name}'이(가) 사용자 '{target_username}'의 모든 파일을 삭제합니다. (S3)")
    else:
        actual_username_for_path = current_user_name
        logger.info(f"사용자 '{current_user_name}'이(가) 자신의 모든 파일을 삭제합니다. (S3)")

    user_folder_name = get_user_folder_name(actual_username_for_path)
    # user_knowledge_base_dir = os.path.join(KNOWLEDGE_BASE_DIR, user_folder_name) # <-- 이 줄은 로컬 파일 시스템 코드이므로 S3에는 불필요
    s3_prefix = f"{user_folder_name}/" # 해당 사용자 폴더의 모든 객체를 지우기 위한 접두사

    deleted_count = 0
    try:
        # 해당 접두사를 가진 모든 객체 목록을 가져옵니다.
        paginator = s3_client.get_paginator('list_objects_v2')
        pages = paginator.paginate(Bucket=bucket_name, Prefix=s3_prefix)

        objects_to_delete = {'Objects': []}
        for page in pages:
            if 'Contents' in page:
                for obj in page['Contents']:
                    if obj['Key'].endswith(".txt"): # .txt 파일만 지우는 경우
                         objects_to_delete['Objects'].append({'Key': obj['Key']})

        if objects_to_delete['Objects']:
            response = s3_client.delete_objects(Bucket=bucket_name, Delete=objects_to_delete)
            deleted_count = len(response.get('Deleted', []))
            logger.info(f"S3 버킷 '{bucket_name}'에서 '{s3_prefix}' 접두사를 가진 객체 {deleted_count}개 삭제 완료. (S3)")
        else:
            logger.info(f"S3 버킷 '{bucket_name}'의 '{s3_prefix}' 접두사에 삭제할 .txt 객체가 없습니다.")


        bedrock_runtime_client = current_app.extensions['rag_bedrock_runtime']
        init_rag_system(bedrock_runtime_client)

        return jsonify({"message": f"사용자 '{actual_username_for_path}'의 모든 지식 베이스 파일({deleted_count}개)이 S3에서 성공적으로 삭제되고 지식 베이스가 업데이트되었습니다."}), 200
    except Exception as e:
        logger.error(f"S3에서 사용자 '{actual_username_for_path}'의 모든 지식 베이스 파일 삭제 중 오류 발생: {e}", exc_info=True)
        return jsonify({"error": "모든 지식 베이스 파일 삭제 중 오류가 발생했습니다."}), 500


@knowledge_base_bp.route('/add_from_url', methods=['POST'])
@login_required
def add_knowledge_base_from_url():
    """
    주어진 URL에서 기사 내용을 추출하고 S3에 .txt 파일로 저장합니다.
    파일은 'knowledge_base/<username>/' S3 객체 키 경로에 직접 저장됩니다.
    이후 RAG 시스템을 재로드합니다.
    """
    # S3 클라이언트 및 버킷 정보 가져오기
    s3_client, bucket_name = get_s3_info()

    data = request.json
    url = data.get('url')

    if not url:
        return jsonify({"error": "URL이 필요합니다."}), 400
    
    if not current_user.is_authenticated:
        return jsonify({"error": "로그인이 필요합니다."}), 401
    
    username_raw = str(current_user.username)
    user_folder_name = get_user_folder_name(username_raw)
        
    logger.info(f"URL로부터 지식 베이스 추가 시도: {url} (대상 사용자 폴더: {user_folder_name}) (S3)")

    try:
        # 1. URL에서 기사 내용 추출
        article_content_data = extract_text_from_url(url)
        if not article_content_data:
            return jsonify({"error": "URL에서 콘텐츠를 추출할 수 없습니다. 유효한 URL인지 확인해주세요."}), 400
        
        article_title = article_content_data.get('title')
        article_content_str = article_content_data.get('content')
        
        logger.info(f"URL: {url} 에서 'extract_text_from_url'로 추출된 원본 제목: '{article_title}'")
        if not article_title:
            logger.warning(f"경고: URL '{url}'에서 유효한 기사 제목을 추출하지 못했습니다. 파일명이 예상과 다를 수 있습니다.")

        base_filename = sanitize_filename(article_title, url) 
        
        # S3 객체 키 생성: username/filename.txt
        s3_object_key = f"{user_folder_name}/{base_filename}"

        # 2. S3에 파일 업로드 (중복 파일명 처리 로직 포함)
        counter = 1
        final_s3_object_key = s3_object_key
        while True:
            try:
                # S3에 해당 키가 존재하는지 확인 (head_object로 객체 메타데이터 가져오기 시도)
                logger.debug(f"S3 HeadObject 호출 시도: Bucket={bucket_name}, Key={final_s3_object_key}")
                s3_client.head_object(Bucket=bucket_name, Key=final_s3_object_key)
                
                # 객체가 존재하면 (200 OK 응답을 받았을 경우) 카운터를 증가시켜 새 키를 생성
                logger.debug(f"S3 HeadObject 성공: 객체 '{final_s3_object_key}'이(가) 이미 존재합니다. 다른 이름으로 시도합니다.")
                name, ext = os.path.splitext(base_filename)
                
                # S3 키 최대 길이 (1024) 및 폴더명, 확장자, 카운터를 고려한 파일명 길이 제한
                max_filename_len = 1024 - len(user_folder_name) - 1 - len(ext) - len(str(counter)) - 1
                if len(name) > max_filename_len:
                    name = name[:max_filename_len]
                final_s3_object_key = f"{user_folder_name}/{name}_{counter}{ext}"
                counter += 1
            except s3_client.exceptions.ClientError as e:
                # S3에서 객체를 찾을 수 없을 때 발생하는 경우를 처리
                http_status = e.response.get('ResponseMetadata', {}).get('HTTPStatusCode')
                error_code = e.response.get('Error', {}).get('Code')
                
                logger.debug(f"S3 HeadObject ClientError 발생: HTTP Status={http_status}, Error Code={error_code}")

                # HTTP 상태 코드가 404이면 객체가 없다는 의미이므로 루프를 빠져나와 업로드 진행
                if http_status == 404:
                    logger.info(f"S3 객체 '{final_s3_object_key}'을(를) 찾을 수 없습니다 (HTTP 404). 새로운 파일로 업로드 시도합니다.")
                    break # 객체가 없으니 이 이름을 사용해도 됨
                else: 
                    # 404가 아닌 다른 ClientError (예: 권한 문제, 버킷 없음 등)는 다시 발생
                    logger.error(f"S3 HeadObject 알 수 없는 ClientError 발생 (HTTP {http_status}): {error_code} - {e}", exc_info=True)
                    raise
            except Exception as e:
                # 예상치 못한 다른 모든 오류는 다시 발생
                logger.error(f"S3 HeadObject 예상치 못한 오류 발생: {e}", exc_info=True)
                raise

        # 3. S3에 콘텐츠 업로드
        s3_client.put_object(Bucket=bucket_name, Key=final_s3_object_key, Body=article_content_str.encode('utf-8'))
        logger.info(f"URL '{url}'의 콘텐츠가 S3에 '{bucket_name}/{final_s3_object_key}'으로 업로드되었습니다. (S3)")

        # 4. RAG 시스템 재로드 (이 부분은 S3에서 파일을 읽어와 RAG 시스템을 구축하도록 변경해야 함)
        # 현재는 init_rag_system이 로컬 파일을 기반으로 하므로, S3 파일 로드 로직이 필요.
        bedrock_runtime_client = current_app.extensions['rag_bedrock_runtime']
        init_rag_system(bedrock_runtime_client) # 이 함수도 S3 기반으로 수정이 필요합니다.
        
        return jsonify({"message": f"URL '{url}'에서 콘텐츠를 가져와 지식 베이스에 추가했습니다 ('{final_s3_object_key}'). 지식 베이스가 업데이트되었습니다."}), 200

    except Exception as e:
        logger.error(f"URL로부터 지식 베이스 추가 오류 (S3): {e}", exc_info=True)
        return jsonify({"error": f"URL에서 콘텐츠를 가져오는 중 오류가 발생했습니다: {e}"}), 500