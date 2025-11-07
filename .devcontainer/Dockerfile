# 개발 컨테이너용 Dockerfile
# 프로덕션 Dockerfile을 기반으로 개발 도구 추가

FROM python:3.11-slim

# 작업 디렉토리 설정
WORKDIR /app

# 시스템 의존성 업데이트 및 개발 도구 설치
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    git \
    vim \
    && rm -rf /var/lib/apt/lists/*

# 의존성 파일 복사
COPY requirements.txt requirements-dev.txt ./

# Python 의존성 설치
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 개발 의존성은 postCreateCommand에서 설치 (더 빠른 빌드)
# RUN pip install --no-cache-dir -r requirements-dev.txt

# 포트 8000 노출
EXPOSE 8000

# 기본 명령어 (dev container에서는 쉘을 유지)
CMD ["/bin/bash"]

