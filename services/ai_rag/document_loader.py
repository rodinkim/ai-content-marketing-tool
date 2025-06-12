# ai-content-marketing-tool/services/ai_rag/document_loader.py

import os
import logging
from typing import List, Tuple

# chunker 모듈에서 chunk_text 함수를 상대 경로로 임포트합니다.
from .chunker import chunk_text
# ai_constants 모듈에서 필요한 상수들을 임포트합니다.
# (이 파일에서 CHUNK_SIZE, CHUNK_OVERLAP을 직접 사용하지는 않지만,
# chunk_text 함수가 이를 사용하며 문서 로더가 청크 관련 설정을 인지한다는 의미에서 명시적 임포트를 유지합니다.)
from .ai_constants import CHUNK_SIZE, CHUNK_OVERLAP 

logger = logging.getLogger(__name__)

def load_documents_from_directory(knowledge_base_dir: str) -> List[str]:
    """
    지정된 디렉토리에서 모든 .txt 파일을 로드하고 청크로 분할하여 반환합니다.
    """
    all_chunks: List[str] = []
    
    # 지식 베이스 디렉토리가 존재하는지 먼저 확인합니다.
    if not os.path.exists(knowledge_base_dir):
        logger.error(f"Error: Knowledge base directory '{knowledge_base_dir}' not found. Please create it.")
        return []

    # 지정된 디렉토리와 모든 하위 디렉토리를 재귀적으로 순회합니다.
    for root, _, files in os.walk(knowledge_base_dir):
        for filename in files:
            # 파일 확장자가 .txt인지 확인합니다.
            if filename.endswith(".txt"):
                filepath = os.path.join(root, filename)
                try:
                    # 파일을 UTF-8 인코딩으로 읽어들입니다.
                    with open(filepath, 'r', encoding='utf-8') as f:
                        full_content = f.read()
                    
                    # chunker.py에 정의된 chunk_text 함수를 사용하여 전체 내용을 청크로 분할합니다.
                    chunks = chunk_text(full_content)
                    # 생성된 청크들을 최종 청크 리스트에 추가합니다.
                    all_chunks.extend(chunks)
                    logger.info(f"File '{filepath}' processed into {len(chunks)} chunks.")
                except Exception as e:
                    # 파일 처리 중 오류가 발생하면 로그를 기록합니다.
                    logger.error(f"Error processing file {filepath}: {e}", exc_info=True)
    
    logger.info(f"Finished loading documents. Total chunks generated: {len(all_chunks)}")
    return all_chunks