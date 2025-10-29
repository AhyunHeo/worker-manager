from sqlalchemy import Column, String, DateTime, Text, Boolean, Integer
from sqlalchemy.sql import func
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

from database import Base

# SQLAlchemy 모델
class Node(Base):
    """노드 정보 DB 모델"""
    __tablename__ = "nodes"

    node_id = Column(String, primary_key=True, index=True)
    node_type = Column(String)  # central, worker
    hostname = Column(String)
    public_ip = Column(String)
    vpn_ip = Column(String, index=True, nullable=True)  # 실제로는 LAN IP 저장 (호환성 위해 필드명 유지, UNIQUE 제거 - 같은 LAN에 여러 노드 가능)
    status = Column(String, default="registered")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # 워커노드 플랫폼 관련 필드
    description = Column(String)  # 워커노드 설명 (예: "2080-test")
    central_server_url = Column(String)  # 중앙서버 공개 URL (예: http://192.168.0.88:8000)
    docker_env_vars = Column(Text)  # Docker Compose 환경변수 저장

class QRToken(Base):
    """QR 코드 토큰 저장"""
    __tablename__ = "qr_tokens"
    
    token = Column(String, primary_key=True, index=True)
    node_id = Column(String, nullable=False)
    node_type = Column(String, default="worker")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False)
    used = Column(Boolean, default=False)

# Pydantic 모델
class NodeCreate(BaseModel):
    """노드 생성 요청 모델"""
    node_id: str = Field(..., description="노드 고유 ID")
    node_type: str = Field(..., description="노드 타입 (central/worker)")
    hostname: str = Field(..., description="호스트명")
    public_ip: Optional[str] = Field(None, description="공인 IP (선택)")
    description: Optional[str] = Field(None, description="워커노드 설명")
    central_server_url: Optional[str] = Field(None, description="중앙서버 공개 URL")

    class Config:
        schema_extra = {
            "example": {
                "node_id": "NODE-20250710-865",
                "node_type": "worker",
                "hostname": "worker01.example.com",
                "public_ip": "203.0.113.1",
                "description": "2080-test",
                "central_server_url": "http://192.168.0.88:8000"
            }
        }

class NodeResponse(BaseModel):
    """노드 등록 응답 모델"""
    node_id: str
    lan_ip: Optional[str] = None  # 워커의 LAN IP
    status: str
    description: Optional[str] = None
    central_server_url: Optional[str] = None

    class Config:
        schema_extra = {
            "example": {
                "node_id": "worker-node-1",
                "lan_ip": "192.168.0.100",
                "status": "registered",
                "description": "Worker Node 1",
                "central_server_url": "http://192.168.0.88:8000"
            }
        }

class NodeStatus(BaseModel):
    """노드 상태 정보 모델"""
    node_id: str
    node_type: str
    hostname: str
    public_ip: Optional[str]
    lan_ip: Optional[str]  # 워커의 LAN IP
    status: str
    description: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        schema_extra = {
            "example": {
                "node_id": "worker-node-1",
                "node_type": "worker",
                "hostname": "worker01.example.com",
                "public_ip": "203.0.113.1",
                "lan_ip": "192.168.0.100",
                "status": "registered",
                "description": "Worker Node 1",
                "created_at": "2024-01-01T10:00:00Z",
                "updated_at": "2024-01-01T12:00:00Z"
            }
        }