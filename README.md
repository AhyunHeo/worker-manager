# Worker Manager

Distributed AI Platform을 위한 워커노드 환경 설정 및 컨테이너 배포 관리 시스템

## 개요

Worker Manager는 분산 AI 학습 플랫폼의 핵심 구성 요소로, 중앙서버와 워커노드의 설치/배포/관리를 자동화합니다.

### 주요 기능

- **자동 환경 설정**: WSL2, Ubuntu, Docker Desktop 자동 설치 및 구성
- **원클릭 배포**: QR 코드 또는 웹 기반 설치 지원
- **GPU 워커 관리**: NVIDIA GPU 기반 분산 학습 노드 관리
- **중앙서버 구축**: AI 플랫폼 중앙서버 Docker 기반 배포
- **실시간 모니터링**: 노드 상태, 연결 상태 확인

## 아키텍처

```
                    ┌─────────────────────────────────────────────────────────────┐
                    │                    Worker Manager (설치관리자)                │
                    ├─────────────────────────────────────────────────────────────┤
                    │                                                             │
                    │  ┌─────────────────┐    ┌─────────────────┐                │
                    │  │  Web Dashboard  │───▶│  Worker Manager │                │
                    │  │   (Flask:5000)  │    │   API (FastAPI) │                │
                    │  └─────────────────┘    │     :8091       │                │
                    │                         └────────┬────────┘                │
                    │                                  │                          │
                    │                         ┌────────▼────────┐                │
                    │                         │   PostgreSQL    │                │
                    │                         │     :5434       │                │
                    │                         └─────────────────┘                │
                    │                                                             │
                    └─────────────────────────────────────────────────────────────┘
                                               │
                       ┌───────────────────────┴───────────────────────┐
                       │ 설치/배포                         설치/배포    │
                       ▼                                              ▼
        ┌─────────────────────────┐                    ┌─────────────────────────┐
        │      Central Server     │                    │      Worker Nodes       │
        ├─────────────────────────┤                    ├─────────────────────────┤
        │ • API Server :8000      │                    │ • GPU Runtime           │
        │ • FL Server :5002       │◀──────────────────▶│ • Ray Cluster           │
        │ • Frontend :3000        │    학습/상태보고    │ • NCCL 분산 학습         │
        │ • PostgreSQL :5432      │                    │ • Flask API :8001       │
        │ • MongoDB :27017        │                    │                         │
        │ • Redis                 │                    │                         │
        └────────────┬────────────┘                    └─────────────────────────┘
                     │
                     │ 워커노드 설치파일 다운로드 요청
                     ▼
              Worker Manager API
```

**통신 흐름:**
- **Worker Manager → Central Server**: 중앙서버 Docker 컨테이너 설치/배포
- **Worker Manager → Worker Nodes**: 워커노드 환경 설정 및 컨테이너 배포
- **Central Server → Worker Manager**: 워커노드 설치 스크립트 다운로드 API 요청
- **Worker Nodes ↔ Central Server**: 분산 학습, 상태 보고, 작업 수신

## 시스템 요구사항

### Worker Manager 서버
- Docker Desktop
- 최소 4GB RAM
- 네트워크 접근 가능

### 워커노드
- Windows 10/11 (WSL2 지원)
- NVIDIA GPU (CUDA 지원)
- Docker Desktop
- 최소 16GB RAM (권장 64GB)

## 빠른 시작

### 1. Docker Desktop 설치

[Docker Desktop 다운로드](https://www.docker.com/products/docker-desktop/)

### 2. Worker Manager 실행

```bash
# 저장소 클론
git clone https://github.com/intownlab/worker-manager.git
cd worker-manager

# 환경 변수 설정
cp .env.example .env
# .env 파일 수정 (LOCAL_SERVER_IP, API_TOKEN 등)

# 실행
docker compose up -d
```

### 3. 대시보드 접속

- 대시보드: `http://<SERVER_IP>:5000`
- API 문서: `http://<SERVER_IP>:8091/docs`

## 프로젝트 구조

```
worker-manager/
├── api/                        # Worker Manager API (FastAPI)
│   ├── main.py                 # API 엔트리포인트
│   ├── models.py               # SQLAlchemy 모델
│   ├── database.py             # DB 연결 설정
│   ├── worker_integration.py   # 워커노드 설정 API
│   ├── central/                # 중앙서버 관련 라우터
│   │   ├── routes.py           # 중앙서버 설정 엔드포인트
│   │   └── docker_runner.py    # Docker 실행 로직
│   ├── gui/                    # GUI 설치 모듈
│   │   ├── worker_setup_gui_modular.py  # PowerShell GUI 생성
│   │   └── modules/            # 모듈화된 설치 스크립트
│   │       ├── wsl_setup_module.py
│   │       ├── ubuntu_setup_module.py
│   │       ├── docker_setup_module.py
│   │       ├── network_setup_module.py
│   │       └── container_deploy_module.py
│   └── migrations/             # DB 마이그레이션
├── web-dashboard/              # 웹 대시보드 (Flask)
│   └── app.py                  # 대시보드 애플리케이션
├── install/                    # 설치 스크립트
│   ├── set-manager.ps1         # PowerShell 설치 스크립트
│   └── install-set-manager.bat # Windows 배치 실행기
├── docker-compose.yml          # Docker Compose 설정
├── Dockerfile                  # Worker Manager API 이미지
├── build.sh                    # 이미지 빌드 스크립트
└── requirements.txt            # Python 의존성
```

## 서비스 구성

### Docker Compose 서비스

| 서비스 | 포트 | 설명 |
|--------|------|------|
| worker-api | 8091 | Worker Manager API (FastAPI) |
| web-dashboard | 5000 | 관리 대시보드 (Flask) |
| postgres | 5434 | PostgreSQL 데이터베이스 |

## API 엔드포인트

### 노드 관리

| Method | Endpoint | 설명 |
|--------|----------|------|
| GET | `/nodes` | 전체 노드 목록 |
| POST | `/nodes` | 새 노드 등록 |
| GET | `/nodes/{node_id}` | 노드 상세 정보 |
| PUT | `/nodes/{node_id}` | 노드 정보 수정 |
| DELETE | `/nodes/{node_id}` | 노드 삭제 |
| POST | `/nodes/{node_id}/status` | 노드 상태 업데이트 |

### 워커 설정

| Method | Endpoint | 설명 |
|--------|----------|------|
| GET | `/worker/setup` | 워커 설정 페이지 (HTML) |
| POST | `/worker/environment` | 환경 설정 API |
| GET | `/worker/download/installer` | PowerShell 설치 스크립트 다운로드 |

### 중앙서버 설정

| Method | Endpoint | 설명 |
|--------|----------|------|
| GET | `/central/setup` | 중앙서버 설정 페이지 |
| POST | `/central/deploy` | 중앙서버 배포 |
| GET | `/central/download/installer` | 중앙서버 설치 스크립트 |

## 환경 변수

```env
# 서버 설정
LOCAL_SERVER_IP=192.168.0.100

# API 인증
API_TOKEN=your-secure-token-here

# 데이터베이스
DATABASE_URL=postgresql://worker:workerpass@postgres:5432/workerdb

# 중앙서버 연결
CENTRAL_SERVER_URL=http://192.168.0.88:8000

# 대시보드
SECRET_KEY=your-secret-key-here
ADMIN_PASSWORD=password

# 로깅
LOG_LEVEL=INFO
TZ=Asia/Seoul
```

## 워커노드 설치 흐름

```
1. 대시보드 접속 (/worker/setup)
      │
2. 설치 스크립트 다운로드 (PowerShell)
      │
3. 자동 환경 설정
      ├── WSL2 활성화
      ├── Ubuntu 설치
      ├── Docker Desktop 연동
      └── NVIDIA Container Toolkit
      │
4. 워커 컨테이너 배포
      ├── Docker Compose 생성
      ├── 환경 변수 설정
      └── GPU 런타임 구성
      │
5. 중앙서버 연결 확인
```

## 개발 가이드

### 로컬 개발 환경

```bash
# API 개발 서버
cd api
pip install -r ../requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8091 --reload

# 대시보드 개발 서버
cd web-dashboard
pip install -r requirements.txt
python app.py
```

### Docker 이미지 빌드

```bash
# Git Bash에서 실행
chmod +x build.sh
./build.sh

# 노캐시 빌드
./build.sh --no-cache
```

### 데이터베이스 마이그레이션

마이그레이션은 API 서버 시작 시 자동으로 실행됩니다.

```python
# api/main.py에서 자동 마이그레이션
# - vpn_ip UNIQUE 제약조건 제거
# - owner_id 컬럼 추가
```

## 워커노드 Docker Compose 설정

워커노드는 다음 환경으로 배포됩니다:

### 주요 환경 변수

- `NODE_ID`: 노드 식별자
- `CENTRAL_SERVER_IP`: 중앙서버 IP
- `OWNER_ID`: 노드 소유자 ID
- `NCCL_*`: 분산 학습 설정
- `RAY_*`: Ray 클러스터 설정

### 포트 매핑

| 포트 | 용도 |
|------|------|
| 8001 | Flask API |
| 6379 | Ray GCS/Redis |
| 10001 | Ray Client |
| 8265 | Ray Dashboard |
| 29500-29509 | DDP TCPStore |
| 29510 | NCCL Socket |

### GPU 설정

```yaml
runtime: nvidia
deploy:
  resources:
    reservations:
      devices:
        - driver: nvidia
          capabilities: [gpu]
          count: all
```

## 문제 해결

### Docker Desktop이 시작되지 않음

1. WSL2가 설치되어 있는지 확인
2. Windows 기능에서 "가상 머신 플랫폼" 활성화
3. BIOS에서 가상화 기능 활성화

### 워커노드가 중앙서버에 연결되지 않음

1. 방화벽 설정 확인 (포트 8000, 8001)
2. `CENTRAL_SERVER_IP` 환경 변수 확인
3. 네트워크 연결 상태 확인

### GPU가 인식되지 않음

1. NVIDIA 드라이버 설치 확인
2. Docker Desktop에서 WSL2 통합 활성화
3. `nvidia-smi` 명령어로 GPU 상태 확인

## 라이선스

Copyright 2025 INTOWN Co., Ltd. All rights reserved.
