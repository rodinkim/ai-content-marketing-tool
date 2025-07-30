import pytest
from unittest.mock import Mock, patch, MagicMock
from services.generation.text_generator import TextGenerator, TextGenerationInput, TextGenerationError
from services.generation.image_generator import ImageGenerator, ImageGenerationInput, ImageGenerationError
from services.generation.translation_generator import TranslationGenerator, TranslationPromptInput, TranslationPromptError


class TestTextGenerator:
    """텍스트 생성기 테스트 클래스"""

    @pytest.fixture
    def mock_bedrock_client(self):
        """Mock Bedrock 클라이언트"""
        return Mock()

    @pytest.fixture
    def mock_rag_system(self):
        """Mock RAG 시스템"""
        mock_rag = Mock()
        mock_rag.retrieve.return_value = ["관련 문서 1: 테스트 내용", "관련 문서 2: 추가 내용"]
        return mock_rag

    @pytest.fixture
    def text_generator(self, mock_bedrock_client, mock_rag_system):
        """텍스트 생성기 인스턴스 생성"""
        with patch('services.generation.text_generator.PromptManager') as mock_prompt_manager:
            mock_prompt_manager.return_value.get_template_key.return_value = "blog_list"
            mock_prompt_manager.return_value.generate_text_prompt.return_value = "생성된 프롬프트"
            
            return TextGenerator(mock_bedrock_client, mock_rag_system, "/app", "claude-3-sonnet")

    def test_text_generator_initialization(self, text_generator):
        """텍스트 생성기 초기화 테스트"""
        assert text_generator.rag_system is not None
        assert text_generator.prompt_manager is not None
        assert text_generator.embedding_manager is not None
        assert text_generator.provider_instances is not None

    def test_generate_content_success(self, text_generator, mock_bedrock_client):
        """콘텐츠 생성 성공 테스트"""
        # Mock 설정
        mock_provider = Mock()
        mock_provider.invoke.return_value = "생성된 텍스트 콘텐츠"
        text_generator.provider_instances = {"text": mock_provider}

        # 테스트 입력 데이터
        input_data = TextGenerationInput(
            topic="AI 마케팅",
            industry="IT",
            content_type="blog",
            blog_style="추천/리스트 글"
        )

        # 테스트 실행
        result = text_generator.generate_content(input_data)
        
        assert result == "생성된 텍스트 콘텐츠"
        mock_provider.invoke.assert_called_once()

    def test_generate_content_missing_required_fields(self, text_generator):
        """필수 필드 누락 테스트"""
        input_data = TextGenerationInput(
            topic="",  # 빈 주제
            industry="IT",
            content_type="blog"
        )

        with pytest.raises(TextGenerationError):
            text_generator.generate_content(input_data)

    def test_generate_content_rag_search(self, text_generator, mock_rag_system):
        """RAG 검색 테스트"""
        input_data = TextGenerationInput(
            topic="AI 마케팅",
            industry="IT",
            content_type="blog"
        )

        # RAG 검색이 호출되는지 확인
        text_generator.generate_content(input_data)
        
        mock_rag_system.retrieve.assert_called_once()
        call_args = mock_rag_system.retrieve.call_args
        assert "AI 마케팅" in call_args[0][0]
        assert "IT" in call_args[0][0]


class TestImageGenerator:
    """이미지 생성기 테스트 클래스"""

    @pytest.fixture
    def mock_bedrock_client(self):
        """Mock Bedrock 클라이언트"""
        return Mock()

    @pytest.fixture
    def mock_s3_client(self):
        """Mock S3 클라이언트"""
        return Mock()

    @pytest.fixture
    def mock_prompt_manager(self):
        """Mock 프롬프트 매니저"""
        return Mock()

    @pytest.fixture
    def image_generator(self, mock_prompt_manager, mock_bedrock_client, mock_s3_client):
        """이미지 생성기 인스턴스 생성"""
        return ImageGenerator(mock_prompt_manager, mock_bedrock_client, mock_s3_client, "stable-diffusion")

    def test_image_generator_initialization(self, image_generator):
        """이미지 생성기 초기화 테스트"""
        assert image_generator.prompt_manager is not None
        assert image_generator.bedrock_client is not None
        assert image_generator.s3_client is not None
        assert image_generator.image_model_id == "stable-diffusion"

    @patch('services.generation.image_generator.base64.b64decode')
    @patch('services.generation.image_generator.json.loads')
    def test_create_image_success(self, mock_json_loads, mock_b64decode, image_generator, mock_bedrock_client):
        """이미지 생성 성공 테스트"""
        # Mock 설정
        mock_response = Mock()
        mock_response.get.return_value.read.return_value = '{"images": ["base64_image_data"]}'
        mock_bedrock_client.invoke_model.return_value = mock_response
        mock_json_loads.return_value = {"images": ["base64_image_data"]}
        mock_b64decode.return_value = b"fake_image_bytes"

        # 테스트 입력 데이터
        input_data = ImageGenerationInput(topic="AI 마케팅 이미지", cut_count=1)

        # 테스트 실행
        with patch('services.generation.image_generator.ImageGenerator._save_image_to_file') as mock_save:
            mock_save.return_value = "/content/generated_images/test.png"
            result = image_generator.create_image(input_data)
            
            assert len(result) == 1
            assert result[0] == "/content/generated_images/test.png"
            mock_bedrock_client.invoke_model.assert_called_once()

    def test_create_image_no_images_response(self, image_generator, mock_bedrock_client):
        """이미지 응답이 없는 경우 테스트"""
        # Mock 설정
        mock_response = Mock()
        mock_response.get.return_value.read.return_value = '{"images": []}'
        mock_bedrock_client.invoke_model.return_value = mock_response

        input_data = ImageGenerationInput(topic="AI 마케팅 이미지", cut_count=1)

        with pytest.raises(ImageGenerationError):
            image_generator.create_image(input_data)


class TestTranslationGenerator:
    """번역 생성기 테스트 클래스"""

    @pytest.fixture
    def mock_prompt_manager(self):
        """Mock 프롬프트 매니저"""
        return Mock()

    @pytest.fixture
    def mock_text_provider(self):
        """Mock 텍스트 Provider"""
        return Mock()

    @pytest.fixture
    def translation_generator(self, mock_prompt_manager, mock_text_provider):
        """번역 생성기 인스턴스 생성"""
        return TranslationGenerator(mock_prompt_manager, mock_text_provider)

    def test_translation_generator_initialization(self, translation_generator):
        """번역 생성기 초기화 테스트"""
        assert translation_generator.prompt_manager is not None
        assert translation_generator.text_provider is not None

    def test_translate_for_image_prompt_success(self, translation_generator, mock_prompt_manager, mock_text_provider):
        """이미지 프롬프트 번역 성공 테스트"""
        # Mock 설정
        mock_prompt_manager.generate_translate_prompt.return_value = "번역 프롬프트"
        mock_text_provider.invoke.return_value = "Translated AI marketing prompt"

        # 테스트 입력 데이터
        input_data = TranslationPromptInput(
            topic="AI 마케팅",
            brand_style_tone="전문적",
            product_category="소프트웨어"
        )

        # 테스트 실행
        result = translation_generator.translate_for_image_prompt(input_data)
        
        assert result["image_prompt"] == "Translated AI marketing prompt"
        mock_text_provider.invoke.assert_called_once()

    def test_translate_for_image_prompt_empty_topic(self, translation_generator):
        """빈 주제 번역 테스트"""
        input_data = TranslationPromptInput(topic="")

        with pytest.raises(TranslationPromptError):
            translation_generator.translate_for_image_prompt(input_data)

    def test_translate_for_image_prompt_provider_error(self, translation_generator, mock_text_provider):
        """Provider 오류 테스트"""
        # Mock 설정
        mock_text_provider.invoke.side_effect = Exception("Provider 오류")

        input_data = TranslationPromptInput(topic="AI 마케팅")

        with pytest.raises(TranslationPromptError):
            translation_generator.translate_for_image_prompt(input_data) 