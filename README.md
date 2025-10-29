# Worker Manager

워커 노드 자동 환경 설정 및 컨테이너 배포 시스템

## 📋 개요

이 프로젝트는 **워커 노드의 자동 환경 설정 및 관리**를 위한 시스템입니다.
VPN 없이 워커 환경 세팅(WSL2, Docker)과 컨테이너 배포에만 집중합니다.

### 주요 기능
- ✅ **GUI 기반 워커 설정** - 웹 인터페이스로 간편한 워커 환경 설정
- ✅ **모듈화된 설치 시스템** - WSL2, Ubuntu, Docker를 단계별로 설치
- ✅ **자동 포트 포워딩** - WSL2 환경에서 자동 네트워크 설정
- ✅ **원격 컨테이너 배포** - 중앙에서 워커에 Docker 컨테이너 배포
- ✅ **중앙 서버 통합** - 중앙 플랫폼과 자동 연동
- ✅ **노드 관리** - 워커 노드 등록, 상태 모니터링, 관리

## 🏗️ 시스템 구조

```
[인터넷/공개망]
    │
    └── [중앙 서버] (공인 IP 또는 도메인)
         ├─ 메인 플랫폼 API (Port 8000)
         └─ 워커 관리 시스템 (이 프로젝트)
              ├─ Worker Manager API (Port 8090)
              ├─ Web Dashboard (Port 5000)
              └─ PostgreSQL (Port 5434, 로컬만)

[워커 노드]
    ├── Worker #1 (직접 HTTP 연결)
    ├── Worker #2 (직접 HTTP 연결)
    └── Worker #N (직접 HTTP 연결)
```

## 🚀 빠른 시작

### 1. 프로젝트 클론
```bash
git clone <repository-url>
cd worker-manager
```

### 2. 자동 시작 (권장)

**Windows (가장 간편):**
```bash
start.bat               # start.ps1을 자동으로 실행
start.bat -d            # 백그라운드 실행
start.bat -f            # 강제 재생성
start.bat -d -f         # 백그라운드 + 강제 재생성
```

**Windows (PowerShell 직접 실행):**
```powershell
.\start.ps1             # 기본 실행
.\start.ps1 -d          # 백그라운드 실행
.\start.ps1 -f          # 강제 재생성
.\start.ps1 -d -f       # 백그라운드 + 강제 재생성
```

**Linux/macOS:**
```bash
./start.sh
```

시작 스크립트는 다음을 자동으로 수행합니다:
- ✅ LAN IP 자동 감지
- ✅ .env 파일 자동 생성 및 설정
- ✅ 방화벽 및 포트 포워딩 설정 (Windows만)
- ✅ WSL2 포트 포워딩 설정 (Windows만)
- ✅ Docker Compose 실행

**💡 추천:** Windows 사용자는 `start.bat`를 더블클릭하거나 명령줄에서 실행하세요!

### 3. 수동 설정 (선택사항)

자동 시작 대신 수동으로 설정하려면:

```bash
# .env 파일 생성
cp .env.example .env

# .env 파일 편집 (주요 설정)
# - LOCAL_SERVER_IP: Worker Manager 서버의 로컬 IP
# - API_TOKEN: API 인증 토큰
# - CENTRAL_SERVER_URL: 중앙 서버 주소 (선택사항)
```

### 3. 서비스 시작

#### Windows (권장)
```powershell
# PowerShell에서 실행 (관리자 권한 자동 요청)
.\start.ps1           # 포그라운드 실행 (로그 확인)
.\start.ps1 -d        # 백그라운드 실행
.\start.ps1 -f        # 강제 재생성
.\start.ps1 -d -f     # 백그라운드 + 강제 재생성
```

start.ps1은 다음 작업을 자동으로 수행합니다:
1. WSL2 포트 포워딩 설정
2. Docker Compose로 모든 서비스 시작
3. 접속 주소 안내

#### Linux
```bash
# Docker Compose 실행
docker-compose up -d
```

#### 서비스 접속
- **Web Dashboard**: `http://<서버IP>:5000`
  - 워커 노드 관리
  - 워커 환경 자동 설정
  - 모니터링

- **API Server**: `http://<서버IP>:8090`
  - RESTful API 엔드포인트
  - `/docs`에서 API 문서 확인

## 📁 프로젝트 구조

```
worker-manager/
├── api/                           # FastAPI 서버
│   ├── main.py                   # API 엔드포인트
│   ├── models.py                 # 데이터 모델
│   ├── database.py               # DB 연결
│   ├── worker_integration.py     # 워커 통합 기능
│   ├── node_manager.py           # 노드 관리
│   ├── simple_worker_docker_runner.py  # 워커 실행기
│   ├── docker_compose_templates.py     # Docker Compose 템플릿
│   ├── gui/                      # GUI 기반 워커 설정
│   │   ├── worker_setup_gui_modular.py
│   │   └── modules/              # 설치 모듈
│   │       ├── wsl_setup_module.py       # WSL2 설치
│   │       ├── ubuntu_setup_module.py    # Ubuntu 설치
│   │       ├── docker_setup_module.py    # Docker 설치
│   │       ├── network_setup_module.py   # 네트워크 설정
│   │       └── container_deploy_module.py # 컨테이너 배포
│   └── central/                  # 중앙 서버 통합
│       ├── routes.py
│       └── docker_runner.py
├── web-dashboard/                # Flask 웹 대시보드
│   ├── app.py
│   └── Dockerfile
├── docker-compose.yml            # Docker Compose 설정
├── Dockerfile                    # API 서버 Dockerfile
├── requirements.txt              # Python 의존성
├── start.ps1                     # Windows 시작 스크립트
├── setup-port-forwarding.ps1     # WSL2 포트 포워딩
└── .env.example                  # 환경변수 예제
```

## 🔧 주요 기능

### 1. 워커 환경 자동 설정
웹 대시보드를 통해 워커 노드의 환경을 자동으로 설정합니다:

#### 자동으로 수행되는 작업
- ✅ **WSL2 설치** - Windows 환경에서 WSL2 자동 설치 및 설정
- ✅ **Ubuntu 설치** - Ubuntu 22.04 배포판 설치 및 사용자 설정
- ✅ **Docker 설치** - Docker Desktop 또는 Docker CE 자동 설치
- ✅ **네트워크 설정** - 포트 포워딩 자동 설정
- ✅ **컨테이너 배포** - 워커 컨테이너 자동 빌드 및 실행

#### 모듈화된 설치 시스템
각 단계가 독립 모듈로 구성되어 있어 문제 발생 시 해당 단계만 재실행 가능합니다.

자세한 내용은 [api/gui/modules/README.md](api/gui/modules/README.md) 참조

### 2. 노드 관리
- 워커 노드 등록
- 실시간 상태 모니터링
- 노드 정보 업데이트

### 3. 컨테이너 배포
- Docker Compose 파일 자동 생성
- 원격 워커에 컨테이너 배포
- 배포 상태 실시간 확인

## 📊 API 사용 예제

### API 문서
```
http://<서버IP>:8090/docs
```

### 노드 관리
```bash
# 노드 목록 조회
curl -H "Authorization: Bearer <API_TOKEN>" \
  http://<서버IP>:8090/nodes

# 새 노드 등록
curl -X POST -H "Authorization: Bearer <API_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"name": "worker-01", "description": "Worker Node 1"}' \
  http://<서버IP>:8090/nodes

# 노드 상세 정보
curl -H "Authorization: Bearer <API_TOKEN>" \
  http://<서버IP>:8090/nodes/{node_id}

# 시스템 통계
curl -H "Authorization: Bearer <API_TOKEN>" \
  http://<서버IP>:8090/stats
```

## 🐳 Docker 명령어

```powershell
# 서비스 로그 확인
docker-compose logs -f              # 전체 로그
docker-compose logs -f worker-api   # API 서버 로그만

# 서비스 상태 확인
docker-compose ps

# 서비스 재시작
docker-compose restart worker-api

# 서비스 중지
docker-compose down

# 완전 삭제 (볼륨 포함)
docker-compose down -v
```

## ⚙️ 환경변수

`.env` 파일에서 설정 가능한 환경변수:

### 필수 설정
| 변수 | 설명 | 예시 |
|------|------|------|
| `LOCAL_SERVER_IP` | Worker Manager 서버의 로컬 IP | `192.168.0.88` |
| `API_TOKEN` | API 인증 토큰 | `your-secure-token` |

### 선택 설정
| 변수 | 설명 | 기본값 |
|------|------|--------|
| `CENTRAL_SERVER_URL` | 중앙 서버 URL (통합 사용 시) | - |
| `DATABASE_URL` | PostgreSQL 연결 문자열 | `postgresql://worker:workerpass@postgres:5432/workerdb` |
| `TZ` | 타임존 | `Asia/Seoul` |

## 🔧 문제 해결

### Docker 접속 안 됨 (Windows)
**증상**: `localhost:8090` 접속 실패
**원인**: WSL2 백엔드 사용 시 Docker가 별도 네트워크에서 실행
**해결**:
```powershell
# 본인의 실제 IP 확인
ipconfig

# 해당 IP로 접속 (예: 192.168.0.88:8090)
```

### 포트 포워딩 실패
**증상**: WSL2에서 외부 접속 안 됨
**해결**:
```powershell
# 관리자 권한으로 PowerShell 실행
.\setup-port-forwarding.ps1
```

### 컨테이너 시작 실패
**증상**: `docker-compose up` 실패
**해결**:
```powershell
# 로그 확인
docker-compose logs

# 기존 컨테이너 완전 삭제 후 재시작
docker-compose down -v
.\start.ps1 -f
```

## 📚 추가 문서

- [GUI 모듈 상세 가이드](api/gui/modules/README.md)
- [FastAPI 문서](http://<서버IP>:8090/docs)

## 🔐 보안

- API 토큰 기반 인증
- 최소 권한 원칙 적용
- 환경변수를 통한 민감 정보 관리

## 📝 라이선스

MIT License
