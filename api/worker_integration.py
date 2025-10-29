"""
Worker Node Integration API
VPN 등록과 워커노드 플랫폼 등록을 통합하는 API
"""

from fastapi import APIRouter, Depends, HTTPException, Response, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from database import SessionLocal
from models import Node, QRToken
from simple_worker_docker_runner import generate_simple_worker_runner, generate_simple_worker_runner_wsl
from utils import get_lan_ip, validate_lan_ip
from typing import Optional
import json
import logging
import qrcode
import io
import base64
from datetime import datetime, timedelta, timezone
import secrets
import os

logger = logging.getLogger(__name__)

# Global configuration - 환경변수에서 한 번만 로드
LOCAL_SERVER_IP = os.getenv('LOCAL_SERVER_IP', '192.168.0.88')
CENTRAL_SERVER_URL = os.getenv('CENTRAL_SERVER_URL', 'http://192.168.0.88:8000')

# GUI 모듈 import 시도 (옵션)
try:
    from gui.worker_setup_gui_modular import generate_worker_setup_gui_modular
    GUI_MODULE_AVAILABLE = True
except ImportError:
    logger.warning("GUI module not available, using fallback")
    GUI_MODULE_AVAILABLE = False

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class WorkerEnvironmentRequest(BaseModel):
    """워커노드 환경변수 설정 요청"""
    node_id: str
    description: str
    central_server_ip: Optional[str] = None
    hostname: Optional[str] = None

@router.get("/worker/setup")
async def worker_setup_page():
    """워커노드 설정 페이지"""
    central_server_url = CENTRAL_SERVER_URL
    
    # Response Headers for better performance
    headers = {
        "Cache-Control": "public, max-age=3600",
        "Connection": "close"
    }
    
    html_content = f"""
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>워커노드 통합 설정</title>
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
                background: linear-gradient(135deg, #f8fafc 0%, #e0f2fe 50%, #c7d2fe 100%);
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
                padding: 20px;
            }}
            .container {{
                background: white;
                border-radius: 20px;
                box-shadow: 0 20px 60px rgba(0,0,0,0.1);
                max-width: 500px;
                width: 100%;
                padding: 40px;
                border: 1px solid #e2e8f0;
            }}
            h1 {{
                color: #1e293b;
                margin-bottom: 10px;
                font-size: 28px;
                background: linear-gradient(135deg, #7fbf55 0%, #2665a0 100%);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-clip: text;
            }}
            .subtitle {{
                color: #64748b;
                margin-bottom: 30px;
                font-size: 14px;
            }}
            .form-group {{
                margin-bottom: 20px;
            }}
            label {{
                display: block;
                margin-bottom: 8px;
                color: #475569;
                font-weight: 500;
            }}
            input, select {{
                width: 100%;
                padding: 12px;
                border: 2px solid #e2e8f0;
                border-radius: 8px;
                font-size: 16px;
                transition: border-color 0.3s;
                background: white;
                color: #1e293b;
            }}
            input:focus, select:focus {{
                outline: none;
                border-color: #7fbf55;
            }}
            .btn {{
                width: 100%;
                padding: 14px;
                background: linear-gradient(135deg, #7fbf55 0%, #69a758 100%);
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 16px;
                font-weight: 600;
                cursor: pointer;
                transition: transform 0.2s, box-shadow 0.2s;
            }}
            .btn:hover {{
                transform: translateY(-2px);
                box-shadow: 0 10px 20px rgba(127, 191, 85, 0.3);
            }}
            .btn:active {{
                transform: translateY(0);
            }}
            .result {{
                display: none;
                margin-top: 30px;
                padding: 20px;
                background: #f8fafc;
                border-radius: 8px;
                text-align: center;
                border: 1px solid #e2e8f0;
            }}
            .qr-code {{
                margin: 20px 0;
            }}
            .qr-code img {{
                max-width: 256px;
                border: 4px solid white;
                border-radius: 8px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.1);
            }}
            .install-link {{
                display: inline-block;
                margin-top: 15px;
                padding: 10px 20px;
                background: #2665a0;
                color: white;
                text-decoration: none;
                border-radius: 8px;
                font-weight: 500;
            }}
            .install-link:hover {{
                background: #1e5090;
            }}
            .info-box {{
                background: rgba(127, 191, 85, 0.1);
                border-left: 4px solid #7fbf55;
                padding: 12px;
                margin-top: 20px;
                border-radius: 4px;
            }}
            .info-box p {{
                color: #5c9f68;
                font-size: 14px;
                line-height: 1.5;
            }}
            .loading {{
                display: none;
                text-align: center;
                margin: 20px 0;
            }}
            .spinner {{
                border: 3px solid #e2e8f0;
                border-top: 3px solid #7fbf55;
                border-radius: 50%;
                width: 40px;
                height: 40px;
                animation: spin 1s linear infinite;
                margin: 0 auto;
            }}
            @keyframes spin {{
                0% {{ transform: rotate(0deg); }}
                100% {{ transform: rotate(360deg); }}
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>워커노드 통합 설정</h1>
            <p class="subtitle">VPN 설치와 워커노드 등록을 한 번에 완료합니다</p>
            
            <form id="workerForm">
                <div class="form-group">
                    <label for="node_id">노드 ID *</label>
                    <input type="text" id="node_id" name="node_id" required 
                           placeholder="예: worker-001" pattern="[a-zA-Z0-9_\-]+">
                </div>
                
                <div class="form-group">
                    <label for="description">설명 *</label>
                    <input type="text" id="description" name="description" required 
                           placeholder="예: GPU 서버 #1">
                </div>
                
                <div class="form-group">
                    <label for="central_server_ip">중앙서버 IP</label>
                    <input type="text" id="central_server_ip" name="central_server_ip" 
                           value="{central_server_url.replace('http://', '').replace('https://', '').split(':')[0]}" 
                           placeholder="예: 192.168.0.88">
                </div>
                
                <button type="submit" class="btn">QR 코드 생성</button>
            </form>
            
            <div class="loading">
                <div class="spinner"></div>
                <p style="margin-top: 10px; color: #666;">QR 코드 생성 중...</p>
            </div>
            
            <div id="result" class="result">
                <h2 style="color: #333; margin-bottom: 20px;">✅ QR 코드 생성 완료</h2>
                <div class="qr-code" id="qrCode"></div>
                <p style="color: #666; margin-bottom: 10px;">또는 이 링크를 사용하세요:</p>
                <div>
                    <input type="text" id="installUrl" readonly 
                           style="margin-bottom: 10px; font-size: 14px;">
                    <button onclick="copyUrl()" class="btn" style="background: #28a745;">
                        📋 링크 복사
                    </button>
                </div>
                <div class="info-box">
                    <p>
                        <strong>설치 프로세스:</strong><br>
                        1. QR 코드 스캔 또는 링크 접속<br>
                        2. VPN IP 자동 할당<br>
                        3. 자동 노드 등록 프로그램 설치 및 실행<br>
                        4. 워커노드 자동 등록<br>
                        5. Docker 환경변수 자동 설정
                    </p>
                </div>
            </div>
        </div>
        
        <script>
            document.getElementById('workerForm').addEventListener('submit', async (e) => {{
                e.preventDefault();
                
                const formData = new FormData(e.target);
                const data = Object.fromEntries(formData.entries());
                
                // 빈 값 제거
                Object.keys(data).forEach(key => {{
                    if (!data[key]) delete data[key];
                }});
                
                // 로딩 표시
                document.querySelector('.loading').style.display = 'block';
                document.querySelector('button[type="submit"]').disabled = true;
                
                try {{
                    const response = await fetch('/worker/generate-qr', {{
                        method: 'POST',
                        headers: {{ 'Content-Type': 'application/json' }},
                        body: JSON.stringify(data)
                    }});
                    
                    if (!response.ok) {{
                        throw new Error('QR 코드 생성 실패');
                    }}
                    
                    const result = await response.json();
                    
                    // QR 코드 표시
                    document.getElementById('qrCode').innerHTML = 
                        '<img src="' + result.qr_code + '" alt="QR Code">';
                    
                    // 설치 URL 표시
                    document.getElementById('installUrl').value = result.install_url;
                    
                    // 결과 표시
                    document.getElementById('result').style.display = 'block';
                    
                }} catch (error) {{
                    alert('오류: ' + error.message);
                }} finally {{
                    document.querySelector('.loading').style.display = 'none';
                    document.querySelector('button[type="submit"]').disabled = false;
                }}
            }});
            
            function copyUrl() {{
                const urlInput = document.getElementById('installUrl');
                urlInput.select();
                document.execCommand('copy');
                
                // 복사 완료 피드백
                const btn = event.target;
                const originalText = btn.textContent;
                btn.textContent = '✅ 복사됨!';
                btn.style.background = '#28a745';
                
                setTimeout(() => {{
                    btn.textContent = originalText;
                }}, 2000);
            }}
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content, headers=headers)

@router.post("/api/worker/setup")
async def api_worker_setup(
    request: WorkerEnvironmentRequest,
    db: Session = Depends(get_db)
):
    """API를 통한 워커노드 설정 및 다운로드 URL 반환

    다른 플랫폼에서 API로 호출하여 워커노드 설치 프로그램을 생성할 수 있습니다.

    Request:
        - node_id: 노드 ID (필수)
        - description: 노드 설명 (필수)
        - central_server_ip: 중앙서버 IP (선택, 기본값: 192.168.0.88)

    Response:
        - node_id: 등록된 노드 ID
        - vpn_ip: 할당된 VPN IP
        - download_url: 통합 설치 프로그램 다운로드 URL
        - status: 등록 상태
    """
    try:
        # 중앙서버 IP 처리 (기본값: 192.168.0.88)
        central_ip = request.central_server_ip or '192.168.0.88'
        central_url = f"http://{central_ip}:8000"

        metadata = {
            "description": request.description,
            "central_server_ip": central_ip,
            "central_server_url": central_url,
            "hostname": request.hostname or request.node_id
        }

        # 기존 노드 확인
        existing = db.query(Node).filter(Node.node_id == request.node_id).first()

        if existing and existing.status == "registered" and existing.vpn_ip:
            # 이미 등록된 노드인 경우 - 메타데이터만 업데이트
            existing.description = request.description
            existing.central_server_url = central_url
            existing.hostname = request.hostname or request.node_id
            existing.docker_env_vars = json.dumps(metadata)
            existing.updated_at = datetime.now(timezone.utc)
            db.commit()

            # 다운로드 URL 생성
            server_host = os.getenv('SERVERURL', 'localhost')
            if server_host == 'auto' or not server_host or server_host == 'localhost':
                server_host = LOCAL_SERVER_IP

            download_url = f"http://{server_host}:8090/api/download/{existing.node_id}/setup-gui"

            return {
                "node_id": existing.node_id,
                "vpn_ip": existing.vpn_ip,
                "download_url": download_url,
                "status": "registered",
                "message": "Node already registered, metadata updated"
            }

        # 새로운 노드 등록 프로세스
        # 고유한 pending 키 생성
        unique_pending_key = f"pending_{request.node_id}_{secrets.token_hex(8)}"

        new_node = Node(
            node_id=request.node_id,
            node_type="worker",
            hostname=request.hostname or request.node_id,
            description=request.description,
            central_server_url=central_url,
            docker_env_vars=json.dumps(metadata),
            status="pending",
            vpn_ip=None  # pending 상태에서는 None (unique constraint 충돌 방지)
        )

        if existing:
            # pending 상태 노드 업데이트
            existing.description = request.description
            existing.central_server_url = central_url
            existing.hostname = request.hostname or request.node_id
            existing.docker_env_vars = json.dumps(metadata)
            existing.updated_at = datetime.now(timezone.utc)
            target_node = existing
        else:
            # 새 노드 추가
            db.add(new_node)
            target_node = new_node
            logger.info(f"Added new worker node {request.node_id} via API")

        db.commit()

        # LAN IP 감지 (VPN 없이 워커의 실제 LAN IP 사용)
        try:
            # LAN IP 감지
            lan_ip = get_lan_ip()
            if not lan_ip or lan_ip == "0.0.0.0":
                logger.warning(f"Could not detect LAN IP for node {request.node_id}, keeping as pending")
                # LAN IP 감지 실패 시 None으로 두고 pending 상태 유지
                target_node.vpn_ip = None
                target_node.status = "pending"
            else:
                # LAN IP 감지 성공 시 등록 완료
                target_node.vpn_ip = lan_ip  # 필드명은 vpn_ip지만 실제로는 LAN IP 저장
                target_node.status = "registered"
                logger.info(f"Successfully registered worker node {request.node_id} via API with LAN IP {lan_ip}")

            db.commit()

            # 다운로드 URL 생성
            server_host = os.getenv('SERVERURL', 'localhost')
            if server_host == 'auto' or not server_host or server_host == 'localhost':
                server_host = LOCAL_SERVER_IP

            download_url = f"http://{server_host}:8090/api/download/{request.node_id}/setup-gui"

            return {
                "node_id": request.node_id,
                "lan_ip": lan_ip,
                "download_url": download_url,
                "status": "registered",
                "message": "Node registered successfully"
            }

        except Exception as e:
            logger.error(f"Failed to register worker node via API: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to register node: {str(e)}")

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        logger.error(f"API worker setup failed: {str(e)}\n{error_detail}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Setup failed: {str(e)}")


@router.post("/worker/generate-qr")
async def generate_worker_qr(
    request: WorkerEnvironmentRequest,
    db: Session = Depends(get_db)
):
    """워커노드용 QR 코드 및 설치 링크 생성"""
    try:
        # 토큰 생성
        token = secrets.token_urlsafe(32)
        expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
        
        # 토큰 정보를 DB에 저장
        qr_token = QRToken(
            token=token,
            node_id=request.node_id,
            node_type="worker",
            expires_at=expires_at,
            used=False
        )
        db.add(qr_token)
        
        # 워커노드 메타데이터도 토큰과 함께 저장 (JSON 형태로)
        # 중앙서버 IP를 URL로 변환
        central_ip = request.central_server_ip or '192.168.0.88'
        central_url = f"http://{central_ip}:8000"
        
        metadata = {
            "description": request.description,
            "central_server_ip": central_ip,
            "central_server_url": central_url,
            "hostname": request.hostname or request.node_id
        }
        
        # Node 테이블에 예비 등록 (config는 나중에 생성)
        # 각 노드에 고유한 pending 키 생성 (충돌 방지)
        unique_pending_key = f"pending_{request.node_id}_{secrets.token_hex(8)}"
        
        new_node = Node(
            node_id=request.node_id,
            node_type="worker",
            hostname=request.hostname or request.node_id,
            description=request.description,
            central_server_url=central_url,
            docker_env_vars=json.dumps(metadata),
            status="pending",  # 아직 VPN 설정 전
            vpn_ip=None  # pending 상태에서는 None (unique constraint 충돌 방지)
        )
        
        # 중복 체크 및 업데이트
        existing = db.query(Node).filter(Node.node_id == request.node_id).first()
        if existing:
            # 기존 노드가 있으면 메타데이터만 업데이트 (pending 키는 건드리지 않음)
            if existing.status != "pending":  # 이미 설정된 노드면 키 유지
                existing.description = request.description
                existing.central_server_url = central_url
                existing.hostname = request.hostname or request.node_id
                existing.docker_env_vars = json.dumps(metadata)
                existing.updated_at = datetime.now(timezone.utc)
            else:  # pending 상태면 메타데이터만 업데이트
                existing.description = request.description
                existing.central_server_url = central_url
                existing.hostname = request.hostname or request.node_id
                existing.docker_env_vars = json.dumps(metadata)
                existing.updated_at = datetime.now(timezone.utc)
        else:
            # 새 노드 추가 (임시로 pending 상태)
            db.add(new_node)
            logger.info(f"Added new worker node {request.node_id} in pending status")
        
        db.commit()

        # LAN IP 감지 및 등록 (pending 상태가 아닌 경우만)
        if not existing or existing.status == "pending":
            try:
                # LAN IP 감지
                lan_ip = get_lan_ip()
                target_node = existing if existing else new_node

                if not lan_ip or lan_ip == "0.0.0.0":
                    logger.warning(f"Could not detect LAN IP for {request.node_id}, keeping as pending")
                    # LAN IP 감지 실패 시 None으로 두고 pending 상태 유지
                    target_node.vpn_ip = None
                    target_node.status = "pending"
                else:
                    # LAN IP 감지 성공 시 등록 완료
                    target_node.vpn_ip = lan_ip  # 필드명은 vpn_ip지만 실제로는 LAN IP
                    target_node.status = "registered"
                    logger.info(f"Successfully registered worker node {request.node_id} with LAN IP {lan_ip}")

                db.commit()

            except Exception as e:
                logger.error(f"Failed to register worker node: {e}")
                # 실패해도 QR 코드는 생성되도록 계속 진행
        
        # 설치 URL 생성
        # SERVERURL 환경변수 사용 (docker-compose.yml에서 설정)
        server_host = os.getenv('SERVERURL', 'localhost')
        if server_host == 'auto' or not server_host or server_host == 'localhost':
            # LOCAL_SERVER_IP 사용 (우선순위)
            server_host = LOCAL_SERVER_IP
        
        server_url = f"http://{server_host}:8090"
        install_url = f"{server_url}/worker/install/{token}"
        
        # QR 코드 생성
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(install_url)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        qr_base64 = base64.b64encode(buffer.getvalue()).decode()
        
        return {
            "token": token,
            "install_url": install_url,
            "qr_code": f"data:image/png;base64,{qr_base64}",
            "expires_at": expires_at.isoformat(),
            "node_id": request.node_id
        }
        
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        logger.error(f"Failed to generate QR: {str(e)}\n{error_detail}")
        db.rollback()  # 트랜잭션 롤백
        raise HTTPException(status_code=500, detail=f"QR 생성 실패: {str(e)}")

# 이제 /api/download/{node_id}/docker-runner 엔드포인트를 사용합니다
# @router.get("/worker/docker-runner/{node_id}")
# async def get_worker_docker_runner(node_id: str, os_type: str = "windows", db: Session = Depends(get_db)):
#     """워커노드 Docker Runner 다운로드 (OS별 분기) - DEPRECATED"""
#     node = db.query(Node).filter(Node.node_id == node_id).first()
#     if not node:
#         raise HTTPException(status_code=404, detail="Node not found")
#     
#     # OS 타입에 따라 적절한 Runner 생성
#     if os_type.lower() == "linux":
#         # Linux 버전은 main.py에서 처리
#         # docker_runner = generate_simple_worker_runner_linux(node)
#         # filename = f"docker-runner-{node_id}.sh"
#         # media_type = "text/x-shellscript"
#         pass
#     else:
#         # Windows (기본값)
#         docker_runner = generate_simple_worker_runner(node)
#         filename = f"docker-runner-{node_id}.bat"
#         media_type = "application/x-msdos-program"
#     
#     return Response(
#         content=docker_runner,
#         media_type=media_type,
#         headers={
#             "Content-Disposition": f"attachment; filename={filename}"
#         }
#     )

@router.get("/worker/install/{token}")
async def worker_install_page(token: str, db: Session = Depends(get_db)):
    """워커노드 자동 설치 페이지"""
    
    # 토큰 확인
    qr_token = db.query(QRToken).filter(QRToken.token == token).first()
    if not qr_token:
        return HTMLResponse(content="<h1>❌ 유효하지 않은 토큰입니다</h1>", status_code=404)
    
    if datetime.now(timezone.utc) > qr_token.expires_at:
        return HTMLResponse(content="<h1>⏰ 만료된 토큰입니다</h1>", status_code=400)
    
    # 노드 정보 가져오기
    node = db.query(Node).filter(Node.node_id == qr_token.node_id).first()
    if not node:
        return HTMLResponse(content="<h1>❌ 노드 정보를 찾을 수 없습니다</h1>", status_code=404)
    
    # Node 테이블의 값 우선, 없으면 metadata에서 가져오기
    metadata = json.loads(node.docker_env_vars) if node.docker_env_vars else {}
    
    html_content = f"""
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>워커노드 자동 설치</title>
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background: linear-gradient(135deg, #f8fafc 0%, #e0f2fe 50%, #c7d2fe 100%);
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
                padding: 20px;
            }}
            .container {{
                background: white;
                border-radius: 20px;
                box-shadow: 0 20px 60px rgba(0,0,0,0.1);
                max-width: 600px;
                width: 100%;
                padding: 40px;
                border: 1px solid #e2e8f0;
            }}
            h1 {{
                color: #1e293b;
                margin-bottom: 20px;
                background: linear-gradient(135deg, #7fbf55 0%, #2665a0 100%);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-clip: text;
            }}
            .info-card {{
                background: #f8fafc;
                border-radius: 8px;
                padding: 20px;
                margin-bottom: 20px;
                border: 1px solid #e2e8f0;
            }}
            .info-row {{
                display: flex;
                justify-content: space-between;
                margin-bottom: 10px;
                padding-bottom: 10px;
                border-bottom: 1px solid #e0e0e0;
            }}
            .info-row:last-child {{
                border-bottom: none;
                margin-bottom: 0;
                padding-bottom: 0;
            }}
            .info-label {{
                font-weight: 600;
                color: #475569;
            }}
            .info-value {{
                color: #1e293b;
            }}
            .status {{
                text-align: center;
                margin: 30px 0;
            }}
            .status-icon {{
                font-size: 48px;
                margin-bottom: 10px;
            }}
            .btn {{
                width: 100%;
                padding: 14px;
                background: linear-gradient(135deg, #7fbf55 0%, #69a758 100%);
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 16px;
                font-weight: 600;
                cursor: pointer;
                transition: transform 0.2s;
                text-decoration: none;
                display: inline-block;
                text-align: center;
            }}
            .btn:hover {{
                transform: translateY(-2px);
                box-shadow: 0 10px 20px rgba(127, 191, 85, 0.3);
            }}
            .btn-success {{
                background: linear-gradient(135deg, #7fbf55 0%, #5c9f68 100%);
            }}
            .steps {{
                margin: 30px 0;
            }}
            .step {{
                display: flex;
                align-items: center;
                margin-bottom: 15px;
                opacity: 0.5;
                transition: opacity 0.3s;
            }}
            .step.active {{
                opacity: 1;
            }}
            .step.completed {{
                opacity: 1;
            }}
            .step-icon {{
                width: 30px;
                height: 30px;
                border-radius: 50%;
                background: #e2e8f0;
                display: flex;
                align-items: center;
                justify-content: center;
                margin-right: 15px;
                font-size: 14px;
            }}
            .step.active .step-icon {{
                background: #7fbf55;
                color: white;
                animation: pulse 1.5s infinite;
            }}
            .step.completed .step-icon {{
                background: #7fbf55;
                color: white;
            }}
            @keyframes pulse {{
                0% {{ transform: scale(1); }}
                50% {{ transform: scale(1.1); }}
                100% {{ transform: scale(1); }}
            }}
            .code-block {{
                background: #1e293b;
                color: #f8f8f2;
                padding: 20px;
                border-radius: 8px;
                margin: 20px 0;
                font-family: 'Courier New', monospace;
                font-size: 14px;
                overflow-x: auto;
            }}
            .loading {{
                display: inline-block;
                width: 20px;
                height: 20px;
                border: 3px solid #e2e8f0;
                border-top: 3px solid #7fbf55;
                border-radius: 50%;
                animation: spin 1s linear infinite;
                margin-left: 10px;
            }}
            @keyframes spin {{
                0% {{ transform: rotate(0deg); }}
                100% {{ transform: rotate(360deg); }}
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>워커노드 자동 설치</h1>
            
            <div class="info-card">
                <div class="info-row">
                    <span class="info-label">노드 ID:</span>
                    <span class="info-value">{qr_token.node_id}</span>
                </div>
                <div class="info-row">
                    <span class="info-label">설명:</span>
                    <span class="info-value">{node.description or metadata.get('description', 'N/A')}</span>
                </div>
                <div class="info-row">
                    <span class="info-label">중앙서버 IP:</span>
                    <span class="info-value">{node.central_server_url or metadata.get('central_server_url', os.getenv('CENTRAL_SERVER_URL', 'http://192.168.0.88:8000'))}</span>
                </div>
                <div class="info-row">
                    <span class="info-label">호스트명:</span>
                    <span class="info-value">{node.hostname or metadata.get('hostname', qr_token.node_id)}</span>
                </div>
            </div>
            
            <div class="steps" id="steps">
                <div class="step" id="step1">
                    <div class="step-icon">1</div>
                    <span>워커 환경 설정 중...</span>
                </div>
                <div class="step" id="step2">
                    <div class="step-icon">2</div>
                    <span>LAN IP 감지 중...</span>
                </div>
                <div class="step" id="step3">
                    <div class="step-icon">3</div>
                    <span>워커노드 등록 준비 중...</span>
                </div>
                <div class="step" id="step4">
                    <div class="step-icon">4</div>
                    <span>설치 스크립트 생성 중...</span>
                </div>
            </div>
            
            <div class="status" id="statusSection">
                <div class="status-icon">⏳</div>
                <p>아래 버튼을 클릭하여 설치를 시작하세요</p>
            </div>
            
            <button class="btn" id="startBtn" onclick="startInstallation()">설치 시작</button>
            
            <div id="result" style="display: none; margin-top: 30px;">
                <h2 style="color: #7fbf55; margin-bottom: 20px;">✅ 설치 준비 완료!</h2>
                
                <div class="info-card">
                    <div class="info-row">
                        <span class="info-label">LAN IP:</span>
                        <span class="info-value" id="lanIp">-</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">상태:</span>
                        <span class="info-value" style="color: #7fbf55;">등록 완료</span>
                    </div>
                </div>
                
                <h3 style="margin-top: 30px; margin-bottom: 10px;">설치 방법을 선택하세요:</h3>
                
                <div style="margin: 20px 0; padding: 15px; background: rgba(127, 191, 85, 0.1); border: 1px solid #7fbf55; border-radius: 8px;">
                    <h4 style="color: #5c9f68; margin-bottom: 10px;">⚠️ 사전 설치 요구사항</h4>
                    <p style="color: #5c9f68; font-size: 14px; line-height: 1.6; margin-bottom: 10px;">
                        워커노드 실행을 위해 <strong>Docker Desktop</strong>이 반드시 설치되어 있어야 합니다.
                    </p>
                    <div style="margin-top: 10px;">
                        <a href="https://www.docker.com/products/docker-desktop/" target="_blank" 
                           style="display: inline-block; padding: 8px 16px; background: #2665a0; color: white; 
                                  text-decoration: none; border-radius: 4px; font-size: 14px;">
                            🐳 Docker Desktop 다운로드
                        </a>
                        <span style="margin-left: 10px; color: #5c9f68; font-size: 12px;">
                            (설치 후 Docker Desktop을 실행한 상태에서 진행하세요)
                        </span>
                    </div>
                    
                    <div style="margin-top: 15px; padding-top: 15px; border-top: 1px solid #7fbf55;">
                        <h5 style="color: #5c9f68; margin-bottom: 8px; font-size: 14px;">✨ Docker Desktop 설치 후 안내:</h5>
                        <p style="color: #5c9f68; font-size: 13px; line-height: 1.8;">
                            Docker Desktop 설치 후 <strong>아래 BAT 파일을 실행하면 WSL Integration이 자동으로 설정됩니다!</strong><br>
                            별도의 수동 설정이 필요없습니다.
                        </p>
                        <p style="color: #5c9f68; font-size: 12px; margin-top: 10px; font-style: italic;">
                            ⚡ BAT 파일이 자동으로 Ubuntu 배포판과 Docker Desktop 연동을 처리합니다.
                        </p>
                    </div>
                </div>
                
                <div style="margin-top: 20px;">
                    <h4 style="margin-bottom: 15px;">📥 다운로드 옵션:</h4>
                    
                    <!-- 통합 설치 버튼 (권장) -->
                    <div style="margin-bottom: 15px; padding: 15px; background: linear-gradient(135deg, #7fbf55 0%, #69a758 100%); border-radius: 10px; box-shadow: 0 4px 10px rgba(127, 191, 85, 0.3);">
                        <div style="color: white; font-size: 12px; margin-bottom: 8px; font-weight: 500;">
                            ⭐ 권장 - 원클릭 통합 설치
                        </div>
                        <button onclick="downloadDockerRunner('setup')" style="
                            width: 100%; 
                            padding: 14px; 
                            background: white;
                            color: #5c9f68;
                            border: 2px solid rgba(255,255,255,0.9);
                            border-radius: 8px;
                            font-size: 16px; 
                            font-weight: bold; 
                            cursor: pointer;
                            transition: all 0.3s ease;
                            box-shadow: 0 2px 6px rgba(0,0,0,0.1);
                        " onmouseover="this.style.background='#f5f5f5'; this.style.transform='translateY(-2px)'; this.style.boxShadow='0 4px 12px rgba(0,0,0,0.2)';" 
                           onmouseout="this.style.background='white'; this.style.transform='translateY(0)'; this.style.boxShadow='0 2px 6px rgba(0,0,0,0.1)';">
                            🚀 통합 설치 프로그램 (VPN + Docker 한번에)
                            <div style="font-size: 12px; margin-top: 5px; color: #666;">VPN과 Docker를 자동으로 순차 설치합니다</div>
                        </button>
                    </div>
                    
                    <!-- 개별 설치 옵션 (숨김 처리) -->
                    <div style="display: none; border: 2px solid #e2e8f0; border-radius: 10px; padding: 15px; background: white;">
                        <div style="font-size: 12px; color: #6c757d; margin-bottom: 12px; font-weight: 500;">
                            또는 개별 설치 (수동):
                        </div>
                        <div style="display: flex; gap: 15px;">
                            <button onclick="downloadWindowsInstaller()" style="
                                flex: 1;
                                padding: 12px;
                                background: linear-gradient(135deg, #7fbf55 0%, #5c9f68 100%);
                                color: white;
                                border: none;
                                border-radius: 6px;
                                font-weight: 600;
                                cursor: pointer;
                                transition: all 0.3s ease;
                                box-shadow: 0 2px 8px rgba(127, 191, 85, 0.3);
                            " onmouseover="this.style.transform='translateY(-2px)'; this.style.boxShadow='0 4px 12px rgba(127, 191, 85, 0.4)';" 
                               onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='0 2px 8px rgba(127, 191, 85, 0.3)';">
                                1️⃣ VPN만 설치
                                <div style="font-size: 11px; margin-top: 3px; opacity: 0.9;">WireGuard VPN 설정</div>
                            </button>

                            <button onclick="downloadDockerRunner('gui')" style="
                                flex: 1;
                                padding: 12px;
                                background: linear-gradient(135deg, #2665a0 0%, #1e5090 100%);
                                color: white;
                                border: none;
                                border-radius: 6px;
                                font-weight: 600;
                                cursor: pointer;
                                transition: all 0.3s ease;
                                box-shadow: 0 2px 8px rgba(38, 101, 160, 0.3);
                            " onmouseover="this.style.transform='translateY(-2px)'; this.style.boxShadow='0 4px 12px rgba(38, 101, 160, 0.4)';" 
                               onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='0 2px 8px rgba(38, 101, 160, 0.3)';">
                                2️⃣ Docker만 설치
                                <div style="font-size: 11px; margin-top: 3px; opacity: 0.9;">워커 노드 배포</div>
                            </button>
                        </div>
                    </div>
                </div>
                
                <div style="margin-top: 20px; padding: 15px; background: rgba(127, 191, 85, 0.1); border-radius: 8px; border: 1px solid rgba(127, 191, 85, 0.3);">
                    <p style="color: #5c9f68; font-size: 14px; line-height: 1.6;">
                        <strong>다음 단계:</strong><br>
                        1. 위 스크립트를 다운로드하여 워커노드에서 실행<br>
                        2. 스크립트가 자동으로 VPN과 Docker 환경을 설정<br>
                        3. 워커노드 컨테이너가 자동으로 시작됨
                    </p>
                </div>
            </div>
        </div>
        
        <script>
            let installData = null;
            
            // 페이지 로드 시 노드 상태 확인
            window.addEventListener('DOMContentLoaded', async () => {{
                try {{
                    // 노드 상태 확인
                    const response = await fetch('/api/nodes/{qr_token.node_id}/status', {{
                        headers: {{
                            'Authorization': 'Bearer test-token-123'
                        }}
                    }});
                    
                    if (response.ok) {{
                        const nodeData = await response.json();
                        console.log('Node status:', nodeData);
                        
                        // 노드가 이미 등록되어 있는 경우
                        if (nodeData.status === 'registered' && nodeData.vpn_ip) {{
                            // 설치 데이터 설정
                            installData = {{
                                lan_ip: nodeData.vpn_ip,  // DB 필드명은 vpn_ip지만 실제는 LAN IP
                                node_id: nodeData.node_id,
                                config_exists: nodeData.config_exists,
                                // Docker Runner는 API에서 직접 다운로드 가능
                                docker_runner: 'available'
                            }};
                            
                            // UI 업데이트
                            document.getElementById('lanIp').textContent = nodeData.vpn_ip;
                            document.getElementById('result').style.display = 'block';
                            document.querySelector('.status-icon').textContent = '✅';
                            document.querySelector('.status p').textContent = '이미 등록이 완료된 노드입니다. 아래에서 필요한 파일을 다운로드하세요.';
                            document.getElementById('startBtn').style.display = 'none';
                            
                            // 모든 단계를 완료 상태로 표시
                            for (let i = 1; i <= 4; i++) {{
                                const step = document.getElementById('step' + i);
                                step.classList.add('completed');
                                step.querySelector('.step-icon').textContent = '✓';
                            }}
                        }}
                    }}
                }} catch (error) {{
                    console.error('Failed to check node status:', error);
                }}
                
                // URL 파라미터로 자동 시작 여부 확인 (선택사항)
                const urlParams = new URLSearchParams(window.location.search);
                if (urlParams.get('autostart') === 'true') {{
                    setTimeout(() => startInstallation(), 1000);
                }}
            }});
            
            async function startInstallation() {{
                const btn = document.getElementById('startBtn');
                // 버튼 비활성화
                btn.disabled = true;
                btn.textContent = '설치 진행 중...';
                
                // 단계별 진행
                await updateStep(1, true);
                
                try {{
                    // API 호출하여 VPN 설정 및 워커노드 등록
                    const response = await fetch('/worker/process-installation/{qr_token.token}', {{
                        method: 'POST'
                    }});
                    
                    if (!response.ok) {{
                        throw new Error('설치 실패');
                    }}
                    
                    installData = await response.json();
                    
                    // 단계 업데이트
                    await updateStep(1, false, true);
                    await updateStep(2, true);
                    await new Promise(r => setTimeout(r, 500));
                    await updateStep(2, false, true);
                    await updateStep(3, true);
                    await new Promise(r => setTimeout(r, 500));
                    await updateStep(3, false, true);
                    await updateStep(4, true);
                    await new Promise(r => setTimeout(r, 500));
                    await updateStep(4, false, true);
                    
                    // 결과 표시
                    showResult(installData);
                    
                }} catch (error) {{
                    alert('설치 중 오류 발생: ' + error.message);
                    const btn = document.getElementById('startBtn');
                    btn.disabled = false;
                    btn.textContent = '설치 재시도';
                }}
            }}
            
            async function updateStep(stepNum, active, completed = false) {{
                const step = document.getElementById('step' + stepNum);
                if (active) {{
                    step.classList.add('active');
                }} else {{
                    step.classList.remove('active');
                }}
                if (completed) {{
                    step.classList.add('completed');
                    step.querySelector('.step-icon').textContent = '✓';
                }}
                await new Promise(r => setTimeout(r, 300));
            }}
            
            function showResult(data) {{
                document.getElementById('lanIp').textContent = data.lan_ip || data.vpn_ip || '0.0.0.0';
                // installScript element no longer exists - removed from HTML
                document.getElementById('result').style.display = 'block';
                
                // 상태 업데이트
                document.querySelector('.status-icon').textContent = '✅';
                document.querySelector('.status p').textContent = '설치 준비가 완료되었습니다!';
                
                // 설치 시작 버튼 숨기기
                document.getElementById('startBtn').style.display = 'none';
            }}
            
            function downloadDockerRunner(osType) {{
                // 통합 설치(setup) 타입인 경우 setup-gui 엔드포인트 사용
                if (osType === 'setup') {{
                    window.location.href = '/api/download/{qr_token.node_id}/setup-gui';
                    return;
                }}
                
                // 이미 등록된 노드인 경우 API에서 직접 다운로드
                if (installData && installData.docker_runner === 'available') {{
                    // API에서 직접 다운로드 (GUI 버전으로)
                    if (osType === 'wsl') {{
                        osType = 'gui';  // WSL 요청 시 GUI 버전으로 변경
                    }}
                    window.location.href = '/api/download/{qr_token.node_id}/docker-runner?os_type=' + osType;
                    return;
                }}
                
                if (!installData || !installData.docker_runner) {{
                    alert('아직 설치 프로세스가 완료되지 않았습니다.\\n\\n"설치 시작" 버튼을 먼저 클릭하여 설치 프로세스를 완료한 후 다운로드하세요.');
                    const btn = document.getElementById('startBtn');
                    if (btn && btn.style.display === 'none') {{
                        btn.style.display = 'block';
                    }}
                    if (btn) {{
                        btn.scrollIntoView({{ behavior: 'smooth' }});
                    }}
                    return;
                }}
                
                // 모든 OS타입은 API에서 직접 다운로드
                // GUI 버전을 기본으로 사용
                if (osType === 'wsl') {{
                    osType = 'gui';  // WSL 요청 시 GUI 버전으로 변경
                }}
                window.location.href = '/api/download/{qr_token.node_id}/docker-runner?os_type=' + osType;
            }}
            
            function downloadWindowsInstaller() {{
                // 이미 등록된 노드인 경우 설정 파일 다운로드 페이지로 이동
                if (installData && installData.config_exists) {{
                    // VPN 설치 스크립트 생성 API 호출
                    fetch('/api/download/{qr_token.node_id}/vpn-installer', {{
                        headers: {{
                            'Authorization': 'Bearer test-token-123'
                        }}
                    }}).then(response => {{
                        if (response.ok) {{
                            return response.blob();
                        }}
                        throw new Error('Download failed');
                    }}).then(blob => {{
                        const url = window.URL.createObjectURL(blob);
                        const a = document.createElement('a');
                        a.href = url;
                        a.download = 'vpn-installer-{qr_token.node_id}.bat';
                        document.body.appendChild(a);
                        a.click();
                        window.URL.revokeObjectURL(url);
                        document.body.removeChild(a);
                    }}).catch(error => {{
                        console.error('Download error:', error);
                        // 대체 방법: 직접 다운로드 링크
                        window.location.href = '/download/{qr_token.node_id}/config';
                    }});
                    return;
                }}
                
                if (!installData || !installData.windows_installer) {{
                    alert('아직 설치 프로세스가 완료되지 않았습니다.\\n\\n"설치 시작" 버튼을 먼저 클릭하여 설치 프로세스를 완료한 후 다운로드하세요.');
                    // 설치 시작 버튼이 숨겨진 경우 다시 표시
                    const btn = document.getElementById('startBtn');
                    if (btn && btn.style.display === 'none') {{
                        btn.style.display = 'block';
                    }}
                    if (btn) {{
                        btn.scrollIntoView({{ behavior: 'smooth' }});
                    }}
                    return;
                }}
                
                try {{
                    // 배치 파일용 MIME 타입 설정
                    const blob = new Blob([installData.windows_installer], {{ 
                        type: 'application/x-msdos-program' 
                    }});
                    const url = window.URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = 'install-worker-{qr_token.node_id}.bat';
                    a.style.display = 'none';
                    document.body.appendChild(a);
                    a.click();
                    
                    // 클린업
                    setTimeout(() => {{
                        window.URL.revokeObjectURL(url);
                        document.body.removeChild(a);
                    }}, 100);
                }} catch (error) {{
                    console.error('Download error:', error);
                    alert('다운로드 중 오류가 발생했습니다: ' + error.message);
                }}
            }}
            
            // showLinuxScript 함수 제거됨 (더 이상 사용하지 않음)
        </script>
    </body>
    </html>
    """
    
    return HTMLResponse(content=html_content)


@router.post("/worker/process-installation/{token}")
async def process_worker_installation(
    token: str,
    db: Session = Depends(get_db)
):
    """워커노드 설치 처리 - VPN 등록 및 설정 생성"""
    
    # 토큰 확인
    qr_token = db.query(QRToken).filter(QRToken.token == token).first()
    if not qr_token:
        raise HTTPException(status_code=404, detail="Invalid token")
    
    if datetime.now(timezone.utc) > qr_token.expires_at:
        raise HTTPException(status_code=400, detail="Token expired")
    
    # 노드 정보 가져오기
    node = db.query(Node).filter(Node.node_id == qr_token.node_id).first()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    
    try:
        # 이미 등록된 경우
        if node.status != "pending":
            # Docker runner 생성 (GUI 통합 버전)
            docker_runner = generate_worker_setup_gui_modular(node)

            return {
                "status": "existing",
                "node_id": node.node_id,
                "lan_ip": node.vpn_ip,  # DB 필드명은 vpn_ip지만 실제는 LAN IP
                "install_script": generate_install_script(node),
                "docker_runner": docker_runner,
                "message": "Already configured"
            }

        # LAN IP 감지
        lan_ip = get_lan_ip()
        if not lan_ip or lan_ip == "0.0.0.0":
            logger.warning(f"Could not detect LAN IP for node {node.node_id}, keeping as pending")
            # LAN IP 감지 실패 시 None으로 두고 pending 상태 유지
            node.vpn_ip = None
            node.status = "pending"
        else:
            # LAN IP 감지 성공 시 등록 완료
            node.vpn_ip = lan_ip  # DB 필드명은 vpn_ip지만 실제는 LAN IP 저장
            node.status = "registered"
        node.updated_at = datetime.now(timezone.utc)

        # Docker 환경변수 업데이트
        metadata = json.loads(node.docker_env_vars) if node.docker_env_vars else {}
        docker_env = {
            "NODE_ID": node.node_id,
            "DESCRIPTION": node.description or metadata.get('description', ''),
            "CENTRAL_SERVER_URL": node.central_server_url or metadata.get('central_server_url', os.getenv('CENTRAL_SERVER_URL', 'http://192.168.0.88:8000')),
            "HOST_IP": lan_ip
        }
        node.docker_env_vars = json.dumps(docker_env)

        db.commit()

        # 토큰을 사용됨으로 표시
        qr_token.used = True
        db.commit()

        # Docker runner 생성 (GUI 통합 버전 - 모듈화)
        docker_runner = generate_worker_setup_gui_modular(node)

        # Linux/Mac용 스크립트도 제공 (선택사항)
        install_script = generate_install_script(node)

        return {
            "status": "success",
            "node_id": node.node_id,
            "lan_ip": lan_ip,
            "docker_env": docker_env,
            "docker_runner": docker_runner,
            "install_script": install_script
        }
        
    except Exception as e:
        logger.error(f"Installation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

def generate_install_script(node: Node) -> str:
    """워커노드 설치 스크립트 생성"""
    
    docker_env = json.loads(node.docker_env_vars) if node.docker_env_vars else {}
    
    script = f"""#!/bin/bash
# Worker Node Setup Script
# Generated for: {node.node_id}
# LAN IP: {node.vpn_ip}

set -e

echo "========================================="
echo "워커노드 환경 설정 스크립트"
echo "노드 ID: {node.node_id}"
echo "LAN IP: {node.vpn_ip}"
echo "========================================="

# 1. Docker 환경변수 파일 생성
echo ""
echo "[1/1] Docker 환경 설정 중..."
cat > worker-node.env << 'EOF'
# Worker Node Environment Variables
NODE_ID={docker_env.get('NODE_ID', node.node_id)}
DESCRIPTION={docker_env.get('DESCRIPTION', '')}
CENTRAL_SERVER_URL={docker_env.get('CENTRAL_SERVER_URL', 'http://192.168.0.88:8000')}
HOST_IP={docker_env.get('HOST_IP', node.vpn_ip)}
EOF

echo "✓ Docker 환경변수 파일 생성 완료"

# 완료 메시지
echo ""
echo "========================================="
echo "✅ 설정 완료!"
echo "========================================="
echo ""
echo "워커노드 정보:"
echo "  - 노드 ID: {node.node_id}"
echo "  - LAN IP: {node.vpn_ip}"
echo "  - 중앙서버 URL: {docker_env.get('CENTRAL_SERVER_URL', 'http://192.168.0.88:8000')}"
echo ""
echo "다음 단계:"
echo "  1. Docker가 설치되어 있는지 확인하세요"
echo "  2. worker-node.env 파일을 워커 컨테이너에 전달하세요"
echo ""
echo "Docker 컨테이너 실행 방법:"
echo "  source worker-node.env"
echo "  docker run -d \\"
echo "    --name worker-{node.node_id} \\"
echo "    --cap-add NET_ADMIN \\"
echo "    --device /dev/net/tun \\"
echo "    -e NODE_ID=\\$NODE_ID \\"
echo "    -e DESCRIPTION=\\\"\\$DESCRIPTION\\\" \\"
echo "    -e CENTRAL_SERVER_URL=\\$CENTRAL_SERVER_URL \\"
echo "    -e HOST_IP=\\$HOST_IP \\"
echo "    -p 8080:8080 \\"
echo "    --restart unless-stopped \\"
echo "    your-image:tag"
echo ""
echo "VPN 상태 확인:"
echo "  sudo wg show"
echo ""
echo "VPN 재시작:"
echo "  sudo wg-quick down wg0 && sudo wg-quick up wg0"
echo "========================================="
"""
    
    return script

@router.get("/worker/status/{node_id}")
async def get_worker_status(node_id: str, db: Session = Depends(get_db)):
    """워커노드 상태 조회"""
    node = db.query(Node).filter(Node.node_id == node_id).first()

    if not node:
        raise HTTPException(status_code=404, detail="Node not found")

    docker_env = json.loads(node.docker_env_vars) if node.docker_env_vars else {}

    return {
        "node_id": node.node_id,
        "status": node.status,
        "vpn_ip": node.vpn_ip,  # 호환성 위해 필드명 유지 (실제는 LAN IP)
        "description": node.description,
        "central_server_url": node.central_server_url,
        "docker_env": docker_env,
        "created_at": node.created_at,
        "updated_at": node.updated_at
    }

@router.get("/api/download/{node_id}/setup-gui")
async def download_setup_gui(node_id: str, db: Session = Depends(get_db)):
    """워커노드 통합 설치 프로그램 다운로드"""
    # 노드 조회
    node = db.query(Node).filter(Node.node_id == node_id).first()

    if not node:
        raise HTTPException(status_code=404, detail=f"Node {node_id} not found")

    if not GUI_MODULE_AVAILABLE:
        raise HTTPException(status_code=500, detail="Setup-GUI module not available")

    # setup-gui 배치 파일 생성
    try:
        setup_script = generate_worker_setup_gui_modular(node)

        # 파일명 생성
        filename = f"DistributedAI_v2.0-worker-setup-{node_id}.bat"

        # Response 생성
        return Response(
            content=setup_script,
            media_type="application/x-msdos-program",
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "Content-Type": "application/x-msdos-program"
            }
        )
    except Exception as e:
        logger.error(f"Failed to generate setup-gui for {node_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate setup file: {str(e)}")