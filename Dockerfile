# ==========================================
# Stage 1: Cython 빌드
# ==========================================
FROM python:3.10-slim AS builder

WORKDIR /build

# 빌드 도구 설치
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Cython 설치
RUN pip install --no-cache-dir cython setuptools

# 소스 코드 복사
COPY api /build/api
COPY setup_cython.py /build/

# 백업 파일 삭제 (파일명에 공백 포함된 파일들)
RUN find /build/api -name "* copy*" -delete 2>/dev/null || true
RUN find /build/api -name "*Copy*" -delete 2>/dev/null || true
RUN find /build/api -name "*.bak" -delete 2>/dev/null || true

# Cython 빌드 실행
WORKDIR /build/api
RUN python /build/setup_cython.py

# 원본 .py 파일 삭제 (FastAPI 라우트 파일, __init__.py, migrations 제외)
# FastAPI Depends()를 사용하는 파일은 Cython과 호환되지 않아 .py 유지
RUN find /build/api -name "*.py" \
    ! -name "__init__.py" \
    ! -name "main.py" \
    ! -name "worker_integration.py" \
    ! -name "routes.py" \
    ! -path "*/migrations/*" \
    -delete

# .c 파일 삭제 (Cython 중간 파일)
RUN find /build/api -name "*.c" -delete

# ==========================================
# Stage 2: 런타임 이미지
# ==========================================
FROM python:3.10-slim

WORKDIR /app

# 런타임 의존성 설치
RUN apt-get update && apt-get install -y \
    iproute2 \
    iptables \
    curl \
    docker.io \
    iputils-ping \
    net-tools \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Python 패키지 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 컴파일된 코드 복사 (Stage 1에서)
COPY --from=builder /build/api /app

# Worker Manager API 시작
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8091"]
