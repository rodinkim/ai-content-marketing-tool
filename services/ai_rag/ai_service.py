# ai-content-marketing-tool/services/ai_rag/ai_service.py

import os
import logging
import json
import numpy as np
from flask import current_app

# services/ai_rag 디렉토리 내의 모듈들을 상대 경로로 임포트합니다.
from .ai_constants import ( 
    ENCODER, CHUNK_SIZE, CHUNK_OVERLAP, # 이 상수들은 여기서 직접 사용되지는 않지만, 다른 모듈에서 사용될 수 있어 임포트 유지
    DEFAULT_LLM_MODEL_ID, DEFAULT_LLM_MAX_TOKENS,
    INDUSTRIES, PROMPT_TEMPLATE_RELATIVE_PATH
)
from .prompt_manager import PromptManager 
from .llm_invoker import BedrockClaudeProvider 
from .embedding_generator import EmbeddingManager 

logger = logging.getLogger(__name__)

# 싱글톤 인스턴스를 저장할 변수
_ai_content_generator_instance = None

class AIContentGenerator:
    def __init__(self, bedrock_runtime_client, rag_system_instance, app_root_path):
        self.rag_system = rag_system_instance
        self.prompt_manager = PromptManager(app_root_path, PROMPT_TEMPLATE_RELATIVE_PATH)

        # EmbeddingManager 초기화 및 업종 임베딩 사전 계산: 임베딩 관련 로직을 담당
        self.embedding_manager = EmbeddingManager(self.rag_system)
        self.embedding_manager.precompute_industry_embeddings(INDUSTRIES)

        # --- 추가: Provider 및 작업 매핑 설정 ---
        # 1. 사용 가능한 전문가(Provider) 목록 정의
        self.providers = {
            'text': BedrockClaudeProvider(bedrock_runtime_client)
            # 나중에 여기에 'image': DallEProvider(openai_client) 등이 추가될 것
        }
        # 2. 콘텐츠 유형을 어떤 작업(Provider)에 연결할지 정의하는 라우팅 테이블
        self.task_mapping = {
            'email_newsletter': 'text',
            'email_promotion': 'text',
            'blog_list': 'text',  # 블로그 스타일 추가
            'blog_review': 'text'   # 블로그 스타일 추가
            # 다른 블로그 스타일이나 콘텐츠 타입이 있다면 여기에 추가
        }
        # -----------------------------------------
        
        logger.info("AIContentGenerator 인스턴스가 성공적으로 초기화되었습니다.")
    
    # 'blog_style' 파라미터 추가
    def generate_content(self, topic, industry, content_type, blog_style, tone, length, 
                         seo_keywords=None, email_subject=None, target_audience=None, 
                         email_type=None, key_points=None, landing_page_url=None):
        """
        주어진 파라미터와 RAG를 사용하여 AI 콘텐츠를 생성합니다.
        """
        # 1. RAG 검색 (주제와 업종 기반)
        # RAGSystem 인스턴스의 retrieve 메서드를 호출하여 관련 문서 청크를 가져옵니다.
        query = f"주제: {topic}, 업종: {industry}, 콘텐츠 종류: {content_type}"
        retrieved_docs = self.rag_system.retrieve(query, k=5) # K개 관련 문서 검색
        
        context_str = "\n".join([f"관련 문서 {i+1}: {doc}" for i, doc in enumerate(retrieved_docs)])
        if not context_str:
            context_str = "참조할 관련 정보 없음."

        # 2. 프롬프트 구성 (PromptManager 사용)
        # prompt_manager 인스턴스의 generate_final_prompt 메서드를 호출하여 최종 프롬프트 생성
        final_prompt = self.prompt_manager.generate_final_prompt(
            topic=topic,
            industry=industry,
            content_type=content_type,
            blog_style=blog_style,
            tone=tone,
            length=length,
            context=context_str,
            seo_keywords=seo_keywords,
            email_subject=email_subject,
            target_audience=target_audience,
            email_type=email_type,
            key_points=key_points,
            landing_page_url=landing_page_url
        )
        
        # 3. 어떤 작업을 할지 결정 (예: 'text' 또는 'image')
        task_type = self.task_mapping.get(content_type)
        if not task_type:
            raise ValueError(f"지원하지 않는 콘텐츠 유형입니다: {content_type}")
            
        # 4. 해당 작업의 전문가(Provider) 선택
        provider = self.providers.get(task_type)
        if not provider:
            raise ValueError(f"'{task_type}' 작업을 처리할 Provider를 찾을 수 없습니다.")

        # 5. 선택된 Provider를 통해 LLM 호출
        # (모델 ID 등은 나중에 content_type에 따라 동적으로 변경 가능)
        generated_text = provider.invoke(
            prompt=final_prompt,
            model_id=DEFAULT_LLM_MODEL_ID,
            max_tokens=DEFAULT_LLM_MAX_TOKENS
        )
        return generated_text

# DALL-E를 나중에 추가할 것이므로, app_factory_utils.py와 시그니처를 맞춰주는 것이 좋습니다.
# 만약 app_factory_utils.py를 이전으로 되돌렸다면, openai_client 파라미터를 빼도 됩니다.
def init_ai_service(bedrock_runtime_client, rag_system_instance):  # openai_client는 나중에 추가
    """
    AIContentGenerator 인스턴스를 초기화하고 싱글톤으로 설정합니다.
    """
    global _ai_content_generator_instance
    if _ai_content_generator_instance is None:
        try:
            project_root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
            _ai_content_generator_instance = AIContentGenerator(
                bedrock_runtime_client, 
                rag_system_instance,
                current_app.root_path
            )
        except Exception as e:
            logger.critical(f"AIContentGenerator 인스턴스 초기화 중 오류 발생: {e}", exc_info=True)
            _ai_content_generator_instance = None
    return _ai_content_generator_instance

def get_ai_content_generator():
    """초기화된 AIContentGenerator 인스턴스를 반환합니다."""
    if _ai_content_generator_instance is None:
        logger.warning("AIContentGenerator가 아직 초기화되지 않았습니다. init_ai_service를 먼저 호출해야 합니다.")
    return _ai_content_generator_instance