# ai-content-marketing-tool/models_vector.py

from extensions import db
from pgvector.sqlalchemy import Vector
from sqlalchemy import Column, Integer, Text, DateTime, func, UniqueConstraint, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship 

class KnowledgeBaseVector(db.Model):
    __tablename__ = 'knowledge_base_vectors'
    __bind_key__ = 'pgvector_db'
    
    # UniqueConstraint 변경: s3_key를 고유 제약 조건으로 사용
    # s3_key는 이미 각 청크의 고유성을 보장하므로, 다른 컬럼들과의 복합 유니크 제약은 필요 없음
    __table_args__ = (
        UniqueConstraint('s3_key', name='_s3_key_uc'),
    )

    id = Column(Integer, primary_key=True)
    
    # user_id는 Flask-Login의 User 모델과 연결될 경우 ForeignKey로 설정할 수 있지만
    # 일단은 독립적인 Integer 컬럼으로 유지 (NotNullViolation 해결 위주)
    user_id = Column(Integer, nullable=False, index=True) 
    
    # 컬럼명 변경: user_folder_name -> industry
    industry = Column('industry', Text, nullable=False, index=True) # S3 폴더 이름 (이제 '산업' 이름)
    
    # 컬럼명 변경: filename -> original_filename
    original_filename = Column('original_filename', Text, nullable=False) # UUID가 제거된 원본 파일명
    
    chunk_index = Column(Integer, nullable=False, default=0)
    
    # 새 컬럼 추가: s3_key (가장 중요한 고유 식별자)
    s3_key = Column('s3_key', Text, unique=True, nullable=False) # S3 객체 키 (예: 'Beauty/제목_uuid.txt')

    text_content = Column(Text, nullable=False)
    embedding = Column(Vector(1024), nullable=False)
    
    # metadata_ 컬럼명 유지. DB에서 'metadata'로 저장됩니다.
    metadata_ = Column('metadata', JSONB, default={}) 

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        # repr 문자열 업데이트: s3_key를 포함하도록 변경
        return f"<KnowledgeBaseVector id={self.id} user_id='{self.user_id}' s3_key='{self.s3_key}' chunk={self.chunk_index}>"

    @classmethod
    def get_nearest(cls, embedding_vector, k: int = 5):
        # l2_distance 대신 코사인 유사도를 사용하는 것이 일반적입니다 (선택사항).
        return cls.query.order_by(cls.embedding.cosine_distance(embedding_vector)).limit(k).all()