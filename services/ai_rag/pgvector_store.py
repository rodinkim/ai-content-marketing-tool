# ai-content-marketing-tool/services/ai_rag/pgvector_store.py

import logging
from typing import List, Tuple, Optional
from sqlalchemy import text, func 
from sqlalchemy.engine import Engine 
from sqlalchemy import inspect 
import numpy as np

logger = logging.getLogger(__name__)

class PgVectorStore:
    def __init__(self):
        logger.info("PgVectorStore 초기화 완료. DB 연결 및 모델은 런타임에 이루어집니다.")

    def _ensure_vector_table_and_index(self):
        """
        벡터 테이블이 존재하는지 확인하고, 존재하지 않으면 생성합니다.
        필요한 인덱스(HNSW 등)도 생성합니다.
        이 함수는 Flask 앱 컨텍스트 내에서 호출되어야 합니다.
        """
        from extensions import db
        from models_vector import KnowledgeBaseVector 

        try:
            pgvector_engine = db.get_engine(bind_key='pgvector_db')
            inspector = inspect(pgvector_engine)
            
            if not inspector.has_table(KnowledgeBaseVector.__tablename__):
                logger.info(f"'{KnowledgeBaseVector.__tablename__}' 테이블이 존재하지 않습니다. 생성합니다.")
                db.create_all() # bind 인자 제거
                logger.info(f"'{KnowledgeBaseVector.__tablename__}' 테이블 생성 완료.")
            else:
                logger.info(f"'{KnowledgeBaseVector.__tablename__}' 테이블이 이미 존재합니다.")

            index_name = 'idx_knowledge_base_vectors_embedding_hnsw'
            
            index_check_query = text(f"""
                SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
                WHERE c.relname = :index_name AND n.nspname = 'public';
            """)
            
            with pgvector_engine.connect() as connection:
                with connection.begin() as transaction:
                    result = connection.execute(index_check_query, {'index_name': index_name}).scalar()
                    if not result:
                        logger.info(f"'{index_name}' 벡터 인덱스가 존재하지 않습니다. 생성합니다.")
                        connection.execute(text(f"""
                            CREATE INDEX {index_name} ON {KnowledgeBaseVector.__tablename__} 
                            USING hnsw (embedding vector_l2_ops) WITH (m = 16, ef_construction = 64);
                        """))
                        logger.info(f"'{index_name}' 벡터 인덱스 생성 완료.")
                    else:
                        logger.info(f"'{index_name}' 벡터 인덱스가 이미 존재합니다.")

        except Exception as e:
            logger.error(f"pgvector 테이블 또는 인덱스 확인/생성 중 오류 발생: {e}", exc_info=True)
            raise

    def add_vectors(self, chunks_data: List[Tuple[str, dict]], embeddings: List[List[float]]):
        """
        새로운 청크 텍스트, 임베딩, 메타데이터를 pgvector 데이터베이스에 추가하거나 업데이트합니다.
        s3_key를 기준으로 기존 레코드를 찾고, 없으면 새로 삽입합니다.
        """
        from extensions import db
        from models_vector import KnowledgeBaseVector 

        # 트랜잭션 관리를 위해 세션 시작
        # Flask-SQLAlchemy는 기본적으로 요청 컨텍스트 내에서 세션을 관리합니다.
        # 여기서는 명시적으로 `db.session`을 사용합니다.
        try:
            for i, (chunk_text, chunk_metadata) in enumerate(chunks_data):
                # chunk_metadata에서 필요한 모든 필드 추출
                current_s3_key = chunk_metadata.get('s3_key')
                current_user_id = chunk_metadata.get('user_id') # rag_system.py에서 이미 None->0 처리됨
                current_industry = chunk_metadata.get('industry')
                current_original_filename = chunk_metadata.get('original_filename')
                current_chunk_index = chunk_metadata.get('chunk_index', i) # 기본값으로 i 사용

                if not current_s3_key:
                    logger.warning(f"Chunk {i} has no s3_key in metadata. Skipping this chunk for PgVector DB insertion.")
                    continue # s3_key 없으면 건너뛰기

                # s3_key를 기준으로 기존 레코드 조회
                existing_record = db.session.query(KnowledgeBaseVector).filter_by(
                    s3_key=current_s3_key
                ).first()

                if existing_record:
                    # 기존 레코드 업데이트
                    existing_record.text_content = chunk_text
                    existing_record.embedding = embeddings[i]
                    existing_record.metadata_ = chunk_metadata
                    existing_record.user_id = current_user_id # user_id 업데이트
                    existing_record.industry = current_industry # industry 업데이트
                    existing_record.original_filename = current_original_filename # original_filename 업데이트
                    existing_record.chunk_index = current_chunk_index # chunk_index 업데이트
                    existing_record.updated_at = func.now()
                    logger.debug(f"업데이트: S3 키 '{current_s3_key}'에 대한 벡터를 업데이트했습니다.")
                else:
                    # 새로운 레코드 생성
                    new_vector = KnowledgeBaseVector(
                        s3_key=current_s3_key,
                        user_id=current_user_id,
                        industry=current_industry,
                        original_filename=current_original_filename,
                        chunk_index=current_chunk_index,
                        text_content=chunk_text,
                        embedding=embeddings[i],
                        metadata_=chunk_metadata
                    )
                    db.session.add(new_vector) # 새로운 벡터를 세션에 추가
                    logger.debug(f"추가: S3 키 '{current_s3_key}'에 대한 새로운 벡터를 추가했습니다.")
            
            # 모든 변경사항을 하나의 트랜잭션으로 커밋
            db.session.commit()
            logger.info(f"pgvector DB에 벡터 추가/업데이트 완료. 총 {len(chunks_data)}개 청크 처리.")
        except Exception as e:
            logger.error(f"pgvector DB에 벡터 추가/업데이트 중 오류 발생: {e}", exc_info=True)
            db.session.rollback() # 오류 발생 시 롤백
            raise 
    
    def get_vectors_by_user_id(self, user_id: int) -> List: # List[KnowledgeBaseVector]를 반환하도록 타입 힌트
        """
        특정 user_id에 해당하는 모든 KnowledgeBaseVector 객체를 PgVector DB에서 가져옵니다.
        """
        from extensions import db
        from models_vector import KnowledgeBaseVector # KnowledgeBaseVector 모델 임포트
        try:
            # user_id로 필터링하여 모든 벡터를 쿼리합니다.
            filtered_vectors = KnowledgeBaseVector.query.filter_by(user_id=user_id).all()
            logger.info(f"Retrieved {len(filtered_vectors)} vectors for user_id {user_id} from PgVector DB.")
            return filtered_vectors
        except Exception as e:
            logger.error(f"Failed to retrieve vectors for user_id {user_id} from PgVector DB: {e}", exc_info=True)
            return []
    
    def get_vector_metadata_by_s3_key(self, s3_key: str) -> Optional[dict]:
        """
        특정 s3_key에 해당하는 벡터의 메타데이터(특히 user_id)를 PgVector DB에서 가져옵니다.
        """
        from extensions import db
        from models_vector import KnowledgeBaseVector # KnowledgeBaseVector 모델 임포트

        try:
            # s3_key로 필터링하여 첫 번째 벡터를 조회합니다.
            vector_obj = KnowledgeBaseVector.query.filter_by(s3_key=s3_key).first()
            if vector_obj:
                # 필요한 메타데이터만 반환합니다. (예: user_id, industry, original_filename)
                return {
                    "user_id": vector_obj.user_id,
                    "industry": vector_obj.industry,
                    "original_filename": vector_obj.original_filename,
                    "s3_key": vector_obj.s3_key,
                    # 기타 필요한 메타데이터_ 필드는 metadata_ 딕셔너리에서 가져올 수 있습니다.
                    "metadata": vector_obj.metadata_ 
                }
            else:
                logger.warning(f"S3 키 '{s3_key}'에 해당하는 벡터를 PgVector DB에서 찾을 수 없습니다.")
                return None
        except Exception as e:
            logger.error(f"PgVector DB에서 S3 키 '{s3_key}'의 메타데이터 조회 중 오류 발생: {e}", exc_info=True)
            return None

    def get_all_vectors(self):
        """
        PgVector DB에 저장된 모든 KnowledgeBaseVector 객체를 가져옵니다.
        """
        from extensions import db
        from models_vector import KnowledgeBaseVector
        try:
            # 모든 벡터를 쿼리하고 반환합니다.
            all_vectors = KnowledgeBaseVector.query.all()
            logger.info(f"Retrieved {len(all_vectors)} vectors from PgVector DB.")
            return all_vectors
        except Exception as e:
            logger.error(f"Failed to retrieve all vectors from PgVector DB: {e}", exc_info=True)
            return []
        
    def search(self, query_embedding: List[float], k: int = 3, user_id: int = None) -> List[Tuple[str, float, dict]]:
        """
        PgVector DB에서 쿼리 임베딩과 가장 유사한 k개의 벡터를 검색합니다.
        user_id가 제공되면 해당 user_id와 연결된 문서만 검색합니다.
        정렬 및 유사도 계산에는 코사인 유사도를 사용합니다.
        """
        from extensions import db
        from models_vector import KnowledgeBaseVector 

        results = []
        try:
            query = KnowledgeBaseVector.query

            if user_id is not None:
                query = query.filter(KnowledgeBaseVector.user_id == user_id)
                logger.debug(f"PgVector 검색 시 user_id 필터링 적용: {user_id}")
            else:
                logger.debug("PgVector 검색 시 user_id 필터링 없음.")

            # 코사인 유사도(cosine_distance)를 기준으로 정렬
            # cosine_distance는 0에 가까울수록 유사함 (0: 동일, 1: 직교, 2: 반대).
            # 따라서 order_by에서 distance를 오름차순으로 정렬하면 가장 유사한 결과가 나옵니다.
            nearest_vectors = query.order_by(
                KnowledgeBaseVector.embedding.cosine_distance(query_embedding) # <-- L2_distance 대신 cosine_distance 사용
            ).limit(k).all()
            
            for vector_obj in nearest_vectors:
                # DB에서 이미 코사인 유사도 기준으로 정렬되었으므로,
                # 여기서 다시 코사인 유사도(값 1에 가까울수록 유사)를 계산하거나,
                # 아니면 pgvector의 cosine_distance가 반환하는 '거리' 값을 직접 사용합니다.
                # pgvector의 cosine_distance는 0(동일) ~ 2(반대) 범위를 가집니다.
                # 이를 일반적인 유사도 점수(0~1, 1이 유사)로 변환하는 공식: 1 - distance / 2
                
                # 코사인 '거리' 값을 가져옴 (DB에서 계산된 값)
                # 이 값을 직접 가져올 방법이 없으므로, 파이썬에서 다시 계산합니다.
                # (SQLAlchemy에서 select(컬럼, 컬럼.distance(..) as dist) 처럼 가져오면 좋겠지만,
                #  간단하게 ORM 객체 로드 후 파이썬에서 계산합니다.)
                query_np = np.array(query_embedding)
                vector_np = np.array(vector_obj.embedding)
                
                # numpy를 사용하여 코사인 유사도 계산
                # 1. 벡터 내적 계산 (dot product)
                dot_product = np.dot(query_np, vector_np)
                # 2. 각 벡터의 L2 노름(크기) 계산
                norm_query = np.linalg.norm(query_np)
                norm_vector = np.linalg.norm(vector_np)

                # 0으로 나누는 오류 방지
                if norm_query == 0 or norm_vector == 0:
                    cosine_similarity = 0.0
                else:
                    cosine_similarity = dot_product / (norm_query * norm_vector)
                
                # 코사인 유사도는 -1 ~ 1 범위, 1에 가까울수록 유사.
                # 이를 그대로 similarity_score로 사용합니다.
                similarity_score = float(cosine_similarity) # float로 캐스팅하여 저장

                # 반환 형식: (chunk_text, 유사도 점수, 메타데이터)
                results.append((vector_obj.text_content, similarity_score, vector_obj.metadata_))
            
            logger.info(f"PgVector DB에서 {len(results)}개의 유사 문서 검색 완료 (User ID: {user_id if user_id is not None else 'None'}).")
            
        except Exception as e:
            logger.error(f"Pgvector DB 검색 중 오류 발생: {e}", exc_info=True)
            return [] 
        
        return results

    def clear_vectors(self, user_id: Optional[int] = None): # user_folder_name 대신 user_id 사용
        """
        pgvector DB에서 모든 벡터 또는 특정 user_id의 벡터를 삭제합니다.
        """
        from extensions import db
        from models_vector import KnowledgeBaseVector
        
        try:
            if user_id is not None: # user_id가 제공된 경우
                count = KnowledgeBaseVector.query.filter_by(user_id=user_id).delete()
                logger.info(f"pgvector DB에서 사용자 {user_id}의 벡터 {count}개 삭제 완료.")
            else: # user_id가 None인 경우 (모든 벡터 삭제)
                count = KnowledgeBaseVector.query.delete()
                logger.info(f"pgvector DB에서 모든 벡터 {count}개 삭제 완료.")
            db.session.commit()
        except Exception as e:
            logger.error(f"pgvector DB에서 벡터 삭제 중 오류 발생: {e}", exc_info=True)
            db.session.rollback()
            raise

    def delete_vector_by_file(self, s3_key: str): # user_folder_name, filename 대신 s3_key 사용
        """
        특정 s3_key에 해당하는 모든 청크 벡터를 pgvector DB에서 삭제합니다.
        """
        from extensions import db
        from models_vector import KnowledgeBaseVector
        
        try:
            count = KnowledgeBaseVector.query.filter_by(
                s3_key=s3_key
            ).delete()
            db.session.commit()
            logger.info(f"pgvector DB에서 S3 키 '{s3_key}'의 벡터 {count}개 삭제 완료.")
        except Exception as e:
            logger.error(f"pgvector DB에서 특정 파일 벡터 삭제 중 오류 발생: {e}", exc_info=True)
            db.session.rollback()
            raise