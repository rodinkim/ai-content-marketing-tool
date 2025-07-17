# ai-content-marketing-tool/services/ai_rag/ai_constants.py

import tiktoken
import os

# 토크나이저 초기화
ENCODER = tiktoken.get_encoding("cl100k_base")

# --- 청킹(Chunking)을 위한 상수 설정 ---
CHUNK_SIZE = 500
CHUNK_OVERLAP = 100

# --- LLM 관련 기본 설정 ---
DEFAULT_LLM_MAX_TOKENS = 2000

# --- 업종 목록 ---
INDUSTRIES = [
    "IT", "Fashion", "Food",
    "Healthcare", "Beauty", "Travel"
]

# --- 프롬프트 템플릿 파일 경로 ---
PROMPT_TEMPLATE_RELATIVE_PATH = os.path.join('templates', 'prompts')