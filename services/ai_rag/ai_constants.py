# ai-content-marketing-tool/services/ai_rag/ai_constants.py

import tiktoken
import os # os 모듈 임포트가 반드시 필요합니다.

# 토크나이저 초기화 (Claude 모델에 사용되는 토크나이저와 유사한 "cl100k_base" 사용)
ENCODER = tiktoken.get_encoding("cl100k_base")

# --- 청킹(Chunking)을 위한 상수 설정 ---
CHUNK_SIZE = 500  # 각 청크의 최대 토큰 수
CHUNK_OVERLAP = 100 # 청크 간 겹치는 토큰 수 (정보 손실 방지)

# --- LLM 관련 설정 ---
DEFAULT_LLM_MODEL_ID = "anthropic.claude-3-5-sonnet-20240620-v1:0"
DEFAULT_LLM_MAX_TOKENS = 2000

# --- 임베딩 모델 관련 설정 ---
EMBEDDING_MODEL_ID = "amazon.titan-embed-text-v2:0" # Titan Text Embeddings v2 모델 ID

# --- 업종 목록 ---
INDUSTRIES = [
    "IT",           # IT 기술
    "Fashion",      # 패션 의류
    "Food",         # 식품 요리
    "Healthcare",   # 헬스케어/건강
    "Beauty",       # 뷰티/코스메틱
    "Travel"        # 여행/레저
]

# --- 프롬프트 템플릿 파일 경로 ---
# ROOT_PATH는 앱 실행 시 동적으로 설정되므로, 여기서는 상대 경로만 정의
#PROMPT_TEMPLATE_RELATIVE_PATH = os.path.join('templates', 'prompts', 'claude_marketing_prompt.md')
PROMPT_TEMPLATE_RELATIVE_PATH = os.path.join('templates', 'prompts')