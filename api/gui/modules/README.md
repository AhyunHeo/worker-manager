# PowerShell Modules for Worker Setup

## 개요
기존의 1497줄짜리 `docker_runner_functions.py` 파일을 작고 관리하기 쉬운 모듈로 분리했습니다.
각 모듈은 특정 기능에 집중하며, 모든 기존 로직과 기능이 보존되었습니다.

## 모듈 구조

### 1. wsl_setup_module.py
**목적**: WSL2 설치 및 환경 설정
- Windows 버전 확인 (Windows 10 빌드 18362 이상)
- WSL2 설치 및 활성화
- WSL2 커널 업데이트
- 재부팅 요구사항 처리

### 2. ubuntu_setup_module.py  
**목적**: Ubuntu 배포판 관리
- Ubuntu 22.04 설치 (최대 지원 버전)
- 기존 배포판 감지 및 재사용
- 사용자 계정 생성 및 sudo 설정
- WSL.conf 구성

### 3. docker_setup_module.py
**목적**: Docker 설치 및 구성
- Docker Desktop 확인 및 시작
- Docker Desktop WSL 통합 확인
- Docker CE 설치 (Docker Desktop 통합 불가시)
- NVIDIA Container Toolkit 설치 (GPU 지원)

### 4. network_setup_module.py
**목적**: 네트워크 및 포트 포워딩
- VPN 연결 상태 확인
- WSL2 IP 주소 가져오기
- VPN IP에서 WSL2 IP로 포트 포워딩 설정
- Windows Firewall 규칙 관리
- 네트워크 연결 테스트

### 5. container_deploy_module.py
**목적**: Docker 컨테이너 배포
- Docker Compose 파일 생성
- Worker 컨테이너 배포
- 컨테이너 상태 모니터링
- 컨테이너 재시작 및 로그 관리

### 6. docker_runner_orchestrator.py
**목적**: 모든 모듈 통합 조정
- 모든 모듈 함수 로드
- 설치 프로세스 순서 관리
- 에러 처리 및 복구
- 사용자 피드백 제공

## 주요 개선사항

### 1. 유지보수성
- 각 모듈이 독립적으로 테스트 가능
- 기능별로 분리되어 코드 찾기 쉬움
- 버그 수정 시 영향 범위 최소화

### 2. 재사용성
- 각 모듈을 다른 프로젝트에서도 사용 가능
- 필요한 기능만 선택적으로 import 가능

### 3. 가독성
- 각 파일이 200-400줄로 관리하기 쉬운 크기
- 명확한 함수명과 모듈명
- 일관된 에러 처리 패턴

### 4. 기능 보존
- 모든 기존 로직 100% 보존
- 에러 처리 및 복구 로직 유지
- Windows 10/11 호환성 유지
- WSL2 재부팅 감지 로직 유지

## 사용 방법

### 기존 방식 (단일 파일)
```python
from gui.docker_runner_functions import get_docker_runner_function

docker_runner = get_docker_runner_function(
    server_ip, node_id, vpn_ip, central_ip, metadata
)
```

### 새로운 방식 (모듈화)
```python
from gui.modules import get_docker_runner_orchestrator

docker_runner = get_docker_runner_orchestrator(
    server_ip, node_id, vpn_ip, central_ip, metadata
)
```

### 개별 모듈 사용
```python
from gui.modules import get_wsl_setup_function, get_ubuntu_setup_function

# WSL2만 설치
wsl_setup = get_wsl_setup_function()

# Ubuntu만 설치
ubuntu_setup = get_ubuntu_setup_function(vpn_ip)
```

## 마이그레이션 가이드

1. **기존 코드 백업**
   - `docker_runner_functions.py` 백업 보관
   - 문제 발생 시 롤백 가능

2. **점진적 전환**
   - 먼저 `worker_setup_gui_modular.py`로 테스트
   - 안정성 확인 후 기존 파일 대체

3. **호환성 유지**
   - 두 버전 모두 동일한 인터페이스 제공
   - 함수 시그니처 동일

## 테스트 체크리스트

- [ ] WSL2 설치 (Windows 10/11)
- [ ] Ubuntu 22.04 설치
- [ ] Docker Desktop 통합
- [ ] Docker CE 설치 (통합 실패시)
- [ ] VPN 연결 확인
- [ ] 포트 포워딩 설정
- [ ] 컨테이너 배포
- [ ] 재부팅 후 재실행
- [ ] 에러 복구 시나리오

## 향후 개선 계획

1. **단위 테스트 추가**
   - 각 모듈별 PowerShell 테스트
   - CI/CD 파이프라인 구축

2. **로깅 개선**
   - 중앙화된 로깅 시스템
   - 디버그 레벨 조정 가능

3. **설정 외부화**
   - JSON/YAML 설정 파일 지원
   - 환경별 설정 관리

4. **에러 복구 강화**
   - 자동 재시도 메커니즘
   - 체크포인트 기반 복구