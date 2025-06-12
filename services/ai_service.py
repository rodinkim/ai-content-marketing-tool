# ai-content-marketing-tool/services/ai_service.py

import os
import logging
import json
import numpy as np
from flask import current_app 

# 새로 만든 모듈들 임포트
from .ai_constants import ENCODER, CHUNK_SIZE, CHUNK_OVERLAP, DEFAULT_LLM_MODEL_ID, DEFAULT_LLM_MAX_TOKENS, INDUSTRIES, PROMPT_TEMPLATE_RELATIVE_PATH
from .prompt_manager import PromptManager
from .llm_invoker import invoke_claude_llm
from .embedding_manager import EmbeddingManager

logger = logging.getLogger(__name__)

# 싱글톤 인스턴스를 저장할 변수
_ai_content_generator_instance = None

class AIContentGenerator:
    def __init__(self, bedrock_runtime_client, rag_system_instance, app_root_path):
        self.bedrock_runtime = bedrock_runtime_client
        self.rag_system = rag_system_instance
        
        # PromptManager 초기화
        self.prompt_manager = PromptManager(app_root_path, PROMPT_TEMPLATE_RELATIVE_PATH)

        # EmbeddingManager 초기화 및 업종 임베딩 사전 계산
        self.embedding_manager = EmbeddingManager(self.rag_system)
        self.embedding_manager.precompute_industry_embeddings(INDUSTRIES)
        
        logger.info("AIContentGenerator 인스턴스가 성공적으로 초기화되었습니다.")

    def generate_content(self, topic, industry, content_type, tone, length, seo_keywords=None, email_subject_input=None):
        """
        주어진 파라미터와 RAG를 사용하여 AI 콘텐츠를 생성합니다.
        """
        # 1. RAG 검색 (주제와 업종 기반)
        query = f"주제: {topic}, 업종: {industry}, 콘텐츠 종류: {content_type}"
        retrieved_docs = self.rag_system.retrieve(query, k=5) # K개 관련 문서 검색
        
        context_str = "\n".join([f"관련 문서 {i+1}: {doc}" for i, doc in enumerate(retrieved_docs)])
        if not context_str:
            context_str = "참조할 관련 정보 없음."

        # 2. 프롬프트 구성 (PromptManager 사용)
        final_prompt = self.prompt_manager.generate_final_prompt(
            topic=topic,
            industry=industry,
            content_type=content_type,
            tone=tone,
            length=length,
            context=context_str,
            seo_keywords=seo_keywords,
            email_subject_input=email_subject_input
        )
        
        # 3. LLM 호출 (llm_invoker.py 사용)
        generated_text = invoke_claude_llm(
            bedrock_runtime_client=self.bedrock_runtime,
            prompt=final_prompt,
            model_id=DEFAULT_LLM_MODEL_ID,
            max_tokens=DEFAULT_LLM_MAX_TOKENS
        )
        return generated_text

def init_ai_service(bedrock_runtime_client, rag_system_instance):
    """
    AIContentGenerator 인스턴스를 초기화하고 싱글톤으로 설정합니다.
    """
    global _ai_content_generator_instance
    if _ai_content_generator_instance is None:
        try:
            _ai_content_generator_instance = AIContentGenerator(
                bedrock_runtime_client, 
                rag_system_instance,
                current_app.root_path # Flask 앱의 루트 경로를 생성자로 전달
            )
        except Exception as e:
            logger.critical(f"AIContentGenerator 인스턴스 초기화 중 오류 발생: {e}")
            _ai_content_generator_instance = None
    return _ai_content_generator_instance

def get_ai_content_generator():
    """초기화된 AIContentGenerator 인스턴스를 반환합니다."""
    if _ai_content_generator_instance is None:
        logger.warning("AIContentGenerator가 아직 초기화되지 않았습니다. init_ai_service를 먼저 호출해야 합니다.")
    return _ai_content_generator_instance