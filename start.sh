#!/bin/bash
# Worker Manager Startup Script
# Automatically detects LAN IP and creates .env file

set -e

echo "========================================"
echo "Worker Manager Startup"
echo "========================================"
echo ""

# LAN IP 감지 함수
detect_lan_ip() {
    local ip=""

    # Method 1: ip route 사용 (가장 정확)
    if command -v ip &> /dev/null; then
        ip=$(ip route get 8.8.8.8 2>/dev/null | grep -oP 'src \K\S+')
        if [[ -n "$ip" ]] && [[ "$ip" =~ ^192\.168\. ]]; then
            echo "$ip"
            return 0
        fi
    fi

    # Method 2: hostname -I 사용
    if command -v hostname &> /dev/null; then
        for addr in $(hostname -I 2>/dev/null); do
            # 192.168.x.x 대역만 허용 (Docker, VPN 제외)
            if [[ "$addr" =~ ^192\.168\. ]] && [[ ! "$addr" =~ ^192\.168\.65\. ]]; then
                echo "$addr"
                return 0
            fi
        done
    fi

    # Method 3: ifconfig 사용 (fallback)
    if command -v ifconfig &> /dev/null; then
        ip=$(ifconfig 2>/dev/null | grep -oP 'inet \K192\.168\.\d+\.\d+' | grep -v '192.168.65.' | head -1)
        if [[ -n "$ip" ]]; then
            echo "$ip"
            return 0
        fi
    fi

    # 감지 실패 시 기본값
    echo "192.168.0.88"
    return 1
}

# [1/4] LAN IP 감지
echo "[1/4] Detecting LAN IP..."
LAN_IP=$(detect_lan_ip)
if [[ $? -eq 0 ]]; then
    echo "Detected LAN IP: $LAN_IP"
else
    echo "WARNING: Could not detect LAN IP automatically."
    echo "Using default: $LAN_IP"
    echo "Please update LOCAL_SERVER_IP in .env file if incorrect."
fi
echo ""

# [2/4] .env 파일 생성
echo "[2/4] Creating/Updating .env file..."
if [[ ! -f .env ]]; then
    echo "Creating new .env file from .env.example..."
    cp .env.example .env
    echo ".env file created."
else
    echo ".env file already exists."
fi
echo ""

# [3/4] LOCAL_SERVER_IP 업데이트
echo "[3/4] Updating LOCAL_SERVER_IP in .env..."
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    sed -i '' "s/^LOCAL_SERVER_IP=.*/LOCAL_SERVER_IP=$LAN_IP/" .env
else
    # Linux
    sed -i "s/^LOCAL_SERVER_IP=.*/LOCAL_SERVER_IP=$LAN_IP/" .env
fi
echo "LOCAL_SERVER_IP set to: $LAN_IP"
echo ""

# .env 파일 내용 확인
echo "Current .env configuration:"
echo "----------------------------------------"
grep -v '^#' .env | grep -v '^$'
echo "----------------------------------------"
echo ""

# [4/4] Docker Compose 실행
echo "[4/4] Starting Docker Compose..."
echo ""
docker-compose up -d

if [[ $? -eq 0 ]]; then
    echo ""
    echo "========================================"
    echo "Worker Manager started successfully!"
    echo "========================================"
    echo ""
    echo "Access points:"
    echo "- API Server: http://$LAN_IP:8091"
    echo "- Dashboard: http://$LAN_IP:5000"
    echo "- Worker Setup: http://$LAN_IP:8091/worker/setup"
    echo "- Central Setup: http://$LAN_IP:8091/central/setup"
    echo ""
    echo "To view logs: docker-compose logs -f"
    echo "To stop: docker-compose down"
    echo ""
else
    echo ""
    echo "ERROR: Failed to start Docker Compose"
    echo "Please check the error messages above."
    echo ""
    exit 1
fi
