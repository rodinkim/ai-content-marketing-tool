# ai-content-marketing-tool/services/ai_rag/chunker.py

from typing import List
from langchain.text_splitter import RecursiveCharacterTextSplitter
from services.utils.constants import CHUNK_SIZE, CHUNK_OVERLAP

def chunk_text(text: str) -> List[str]:
    """
    LangChain 기반 텍스트 청킹 함수.
    Titan Text Embeddings v2, Claude 기반에 최적화된 토크나이저 사용.
    입력 텍스트를 CHUNK_SIZE, CHUNK_OVERLAP 기준으로 분할하여 리스트로 반환.
    """
    # 입력값이 문자열이 아니거나 비어 있으면 빈 리스트 반환
    if not isinstance(text, str) or not text:
        return []

    splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
        encoding_name="cl100k_base",  # Titan 및 Claude 모델 계열과 가장 유사한 토크나이저
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
    )

    return splitter.split_text(text)
