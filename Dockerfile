FROM python:3.10-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    iproute2 \
    iptables \
    curl \
    docker.io \
    iputils-ping \
    net-tools \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# API 소스 코드 복사
COPY api /app

# Worker Manager API 시작
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8090"]