import pytest
import numpy as np
from unittest.mock import Mock, patch, MagicMock
from services.ai_rag.rag_system import RAGSystem
from services.ai_rag.chunker import chunk_text
from services.ai_rag.embedding_generator import EmbeddingManager


class TestRAGSystem:
    """RAG 시스템 테스트 클래스"""

    @pytest.fixture
    def mock_bedrock_client(self):
        """Mock Bedrock 클라이언트"""
        return Mock()

    @pytest.fixture
    def mock_s3_client(self):
        """Mock S3 클라이언트"""
        return Mock()

    @pytest.fixture
    def rag_system(self, mock_bedrock_client, mock_s3_client):
        """RAG 시스템 인스턴스 생성"""
        with patch('services.ai_rag.rag_system.current_app'):
            return RAGSystem(mock_bedrock_client, mock_s3_client, "test-bucket")

    def test_rag_system_initialization(self, rag_system):
        """RAG 시스템 초기화 테스트"""
        assert rag_system.bedrock_runtime is not None
        assert rag_system.s3_client is not None
        assert rag_system.s3_bucket_name == "test-bucket"
        assert rag_system.embedding_manager is not None
        assert rag_system.faiss_indexer is not None
        assert rag_system.pgvector_store is not None

    def test_extract_metadata_from_s3_key(self, rag_system):
        """S3 키에서 메타데이터 추출 테스트"""
        s3_key = "IT/test_article_12345678.txt"
        industry, filename = rag_system._extract_metadata_from_s3_key(s3_key)
        
        assert industry == "IT"
        assert filename == "test_article.txt"

    def test_extract_metadata_from_s3_key_no_hash(self, rag_system):
        """해시가 없는 S3 키에서 메타데이터 추출 테스트"""
        s3_key = "Fashion/article.txt"
        industry, filename = rag_system._extract_metadata_from_s3_key(s3_key)
        
        assert industry == "Fashion"
        assert filename == "article.txt"


class TestChunker:
    """텍스트 청킹 테스트 클래스"""

    def test_chunk_text_normal(self):
        """일반적인 텍스트 청킹 테스트"""
        text = "이것은 테스트 텍스트입니다. " * 50  # 충분히 긴 텍스트
        chunks = chunk_text(text)
        
        assert len(chunks) > 0
        assert all(len(chunk) > 0 for chunk in chunks)

    def test_chunk_text_empty(self):
        """빈 텍스트 청킹 테스트"""
        chunks = chunk_text("")
        assert chunks == []

    def test_chunk_text_none(self):
        """None 텍스트 청킹 테스트"""
        chunks = chunk_text(None)
        assert chunks == []

    def test_chunk_text_short(self):
        """짧은 텍스트 청킹 테스트"""
        text = "짧은 텍스트"
        chunks = chunk_text(text)
        
        assert len(chunks) == 1
        assert chunks[0] == text


class TestEmbeddingManager:
    """임베딩 매니저 테스트 클래스"""

    @pytest.fixture
    def mock_bedrock_client(self):
        """Mock Bedrock 클라이언트"""
        return Mock()

    @pytest.fixture
    def embedding_manager(self, mock_bedrock_client):
        """임베딩 매니저 인스턴스 생성"""
        return EmbeddingManager(mock_bedrock_client)

    def test_embedding_manager_initialization(self, embedding_manager):
        """임베딩 매니저 초기화 테스트"""
        assert embedding_manager.bedrock_runtime_client is not None
        assert embedding_manager.industry_embeddings == {}

    @patch('services.ai_rag.embedding_generator.json.loads')
    @patch('services.ai_rag.embedding_generator.np.array')
    def test_get_embedding_success(self, mock_np_array, mock_json_loads, embedding_manager, mock_bedrock_client):
        """임베딩 생성 성공 테스트"""
        # Mock 설정
        mock_response = Mock()
        mock_response.get.return_value.read.return_value = '{"embedding": [0.1, 0.2, 0.3]}'
        mock_bedrock_client.invoke_model.return_value = mock_response
        mock_json_loads.return_value = {"embedding": [0.1, 0.2, 0.3]}
        mock_np_array.return_value = np.array([0.1, 0.2, 0.3])

        # 테스트 실행
        result = embedding_manager._get_embedding("테스트 텍스트")
        
        assert result is not None
        mock_bedrock_client.invoke_model.assert_called_once()

    def test_get_embedding_empty_text(self, embedding_manager):
        """빈 텍스트 임베딩 생성 테스트"""
        result = embedding_manager._get_embedding("")
        assert result is None

    def test_get_embedding_none_text(self, embedding_manager):
        """None 텍스트 임베딩 생성 테스트"""
        result = embedding_manager._get_embedding(None)
        assert result is None

    def test_precompute_industry_embeddings(self, embedding_manager, mock_bedrock_client):
        """업종별 임베딩 사전 계산 테스트"""
        with patch.object(embedding_manager, '_get_embedding') as mock_get_embedding:
            mock_get_embedding.return_value = np.array([0.1, 0.2, 0.3])
            
            industries = ["IT", "Fashion"]
            embedding_manager.precompute_industry_embeddings(industries)
            
            assert len(embedding_manager.industry_embeddings) == 2
            assert "IT" in embedding_manager.industry_embeddings
            assert "Fashion" in embedding_manager.industry_embeddings 