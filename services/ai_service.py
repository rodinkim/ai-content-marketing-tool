# ai-content-marketing-tool/services/ai_service.py
import json
import logging
import os # 파일 경로 조작을 위해 os 모듈 임포트
from config import Config # config.py에서 Config 클래스를 임포트

# AI 서비스 모듈 전용 로거 인스턴스 생성
logger = logging.getLogger(__name__)

# 프롬프트 템플릿 파일 경로 설정
# ai_service.py 파일이 있는 디렉토리를 기준으로 templates/prompts/claude_marketing_prompt.md를 찾습니다.
PROMPT_TEMPLATE_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), # services/ 디렉토리
    '..', # ai-content-marketing-tool/ 디렉토리로 이동
    'templates', # templates/ 디렉토리
    'prompts', # prompts/ 디렉토리
    'claude_marketing_prompt.md'
)

# AI 서비스 클래스 정의
class AIContentGenerator:
    def __init__(self, bedrock_client, rag_system):
        """
        AIContentGenerator 클래스를 초기화합니다.
        app.py에서 Bedrock 클라이언트와 RAG 시스템 인스턴스를 주입받습니다.
        """
        if not bedrock_client:
            raise ValueError("Bedrock client must be provided for AIContentGenerator.")
        
        self.bedrock_runtime_client = bedrock_client
        self.rag_system_instance = rag_system
        logger.info("AIContentGenerator initialized with Bedrock client and RAG system.")
        
        # 프롬프트 템플릿 파일을 로드합니다.
        self._load_prompt_template()

    def _load_prompt_template(self):
        """프롬프트 템플릿 파일을 로드합니다."""
        try:
            with open(PROMPT_TEMPLATE_PATH, 'r', encoding='utf-8') as f:
                self._base_prompt_template = f.read()
            logger.info(f"Prompt template loaded from: {PROMPT_TEMPLATE_PATH}")
        except FileNotFoundError:
            logger.critical(f"Prompt template file not found: {PROMPT_TEMPLATE_PATH}. Exiting.")
            raise FileNotFoundError(f"Prompt template file not found at {PROMPT_TEMPLATE_PATH}")
        except Exception as e:
            logger.critical(f"Error loading prompt template: {e}. Exiting.")
            raise RuntimeError(f"Failed to load prompt template: {e}")

    def _build_claude_prompt(self, topic, industry, content_type, tone, length, seo_keywords, email_subject_input, retrieved_docs):
        """
        Claude 모델에 전달할 프롬프트 문자열을 생성합니다.
        """
        context_info = ""
        if retrieved_docs:
            context_info = "\n\n--- 참고 자료 (Reference Document) ---\n" + "\n---\n".join(retrieved_docs) + "\n-----------------------------------------\n"
            logger.info(f"RAG: Retrieved document for query '{topic[:50]}...': {retrieved_docs[0][:100]}...")
        else:
            logger.info(f"RAG: No relevant document found for query '{topic[:50]}...'.")

        length_instruction = ""
        if length == "short":
            length_instruction = "간결하면서도 핵심적인 내용으로 작성하여, 약 500-1000자 내외로 작성해 주십시오."
        elif length == "medium":
            length_instruction = "적당한 길이로 상세하게 작성하여, 약 1000-2000자 내외로 작성해 주십시오."
        elif length == "long":
            length_instruction = "풍부한 내용으로 매우 상세하게 작성하여, 약 2000-4000자 내외로 작성해 주십시오."

        seo_instruction = ""
        if seo_keywords:
            keyword_list = [k.strip() for k in seo_keywords.split(',') if k.strip()]
            if keyword_list:
                seo_instruction = f"다음 SEO 키워드를 콘텐츠에 **자연스럽게 그리고 여러 번** 포함하여 검색 엔진 최적화에 유리하도록 작성해 주십시오: {', '.join(keyword_list)}."
                logger.info(f"SEO Keywords to include: {seo_keywords}")
            else:
                logger.warning("SEO Keywords field was provided, but no valid keywords found after splitting.")

        email_instruction = ""
        if content_type == "이메일 뉴스레터":
            email_instruction = "이메일 뉴스레터 형식으로 작성해 주십시오. 매력적인 제목과 함께 본문은 구독자에게 유용하고 흥미로운 정보를 제공하고, 명확한 CTA(Call-to-Action)를 포함해야 합니다."
            if email_subject_input:
                email_instruction += f"\n사용자가 제공한 이메일 제목은 '{email_subject_input}' 입니다. 이 제목으로 작성해 주십시오."
            else:
                email_instruction += "\n**이메일 본문 앞에 이메일 제목을 2~3개 제안하고, 그 중 가장 매력적인 하나를 선택하여 최종 이메일 제목으로 사용한 후 본문을 시작하십시오.**"

        # 로드된 템플릿 문자열에 파이썬 f-string 포매팅을 적용합니다.
        # 이 변수들은 _build_claude_prompt 함수로 전달되는 인자들입니다.
        prompt = self._base_prompt_template.format(
            industry=industry,
            content_type=content_type,
            context_info=context_info,
            topic=topic,
            tone=tone,
            length_instruction=length_instruction,
            seo_instruction=seo_instruction,
            email_instruction=email_instruction
        )
        return prompt

    def generate_content(self, topic, industry, content_type, tone, length, seo_keywords, email_subject_input):
        """
        AI 모델을 호출하여 콘텐츠를 생성하는 핵심 로직입니다.
        (클래스 메서드로 변경)
        """
        if self.bedrock_runtime_client is None:
            logger.error("Bedrock client is not initialized in AIContentGenerator.")
            raise RuntimeError("Bedrock client is not initialized for content generation.")
        
        # RAG 시스템을 사용하여 관련 문서 검색
        retrieved_docs = []
        if self.rag_system_instance: # RAG 시스템 인스턴스가 존재할 때만 검색 시도
            rag_query = f"{industry} 업계 {topic} 관련 마케팅 전략"
            try:
                retrieved_docs = self.rag_system_instance.retrieve(rag_query, k=3)
            except Exception as e:
                logger.error(f"Error retrieving documents from RAG system: {e}")
                retrieved_docs = [] # 오류 발생 시 빈 리스트로 처리

        # 콘텐츠 길이에 따라 max_tokens 설정
        max_tokens_map = {
            "short": 1000,
            "medium": 2000,
            "long": 4000
        }
        selected_max_tokens = max_tokens_map.get(length, 2000)
        
        # 프롬프트 생성
        prompt = self._build_claude_prompt(
            topic=topic,
            industry=industry,
            content_type=content_type,
            tone=tone,
            length=length,
            seo_keywords=seo_keywords,
            email_subject_input=email_subject_input,
            retrieved_docs=retrieved_docs
        )
        
        # 모델 ID를 config.py에서 가져옵니다.
        model_id = Config.CLAUDE_MODEL_ID 

        body = json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "messages": [
                {
                    "role": "user",
                    "content": [{"type": "text", "text": prompt}]
                }
            ],
            "max_tokens": selected_max_tokens,
            "temperature": 0.7,
            "top_p": 0.9
        })

        generated_text = "콘텐츠 생성 실패."
        try:
            response = self.bedrock_runtime_client.invoke_model(
                body=body,
                modelId=model_id,
                accept="application/json",
                contentType="application/json"
            )
            response_body = json.loads(response.get('body').read())
            
            if response_body and response_body.get('content'):
                for item in response_body['content']:
                    if item['type'] == 'text':
                        generated_text = item['text']
                        break
        except Exception as e:
            logger.error(f"Error invoking Bedrock model for content generation: {e}")
            generated_text = f"콘텐츠 생성 중 오류 발생: {e}"
        return generated_text

# AIContentGenerator 인스턴스를 저장할 전역 변수
_ai_content_generator_instance = None

# app.py에서 호출할 초기화 함수
def init_ai_service(bedrock_client, rag_system):
    """
    AI 서비스 모듈을 초기화합니다.
    app.py에서 Bedrock 클라이언트와 RAG 시스템 인스턴스를 주입받습니다.
    """
    global _ai_content_generator_instance
    if _ai_content_generator_instance is None: # 한 번만 초기화되도록
        try:
            _ai_content_generator_instance = AIContentGenerator(bedrock_client, rag_system)
            logger.info("AIContentGenerator 인스턴스가 성공적으로 초기화되었습니다.")
        except Exception as e:
            logger.critical(f"AIContentGenerator 인스턴스 초기화 중 오류 발생: {e}")
            _ai_content_generator_instance = None # 초기화 실패 시 None으로 유지

# 외부에서 AIContentGenerator 인스턴스를 가져올 수 있도록 함수 제공
def get_ai_content_generator():
    return _ai_content_generator_instance