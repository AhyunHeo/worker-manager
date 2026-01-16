# Cython 빌드 가이드

## 개요

Docker 이미지 내 Python 소스 코드 보호를 위해 Cython을 사용하여 `.py` 파일을 `.so` 바이너리로 컴파일합니다.

## 보호 수준

| 항목 | 상태 |
|------|------|
| 소스 코드 직접 열람 | 불가능 |
| 일반 사용자 역공학 | 매우 어려움 |
| 전문가 역공학 | 가능 (시간/노력 필요) |

**참고**: 100% 보호는 불가능하지만, 대부분의 상용 소프트웨어 수준의 보호를 제공합니다.

## 빌드 구조

### Multi-stage Docker 빌드

```
Stage 1 (builder)          Stage 2 (runtime)
┌─────────────────┐        ┌─────────────────┐
│ gcc, g++        │        │ python:slim     │
│ python3-dev     │        │ (빌드 도구 없음) │
│ cython          │        │                 │
│                 │        │                 │
│ .py → .so 컴파일 │ ────▶  │ .so 파일만 복사  │
│ .py 파일 삭제    │        │                 │
└─────────────────┘        └─────────────────┘
```

### 이점
- 최종 이미지에 빌드 도구 없음 (이미지 크기 감소)
- 소스 코드 (.py) 없음
- 중간 파일 (.c) 없음

## 적용된 이미지

### 1. worker-manager (`intownlab/worker-manager`)
- 위치: `/Dockerfile`
- 컴파일 대상: `/api/**/*.py`
- 제외: `__init__.py`, `migrations/`

### 2. worker-manager-dashboard (`intownlab/worker-manager-dashboard`)
- 위치: `/web-dashboard/Dockerfile`
- 컴파일 대상: `app.py`

## 빌드 명령어

```bash
# worker-manager 이미지 빌드
docker build -t intownlab/worker-manager:latest -f Dockerfile .

# worker-manager-dashboard 이미지 빌드
docker build -t intownlab/worker-manager-dashboard:latest -f web-dashboard/Dockerfile .
```

## 빌드 확인

```bash
# 컨테이너 내부 확인
docker run --rm -it intownlab/worker-manager:latest ls -la /app

# 예상 결과: .so 파일만 존재, .py 파일 없음
# main.cpython-310-x86_64-linux-gnu.so
# database.cpython-310-x86_64-linux-gnu.so
# ...
```

## 컴파일 제외 파일

| 파일/디렉토리 | 제외 이유 |
|--------------|----------|
| `__init__.py` | Python 패키지 인식 필요 |
| `migrations/` | DB 마이그레이션 스크립트 (가독성 유지) |

## 로컬 테스트 (선택사항)

로컬에서 Cython 빌드 테스트:

```bash
# 의존성 설치
pip install cython setuptools

# 빌드 실행
cd worker-manager
python setup_cython.py

# 결과 확인
ls api/*.so
```

## 트러블슈팅

### 빌드 실패: gcc not found
```
apt-get install gcc g++ python3-dev
```

### 런타임 오류: module not found
- `__init__.py` 파일이 삭제되지 않았는지 확인
- 패키지 구조 확인

### uvicorn 실행 오류
- `main.py`가 컴파일되면 uvicorn이 `main:app`을 찾을 수 있는지 확인
- 필요시 진입점 스크립트 추가

## 보안 참고사항

1. **Cython은 난독화가 아님**: 디컴파일 도구로 일부 복원 가능
2. **핵심 비즈니스 로직**: 가능하면 서버 사이드에만 유지
3. **API 키/비밀번호**: 절대 코드에 하드코딩하지 않음
4. **추가 보호**: PyArmor 등 난독화 도구 병행 고려
