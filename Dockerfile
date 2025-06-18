# 1. 베이스 이미지 선택 (원하는 파이썬 버전이 설치된 리눅스)
FROM python:3.13-slim

# 2. 컨테이너 안에서 작업할 디렉토리 설정
WORKDIR /app

# 3. requirements.txt 파일을 먼저 복사 및 설치 (빌드 속도 향상을 위한 캐싱 기법)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4. 나머지 프로젝트 코드 전체 복사
COPY . .

# 5. 컨테이너가 시작될 때 실행할 명령어
CMD ["python3", "run.py"]