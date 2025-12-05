#!/bin/bash

# 워커매니저 이미지 빌드 스크립트


# ========================================
# 설정 변수 (필요시 수정)
# ========================================
DOCKER_USER="intownlab"
IMAGE_NAME="worker-manager"
VERSION="v1.0"

FULL_IMAGE="${DOCKER_USER}/${IMAGE_NAME}"

IMAGE_NAME_DASHBOARD="worker-manager-dashboard"
VERSION_DASHBOARD="v1.0"

FULL_IMAGE_DASHBOARD="${DOCKER_USER}/${IMAGE_NAME_DASHBOARD}"

echo "========================================="
echo "워커매니저 이미지 빌드 시작"
echo "========================================="
echo "이미지: ${FULL_IMAGE}:${VERSION}"
echo ""

# 프로젝트 루트 디렉토리로 이동
cd ..

# 기본 서버 이미지 빌드
echo ""
echo "[1/2] 워커매니저 이미지 빌드 중..."
docker build -f worker-manager/Dockerfile -t ${FULL_IMAGE}:${VERSION} .

if [ $? -eq 0 ]; then
    echo "✓ 워커매니저 이미지 빌드 성공"
else
    echo "✗ 워커매니저 이미지 빌드 실패"
    exit 1
fi

# 대시보드 이미지 빌드 (수정사항 있으면 주석 해제)
echo ""
echo "[2/2] 대시보드 보호 이미지 빌드 중..."
docker build -f worker-manager/Dockerfile_fl -t ${FULL_IMAGE_DASHBOARD}:${VERSION_DASHBOARD} .

if [ $? -eq 0 ]; then
    echo "✓ 대시보드 보호 이미지 빌드 성공"
else
    echo "✗ 대시보드 보호 이미지 빌드 실패"
    exit 1
fi

echo ""
echo "========================================="
echo "모든 보호 이미지 빌드 완료!"
echo "========================================="
echo ""
echo "빌드된 이미지:"
docker images | grep "${FULL_IMAGE}"

# Docker Hub에 푸시
echo ""
echo "========================================="
echo "Docker Hub에 이미지 푸시 중..."
echo "========================================="

echo "[1/2] 워커매니저 태그 업데이트 및 이미지 푸시 중..."
docker tag ${FULL_IMAGE}:${VERSION} ${FULL_IMAGE}:latest
docker push ${FULL_IMAGE}:latest
if [ $? -eq 0 ]; then
    echo "✓ 워커매니저 latest 이미지 푸시 성공"
else
    echo "✗ 워커매니저 latest 이미지 푸시 실패"
    exit 1
fi

echo "[2/2] 대시보드 latest 태그 업데이트 및 이미지 푸시 중..."
docker tag ${FULL_IMAGE_DASHBOARD}:${VERSION_DASHBOARD} ${FULL_IMAGE_DASHBOARD}:latest
docker push ${FULL_IMAGE_DASHBOARD}:latest
if [ $? -eq 0 ]; then
    echo "✓ 대시보드 latest 이미지 푸시 성공"
else
    echo "✗ 대시보드 latest 이미지 푸시 실패"
    exit 1
fi

echo ""
echo "========================================="
echo "모든 이미지 푸시 완료!"
echo "========================================="

