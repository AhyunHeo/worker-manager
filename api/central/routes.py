"""
Central Server API Routes
중앙서버 등록과 Docker 설정을 위한 엔드포인트
"""

from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import HTMLResponse, FileResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from database import SessionLocal
from models import Node, QRToken
from typing import Optional
import json
import logging
import qrcode
import io
import base64
from datetime import datetime, timedelta, timezone
import secrets
import os
import tempfile
from .docker_runner import generate_central_docker_runner

logger = logging.getLogger(__name__)
router = APIRouter()

# Global configuration - 환경변수에서 한 번만 로드
LOCAL_SERVER_IP = os.getenv('LOCAL_SERVER_IP', '192.168.0.88')
CENTRAL_SERVER_URL = os.getenv('CENTRAL_SERVER_URL', 'http://192.168.0.88:8000')

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class CentralEnvironmentRequest(BaseModel):
    """중앙서버 환경변수 설정 요청"""
    node_id: str
    server_ip: Optional[str] = "192.168.0.88"
    api_port: Optional[int] = 8000
    fl_port: Optional[int] = 5002
    dashboard_port: Optional[int] = 5000
    db_port: Optional[int] = 5432
    mongo_port: Optional[int] = 27017

@router.get("/central/setup")
async def central_setup_page():
    """중앙서버 설정 페이지"""
    html_content = """
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>중앙서버 통합 설정</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
                background: linear-gradient(135deg, #f8fafc 0%, #e0f2fe 50%, #c7d2fe 100%);
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
                padding: 20px;
            }
            .container {
                background: white;
                border-radius: 16px;
                box-shadow: 0 20px 60px rgba(0,0,0,0.1);
                border: 1px solid #e2e8f0;
                max-width: 600px;
                width: 100%;
                padding: 48px;
            }
            h1 {
                color: #1e293b;
                margin-bottom: 12px;
                font-size: 32px;
                background: linear-gradient(135deg, #7fbf55 0%, #2665a0 100%);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-clip: text;
            }
            .subtitle {
                color: #64748b;
                margin-bottom: 32px;
                font-size: 16px;
            }
            .form-group {
                margin-bottom: 24px;
            }
            label {
                display: block;
                margin-bottom: 8px;
                color: #475569;
                font-weight: 600;
                font-size: 14px;
            }
            input, select {
                width: 100%;
                padding: 12px 16px;
                border: 2px solid #e2e8f0;
                border-radius: 10px;
                font-size: 15px;
                transition: all 0.3s;
                background: #f8fafc;
            }
            input:focus, select:focus {
                outline: none;
                border-color: #6366f1;
                background: white;
                box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.1);
            }
            .port-group {
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 16px;
            }
            .btn {
                width: 100%;
                padding: 14px 24px;
                background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
                color: white;
                border: none;
                border-radius: 10px;
                font-size: 16px;
                font-weight: 600;
                cursor: pointer;
                transition: all 0.3s;
                margin-top: 24px;
                box-shadow: 0 4px 15px rgba(99, 102, 241, 0.3);
            }
            .btn:hover {
                transform: translateY(-3px);
                box-shadow: 0 8px 25px rgba(99, 102, 241, 0.4);
            }
            .btn:active {
                transform: translateY(-1px);
            }
            .result {
                display: none;
                margin-top: 32px;
                padding: 24px;
                background: #f8fafc;
                border: 1px solid #e2e8f0;
                border-radius: 12px;
                text-align: center;
            }
            .qr-code {
                margin: 20px 0;
            }
            .qr-code img {
                max-width: 256px;
                border: 4px solid white;
                border-radius: 12px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.15);
            }
            .info-box {
                background: #eff6ff;
                border-left: 4px solid #6366f1;
                padding: 16px;
                margin-top: 24px;
                border-radius: 8px;
                text-align: left;
            }
            .info-box p {
                color: #4338ca;
                font-size: 14px;
                line-height: 1.6;
            }
            .loading {
                display: none;
                text-align: center;
                margin: 20px 0;
            }
            .spinner {
                border: 3px solid #e2e8f0;
                border-top: 3px solid #6366f1;
                border-radius: 50%;
                width: 40px;
                height: 40px;
                animation: spin 1s linear infinite;
                margin: 0 auto;
            }
            @keyframes spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }
            .advanced-toggle {
                color: #6366f1;
                cursor: pointer;
                font-size: 14px;
                margin-top: 24px;
                text-align: center;
                font-weight: 600;
                transition: color 0.3s;
            }
            .advanced-toggle:hover {
                color: #4338ca;
                text-decoration: underline;
            }
            .advanced-settings {
                display: none;
                margin-top: 24px;
                padding-top: 24px;
                border-top: 2px solid #e2e8f0;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🐳 중앙서버 Docker 설정</h1>
            <p class="subtitle">중앙서버 Docker 실행을 위한 설정을 생성합니다</p>
            
            <form id="centralForm">
                <div class="form-group">
                    <label for="server_ip">중앙서버 IP 주소 *</label>
                    <input type="text" id="server_ip" name="server_ip" required 
                           value="192.168.0.88" 
                           placeholder="예: 192.168.0.88" 
                           pattern="^([0-9]{1,3}\.){3}[0-9]{1,3}$"
                           title="올바른 IP 주소를 입력해주세요">
                    <small style="color: #666; display: block; margin-top: 5px;">
                        중앙서버가 실행될 실제 IP 주소를 입력하세요
                    </small>
                </div>
                
                <input type="hidden" id="node_id" name="node_id" value="central-server-01">

                <!-- 고급 설정 (포트 구성) - 현재 사용 안 함
                <div class="advanced-toggle" onclick="toggleAdvanced()">
                    ⚙️ 고급 설정 (포트 구성)
                </div>

                <div class="advanced-settings" id="advancedSettings">
                    <div class="port-group">
                        <div class="form-group">
                            <label for="api_port">API 포트</label>
                            <input type="number" id="api_port" name="api_port"
                                   value="8000" min="1" max="65535">
                        </div>

                        <div class="form-group">
                            <label for="fl_port">FL 서버 포트</label>
                            <input type="number" id="fl_port" name="fl_port"
                                   value="5002" min="1" max="65535">
                        </div>

                        <div class="form-group">
                            <label for="dashboard_port">대시보드 포트</label>
                            <input type="number" id="dashboard_port" name="dashboard_port"
                                   value="5000" min="1" max="65535">
                        </div>

                        <div class="form-group">
                            <label for="db_port">DB 포트</label>
                            <input type="number" id="db_port" name="db_port"
                                   value="5432" min="1" max="65535">
                        </div>
                    </div>
                </div>
                -->
                
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
                    <div style="display: flex; gap: 10px;">
                        <button onclick="openInNewTab()" class="btn" style="background: #6366f1; flex: 1;">
                            🔗 새 탭으로 열기
                        </button>
                        <button onclick="copyUrl()" class="btn" style="background: #28a745; flex: 1;">
                            📋 링크 복사
                        </button>
                    </div>
                </div>
                <div class="info-box">
                    <p>
                        <strong>설치 프로세스:</strong><br>
                        1. QR 코드 스캔 또는 링크 접속<br>
                        2. Docker 설치 파일 다운로드<br>
                        3. Docker Desktop 설치 확인<br>
                        4. Docker Compose로 중앙서버 실행<br>
                        5. 설정된 IP로 서비스 접속
                    </p>
                </div>
            </div>
        </div>
        
        <script>
            function toggleAdvanced() {
                const advanced = document.getElementById('advancedSettings');
                advanced.style.display = advanced.style.display === 'none' ? 'block' : 'none';
            }
            
            document.getElementById('centralForm').addEventListener('submit', async (e) => {
                e.preventDefault();
                
                const formData = new FormData(e.target);
                const data = Object.fromEntries(formData.entries());
                
                // 숫자 타입 변환
                ['api_port', 'fl_port', 'dashboard_port', 'db_port', 'mongo_port'].forEach(key => {
                    if (data[key]) data[key] = parseInt(data[key]);
                });
                
                // IP 주소 유효성 검사
                if (data.server_ip && !isValidIP(data.server_ip)) {
                    alert('올바른 IP 주소를 입력해주세요.');
                    document.querySelector('.loading').style.display = 'none';
                    document.querySelector('button[type="submit"]').disabled = false;
                    return;
                }
                
                // 로딩 표시
                document.querySelector('.loading').style.display = 'block';
                document.querySelector('button[type="submit"]').disabled = true;
                
                try {
                    const response = await fetch('/central/generate-qr', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(data)
                    });
                    
                    if (!response.ok) {
                        throw new Error('QR 코드 생성 실패');
                    }
                    
                    const result = await response.json();
                    
                    // QR 코드 표시
                    document.getElementById('qrCode').innerHTML = 
                        '<img src="' + result.qr_code + '" alt="QR Code">';
                    
                    // 설치 URL 표시
                    document.getElementById('installUrl').value = result.install_url;
                    
                    // 결과 표시
                    document.getElementById('result').style.display = 'block';
                    
                } catch (error) {
                    alert('오류: ' + error.message);
                } finally {
                    document.querySelector('.loading').style.display = 'none';
                    document.querySelector('button[type="submit"]').disabled = false;
                }
            });
            
            function openInNewTab() {
                const url = document.getElementById('installUrl').value;
                window.open(url, '_blank');

                // 버튼 피드백
                const btn = event.target;
                const originalText = btn.textContent;
                btn.textContent = '✅ 새 탭에서 열림!';

                setTimeout(() => {
                    btn.textContent = originalText;
                }, 2000);
            }

            function openInNewTab() {
                const url = document.getElementById('installUrl').value;
                if (url) {
                    window.open(url, '_blank');
                }
            }

            function copyUrl() {
                const urlInput = document.getElementById('installUrl');
                urlInput.select();
                document.execCommand('copy');

                // 복사 완료 피드백
                const btn = event.target;
                const originalText = btn.textContent;
                btn.textContent = '✅ 복사됨!';
                btn.style.background = '#28a745';

                setTimeout(() => {
                    btn.textContent = originalText;
                }, 2000);
            }

            function isValidIP(ip) {
                const parts = ip.split('.');
                if (parts.length !== 4) return false;
                return parts.every(part => {
                    const num = parseInt(part, 10);
                    return num >= 0 && num <= 255;
                });
            }
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@router.post("/central/generate-qr")
async def generate_central_qr(
    request: CentralEnvironmentRequest,
    db: Session = Depends(get_db)
):
    """중앙서버용 QR 코드 및 설치 링크 생성"""
    try:
        # 토큰 생성
        token = secrets.token_urlsafe(32)
        expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
        
        # 토큰 정보를 DB에 저장
        qr_token = QRToken(
            token=token,
            node_id=request.node_id,
            node_type="central",
            expires_at=expires_at,
            used=False
        )
        db.add(qr_token)
        
        # 중앙서버 메타데이터 저장
        metadata = {
            "server_ip": request.server_ip or "192.168.0.88",
            "api_port": request.api_port or 8000,
            "fl_port": request.fl_port or 5002,
            "dashboard_port": request.dashboard_port or 5000,
            "db_port": request.db_port or 5432,
            "mongo_port": request.mongo_port or 27017
        }
        
        # 고정된 node_id 사용
        node_id = "central-server-01"
        
        # Node 테이블에 예비 등록
        new_node = Node(
            node_id=node_id,
            node_type="central",
            hostname=node_id,
            description="Central Server",
            central_server_url=f"http://{request.server_ip}:8000",
            docker_env_vars=json.dumps(metadata),
            status="pending",
            vpn_ip=request.server_ip  # LAN IP 저장
        )
        
        # 중앙서버는 하나만 존재해야 함 - 기존 중앙서버 체크
        existing = db.query(Node).filter(Node.node_id == node_id).first()
        if existing:
            # 메타데이터만 업데이트
            existing.central_server_url = f"http://{request.server_ip}:8000"
            existing.docker_env_vars = json.dumps(metadata)
            existing.updated_at = datetime.now(timezone.utc)
            existing.status = "pending" if existing.status == "pending" else existing.status
        else:
            db.add(new_node)
        
        db.commit()
        
        # 설치 URL 생성
        server_host = os.getenv('SERVERURL', 'localhost')
        if server_host == 'auto' or not server_host or server_host == 'localhost':
            server_host = LOCAL_SERVER_IP

        server_url = f"http://{server_host}:5000"
        install_url = f"{server_url}/central/install/{token}"
        
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
            "node_id": node_id
        }
        
    except Exception as e:
        logger.error(f"Failed to generate QR: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# VPN 관련 엔드포인트 제거 - 중앙서버는 VPN 불필요

@router.get("/central/docker-runner/{node_id}")
async def get_docker_runner(node_id: str, db: Session = Depends(get_db)):
    """Docker Runner 배치 파일 다운로드"""
    node = db.query(Node).filter(Node.node_id == node_id).first()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    
    # Docker Runner 생성
    docker_runner = generate_central_docker_runner(node)
    
    # Create a temporary file with proper encoding for Windows batch files
    with tempfile.NamedTemporaryFile(mode='w', suffix='.bat', delete=False, encoding='utf-8-sig', newline='\r\n') as tmp_file:
        tmp_file.write(docker_runner)
        temp_path = tmp_file.name
    
    try:
        # Return file response
        return FileResponse(
            path=temp_path,
            filename=f"docker-runner-{node_id}.bat",
            media_type="application/x-bat",
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0"
            }
        )
    finally:
        # Schedule file deletion after response is sent
        import asyncio
        asyncio.create_task(delete_temp_file(temp_path))
        
async def delete_temp_file(path: str):
    """Delete temporary file after a delay"""
    import asyncio
    await asyncio.sleep(5)  # Wait 5 seconds for download to complete
    try:
        os.unlink(path)
    except:
        pass

@router.get("/central/install/{token}")
async def central_install_page(token: str, db: Session = Depends(get_db)):
    """중앙서버 Docker 설치 페이지 (VPN 없음)"""
    
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
    
    metadata = json.loads(node.docker_env_vars) if node.docker_env_vars else {}
    
    html_content = f"""
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>중앙서버 자동 설치</title>
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
                background: linear-gradient(135deg, #f8fafc 0%, #e0f2fe 50%, #c7d2fe 100%);
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
                padding: 20px;
            }}
            .container {{
                background: white;
                border-radius: 16px;
                box-shadow: 0 20px 60px rgba(0,0,0,0.1);
                border: 1px solid #e2e8f0;
                max-width: 700px;
                width: 100%;
                padding: 48px;
            }}
            h1 {{
                color: #1e293b;
                margin-bottom: 24px;
                font-size: 32px;
                background: linear-gradient(135deg, #7fbf55 0%, #2665a0 100%);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-clip: text;
            }}
            .info-card {{
                background: #f8fafc;
                border: 1px solid #e2e8f0;
                border-radius: 12px;
                padding: 24px;
                margin-bottom: 24px;
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
                color: #64748b;
            }}
            .info-value {{
                color: #1e293b;
                font-weight: 500;
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
                padding: 14px 24px;
                background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
                color: white;
                border: none;
                border-radius: 10px;
                font-size: 16px;
                font-weight: 600;
                cursor: pointer;
                transition: all 0.3s;
                text-decoration: none;
                display: inline-block;
                text-align: center;
                box-shadow: 0 4px 15px rgba(99, 102, 241, 0.3);
            }}
            .btn:hover {{
                transform: translateY(-3px);
                box-shadow: 0 8px 25px rgba(99, 102, 241, 0.4);
            }}
            .btn-success {{
                background: linear-gradient(135deg, #10b981 0%, #059669 100%);
                box-shadow: 0 4px 15px rgba(16, 185, 129, 0.3);
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
                background: #e0e0e0;
                display: flex;
                align-items: center;
                justify-content: center;
                margin-right: 15px;
                font-size: 14px;
            }}
            .step.active .step-icon {{
                background: #6366f1;
                color: white;
                animation: pulse 1.5s infinite;
            }}
            .step.completed .step-icon {{
                background: #10b981;
                color: white;
            }}
            @keyframes pulse {{
                0% {{ transform: scale(1); }}
                50% {{ transform: scale(1.1); }}
                100% {{ transform: scale(1); }}
            }}
            .code-block {{
                background: #2d2d2d;
                color: #f8f8f2;
                padding: 20px;
                border-radius: 8px;
                margin: 20px 0;
                font-family: 'Courier New', monospace;
                font-size: 14px;
                overflow-x: auto;
                max-height: 400px;
                overflow-y: auto;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🐳 중앙서버 Docker 설치</h1>
            
            <div class="info-card">
                <div class="info-row">
                    <span class="info-label">서버 IP:</span>
                    <span class="info-value">{metadata.get('server_ip', '192.168.0.88')}</span>
                </div>
                <div class="info-row">
                    <span class="info-label">API 포트:</span>
                    <span class="info-value">{metadata.get('api_port', 8000)}</span>
                </div>
                <div class="info-row">
                    <span class="info-label">FL 서버 포트:</span>
                    <span class="info-value">{metadata.get('fl_port', 5002)}</span>
                </div>
                <div class="info-row">
                    <span class="info-label">대시보드 포트:</span>
                    <span class="info-value">{metadata.get('dashboard_port', 5000)}</span>
                </div>
            </div>
            
            <div class="steps" id="steps">
                <div class="step" id="step1">
                    <div class="step-icon">1</div>
                    <span>중앙서버 등록 중...</span>
                </div>
                <div class="step" id="step2">
                    <div class="step-icon">2</div>
                    <span>Docker Compose 설정 생성 중...</span>
                </div>
                <div class="step" id="step3">
                    <div class="step-icon">3</div>
                    <span>설치 스크립트 생성 중...</span>
                </div>
            </div>
            
            <div class="status" id="statusSection">
                <div class="status-icon">⏳</div>
                <p>아래 버튼을 클릭하여 Docker 설정을 생성하세요</p>
            </div>
            
            <button class="btn" id="startBtn" onclick="startInstallation()">Docker 설정 생성</button>
            
            <div id="result" style="display: none; margin-top: 30px;">
                <h2 style="color: #28a745; margin-bottom: 20px;">✅ Docker 설정 준비 완료!</h2>
                
                <div class="info-card">
                    <div class="info-row">
                        <span class="info-label">서버 주소:</span>
                        <span class="info-value">{metadata.get('server_ip', '192.168.0.88')}</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">상태:</span>
                        <span class="info-value" style="color: #10b981; font-weight: 600;">설정 완료</span>
                    </div>
                </div>
                
                <div style="margin: 24px 0; padding: 20px; background: #dcfce7; border: 1px solid #bbf7d0; border-radius: 12px;">
                    <h4 style="color: #14532d; margin-bottom: 12px; font-size: 18px;">🚀 간단한 Docker 실행</h4>
                    <p style="color: #166534; font-size: 14px; line-height: 1.8; margin-bottom: 15px;">
                        아래 BAT 파일을 다운로드하여 실행하면 <strong>중앙서버가 자동으로 시작</strong>됩니다.
                    </p>
                    <button class="btn" onclick="downloadDockerRunner()" style="width: 100%; background: linear-gradient(135deg, #0891b2 0%, #06b6d4 100%); box-shadow: 0 4px 15px rgba(6, 182, 212, 0.3);">
                        🐳 Docker 실행 파일 다운로드
                    </button>
                </div>
                
                
                <div style="margin-top: 24px; padding: 20px; background: #eff6ff; border: 1px solid #dbeafe; border-radius: 12px;">
                    <p style="color: #1e40af; font-size: 14px; line-height: 1.6;">
                        <strong>실행 순서:</strong><br>
                        1. 위 BAT 파일을 다운로드하여 실행<br>
                        2. Docker Desktop이 자동으로 확인/시작됨<br>
                        3. Docker Compose로 중앙서버 컨테이너 실행<br>
                        4. 서비스 접속: http://{metadata.get('server_ip', '192.168.0.88')}:8000
                    </p>
                </div>
            </div>
        </div>
        
        <script>
            let installData = null;
            
            async function startInstallation() {{
                const btn = document.getElementById('startBtn');
                btn.disabled = true;
                btn.textContent = '설치 진행 중...';
                
                await updateStep(1, true);
                
                try {{
                    const response = await fetch('/central/process-installation/{token}', {{
                        method: 'POST'
                    }});
                    
                    if (!response.ok) {{
                        throw new Error('설치 실패');
                    }}
                    
                    installData = await response.json();
                    
                    for (let i = 1; i <= 3; i++) {{
                        await updateStep(i, i === 1, true);
                        if (i < 3) {{
                            await updateStep(i + 1, true);
                            await new Promise(r => setTimeout(r, 500));
                        }}
                    }}
                    
                    showResult(installData);
                    
                }} catch (error) {{
                    alert('설치 중 오류 발생: ' + error.message);
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
                document.getElementById('result').style.display = 'block';
                const statusIcon = document.querySelector('.status-icon');
                const statusText = document.querySelector('#statusSection p');
                if (statusIcon) statusIcon.textContent = '✅';
                if (statusText) statusText.textContent = 'Docker 설정이 준비되었습니다!';
                document.getElementById('startBtn').style.display = 'none';
            }}
            
            
            function downloadDockerRunner() {{
                window.location.href = '/central/docker-runner/{qr_token.node_id}';
            }}
            
        </script>
    </body>
    </html>
    """
    
    return HTMLResponse(content=html_content)

@router.post("/central/process-installation/{token}")
async def process_central_installation(
    token: str,
    db: Session = Depends(get_db)
):
    """중앙서버 Docker 설정 처리 (VPN 없음)"""
    
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
        # 노드 정보 업데이트 (VPN 없이)
        node.status = "registered"
        node.updated_at = datetime.now(timezone.utc)
        
        # Docker 환경변수 업데이트 (기존 값 유지)
        metadata = json.loads(node.docker_env_vars) if node.docker_env_vars else {}
        # server_ip가 이미 저장되어 있으므로 그대로 사용
        node.docker_env_vars = json.dumps(metadata)
        
        # 토큰을 사용됨으로 표시
        qr_token.used = True
        db.commit()
        
        # Docker 실행 스크립트만 생성
        docker_runner = generate_central_docker_runner(node)
        
        return {
            "status": "success",
            "node_id": node.node_id,
            "docker_runner": docker_runner,
            "install_script": docker_runner  # Docker runner를 설치 스크립트로 사용
        }
        
    except Exception as e:
        logger.error(f"Installation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/central/status/{node_id}")
async def get_central_status(node_id: str, db: Session = Depends(get_db)):
    """중앙서버 상태 조회"""
    node = db.query(Node).filter(Node.node_id == node_id).first()
    
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    
    metadata = json.loads(node.docker_env_vars) if node.docker_env_vars else {}
    
    return {
        "node_id": node.node_id,
        "status": node.status,
        "lan_ip": node.vpn_ip,  # LAN IP (vpn_ip 필드 재사용)
        "description": node.description,
        "ports": {
            "api": metadata.get('api_port', 8000),
            "fl": metadata.get('fl_port', 5002),
            "dashboard": metadata.get('dashboard_port', 5000),
            "db": metadata.get('db_port', 5432),
            "mongo": metadata.get('mongo_port', 27017)
        },
        "created_at": node.created_at,
        "updated_at": node.updated_at
    }