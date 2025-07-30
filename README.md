# 🤖 AI 콘텐츠 마케팅 도구

> **AI 기반 마케팅 콘텐츠 자동 생성 플랫폼**  
> RAG(Retrieval-Augmented Generation) 기술을 활용한 업계별 맞춤형 마케팅 콘텐츠 생성 시스템

[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.1.1-green.svg)](https://flask.palletsprojects.com/)
[![AWS](https://img.shields.io/badge/AWS-Bedrock-orange.svg)](https://aws.amazon.com/bedrock/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-pgvector-blue.svg)](https://www.postgresql.org/)

## 📋 목차

- [프로젝트 개요](#-프로젝트-개요)
- [주요 기능](#-주요-기능)
- [기술 스택](#-기술-스택)
- [시스템 아키텍처](#-시스템-아키텍처)
- [설치 및 실행](#-설치-및-실행)
- [사용법](#-사용법)
- [API 문서](#-api-문서)
- [테스트](#-테스트)
- [배포](#-배포)


## 🎯 프로젝트 개요

AI 콘텐츠 마케팅 도구는 **RAG(Retrieval-Augmented Generation)** 기술을 활용하여 업계별 맞춤형 마케팅 콘텐츠를 자동으로 생성하는 웹 애플리케이션입니다.

### 핵심 특징

- 🧠 **RAG 기반 지능형 콘텐츠 생성**: 업계별 지식베이스를 활용한 정확하고 관련성 높은 콘텐츠 생성
- 🕷️ **자동 웹 크롤링**: 주간 자동 업데이트로 최신 마케팅 트렌드 수집
- 🎨 **멀티미디어 콘텐츠**: 텍스트와 이미지 동시 생성 지원
- 🏭 **업계별 특화**: IT, 패션, 헬스케어, 여행 등 다양한 업계 지원
- 🔄 **실시간 번역**: 한국어 입력을 영어 프롬프트로 자동 번역하여 이미지 생성

## ✨ 주요 기능

### 📝 텍스트 콘텐츠 생성
- **블로그 글**: 추천/리스트 글, 리뷰/후기 글
- **이메일 마케팅**: 뉴스레터, 프로모션 이메일
- **SNS 콘텐츠**: 소셜미디어용 짧은 콘텐츠
- **SEO 최적화**: 키워드 기반 검색엔진 최적화

### 🖼️ 이미지 콘텐츠 생성
- **AI 이미지 생성**: Stable Diffusion 기반 고품질 이미지
- **자동 번역**: 한국어 → 영어 프롬프트 자동 변환
- **다양한 비율**: SNS, 블로그, 광고용 비율 지원

### 🕷️ 지능형 웹 크롤링
- **도메인별 특화 추출기**: ITWorld, Fashionbiz, Hidoc, Beautynury, TLNews
- **자동 스케줄링**: 주간 자동 업데이트 (매주 월요일 오전 9시)
- **콘텐츠 정제**: HTML 디코딩 및 품질 관리

### 🧠 RAG 시스템
- **벡터 검색**: FAISS + PostgreSQL pgvector 이중 인덱싱
- **임베딩 생성**: Bedrock Titan Text Embeddings v2
- **청킹 처리**: LangChain RecursiveCharacterTextSplitter
- **메타데이터 관리**: 업계별 태깅 및 분류

## 🛠️ 기술 스택

### Backend
- **Framework**: Flask 3.1.1
- **Language**: Python 3.9+
- **Database**: PostgreSQL + pgvector
- **ORM**: SQLAlchemy 2.0.41
- **Authentication**: Flask-Login

### AI/ML
- **LLM**: Claude 3.5 Sonnet (via AWS Bedrock)
- **Embeddings**: Titan Text Embeddings v2
- **Image Generation**: Stable Diffusion (via Bedrock)
- **Vector Search**: FAISS 1.11.0
- **Text Processing**: LangChain 0.3.25

### Cloud & Infrastructure
- **Cloud Platform**: AWS
- **Compute**: EC2
- **Storage**: S3
- **Database**: RDS (PostgreSQL)
- **Container**: Docker
- **Infrastructure as Code**: Terraform

### Frontend
- **Template Engine**: Jinja2
- **Styling**: CSS3
- **JavaScript**: Vanilla JS
- **UI Framework**: Bootstrap

### Testing & Quality
- **Testing Framework**: pytest
- **Code Quality**: flake8, black, isort
- **Coverage**: pytest-cov

## 🏗️ 시스템 아키텍처

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   Flask API     │    │   RAG System    │
│   (HTML/CSS/JS) │◄──►│   (Python)      │◄──►│   (FAISS+pgvector)│
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │   AWS Services  │
                       │  • Bedrock      │
                       │  • S3           │
                       │  • RDS          │
                       └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │  Web Crawlers   │
                       │  (Selenium)     │
                       └─────────────────┘
```

## 🚀 설치 및 실행

### 사전 요구사항

- Python 3.9+
- PostgreSQL 13+ (pgvector 확장 포함)
- AWS 계정 및 권한
- Chrome/Chromium (웹 크롤링용)

### 1. 저장소 클론

```bash
git clone https://github.com/yourusername/ai-content-marketing-tool.git
cd ai-content-marketing-tool
```

### 2. 가상환경 생성 및 활성화

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

### 3. 의존성 설치

```bash
pip install -r requirements.txt
```

### 4. 환경 변수 설정

`.env` 파일을 생성하고 다음 내용을 추가:

```env
# AWS 설정
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_REGION_NAME=us-east-1

# 데이터베이스 설정
DATABASE_URL=postgresql://username:password@localhost:5432/dbname

# S3 설정
S3_BUCKET_NAME=your-bucket-name

# Flask 설정
SECRET_KEY=your-secret-key
FLASK_ENV=development
```

### 5. 데이터베이스 설정

```bash
# PostgreSQL에 pgvector 확장 설치
CREATE EXTENSION IF NOT EXISTS vector;

# 마이그레이션 실행
flask db upgrade
```

### 6. 시스템 사용자 생성

```bash
python create_system_user.py
```

### 7. 애플리케이션 실행

```bash
python run.py
```

애플리케이션이 `http://localhost:5000`에서 실행됩니다.

## 📖 사용법

### 1. 회원가입 및 로그인

- 웹 브라우저에서 `http://localhost:5000` 접속
- 회원가입 후 로그인

### 2. 텍스트 콘텐츠 생성

1. **콘텐츠 타입 선택**: 블로그, 이메일, SNS
2. **주제 입력**: 생성할 콘텐츠의 주제
3. **업계 선택**: IT, 패션, 헬스케어, 여행 등
4. **추가 옵션 설정**:
   - 대상 독자
   - 핵심 포인트
   - 톤앤매너
   - 길이 옵션
   - SEO 키워드
5. **생성 버튼 클릭**

### 3. 이미지 콘텐츠 생성

1. **이미지 주제 입력**
2. **브랜드 스타일 선택**
3. **제품 카테고리 선택**
4. **광고 목적 선택**
5. **생성 개수 및 비율 설정**
6. **생성 버튼 클릭**

### 4. 지식베이스 관리

- **URL 업로드**: 관련 웹페이지 URL 입력
- **파일 업로드**: PDF, TXT 파일 업로드
- **업계별 분류**: 자동 업계 분류 및 태깅

## 📚 API 문서

### 인증

Flask-Login을 사용한 세션 기반 인증

### 주요 엔드포인트

#### 콘텐츠 생성
```http
POST /generate_content
Content-Type: application/json

{
  "topic": "AI 마케팅",
  "industry": "IT",
  "content_type": "blog",
  "blog_style": "추천/리스트 글",
  "target_audience": "마케터",
  "key_points": "AI 활용, 효율성, ROI",
  "tone": "전문적",
  "length_option": "medium",
  "seo_keywords": "AI 마케팅, 디지털 마케팅"
}
```

#### 이미지 생성
```http
POST /generate_image
Content-Type: application/json

{
  "topic": "AI 마케팅 이미지",
  "industry": "IT",
  "content_type": "sns",
  "target_audience": "마케터",
  "brand_style_tone": "전문적",
  "product_category": "소프트웨어",
  "ad_purpose": "브랜드 인지도",
  "cut_count": 1,
  "aspect_ratio_sns": "1:1"
}
```

#### 지식베이스 관리
```http
GET /knowledge_base/files?page=1&per_page=10
POST /knowledge_base/upload
DELETE /knowledge_base/delete/<s3_key>
```

자세한 API 문서는 [API_SPECIFICATION.md](docs/API_SPECIFICATION.md)를 참조하세요.

## 🧪 테스트

### 테스트 실행

```bash
# 테스트 의존성 설치
pip install -r requirements-test.txt

# 전체 테스트 실행
pytest

# 커버리지와 함께 실행
pytest --cov=services --cov-report=html

# 특정 테스트 실행
pytest tests/test_rag_system.py
```

### 테스트 구조

```
tests/
├── conftest.py              # 공통 설정 및 fixture
├── test_rag_system.py       # RAG 시스템 테스트
├── test_content_generation.py # 콘텐츠 생성 테스트
└── test_web_crawling.py     # 웹 크롤링 테스트
```

자세한 테스트 가이드는 [README_TESTING.md](README_TESTING.md)를 참조하세요.

## 🚀 배포

### Docker 배포

```bash
# Docker 이미지 빌드
docker build -t ai-content-marketing-tool .

# 컨테이너 실행
docker run -p 5000:5000 ai-content-marketing-tool
```

### AWS 배포

Terraform을 사용한 인프라 자동 배포:

```bash
cd infra
terraform init
terraform plan
terraform apply
```

### 환경별 설정

- **개발 환경**: `FLASK_ENV=development`
- **테스트 환경**: `FLASK_ENV=testing`
- **운영 환경**: `FLASK_ENV=production`

## 🤝 기여하기

### 개발 환경 설정

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

### 코드 스타일

- Python: PEP 8 준수
- 테스트 커버리지: 80% 이상 유지
- 커밋 메시지: Conventional Commits 형식 사용

---

⭐ 이 프로젝트가 도움이 되었다면 스타를 눌러주세요! 
