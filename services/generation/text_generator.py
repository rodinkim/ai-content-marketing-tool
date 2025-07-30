# ai-content-marketing-tool/services/ai_rag/text_generator.py

import logging
from dataclasses import dataclass
from typing import Optional
from services.utils.constants import (
    DEFAULT_LLM_MAX_TOKENS,
    INDUSTRIES, PROMPT_TEMPLATE_RELATIVE_PATH,
    DEFAULT_LLM_TEMPERATURE, DEFAULT_LLM_TOP_P,
    RAG_TOP_K
)
from ..utils.prompt_manager import PromptManager
from ..utils.llm_invoker import BedrockClaudeProvider
from services.ai_rag.embedding_generator import EmbeddingManager

logger = logging.getLogger(__name__)

class TextGenerationError(Exception):
    """텍스트 생성 관련 예외"""
    pass

@dataclass
class TextGenerationInput:
    """텍스트 생성에 필요한 입력값 데이터 클래스"""
    topic: str
    industry: str
    content_type: str
    blog_style: Optional[str] = None
    tone: Optional[str] = None
    length_option: Optional[str] = None
    seo_keywords: Optional[str] = None
    email_subject: Optional[str] = None
    target_audience: Optional[str] = None
    email_type: Optional[str] = None
    key_points: Optional[str] = None
    landing_page_url: Optional[str] = None
    brand_style_tone: Optional[str] = None
    product_category: Optional[str] = None
    ad_purpose: Optional[str] = None

class TextGenerator:
    """
    AI 텍스트 콘텐츠 생성을 담당하는 클래스
    """
    PROVIDERS = {
        'text': BedrockClaudeProvider
    }
    TASK_MAPPING = {
        'email_newsletter': 'text',
        'email_promotion': 'text',
        'blog_list': 'text',
        'blog_review': 'text'
    }

    def __init__(self, bedrock_runtime_client, rag_system_instance, app_root_path, model_id: str):
        self.rag_system = rag_system_instance
        self.prompt_manager = PromptManager(app_root_path, PROMPT_TEMPLATE_RELATIVE_PATH)
        self.embedding_manager = EmbeddingManager(bedrock_runtime_client)
        self.embedding_manager.precompute_industry_embeddings(INDUSTRIES)
        self.provider_instances = {
            key: provider_cls(bedrock_runtime_client, model_id)
            for key, provider_cls in self.PROVIDERS.items()
        }
        logger.info("TextGenerator 인스턴스가 성공적으로 초기화되었습니다.")

    def generate_content(self, input_data: TextGenerationInput) -> str:
        """
        입력값과 RAG를 활용해 AI 텍스트 콘텐츠를 생성합니다.
        """
        # 1. RAG 검색
        query = f"주제: {input_data.topic}, 업종: {input_data.industry}, 콘텐츠 종류: {input_data.content_type}"
        retrieved_docs = self.rag_system.retrieve(query, k=RAG_TOP_K)
        context_str = "\n".join([f"관련 문서 {i+1}: {doc}" for i, doc in enumerate(retrieved_docs)])
        if not context_str:
            context_str = "참조할 관련 정보 없음."

        # 2. 템플릿 파일명 결정
        template_key = self.prompt_manager.get_template_key(
            input_data.content_type, input_data.blog_style, input_data.email_type
        )

        # 3. 프롬프트 구성
        final_prompt = self.prompt_manager.generate_text_prompt(
            content_type=template_key,
            topic=input_data.topic,
            industry=input_data.industry,
            context=context_str,
            target_audience=input_data.target_audience,
            key_points=input_data.key_points,
            blog_style=input_data.blog_style,
            tone=input_data.tone,
            length=input_data.length_option,
            seo_keywords=input_data.seo_keywords,
            email_subject=input_data.email_subject,
            email_type=input_data.email_type,
            landing_page_url=input_data.landing_page_url,
            brand_style_tone=input_data.brand_style_tone,
            product_category=input_data.product_category,
            ad_purpose=input_data.ad_purpose
        )

        # 4. 작업 유형 결정 및 Provider 선택
        task_type = self.TASK_MAPPING.get(template_key)
        if not task_type:
            logger.error(f"지원하지 않는 콘텐츠 유형입니다: {template_key}")
            raise TextGenerationError(f"지원하지 않는 콘텐츠 유형입니다: {template_key}")
        provider = self.provider_instances.get(task_type)
        if not provider:
            logger.error(f"'{task_type}' 작업을 처리할 Provider를 찾을 수 없습니다.")
            raise TextGenerationError(f"'{task_type}' 작업을 처리할 Provider를 찾을 수 없습니다.")

        # 5. LLM 호출
        try:
            generated_text = provider.invoke(
                prompt=final_prompt,
                max_tokens=DEFAULT_LLM_MAX_TOKENS,
                temperature=DEFAULT_LLM_TEMPERATURE,
                top_p=DEFAULT_LLM_TOP_P
            )
        except Exception as e:
            logger.error(f"텍스트 생성 중 예외 발생: {e}", exc_info=True)
            raise TextGenerationError(f"텍스트 생성 중 예외 발생: {e}")
        return generated_text

def create_text_generator(bedrock_runtime_client, rag_system_instance, app_root_path, model_id: str):
    """
    TextGenerator 인스턴스를 생성합니다.
    """
    return TextGenerator(bedrock_runtime_client, rag_system_instance, app_root_path, model_id)