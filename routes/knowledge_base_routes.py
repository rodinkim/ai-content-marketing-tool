# routes/knowledge_base_routes.py

from flask import request, jsonify, Blueprint, current_app, render_template
from flask_login import login_required, current_user 
from models import User
import logging
import re

from services.ai_rag.rag_system import get_rag_system 
from services.web_crawling.web_content_extractor import extract_text_from_url
from services.web_crawling.web_utils import sanitize_filename
from services.ai_rag.ai_constants import INDUSTRIES
from services.ai_rag.pgvector_store import PgVectorStore

logger = logging.getLogger(__name__)

knowledge_base_bp = Blueprint('knowledge_base_routes', __name__)


def sanitize_industry_name(raw_industry_name):
    if not raw_industry_name: 
        return "default_industry"
    user_folder_name = re.sub(r'[^a-zA-Z0-9가-힣_-]', '', raw_industry_name).strip()
    return user_folder_name if user_folder_name else "default_industry"

def get_s3_info():
    s3_client = current_app.extensions.get('s3_client')
    if not s3_client:
        logger.error("S3 클라이언트가 초기화되지 않았습니다.")
        raise RuntimeError("S3 클라이언트를 사용할 수 없습니다.")
    bucket_name = current_app.config.get('S3_BUCKET_NAME')
    if not bucket_name:
        logger.error("S3 버킷 이름이 설정되지 않았습니다.")
        raise RuntimeError("S3 버킷 이름을 사용할 수 없습니다.")
    return s3_client, bucket_name

@knowledge_base_bp.route('/', methods=['GET'])
@login_required
def manage_knowledge_base():
    is_admin = current_user.username == current_app.config.get('ADMIN_USERNAME')
    return render_template('knowledge_base_manager.html', is_admin=is_admin)

@knowledge_base_bp.route('/users', methods=['GET'])
@login_required
def list_all_users_for_admin():
    if current_user.username != current_app.config.get('ADMIN_USERNAME'):
        return jsonify({"error": "접근 권한이 없습니다."}), 403
    try:
        all_usernames = [user.username for user in User.query.all()]
        all_usernames.sort()
        return jsonify({"users": all_usernames}), 200
    except Exception as e:
        logger.error(f"등록된 사용자 목록 조회 중 오류 발생: {e}", exc_info=True)
        return jsonify({"error": "사용자 목록 조회 중 오류가 발생했습니다."}), 500

@knowledge_base_bp.route('/files', methods=['GET'])
@login_required
def list_knowledge_base_files():
    PAGE_SIZE = 15
    page = request.args.get('page', 1, type=int)
    all_files_data = []
    is_admin = current_user.username == current_app.config.get('ADMIN_USERNAME')

    try:
        if is_admin:
            target_filter_type = request.args.get('target_type')
            target_filter_name = request.args.get('target_username')
            if target_filter_type == 'user':
                target_user_object = User.query.filter_by(username=target_filter_name).first()
                if target_user_object:
                    pg_store = PgVectorStore()
                    vectors = pg_store.get_vectors_by_user_id(target_user_object.id)
                    for v in vectors:
                        display_name = re.sub(r'_[0-9a-fA-F]{8}\.txt$', '.txt', v.original_filename)
                        all_files_data.append({"display_name": display_name, "s3_key": v.s3_key})
            else:
                s3_client, bucket_name = get_s3_info()
                s3_filter_prefix = f"{target_filter_name}/" if target_filter_name else ""
                paginator = s3_client.get_paginator('list_objects_v2')
                pages = paginator.paginate(Bucket=bucket_name, Prefix=s3_filter_prefix)
                config_prefix = current_app.config.get('CRAWLER_CONFIG_S3_KEY', '_system_configs/crawler_urls.json').split('/')[0] + '/'
                for s3_page in pages:
                    for obj in s3_page.get('Contents', []):
                        key = obj['Key']
                        if not key.endswith('/') and key.endswith('.txt') and not key.startswith(config_prefix):
                            display_name = re.sub(r'_[0-9a-fA-F]{8}\.txt$', '.txt', key.split('/')[-1])
                            all_files_data.append({"display_name": display_name, "s3_key": key})
        else:
            pg_store = PgVectorStore()
            vectors = pg_store.get_vectors_by_user_id(current_user.id)
            for v in vectors:
                display_name = re.sub(r'_[0-9a-fA-F]{8}\.txt$', '.txt', v.original_filename)
                all_files_data.append({"display_name": display_name, "s3_key": v.s3_key})
    except Exception as e:
        logger.error(f"파일 목록 조회 중 오류 발생: {e}", exc_info=True)
        return jsonify({"error": "파일 목록을 불러오는 중 오류가 발생했습니다."}), 500

    all_files_data.sort(key=lambda x: x['s3_key'])
    total_items = len(all_files_data)
    total_pages = (total_items + PAGE_SIZE - 1) // PAGE_SIZE if total_items > 0 else 1
    start_index = (page - 1) * PAGE_SIZE
    end_index = start_index + PAGE_SIZE
    paginated_files = all_files_data[start_index:end_index]

    return jsonify({
        "files": paginated_files,
        "pagination": {
            "page": page,
            "per_page": PAGE_SIZE,
            "total_items": total_items,
            "total_pages": total_pages,
        }
    }), 200

@knowledge_base_bp.route('/delete/<path:s3_key>', methods=['DELETE'])
@login_required
def delete_knowledge_base_file(s3_key):
    is_admin = current_user.username == current_app.config.get('ADMIN_USERNAME')
    pg_store = PgVectorStore()
    file_metadata = pg_store.get_vector_metadata_by_s3_key(s3_key)
    authorized_to_delete = False
    if is_admin or (file_metadata and file_metadata.get('user_id') == current_user.id):
        authorized_to_delete = True

    if not authorized_to_delete:
        return jsonify({"error": "이 파일을 삭제할 권한이 없습니다."}), 403

    s3_client, bucket_name = get_s3_info()
    try:
        s3_client.delete_object(Bucket=bucket_name, Key=s3_key)
        rag_system_instance = get_rag_system()
        if rag_system_instance:
            rag_system_instance.remove_document_from_rag_system(s3_key)
        else:
            return jsonify({"error": "RAG 시스템 오류로 파일 삭제에 실패했습니다."}), 500
        filename = re.sub(r'_[0-9a-fA-F]{8}\.txt$', '.txt', s3_key.split('/')[-1])
        return jsonify({"message": f"파일 '{filename}'이(가) 성공적으로 삭제되었습니다."}), 200
    except Exception as e:
        return jsonify({"error": "파일 삭제 중 예기치 않은 오류가 발생했습니다."}), 500

@knowledge_base_bp.route('/add_from_url', methods=['POST'])
@login_required
def add_knowledge_base_from_url():
    s3_client, bucket_name = get_s3_info()
    data = request.json
    url, industry = data.get('url'), data.get('industry')
    if not url or not industry:
        return jsonify({"error": "URL과 산업(industry)이 필요합니다."}), 400
    industry_folder_name = sanitize_industry_name(industry)
    try:
        article_content_data = extract_text_from_url(url)
        if not article_content_data or not article_content_data.get('content'):
            return jsonify({"error": "URL에서 콘텐츠를 추출할 수 없습니다."}), 400
        
        article_title = article_content_data.get('title')
        article_content_str = article_content_data.get('content')
        base_filename = sanitize_filename(article_title, url)
        final_s3_object_key = f"{industry_folder_name}/{base_filename}"
        message_prefix = "URL에서 콘텐츠를 가져와 지식 베이스에 추가했습니다."
        
        try:
            s3_client.head_object(Bucket=bucket_name, Key=final_s3_object_key)
            message_prefix = "이미 등록된 URL입니다. 최신 정보로 업데이트했습니다."
        except s3_client.exceptions.ClientError as e:
            if e.response.get('ResponseMetadata', {}).get('HTTPStatusCode') != 404:
                raise

        s3_client.put_object(Bucket=bucket_name, Key=final_s3_object_key, Body=article_content_str.encode('utf-8'))
        
        rag_system_instance = get_rag_system()
        if rag_system_instance:
            rag_system_instance.add_document_to_rag_system(s3_key=final_s3_object_key, user_id=current_user.id)
        else:
            return jsonify({"error": "RAG 시스템 오류로 파일 추가에 실패했습니다."}), 500
        
        return jsonify({"message": message_prefix}), 200
    except Exception as e:
        return jsonify({"error": f"URL에서 콘텐츠를 가져오는 중 오류가 발생했습니다: {e}"}), 500

@knowledge_base_bp.route('/industries', methods=['GET'])
@login_required
def get_industries():
    return jsonify({"industries": INDUSTRIES}), 200