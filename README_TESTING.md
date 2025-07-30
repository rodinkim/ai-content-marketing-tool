# AI 콘텐츠 마케팅 도구 - 테스트 가이드

## 테스트 환경 설정

### 1. 테스트 의존성 설치

```bash
# 테스트용 의존성 설치
pip install -r requirements-test.txt

# 또는 개발 환경에서
pip install pytest pytest-cov pytest-mock pytest-flask
```

### 2. 환경 변수 설정

테스트 실행을 위한 환경 변수를 설정합니다:

```bash
# .env.test 파일 생성
export FLASK_ENV=testing
export TESTING=True
export AWS_ACCESS_KEY_ID=test_key
export AWS_SECRET_ACCESS_KEY=test_secret
export AWS_REGION_NAME=us-east-1
export S3_BUCKET_NAME=test-bucket
export DATABASE_URL=sqlite:///test.db
```

## 테스트 실행 방법

### 1. 전체 테스트 실행

```bash
# 모든 테스트 실행
pytest

# 상세한 출력과 함께 실행
pytest -v

# 테스트 진행률 표시
pytest -v --tb=short
```

### 2. 특정 테스트 실행

```bash
# 특정 테스트 파일 실행
pytest tests/test_rag_system.py

# 특정 테스트 클래스 실행
pytest tests/test_rag_system.py::TestRAGSystem

# 특정 테스트 메서드 실행
pytest tests/test_rag_system.py::TestRAGSystem::test_rag_system_initialization
```

### 3. 마커를 사용한 테스트 실행

```bash
# 단위 테스트만 실행
pytest -m unit

# 통합 테스트만 실행
pytest -m integration

# 느린 테스트 제외하고 실행
pytest -m "not slow"

# AWS 서비스가 필요한 테스트 제외
pytest -m "not aws"
```

### 4. 커버리지와 함께 실행

```bash
# 커버리지 리포트 생성
pytest --cov=services --cov-report=html

# 터미널에 커버리지 출력
pytest --cov=services --cov-report=term-missing

# XML 리포트 생성 (CI/CD용)
pytest --cov=services --cov-report=xml
```

### 5. 병렬 실행

```bash
# 여러 프로세스로 병렬 실행
pytest -n auto

# 특정 개수의 프로세스로 실행
pytest -n 4
```

## 테스트 구조

### 테스트 파일 구성

```
tests/
├── __init__.py
├── conftest.py              # 공통 설정 및 fixture
├── test_rag_system.py       # RAG 시스템 테스트
├── test_content_generation.py # 콘텐츠 생성 테스트
└── test_web_crawling.py     # 웹 크롤링 테스트
```

### 테스트 카테고리

1. **Unit Tests (단위 테스트)**
   - 개별 함수/클래스 테스트
   - Mock을 사용한 외부 의존성 격리
   - 빠른 실행 속도

2. **Integration Tests (통합 테스트)**
   - 여러 컴포넌트 간 상호작용 테스트
   - 실제 데이터베이스나 외부 서비스 사용
   - 상대적으로 느린 실행 속도

3. **API Tests (API 테스트)**
   - Flask 라우트 테스트
   - HTTP 요청/응답 테스트
   - 인증 및 권한 테스트

## Mock 사용법

### AWS 서비스 Mock

```python
@pytest.fixture
def mock_bedrock_client():
    return Mock()

def test_embedding_generation(mock_bedrock_client):
    # Mock 설정
    mock_bedrock_client.invoke_model.return_value = {
        'body': Mock(read=lambda: '{"embedding": [0.1, 0.2, 0.3]}')
    }
    
    # 테스트 실행
    result = generate_embedding("테스트 텍스트", mock_bedrock_client)
    assert result is not None
```

### 데이터베이스 Mock

```python
@pytest.fixture
def mock_db_session():
    return Mock()

def test_user_creation(mock_db_session):
    # Mock 설정
    mock_db_session.add.return_value = None
    mock_db_session.commit.return_value = None
    
    # 테스트 실행
    create_user("testuser", "test@example.com", mock_db_session)
    mock_db_session.add.assert_called_once()
```

## 테스트 작성 가이드

### 1. 테스트 네이밍

```python
def test_function_name_expected_behavior():
    """테스트 설명"""
    pass

def test_function_name_edge_case():
    """엣지 케이스 테스트"""
    pass

def test_function_name_error_condition():
    """오류 조건 테스트"""
    pass
```

### 2. Fixture 사용

```python
@pytest.fixture
def sample_data():
    """테스트용 샘플 데이터"""
    return {
        "topic": "AI 마케팅",
        "industry": "IT",
        "content_type": "blog"
    }

def test_content_generation(sample_data):
    """샘플 데이터를 사용한 테스트"""
    result = generate_content(sample_data)
    assert result is not None
```

### 3. Assertion 작성

```python
def test_rag_search():
    # Given (준비)
    query = "AI 마케팅"
    
    # When (실행)
    result = rag_system.retrieve(query, k=5)
    
    # Then (검증)
    assert len(result) <= 5
    assert all(isinstance(doc, str) for doc in result)
```

## CI/CD 통합

### GitHub Actions 예시

```yaml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: 3.9
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install -r requirements-test.txt
      - name: Run tests
        run: |
          pytest --cov=services --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v1
```

## 문제 해결

### 1. Import 오류

```bash
# PYTHONPATH 설정
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# 또는 pytest 실행 시
PYTHONPATH=. pytest
```

### 2. 환경 변수 문제

```bash
# .env 파일 로드
export $(cat .env | xargs)

# 또는 pytest-dotenv 사용
pip install pytest-dotenv
```

### 3. 데이터베이스 연결 문제

```python
# 테스트용 데이터베이스 사용
@pytest.fixture
def test_db():
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    with app.app_context():
        db.create_all()
        yield db
        db.drop_all()
```

## 성능 최적화

### 1. 테스트 병렬화

```bash
# CPU 코어 수에 맞춰 병렬 실행
pytest -n auto

# 특정 테스트만 병렬 실행
pytest -n 4 tests/test_rag_system.py
```

### 2. 테스트 선택적 실행

```bash
# 실패한 테스트만 재실행
pytest --lf

# 마지막 실패한 테스트부터 실행
pytest --ff
```

### 3. 캐시 활용

```bash
# pytest 캐시 사용
pytest --cache-clear  # 캐시 초기화
pytest --cache-show   # 캐시 정보 확인
``` 