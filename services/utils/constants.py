# ai-content-marketing-tool/services/utils/constants.py

import tiktoken
import os

# 토크나이저 (Claude 3.5 Sonnet, GPT-4 등 호환)
ENCODER = tiktoken.get_encoding("cl100k_base")

# 청킹 설정
CHUNK_SIZE = 500
CHUNK_OVERLAP = 100

# LLM 기본값
DEFAULT_LLM_MAX_TOKENS = 2000
DEFAULT_LLM_TEMPERATURE = 0.7  # LLM 생성 시 창의성/랜덤성(0=고정, 1=완전랜덤)
DEFAULT_LLM_TOP_P = 0.9        # LLM 생성 시 샘플링 다양성(1=최대 다양성)

# RAG/임베딩 옵션
RAG_TOP_K = 5  # RAG 검색 시 반환할 문서(청크) 개수(Top-K, 검색 다양성/정확도 트레이드오프)

# 업종(산업군) 목록
INDUSTRIES = [
    "IT",
    "Fashion",
    "Healthcare",
    "Beauty",
    "Travel"
]

# 경로 설정
PROMPT_TEMPLATE_RELATIVE_PATH = os.path.join('templates', 'prompts')
IMAGE_SAVE_PATH = os.getenv('IMAGE_SAVE_PATH', 'generated_images')