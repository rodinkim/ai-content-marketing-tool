# ai-content-marketing-tool/services/rag_system.py
import boto3
import json
import numpy as np
import faiss
import os 
import tiktoken
import logging
from flask import current_app 

logger = logging.getLogger(__name__)

ENCODER = tiktoken.get_encoding("cl100k_base")

CHUNK_SIZE = 500    
CHUNK_OVERLAP = 100 

class RAGSystem:
    def __init__(self, bedrock_runtime_client, knowledge_base_dir):
        self.bedrock_runtime = bedrock_runtime_client
        if not self.bedrock_runtime:
            logger.critical("RAGSystem 초기화 실패: Bedrock runtime 클라이언트가 유효하지 않습니다.")
            raise ValueError("Bedrock runtime 클라이언트가 유효하지 않아 RAGSystem을 초기화할 수 없습니다.")

        self.knowledge_base_dir = knowledge_base_dir 

        self.documents = []
        self.embeddings = None
        self.index = None
        self.load_and_process_knowledge_base()

    def get_embedding(self, text):
        """텍스트를 받아 Titan Text Embeddings v2를 사용하여 임베딩 생성"""
        # 입력 텍스트가 확실히 문자열이도록 강제합니다.
        # 혹시 None, dict, list 등이 전달되어도 문자열로 변환 시도합니다.
        if text is None:
            logger.warning("get_embedding: 입력 텍스트가 None입니다. 임베딩 생성 실패.")
            return None
        
        # Bedrock에 전달할 최종 inputText를 구성
        final_input_text = ""
        if isinstance(text, str):
            final_input_text = text
        else:
            try:
                # 문자열이 아니면 JSON 등으로 직렬화하여 문자열로 변환 시도 (한글 깨짐 방지)
                # 이전에 발생했던 ValidationException을 방지합니다.
                final_input_text = json.dumps(text, ensure_ascii=False) 
                logger.warning(f"get_embedding: 입력 텍스트가 문자열이 아닙니다 ({type(text)}). JSON 직렬화 후 사용합니다.")
            except TypeError:
                # JSON으로도 직렬화 불가능한 경우, 단순히 str()로 변환
                final_input_text = str(text)
                logger.warning(f"get_embedding: 입력 텍스트를 JSON 직렬화할 수 없습니다. str()로 변환하여 사용합니다 ({type(text)}).")
            except Exception as e:
                logger.error(f"get_embedding: 입력 텍스트 변환 중 예상치 못한 오류 발생: {e}", exc_info=True)
                return None

        model_id = "amazon.titan-embed-text-v2:0"
        # body는 {"inputText": "순수한 문자열"} 형태여야 합니다.
        body = json.dumps({"inputText": final_input_text}) 

        try:
            response = self.bedrock_runtime.invoke_model(
                body=body,
                modelId=model_id,
                accept="application/json",
                contentType="application/json"
            )
            response_body = json.loads(response.get('body').read())
            return np.array(response_body.get("embedding"), dtype=np.float32)
        except Exception as e:
            # 오류 로그 메시지도 안전하게 수정
            log_text_preview = final_input_text[:50] if isinstance(final_input_text, str) else str(type(final_input_text))
            logger.error(f"Error getting embedding for text: {log_text_preview}... Error: {e}", exc_info=True)
            return None

    def chunk_text(self, text, chunk_size, chunk_overlap):
        tokens = ENCODER.encode(text)
        chunks = []
        for i in range(0, len(tokens), chunk_size - chunk_overlap):
            chunk_tokens = tokens[i : i + chunk_size]
            chunks.append(ENCODER.decode(chunk_tokens))
        return chunks

    def load_and_process_knowledge_base(self):
        logger.info(f"Loading knowledge base from: {self.knowledge_base_dir}") 
        temp_embeddings = []
        self.documents = []

        if not os.path.exists(self.knowledge_base_dir):
            logger.error(f"Error: Knowledge base directory '{self.knowledge_base_dir}' not found. Please create it and add .txt files.")
            return

        # os.walk() 사용
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

_rag_system_instance = None
def init_rag_system(bedrock_runtime_client):
    """
    RAGSystem 인스턴스를 초기화하고 싱글톤으로 설정합니다.
    """
    global _rag_system_instance
    if _rag_system_instance is None:
        try:
            from flask import current_app
            knowledge_base_path = os.path.join(current_app.root_path, "knowledge_base")
            _rag_system_instance = RAGSystem(bedrock_runtime_client, knowledge_base_dir=knowledge_base_path) 
            logger.info("RAGSystem 인스턴스가 성공적으로 초기화되었습니다.")
        except Exception as e:
            logger.critical(f"RAGSystem 인스턴스 초기화 중 오류 발생: {e}")
            _rag_system_instance = None
    return _rag_system_instance

def get_rag_system():
    return _rag_system_instance