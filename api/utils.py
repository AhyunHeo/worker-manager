"""
Utility functions for Worker Manager
"""
import socket
import platform
import subprocess
import re
import logging

logger = logging.getLogger(__name__)


def get_lan_ip() -> str:
    """
    워커의 LAN IP 주소를 감지합니다.
    Docker(192.168.65.x), WSL2, VPN(10.x.x.x) 대역은 제외합니다.

    Returns:
        str: LAN IP 주소 (예: "192.168.0.100")
             실패 시 "0.0.0.0" 반환
    """

    def is_valid_lan_ip(ip: str) -> bool:
        """LAN IP로 유효한지 확인 (Docker, WSL2, VPN 대역 제외)"""
        if not ip or ip == '127.0.0.1':
            return False
        # Docker, WSL2 대역 제외
        if ip.startswith('192.168.65.') or ip.startswith('172.'):
            return False
        # VPN 대역 제외
        if ip.startswith('10.100.'):
            return False
        # 192.168.x.x 또는 10.x.x.x (VPN 제외) 허용
        return ip.startswith('192.168.') or ip.startswith('10.')

    try:
        # Method 1: socket을 이용한 방법 (가장 안정적)
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.1)
        try:
            # 실제로 연결하지 않고, 라우팅 테이블을 통해 IP를 얻음
            s.connect(('8.8.8.8', 80))
            lan_ip = s.getsockname()[0]
        finally:
            s.close()

        # 유효한 LAN IP인지 확인
        if is_valid_lan_ip(lan_ip):
            logger.info(f"Detected LAN IP (socket): {lan_ip}")
            return lan_ip

    except Exception as e:
        logger.warning(f"Socket method failed: {e}")

    try:
        # Method 2: hostname을 통한 방법
        hostname = socket.gethostname()
        lan_ip = socket.gethostbyname(hostname)

        if is_valid_lan_ip(lan_ip):
            logger.info(f"Detected LAN IP via hostname: {lan_ip}")
            return lan_ip

    except Exception as e:
        logger.warning(f"Hostname method failed: {e}")

    try:
        # Method 3: OS별 명령어 사용
        os_type = platform.system()

        if os_type == "Windows":
            # ipconfig 사용 (기존 network_setup_module.py 로직 참고)
            result = subprocess.run(
                ['ipconfig'],
                capture_output=True,
                text=True,
                timeout=5
            )

            # IPv4 주소 찾기 (Docker, WSL2, VPN 대역 제외)
            ipv4_pattern = r'IPv4.*?:\s*(\d+\.\d+\.\d+\.\d+)'
            matches = re.findall(ipv4_pattern, result.stdout)

            for ip in matches:
                if is_valid_lan_ip(ip):
                    logger.info(f"Detected LAN IP via ipconfig: {ip}")
                    return ip

        elif os_type == "Linux":
            # ip addr 또는 hostname -I 사용
            try:
                result = subprocess.run(
                    ['hostname', '-I'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                ips = result.stdout.strip().split()

                # 사설 LAN IP 찾기
                for ip in ips:
                    if is_valid_lan_ip(ip):
                        logger.info(f"Detected LAN IP via hostname -I: {ip}")
                        return ip

            except:
                # ip addr 명령어 시도
                result = subprocess.run(
                    ['ip', 'addr'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )

                ipv4_pattern = r'inet (\d+\.\d+\.\d+\.\d+)'
                matches = re.findall(ipv4_pattern, result.stdout)

                for ip in matches:
                    if is_valid_lan_ip(ip):
                        logger.info(f"Detected LAN IP via ip addr: {ip}")
                        return ip

    except Exception as e:
        logger.warning(f"OS-specific method failed: {e}")

    # 모든 방법 실패 시
    logger.error("Failed to detect LAN IP, returning 0.0.0.0")
    return "0.0.0.0"


def generate_node_id() -> str:
    """
    고유한 노드 ID를 생성합니다.

    Returns:
        str: 노드 ID (예: "WORKER-20250128-A1B2C3")
    """
    import secrets
    from datetime import datetime

    date_str = datetime.now().strftime("%Y%m%d")
    random_str = secrets.token_hex(3).upper()

    return f"WORKER-{date_str}-{random_str}"


def validate_lan_ip(ip: str) -> bool:
    """
    LAN IP가 유효한지 검증합니다.

    Args:
        ip: 검증할 IP 주소

    Returns:
        bool: 유효하면 True, 아니면 False
    """
    if not ip or ip == "0.0.0.0":
        return False

    # IP 형식 검증
    try:
        parts = ip.split('.')
        if len(parts) != 4:
            return False

        for part in parts:
            num = int(part)
            if num < 0 or num > 255:
                return False

        # 로컬호스트는 제외
        if ip.startswith('127.'):
            return False

        return True

    except:
        return False
