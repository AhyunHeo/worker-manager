"""
Cython 빌드 스크립트
- .py 파일을 .so (Linux) / .pyd (Windows) 바이너리로 컴파일
- 소스 코드 보호 목적
"""

import os
import shutil
from setuptools import setup, find_packages
from Cython.Build import cythonize
from Cython.Distutils import build_ext
import glob

# 컴파일에서 제외할 파일들
EXCLUDE_FILES = [
    '__init__.py',           # 패키지 인식용
    'setup_cython.py',       # 이 파일 자체
    'main.py',               # FastAPI 앱 (Depends 사용)
    'worker_integration.py', # FastAPI 라우터 (Depends 사용)
    'routes.py',             # FastAPI 라우터 (Depends 사용)
]

# 컴파일에서 제외할 파일 패턴 (공백, 백업 파일 등)
EXCLUDE_PATTERNS = [
    ' copy',            # 백업 복사본 (파일명에 공백)
    ' - Copy',          # Windows 복사본
    '.bak',             # 백업 파일
    '.backup',          # 백업 파일
]

# 컴파일에서 제외할 디렉토리
EXCLUDE_DIRS = [
    'migrations',       # DB 마이그레이션은 그대로 유지
    '__pycache__',
]


def get_py_files(base_dir):
    """컴파일할 .py 파일 목록 수집"""
    py_files = []

    for root, dirs, files in os.walk(base_dir):
        # 제외할 디렉토리 스킵
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]

        for file in files:
            if file.endswith('.py') and file not in EXCLUDE_FILES:
                # 제외 패턴 체크 (공백, 백업 파일 등)
                skip = False
                for pattern in EXCLUDE_PATTERNS:
                    if pattern in file:
                        skip = True
                        print(f"  Skipping (pattern '{pattern}'): {file}")
                        break

                if not skip:
                    filepath = os.path.join(root, file)
                    py_files.append(filepath)

    return py_files


def clean_source_files(base_dir, keep_init=True):
    """컴파일 후 원본 .py 파일 삭제"""
    for root, dirs, files in os.walk(base_dir):
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]

        for file in files:
            if file.endswith('.py'):
                if keep_init and file == '__init__.py':
                    continue
                if file in EXCLUDE_FILES:
                    continue

                filepath = os.path.join(root, file)
                print(f"Removing source: {filepath}")
                os.remove(filepath)


if __name__ == "__main__":
    # API 디렉토리의 .py 파일들 수집
    base_dir = os.path.dirname(os.path.abspath(__file__))
    api_dir = os.path.join(base_dir, 'api')

    if not os.path.exists(api_dir):
        # Docker 빌드 시 /app 디렉토리에서 실행
        api_dir = '/app'
        base_dir = '/app'

    py_files = get_py_files(api_dir if os.path.exists(api_dir) else base_dir)

    print(f"Found {len(py_files)} Python files to compile:")
    for f in py_files:
        print(f"  - {f}")

    if py_files:
        setup(
            name="worker-manager",
            ext_modules=cythonize(
                py_files,
                compiler_directives={
                    'language_level': "3",
                    'boundscheck': False,
                    'wraparound': False,
                },
                nthreads=4,
            ),
            cmdclass={'build_ext': build_ext},
            script_args=['build_ext', '--inplace'],
        )

        print("\n" + "="*50)
        print("Cython compilation completed!")
        print("="*50)
