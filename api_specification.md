# AI 콘텐츠 마케팅 도구 - API 명세서

## 1. 인증 관련 API

### 1.1. 메인 페이지

| 항목 | 설명 |
| --- | --- |
| URL | `/` |
| Method | `GET` |
| Description | 메인 랜딩 페이지 렌더링 |
| Response | HTML (index.html) |

### 1.2. 회원가입

| 항목 | 설명 |
| --- | --- |
| URL | `/register` |
| Method | `GET`, `POST` |
| Description | 회원가입 페이지 렌더링 및 가입 처리 |

**Request Body (POST):**

```json
{
    "username": "string (2-20자)",
    "email": "string (유효한 이메일)",
    "password": "string (최소 6자)",
    "confirm_password": "string (비밀번호 확인)"
}
```

**Response:**

- 성공: 리다이렉트 `/login`
- 실패: 에러 메시지와 함께 회원가입 폼

### 1.3. 로그인

| 항목 | 설명 |
| --- | --- |
| URL | `/login` |
| Method | `GET`, `POST` |
| Description | 로그인 페이지 렌더링 및 로그인 처리 |

**Request Body (POST):**

```json
{
    "email": "string",
    "password": "string",
    "remember_me": "boolean (선택)"
}
```

**Response:**

- 성공: 리다이렉트 `/content`
- 실패: 에러 메시지와 함께 로그인 폼

### 1.4. 로그아웃

| 항목 | 설명 |
| --- | --- |
| URL | `/logout` |
| Method | `GET` |
| Description | 로그아웃 처리 |
| Auth Required | Yes |
| Response | 리다이렉트 `/` |

---

## 2. 콘텐츠 생성 API

### 2.1. 콘텐츠 생성 페이지

| 항목 | 설명 |
| --- | --- |
| URL | `/content` |
| Method | `GET` |
| Auth Required | Yes |
| Description | 메인 콘텐츠 생성 페이지 렌더링 |
| Response | HTML (content.html) |

### 2.2. 텍스트 콘텐츠 생성

| 항목 | 설명 |
| --- | --- |
| URL | `/generate_content` |
| Method | `POST` |
| Auth Required | Yes |

**Request Body:**

```json
{
    "topic": "string (필수)",
    "industry": "string (필수)",
    "content_type": "string (필수: blog/email)",
    "target_audience": "string (선택)",
    "key_points": "string (선택)",
    "blog_style": "string (블로그일 때: 추천/리스트 글, 리뷰/후기 글)",
    "tone": "string (선택)",
    "length_option": "string (선택: short/medium/long)",
    "seo_keywords": "string (블로그일 때)",
    "email_subject": "string (이메일일 때)",
    "email_type": "string (이메일일 때: newsletter/promotion)",
    "landing_page_url": "string (선택)",
    "brand_style_tone": "string (선택)",
    "product_category": "string (선택)",
    "ad_purpose": "string (선택)"
}
```

**Response:**

```json
{
    "content": "string (생성된 텍스트)",
    "error": "string (에러 발생 시)"
}
```

### 2.3. 이미지 콘텐츠 생성

| 항목 | 설명 |
| --- | --- |
| URL | `/generate-image` |
| Method | `POST` |
| Auth Required | Yes |

**Request Body:**

```json
{
    "topic": "string (필수)",
    "industry": "string (필수)",
    "content_type": "string (필수: sns)",
    "target_audience": "string (선택)",
    "brand_style_tone": "string (선택)",
    "product_category": "string (선택)",
    "ad_purpose": "string (선택)",
    "key_points": "string (선택)",
    "cut_count": "integer (선택, 기본값: 1)",
    "aspect_ratio_sns": "string (선택)",
    "other_requirements": "string (선택)"
}
```

**Response:**

```json
{
    "status": "success/error",
    "image_urls": ["string (생성된 이미지 URL)"],
    "translated_prompt": {
        "image_prompt": "string (영문 변환 프롬프트)"
    },
    "message": "string (에러 발생 시)"
}
```

### 2.4. 생성된 이미지 조회

| 항목 | 설명 |
| --- | --- |
| URL | `/generated_images/<filename>` |
| Method | `GET` |
| Description | 생성된 이미지 파일 서빙 |
| Response | Image file |

---

## 3. 지식베이스 API

### 3.1. 지식베이스 관리 페이지

| 항목 | 설명 |
| --- | --- |
| URL | `/knowledge_base/` |
| Method | `GET` |
| Auth Required | Yes |
| Description | 지식베이스 관리 페이지 렌더링 |
| Response | HTML (knowledge_base_manager.html) |

### 3.2. URL에서 지식베이스 추가

| 항목 | 설명 |
| --- | --- |
| URL | `/knowledge_base/add_from_url` |
| Method | `POST` |
| Auth Required | Yes |

**Request Body:**

```json
{
    "url": "string (필수)",
    "industry": "string (필수)"
}
```

**Response:**

```json
{
    "message": "string (성공 메시지)",
    "error": "string (에러 발생 시)"
}
```

### 3.3. 지식베이스 파일 목록 조회

| 항목 | 설명 |
| --- | --- |
| URL | `/knowledge_base/files` |
| Method | `GET` |
| Auth Required | Yes |
| Query Parameters | `page` (int, 기본값: 1), `target_type` (string, 관리자용), `target_username` (string, 관리자용) |

**Response:**

```json
{
    "files": [
        {
            "display_name": "string (원본 파일명)",
            "s3_key": "string (S3 키)"
        }
    ],
    "pagination": {
        "current_page": "integer",
        "total_pages": "integer",
        "total_items": "integer"
    }
}
```

### 3.4. 지식베이스 파일 삭제

| 항목 | 설명 |
| --- | --- |
| URL | `/knowledge_base/delete/<s3_key>` |
| Method | `DELETE` |
| Auth Required | Yes |
| Description | 특정 파일 삭제 (권한 체크 포함) |

**Response:**

```json
{
    "message": "string (성공 메시지)",
    "error": "string (에러 발생 시)"
}
```

### 3.5. 업종 목록 조회

| 항목 | 설명 |
| --- | --- |
| URL | `/knowledge_base/industries` |
| Method | `GET` |
| Auth Required | Yes |

**Response:**

```json
{
    "industries": ["IT", "Fashion", "Healthcare", "Beauty", "Travel"]
}
```

### 3.6. 전체 사용자 목록 (관리자 전용)

| 항목 | 설명 |
| --- | --- |
| URL | `/knowledge_base/users` |
| Method | `GET` |
| Auth Required | Yes (관리자만) |

**Response:**

```json
{
    "users": ["string (사용자명 목록)"]
}
```

---

## 4. 히스토리 API

### 4.1. 콘텐츠 히스토리 페이지

| 항목 | 설명 |
| --- | --- |
| URL | `/history` |
| Method | `GET` |
| Auth Required | Yes |
| Description | 콘텐츠 히스토리 페이지 렌더링 |
| Response | HTML (history.html) |

### 4.2. 히스토리 API (JSON)

| 항목 | 설명 |
| --- | --- |
| URL | `/history-api` |
| Method | `GET` |
| Auth Required | Yes |
| Description | 현재 사용자의 모든 콘텐츠 기록을 JSON으로 반환 |

**Response:**

```json
[
    {
        "id": "integer",
        "user_id": "integer",
        "generated_text": "string",
        "generated_image_url": "string",
        "topic": "string",
        "industry": "string",
        "content_type": "string",
        "timestamp": "datetime",
        "blog_style": "string",
        "email_type": "string",
        "brand_style_tone": "string",
        "product_category": "string",
        "ad_purpose": "string"
    }
]
```

### 4.3. 개별 콘텐츠 상세 조회

| 항목 | 설명 |
| --- | --- |
| URL | `/history-api/<content_id>` |
| Method | `GET` |
| Auth Required | Yes |
| Description | 특정 콘텐츠의 상세 정보 조회 |

### 4.4. 콘텐츠 상세 페이지

| 항목 | 설명 |
| --- | --- |
| URL | `/history/<content_id>` |
| Method | `GET` |
| Auth Required | Yes |
| Description | 콘텐츠 상세 페이지 렌더링 |
| Response | HTML (history_detail.html) |

### 4.5. 콘텐츠 삭제

| 항목 | 설명 |
| --- | --- |
| URL | `/history/<content_id>` |
| Method | `DELETE` |
| Auth Required | Yes |
| Description | 특정 콘텐츠 삭제 |

**Response:**

```json
{
    "message": "string (삭제 완료 메시지)"
}
```

---

## 5. 공통 사항

### 인증

- 대부분의 API는 로그인이 필요합니다 (`@login_required` 데코레이터 사용)
- 인증되지 않은 요청은 로그인 페이지로 리다이렉트됩니다
- Flask-Login 기반 세션 인증 시스템 사용

### 에러 응답 형식

```json
{
    "error": "string (에러 메시지)",
    "status": "error"
}
```

### 성공 응답 형식

```json
{
    "message": "string (성공 메시지)",
    "status": "success",
    "data": "object (해당하는 경우)"
}
```

### HTTP 상태 코드

| 코드 | 설명 |
| --- | --- |
| 200 | 성공 |
| 400 | 잘못된 요청 (필수 파라미터 누락 등) |
| 401 | 인증 필요 |
| 403 | 권한 없음 |
| 404 | 리소스 없음 |
| 500 | 서버 에러 |

---

## 6. 백그라운드 및 스케줄링 작업

서버 내부의 Flask-APScheduler에 의해 자동으로 실행되는 작업들입니다.

### 6.1. 주간 마케팅 뉴스 크롤링

| 항목 | 내용 |
| --- | --- |
| **작업 명** | `사이트별 마케팅 뉴스 크롤링` |
| **개요** | 외부 뉴스 사이트에서 주기적으로 최신 마케팅 기사를 수집하여 S3에 저장하고 RAG 시스템에 등록합니다. |
| **실행 방식** | **스케줄링 (매주 목요일 오후 3시)** |
| **대상 사이트** | ITWorld, Fashionbiz, Hidoc, Beautynury, TLNews |
| **결과물** | S3에 `.txt` 파일 저장 및 RAG 시스템 자동 등록 |
| **기술 스택** | Selenium + ChromeDriver, 도메인별 전용 추출기 |

**주요 동작 과정:**

1. S3에서 `crawler_urls.json` 설정 파일 로드
2. 지정된 뉴스 사이트 목록을 순회
3. 각 사이트별 전용 추출기로 콘텐츠 추출
4. S3에 기사 파일 저장
5. RAG 시스템에 자동 등록 (청킹, 임베딩, 인덱싱)

### 6.2. FAISS 인덱스 재로드

| 항목 | 내용 |
| --- | --- |
| **작업 명** | `FAISS 인덱스 재로드` |
| **개요** | PostgreSQL의 모든 벡터 데이터를 FAISS 인덱스에 재로드하여 동기화합니다. |
| **실행 방식** | **스케줄링 (매일 새벽 3시)** |
| **결과물** | FAISS 인덱스 동기화 완료 |
| **기술 스택** | PostgreSQL + pgvector, FAISS |

**주요 동작 과정:**

1. PostgreSQL에서 모든 벡터 데이터 조회
2. FAISS 인덱스 재구축
3. 검색 성능 최적화
4. 인덱스 무결성 보장

### 6.3. 시스템 크롤러 사용자

- **전용 사용자**: 시스템 크롤링 작업을 위한 별도 사용자 계정
- **설정**: `CRAWLER_UPLOADER_USERNAME` 환경변수로 관리
- **권한**: 자동 크롤링된 콘텐츠의 소유자로 설정
- **데이터 분리**: 사용자별 데이터 격리 유지