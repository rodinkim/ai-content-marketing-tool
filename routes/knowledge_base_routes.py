# routes/knowledge_base_routes.py

from flask import request, jsonify, Blueprint, current_app, render_template
from flask_login import login_required, current_user 
from models import User
import logging
import re

from services.ai_rag.rag_system import get_rag_system 
from services.web_crawling.web_content_extractor import extract_text_from_url
from services.web_crawling.web_utils import sanitize_filename
from services.utils.constants import INDUSTRIES
from services.ai_rag.pgvector_store import PgVectorStore

logger = logging.getLogger(__name__)

knowledge_base_bp = Blueprint('knowledge_base_routes', __name__)


def sanitize_industry_name(raw_industry_name):
    # 업종명 폴더명 정제
    if not raw_industry_name:
        return "default_industry"
    user_folder_name = re.sub(r'[^a-zA-Z0-9가-힣_-]', '', raw_industry_name).strip()
    return user_folder_name if user_folder_name else "default_industry"

def get_s3_info():
    # S3 클라이언트와 버킷명 반환
    s3_client = current_app.extensions.get('s3_client')
    bucket_name = current_app.config.get('S3_BUCKET_NAME')
    if not s3_client or not bucket_name:
        raise RuntimeError("S3 설정 오류")
    return s3_client, bucket_name

@knowledge_base_bp.route('/', methods=['GET'])
@login_required
def manage_knowledge_base():
    # 지식베이스 관리 페이지
    is_admin = current_user.username == current_app.config.get('ADMIN_USERNAME')
    return render_template('knowledge_base_manager.html', is_admin=is_admin)

@knowledge_base_bp.route('/users', methods=['GET'])
@login_required
def list_all_users_for_admin():
    # 전체 사용자 목록 (관리자 전용)
    if current_user.username != current_app.config.get('ADMIN_USERNAME'):
        return jsonify({"error": "접근 권한이 없습니다."}), 403
    try:
        all_usernames = sorted([user.username for user in User.query.all()])
        return jsonify({"users": all_usernames}), 200
    except Exception:
        return jsonify({"error": "사용자 목록 조회 중 오류가 발생했습니다."}), 500

@knowledge_base_bp.route('/files', methods=['GET'])
@login_required
def list_knowledge_base_files():
    # 지식베이스 파일 목록 (페이징)
    PAGE_SIZE = 15
    page = request.args.get('page', 1, type=int)
    is_admin = current_user.username == current_app.config.get('ADMIN_USERNAME')
    all_files_data = []
    try:
        if is_admin:
            target_type = request.args.get('target_type')
            target_name = request.args.get('target_username')
            if target_type == 'user':
                user = User.query.filter_by(username=target_name).first()
                if user:
                    vectors = PgVectorStore().get_vectors_by_user_id(user.id)
                    all_files_data = [{
                        "display_name": re.sub(r'_[0-9a-fA-F]{8}\.txt$', '.txt', v.original_filename),
                        "s3_key": v.s3_key
                    } for v in vectors]
            else:
                s3_client, bucket_name = get_s3_info()
                prefix = f"{target_name}/" if target_name else ""
                config_prefix = current_app.config.get('CRAWLER_CONFIG_S3_KEY', '_system_configs/crawler_urls.json').split('/')[0] + '/'
                paginator = s3_client.get_paginator('list_objects_v2')
                pages = paginator.paginate(Bucket=bucket_name, Prefix=prefix)
                for s3_page in pages:
                    for obj in s3_page.get('Contents', []):
                        key = obj['Key']
                        if not key.endswith('/') and key.endswith('.txt') and not key.startswith(config_prefix):
                            all_files_data.append({
                                "display_name": re.sub(r'_[0-9a-fA-F]{8}\.txt$', '.txt', key.split('/')[-1]),
                                "s3_key": key
                            })
        else:
            vectors = PgVectorStore().get_vectors_by_user_id(current_user.id)
            all_files_data = [{
                "display_name": re.sub(r'_[0-9a-fA-F]{8}\.txt$', '.txt', v.original_filename),
                "s3_key": v.s3_key
            } for v in vectors]
    except Exception:
        return jsonify({"error": "파일 목록을 불러오는 중 오류가 발생했습니다."}), 500

    all_files_data.sort(key=lambda x: x['s3_key'])
    total_items = len(all_files_data)
    total_pages = (total_items + PAGE_SIZE - 1) // PAGE_SIZE if total_items > 0 else 1
    start = (page - 1) * PAGE_SIZE
    end = start + PAGE_SIZE
    paginated_files = all_files_data[start:end]
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
    # 파일 삭제 (권한 체크)
    is_admin = current_user.username == current_app.config.get('ADMIN_USERNAME')
    file_metadata = PgVectorStore().get_vector_metadata_by_s3_key(s3_key)
    if not (is_admin or (file_metadata and file_metadata.get('user_id') == current_user.id)):
        return jsonify({"error": "이 파일을 삭제할 권한이 없습니다."}), 403
    s3_client, bucket_name = get_s3_info()
    try:
        s3_client.delete_object(Bucket=bucket_name, Key=s3_key)
        rag_system = get_rag_system()
        if rag_system:
            rag_system.remove_document_from_rag_system(s3_key)
        else:
            return jsonify({"error": "RAG 시스템 오류로 파일 삭제에 실패했습니다."}), 500
        filename = re.sub(r'_[0-9a-fA-F]{8}\.txt$', '.txt', s3_key.split('/')[-1])
        return jsonify({"message": f"파일 '{filename}'이(가) 성공적으로 삭제되었습니다."}), 200
    except Exception:
        return jsonify({"error": "파일 삭제 중 예기치 않은 오류가 발생했습니다."}), 500

@knowledge_base_bp.route('/add_from_url', methods=['POST'])
@login_required
def add_knowledge_base_from_url():
    # URL에서 콘텐츠 추출 후 S3 업로드 및 벡터DB 반영
    s3_client, bucket_name = get_s3_info()
    data = request.json
    url, industry = data.get('url'), data.get('industry')
    if not url or not industry:
        return jsonify({"error": "URL과 산업(industry)이 필요합니다."}), 400
    industry_folder = sanitize_industry_name(industry)
    try:
        article = extract_text_from_url(url)
        if not article or not article.get('content'):
            return jsonify({"error": "URL에서 콘텐츠를 추출할 수 없습니다."}), 400
        base_filename = sanitize_filename(article.get('title'), url)
        s3_key = f"{industry_folder}/{base_filename}"
        msg = "URL에서 콘텐츠를 가져와 지식 베이스에 추가했습니다."
        try:
            s3_client.head_object(Bucket=bucket_name, Key=s3_key)
            msg = "이미 등록된 URL입니다. 최신 정보로 업데이트했습니다."
        except s3_client.exceptions.ClientError as e:
            if e.response.get('ResponseMetadata', {}).get('HTTPStatusCode') != 404:
                raise
        s3_client.put_object(Bucket=bucket_name, Key=s3_key, Body=article.get('content').encode('utf-8'))
        rag_system = get_rag_system()
        if rag_system:
            rag_system.add_document_to_rag_system(s3_key=s3_key, user_id=current_user.id)
        else:
            return jsonify({"error": "RAG 시스템 오류로 파일 추가에 실패했습니다."}), 500
        return jsonify({"message": msg}), 200
    except Exception as e:
        return jsonify({"error": f"URL에서 콘텐츠를 가져오는 중 오류가 발생했습니다: {e}"}), 500

@knowledge_base_bp.route('/industries', methods=['GET'])
@login_required
def get_industries():
    # 업종 리스트 반환
    return jsonify({"industries": INDUSTRIES}), 200