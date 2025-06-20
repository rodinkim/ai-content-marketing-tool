# ai-content-marketing-tool/services/ai_rag/chunker.py

import tiktoken
from typing import List

# ai_constants 모듈에서 필요한 상수들을 상대 경로로 임포트합니다.
from .ai_constants import ENCODER, CHUNK_SIZE, CHUNK_OVERLAP

def chunk_text(text: str) -> List[str]:
    """텍스트를 토큰 기반으로 청크로 분할합니다."""
    # 입력이 유효한 문자열이 아니면 빈 리스트 반환
    if not isinstance(text, str) or not text:
        return []

    # tiktoken ENCODER를 사용하여 텍스트를 토큰으로 인코딩
    tokens = ENCODER.encode(text)
    chunks = []
    # 청크 크기와 오버랩을 고려하여 토큰을 분할
    for i in range(0, len(tokens), CHUNK_SIZE - CHUNK_OVERLAP):
        chunk_tokens = tokens[i : i + CHUNK_SIZE]
        # 분할된 토큰을 다시 텍스트로 디코딩하여 청크 리스트에 추가
        chunks.append(ENCODER.decode(chunk_tokens))
    return chunks