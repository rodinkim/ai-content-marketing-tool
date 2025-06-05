# rag_system.py
import boto3
import json
import numpy as np
import faiss
import os
import tiktoken
import logging

# 이 로거는 현재 모듈(rag_system)의 이름을 가집니다.
logger = logging.getLogger(__name__) # <--- 로거 인스턴스 생성

bedrock_runtime = None # <--- 초기화 방식을 변경

# 토크나이저 초기화 (Claude 모델에 사용되는 토크나이저와 유사한 "cl100k_base" 사용)
ENCODER = tiktoken.get_encoding("cl100k_base")

# --- 청킹(Chunking)을 위한 상수 설정 ---
CHUNK_SIZE = 500  # 각 청크의 최대 토큰 수
CHUNK_OVERLAP = 100 # 청크 간 겹치는 토큰 수 (정보 손실 방지)

class RAGSystem:
    # bedrock_runtime을 생성자에서 주입받도록 변경
    def __init__(self, bedrock_runtime_client, knowledge_base_dir="knowledge_base"): # <--- 인자 추가
        self.bedrock_runtime = bedrock_runtime_client # <--- 주입받은 클라이언트 사용
        if not self.bedrock_runtime: # Bedrock 클라이언트가 없으면 에러
            logger.critical("RAGSystem 초기화 실패: Bedrock runtime 클라이언트가 유효하지 않습니다.")
            raise ValueError("Bedrock runtime 클라이언트가 유효하지 않아 RAGSystem을 초기화할 수 없습니다.")

        self.knowledge_base_dir = knowledge_base_dir
        self.documents = []
        self.embeddings = None
        self.index = None
        self.load_and_process_knowledge_base()

    def get_embedding(self, text):
        """텍스트를 받아 Titan Text Embeddings v2를 사용하여 임베딩 생성"""
        model_id = "amazon.titan-embed-text-v2:0"
        body = json.dumps({"inputText": text})
        try:
            # self.bedrock_runtime 사용
            response = self.bedrock_runtime.invoke_model( # <--- 변경
                body=body,
                modelId=model_id,
                accept="application/json",
                contentType="application/json"
            )
            response_body = json.loads(response.get('body').read())
            return np.array(response_body.get("embedding"), dtype=np.float32)
        except Exception as e:
            logger.error(f"Error getting embedding for text: {text[:50]}... Error: {e}")
            return None

    def chunk_text(self, text, chunk_size, chunk_overlap):
        """텍스트를 주어진 토큰 크기와 겹침으로 청크로 분할합니다."""
        tokens = ENCODER.encode(text)
        chunks = []
        for i in range(0, len(tokens), chunk_size - chunk_overlap):
            chunk_tokens = tokens[i : i + chunk_size]
            chunks.append(ENCODER.decode(chunk_tokens))
        return chunks

    def load_and_process_knowledge_base(self):
        """지식 베이스 디렉터리 및 서브 디렉터리에서 문서 로드, 청크 분할 및 임베딩 생성"""
        logger.info(f"Loading knowledge base from: {self.knowledge_base_dir}") 
        temp_embeddings = []
        self.documents = []

        if not os.path.exists(self.knowledge_base_dir):
            logger.error(f"Error: Knowledge base directory '{self.knowledge_base_dir}' not found. Please create it and add .txt files.")
            return

        for root, _, files in os.walk(self.knowledge_base_dir):
            for filename in files:
                if filename.endswith(".txt"):
                    filepath = os.path.join(root, filename)
                    try:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            full_content = f.read()
                            
                        chunks = self.chunk_text(full_content, CHUNK_SIZE, CHUNK_OVERLAP)
                        logger.info(f"File '{filepath}' processed into {len(chunks)} chunks.") 

                        for chunk in chunks:
                            self.documents.append(chunk)
                            embedding = self.get_embedding(chunk)
                            if embedding is not None:
                                temp_embeddings.append(embedding)
                    except Exception as e:
                        logger.error(f"Error processing file {filepath}: {e}") 
            
        if temp_embeddings:
            self.embeddings = np.vstack(temp_embeddings)
            d = self.embeddings.shape[1]
            self.index = faiss.IndexFlatL2(d)
            self.index.add(self.embeddings)
            logger.info(f"Knowledge base loaded and indexed. Total chunks: {len(self.documents)}, Embedding dimension: {d}") 
        else:
            logger.warning("No documents (or chunks) found or embeddings generated for knowledge base.") 
            logger.warning("Please ensure your 'knowledge_base' directory contains .txt files, possibly in subdirectories.") 

    def retrieve(self, query_text, k=3):
        """쿼리 텍스트와 유사한 문서 청크 검색"""
        query_embedding = self.get_embedding(query_text)
        if query_embedding is None:
            return []

        if self.index is None:
            logger.warning("FAISS index is not initialized. Cannot perform retrieval.") 
            return []

        D, I = self.index.search(query_embedding.reshape(1, -1), k)
        
        retrieved_docs = []
        for i in I[0]:
            if 0 <= i < len(self.documents):
                retrieved_docs.append(self.documents[i])
            else:
                logger.warning(f"Warning: Invalid index {i} found during retrieval. Index out of bounds.")
        return retrieved_docs

# 외부에서 RAG 시스템 인스턴스를 가져올 수 있도록 함수 제공
_rag_system_instance = None # 전역 변수로 인스턴스를 저장할 공간
def init_rag_system(bedrock_runtime_client): # <--- 초기화 함수 추가
    global _rag_system_instance
    if _rag_system_instance is None:
        try:
            _rag_system_instance = RAGSystem(bedrock_runtime_client)
            logger.info("RAGSystem 인스턴스가 성공적으로 초기화되었습니다.")
        except Exception as e:
            logger.critical(f"RAGSystem 인스턴스 초기화 중 오류 발생: {e}")
            _rag_system_instance = None # 초기화 실패 시 None으로 유지
    return _rag_system_instance

def get_rag_system():
    return _rag_system_instance