# ai-content-marketing-tool/models_vector.py

from extensions import db # 기존 db 객체 임포트 (db_vector 대신)
from pgvector.sqlalchemy import Vector
from sqlalchemy import Column, Integer, Text, DateTime, func, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB

class KnowledgeBaseVector(db.Model): # <-- db_vector.Model 대신 db.Model 사용
    __tablename__ = 'knowledge_base_vectors'
    __bind_key__ = 'pgvector_db' # <-- pgvector DB에 바인딩
    __table_args__ = (
        UniqueConstraint('user_folder_name', 'filename', 'chunk_index', name='_user_filename_chunk_uc'), # chunk_index 추가하여 유니크성 강화
    )

    id = Column(Integer, primary_key=True)
    user_folder_name = Column(Text, nullable=False, index=True)
    filename = Column(Text, nullable=False)
    chunk_index = Column(Integer, nullable=False, default=0)
    text_content = Column(Text, nullable=False)
    embedding = Column(Vector(1024), nullable=False)
    metadata_ = Column('metadata', JSONB, default={})

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<KnowledgeBaseVector id={self.id} user='{self.user_folder_name}' file='{self.filename}' chunk={self.chunk_index}>"

    @classmethod
    def get_nearest(cls, embedding_vector, k: int = 5):
        return cls.query.order_by(cls.embedding.l2_distance(embedding_vector)).limit(k).all()