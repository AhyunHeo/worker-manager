# ==========================================
# Stage 1: Cython 빌드
# ==========================================
FROM python:3.11-slim AS builder

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
COPY web-dashboard/app.py /build/

# Cython 빌드 스크립트 생성 및 실행
RUN echo "from setuptools import setup\n\
from Cython.Build import cythonize\n\
setup(ext_modules=cythonize('app.py', compiler_directives={'language_level': '3'}))" > /build/setup.py \
    && python /build/setup.py build_ext --inplace

# 원본 .py 파일 및 .c 파일 삭제
RUN rm -f /build/app.py /build/app.c /build/setup.py

# ==========================================
# Stage 2: 런타임 이미지
# ==========================================
FROM python:3.11-slim

# Install ping utility
RUN apt-get update && apt-get install -y iputils-ping && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY web-dashboard/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 컴파일된 코드 복사
COPY --from=builder /build/*.so /app/

# 실행 스크립트 생성 (컴파일된 .so 모듈에서 Flask app 실행)
RUN echo "import app; app.app.run(host='0.0.0.0', port=5000, debug=False)" > /app/run.py

EXPOSE 5000

CMD ["python", "run.py"]
