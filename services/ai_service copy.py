# ai-content-marketing-tool/services/ai_service.py

import os
import logging
import json
import numpy as np
import tiktoken
from flask import current_app 

logger = logging.getLogger(__name__)

# 토크나이저 초기화 (Claude 모델에 사용되는 토크나이저와 유사한 "cl100k_base" 사용)
ENCODER = tiktoken.get_encoding("cl100k_base")

# --- 청킹(Chunking)을 위한 상수 설정 ---
CHUNK_SIZE = 500    # 각 청크의 최대 토큰 수
CHUNK_OVERLAP = 100 # 청크 간 겹치는 토큰 수 (정보 손실 방지)

# 싱글톤 인스턴스를 저장할 변수
_ai_content_generator_instance = None

class AIContentGenerator:
    def __init__(self, bedrock_runtime_client, rag_system_instance, app_root_path):
        self.bedrock_runtime = bedrock_runtime_client
        self.rag_system = rag_system_instance
        self.prompt_template = ""
        self.industry_embeddings = {} # 업종별 임베딩 캐시

        # --- 프롬프트 템플릿 로드 ---
        # app_root_path를 사용하여 안전하게 경로 구성
        prompt_template_path = os.path.join(app_root_path, 'templates', 'prompts', 'claude_marketing_prompt.md')
        
        try:
            with open(prompt_template_path, 'r', encoding='utf-8') as f:
                self.prompt_template = f.read()
            logger.info(f"Prompt template loaded from: {prompt_template_path}")
        except FileNotFoundError:
            logger.critical(f"Prompt template file not found: {prompt_template_path}. Exiting.")
            raise RuntimeError(f"Prompt template file not found at {prompt_template_path}")
        except Exception as e:
            logger.critical(f"Error loading prompt template: {e}. Exiting.")
            raise RuntimeError(f"Error loading prompt template: {e}")

        # 업종별 프롬프트 임베딩 사전 계산 (RAG 검색 효율성 증대)
        self.precompute_industry_embeddings()
        logger.info("AIContentGenerator 인스턴스가 성공적으로 초기화되었습니다.")
        
    def _invoke_llm(self, prompt, model_id="anthropic.claude-3-5-sonnet-20240620-v1:0", max_tokens=2000):
        """Bedrock Claude 3.5 Sonnet 모델 호출"""
        body = json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens,
            "messages": [
                {"role": "user", "content": prompt}
            ]
        })
        try:
            response = self.bedrock_runtime.invoke_model(
                body=body,
                modelId=model_id,
                accept="application/json",
                contentType="application/json"
            )
            response_body = json.loads(response.get('body').read())
            # Claude 3.5 Sonnet 응답 파싱
            return response_body['content'][0]['text']
        except Exception as e:
            logger.error(f"LLM 호출 실패: {e}")
            raise RuntimeError(f"콘텐츠 생성 중 오류 발생: {e}")

    def precompute_industry_embeddings(self):
        """사전 정의된 업종 목록에 대한 임베딩을 미리 계산하여 캐시합니다."""
        industries = [
            "IT",           # IT 기술
            "Fashion",      # 패션 의류
            "Food",         # 식품 요리
            "Healthcare",   # 헬스케어/건강
            "Beauty",       # 뷰티/코스메틱
            "Travel"        # 여행/레저
        ]
        logger.info("Precomputing industry embeddings...")
        for industry in industries:
            embedding = self.rag_system.get_embedding(industry)
            if embedding is not None:
                self.industry_embeddings[industry] = embedding
            else:
                logger.warning(f"업종 '{industry}'에 대한 임베딩 생성 실패.")
        logger.info(f"Finished precomputing {len(self.industry_embeddings)} industry embeddings.")

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

        # 2. 프롬프트 구성
        # length_instruction 값 생성
        length_instruction_text = ""
        if length == "short":
            length_instruction_text = "콘텐츠 길이는 짧게(약 500-1000자) 작성하십시오."
        elif length == "medium":
            length_instruction_text = "콘텐츠 길이는 중간(약 1000-2000자)으로 작성하십시오."
        elif length == "long":
            length_instruction_text = "콘텐츠 길이는 길게(약 2000-4000자) 작성하십시오."

        # seo_instruction 값 생성
        seo_instruction_text = f"다음 키워드를 자연스럽게 포함: {seo_keywords}" if seo_keywords else "별도의 SEO 키워드 지시 없음."

        # email_instruction 값 생성
        email_instruction_text = ""
        if content_type == "이메일 뉴스레터":
            if email_subject_input:
                email_instruction_text = f"다음 제목으로 이메일을 작성해주세요: '{email_subject_input}'"
            else:
                email_instruction_text = "적절한 이메일 제목을 2~3개 제안하고, 그중 하나를 본문에 사용해주세요."
        
        prompt_parts = {
            "topic": topic,
            "industry": industry,
            "content_type": content_type,
            "tone": tone,
            "context": context_str,
            "length_instruction": length_instruction_text,
            "seo_instruction": seo_instruction_text,
            "email_instruction": email_instruction_text
        }
        
        final_prompt = self.prompt_template.format(**prompt_parts)
        
        logger.info(f"LLM Prompt for '{topic}' ({content_type}, {industry}) generated.")

        # 3. LLM 호출
        generated_text = self._invoke_llm(final_prompt)
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