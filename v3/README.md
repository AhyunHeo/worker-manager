# Worker Manager v3 - EXE Installers

## 구조

```
v3/
├── scripts/                    # PowerShell 소스 스크립트
│   ├── set-manager.ps1        # Worker Manager 설치 (정적)
│   ├── central-setup.ps1      # 중앙서버 설치 (config.json 사용)
│   └── worker-setup.ps1       # 워커노드 설치 (config.json 사용)
├── build/
│   └── build-exe.ps1          # PS2EXE 빌드 스크립트
├── dist/                       # 빌드된 exe 파일
│   ├── WorkerManager-Setup.exe
│   ├── CentralServer-Setup.exe
│   └── WorkerNode-Setup.exe
└── README.md
```

## 빌드 방법

### 1. PS2EXE 설치
```powershell
Install-Module -Name ps2exe -Scope CurrentUser
```

### 2. 빌드 실행
```powershell
cd v3/build
.\build-exe.ps1
```

## 배포 방식

### 정적 설치 파일 (set-manager)
- `WorkerManager-Setup.exe` 단독 배포
- 설정 파일 불필요

### 동적 설치 파일 (central, worker)
- API에서 `config.json` 생성
- exe + config.json 함께 다운로드
- exe 실행 시 같은 폴더의 config.json 읽음

## config.json 예시

### central-setup용
```json
{
  "node_id": "central-001",
  "server_ip": "192.168.0.100",
  "api_port": 8000,
  "fl_port": 5002,
  "frontend_port": 3000,
  "db_port": 5432,
  "mongo_port": 27017,
  "jwt_secret_key": "your-secret-key",
  "worker_manager_ip": "192.168.0.88"
}
```

### worker-setup용
```json
{
  "node_id": "worker-001",
  "worker_manager_ip": "192.168.0.88",
  "central_server_ip": "192.168.0.100",
  "central_api_port": 8000
}
```
