#!/bin/bash

# Worker Manager 배포 스크립트

set -e

echo "======================================"
echo "Worker Manager 배포"
echo "======================================"

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 환경변수 확인
if [ -f .env ]; then
    source .env
else
    echo -e "${YELLOW}[WARNING] .env 파일이 없습니다. 기본값을 사용합니다.${NC}"

    # 기본값 설정
    export LOCAL_SERVER_IP=${LOCAL_SERVER_IP:-192.168.0.88}
    export CENTRAL_SERVER_URL=${CENTRAL_SERVER_URL:-http://192.168.0.88:8000}
    export API_TOKEN=${API_TOKEN:-test-token-123}

    # .env 파일 생성
    cat > .env << EOF
LOCAL_SERVER_IP=$LOCAL_SERVER_IP
CENTRAL_SERVER_URL=$CENTRAL_SERVER_URL
API_TOKEN=$API_TOKEN
DB_USER=worker_manager
DB_PASSWORD=worker_pass
DB_NAME=worker_db
API_PORT=8090
DASHBOARD_PORT=5000
TZ=Asia/Seoul
EOF

    echo -e "${GREEN}[INFO] .env 파일이 생성되었습니다.${NC}"
fi

echo ""
echo "설정 정보:"
echo "  로컬 서버 IP: $LOCAL_SERVER_IP"
echo "  API 포트: 8090"
echo "  Dashboard 포트: 5000"
echo ""

# Docker 확인
if ! command -v docker &> /dev/null; then
    echo -e "${RED}[ERROR] Docker가 설치되어 있지 않습니다.${NC}"
    exit 1
fi

if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo -e "${RED}[ERROR] Docker Compose가 설치되어 있지 않습니다.${NC}"
    exit 1
fi

# 설정 디렉토리 생성
echo -e "${GREEN}[INFO] 설정 디렉토리 생성 중...${NC}"
mkdir -p config

# 기존 컨테이너 정리
echo -e "${GREEN}[INFO] 기존 컨테이너 정리 중...${NC}"
docker compose down 2>/dev/null || docker-compose down 2>/dev/null || true

# 컨테이너 시작
echo -e "${GREEN}[INFO] 컨테이너 시작 중...${NC}"
docker compose up -d 2>/dev/null || docker-compose up -d

# 서비스 상태 확인
echo -e "${GREEN}[INFO] 서비스 시작 대기 중...${NC}"
sleep 10

# API 헬스체크
echo -e "${GREEN}[INFO] API 서버 상태 확인 중...${NC}"
if curl -s -f http://localhost:8090/health > /dev/null; then
    echo -e "${GREEN}[SUCCESS] API 서버가 정상적으로 실행 중입니다.${NC}"
else
    echo -e "${RED}[ERROR] API 서버 시작 실패${NC}"
    echo "로그 확인:"
    docker compose logs worker-api 2>/dev/null || docker-compose logs worker-api
    exit 1
fi

echo ""
echo "======================================"
echo -e "${GREEN}배포 완료!${NC}"
echo "======================================"
echo ""
echo "API 엔드포인트: http://$LOCAL_SERVER_IP:8090"
echo "Web Dashboard: http://$LOCAL_SERVER_IP:5000"
echo "API 토큰: $API_TOKEN"
echo ""
echo "다음 명령으로 상태를 확인할 수 있습니다:"
echo "  docker compose ps"
echo "  docker compose logs -f"
echo ""
echo "워커 등록:"
echo "  중앙서버: http://$LOCAL_SERVER_IP:8090/central/setup"
echo "  워커노드: http://$LOCAL_SERVER_IP:5000/worker/setup"
echo ""
