# ai-content-marketing-tool/services/ai_rag/pgvector_store.py

import logging
from typing import List, Tuple, Optional
from sqlalchemy import text, func 
from sqlalchemy.engine import Engine 
from sqlalchemy import inspect 

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
                db.create_all() # <-- 'bind' 인자 제거
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
        """
        from extensions import db
        from models_vector import KnowledgeBaseVector 

        new_vectors = []
        try:
            # 수정된 부분: db.session.using_bind() 제거
            # __bind_key__가 설정된 모델은 자동으로 올바른 바인드를 사용합니다.
            for i, (chunk_text, chunk_metadata) in enumerate(chunks_data):
                user_folder_name = chunk_metadata.get('user_folder_name')
                filename = chunk_metadata.get('filename')
                chunk_idx = chunk_metadata.get('chunk_index', i) 

                # 쿼리에 binds를 명시
                existing_record = db.session.query(KnowledgeBaseVector).filter_by(
                    user_folder_name=user_folder_name,
                    filename=filename,
                    chunk_index=chunk_idx
                ).first() # .first()는 세션에 바인드 설정 필요 없음.

                if existing_record:
                    existing_record.text_content = chunk_text
                    existing_record.embedding = embeddings[i]
                    existing_record.metadata_ = chunk_metadata
                    existing_record.updated_at = func.now()
                    logger.debug(f"업데이트: Vector for '{user_folder_name}/{filename}' chunk {chunk_idx}")
                else:
                    new_vector = KnowledgeBaseVector(
                        user_folder_name=user_folder_name,
                        filename=filename,
                        chunk_index=chunk_idx,
                        text_content=chunk_text,
                        embedding=embeddings[i],
                        metadata_=chunk_metadata
                    )
                    new_vectors.append(new_vector)
            
            # 모든 add/update를 하나의 트랜잭션으로 커밋
            # Flask-SQLAlchemy의 기본 세션은 __bind_key__를 통해 올바른 바인딩을 찾아 트랜잭션 처리
            if new_vectors:
                db.session.add_all(new_vectors)
            db.session.commit() # <-- 변경: begin() 컨텍스트 매니저 제거, 직접 commit()
            logger.info(f"pgvector DB에 새로운 벡터 {len(new_vectors)}개 추가 또는 기존 벡터 업데이트 완료.")
        except Exception as e:
            logger.error(f"pgvector DB에 벡터 추가/업데이트 중 오류 발생: {e}", exc_info=True)
            db.session.rollback() # <-- 변경: 오류 발생 시 롤백
            raise 

    def search(self, query_embedding: List[float], k: int = 3) -> List[Tuple[str, float, dict]]:
        """
        쿼리 임베딩과 유사한 상위 k개의 문서 청크를 pgvector DB에서 검색합니다.
        """
        from extensions import db
        from models_vector import KnowledgeBaseVector 

        results = []
        try:
            # __bind_key__가 설정된 모델의 쿼리는 자동으로 올바른 바인드를 사용합니다.
            nearest_vectors = KnowledgeBaseVector.query.order_by(
                KnowledgeBaseVector.embedding.l2_distance(query_embedding)
            ).limit(k).all()
            
            for vector_obj in nearest_vectors:
                distance = vector_obj.embedding.l2_distance(query_embedding)
                similarity_score = 1 / (1 + distance) 

                results.append((vector_obj.text_content, similarity_score, vector_obj.metadata_))
            
            logger.info(f"pgvector DB에서 {len(results)}개의 유사 문서 검색 완료.")
        except Exception as e:
            logger.error(f"pgvector DB 검색 중 오류 발생: {e}", exc_info=True)
        
        return results

    def clear_vectors(self, user_folder_name: Optional[str] = None):
        """
        pgvector DB에서 모든 벡터 또는 특정 사용자 폴더의 벡터를 삭제합니다.
        """
        from extensions import db
        from models_vector import KnowledgeBaseVector
        
        try:
            # 수정된 부분: db.session.using_bind() 제거
            if user_folder_name:
                count = KnowledgeBaseVector.query.filter_by(user_folder_name=user_folder_name).delete()
            else:
                count = KnowledgeBaseVector.query.delete()
            db.session.commit() # <-- 변경: 직접 commit()
            logger.info(f"pgvector DB에서 {'모든' if user_folder_name is None else f'사용자 {user_folder_name}의'} 벡터 {count}개 삭제 완료.")
        except Exception as e:
            logger.error(f"pgvector DB에서 벡터 삭제 중 오류 발생: {e}", exc_info=True)
            db.session.rollback() # <-- 변경: 오류 시 롤백
            raise

    def delete_vector_by_file(self, user_folder_name: str, filename: str):
        """
        특정 파일(user_folder_name/filename)에 해당하는 모든 청크 벡터를 pgvector DB에서 삭제합니다.
        """
        from extensions import db
        from models_vector import KnowledgeBaseVector
        
        try:
            # 수정된 부분: db.session.using_bind() 제거
            count = KnowledgeBaseVector.query.filter_by(
                user_folder_name=user_folder_name,
                filename=filename
            ).delete()
            db.session.commit() # <-- 변경: 직접 commit()
            logger.info(f"pgvector DB에서 파일 '{user_folder_name}/{filename}'의 벡터 {count}개 삭제 완료.")
        except Exception as e:
            logger.error(f"pgvector DB에서 특정 파일 벡터 삭제 중 오류 발생: {e}", exc_info=True)
            db.session.rollback() # <-- 변경: 오류 시 롤백
            raise