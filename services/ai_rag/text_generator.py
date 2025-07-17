# ai-content-marketing-tool/services/ai_rag/text_generator.py

import logging
from flask import current_app
from config import config

from .ai_constants import (
    DEFAULT_LLM_MAX_TOKENS,
    INDUSTRIES, PROMPT_TEMPLATE_RELATIVE_PATH
)
from .prompt_manager import PromptManager
from .llm_invoker import BedrockClaudeProvider
from .embedding_generator import EmbeddingManager

logger = logging.getLogger(__name__)

# 싱글톤 인스턴스를 저장할 변수
_text_generator_instance = None


class TextGenerator:
    def __init__(self, bedrock_runtime_client, rag_system_instance, app_root_path):
        self.rag_system = rag_system_instance
        self.prompt_manager = PromptManager(app_root_path, PROMPT_TEMPLATE_RELATIVE_PATH)
        
        self.embedding_manager = EmbeddingManager(bedrock_runtime_client)
        self.embedding_manager.precompute_industry_embeddings(INDUSTRIES)

        # 사용 가능한 전문가(Provider) 목록 정의
        self.providers = {
            'text': BedrockClaudeProvider(bedrock_runtime_client)
        }
        self.task_mapping = {
            'email_newsletter': 'text',
            'email_promotion': 'text',
            'blog_list': 'text',
            'blog_review': 'text'
        }
        
        logger.info("TextGenerator 인스턴스가 성공적으로 초기화되었습니다.")


    def generate_content(
        self,
        topic,
        industry,
        content_type,
        blog_style=None,
        tone=None,
        length_option=None,
        seo_keywords=None,
        email_subject=None,
        target_audience=None,
        email_type=None,
        key_points=None,
        landing_page_url=None,
        brand_style_tone=None,
        product_category=None,
        ad_purpose=None
    ):
        """
        주어진 파라미터와 RAG를 사용하여 AI 텍스트 콘텐츠를 생성합니다.
        """
        # 1. RAG 검색
        query = f"주제: {topic}, 업종: {industry}, 콘텐츠 종류: {content_type}"
        retrieved_docs = self.rag_system.retrieve(query, k=5)
        
        context_str = "\n".join([f"관련 문서 {i+1}: {doc}" for i, doc in enumerate(retrieved_docs)])
        if not context_str:
            context_str = "참조할 관련 정보 없음."

        # 템플릿 파일명 결정 로직 추가
        if content_type == "blog":
            if blog_style == "추천/리스트 글":
                template_key = "blog_list"
            elif blog_style == "리뷰/후기 글":
                template_key = "blog_review"
            else:
                template_key = "blog_list"  # 기본값
        elif content_type == "email":
            if email_type == "newsletter":
                template_key = "email_newsletter"
            elif email_type == "promotion":
                template_key = "email_promotion"
            else:
                template_key = "email_newsletter"  # 기본값
        else:
            template_key = content_type

        # 2. 프롬프트 구성
        final_prompt = self.prompt_manager.generate_text_prompt(
            content_type=template_key,
            topic=topic,
            industry=industry,
            context=context_str,
            target_audience=target_audience,
            key_points=key_points,
            blog_style=blog_style,
            tone=tone,
            length=length_option,
            seo_keywords=seo_keywords,
            email_subject=email_subject,
            email_type=email_type,
            landing_page_url=landing_page_url,
            brand_style_tone=brand_style_tone,
            product_category=product_category,
            ad_purpose=ad_purpose
        )
        
        # 3. 작업 유형 결정
        task_type = self.task_mapping.get(template_key)
        if not task_type:
            raise ValueError(f"지원하지 않는 콘텐츠 유형입니다: {template_key}")
            
        # 4. 해당 작업의 전문가(Provider) 선택
        provider = self.providers.get(task_type)
        if not provider:
            raise ValueError(f"'{task_type}' 작업을 처리할 Provider를 찾을 수 없습니다.")

        # 5. 선택된 Provider를 통해 LLM 호출
        generated_text = provider.invoke(
            prompt=final_prompt,
            model_id=config.CLAUDE_MODEL_ID,
            max_tokens=DEFAULT_LLM_MAX_TOKENS
        )
        return generated_text


def init_text_generator(bedrock_runtime_client, rag_system_instance):
    """
    TextGenerator 인스턴스를 초기화하고 싱글톤으로 설정합니다.
    """
    global _text_generator_instance
    if _text_generator_instance is None:
        try:
            _text_generator_instance = TextGenerator(
                bedrock_runtime_client,
                rag_system_instance,
                current_app.root_path
            )
        except Exception as e:
            logger.critical(f"TextGenerator 인스턴스 초기화 중 오류 발생: {e}", exc_info=True)
            _text_generator_instance = None
    return _text_generator_instance


def get_text_generator():
    """초기화된 TextGenerator 인스턴스를 반환합니다."""
    if _text_generator_instance is None:
        logger.warning("TextGenerator가 아직 초기화되지 않았습니다. init_text_generator를 먼저 호출해야 합니다.")
    return _text_generator_instance