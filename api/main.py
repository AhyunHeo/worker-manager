from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy.exc import OperationalError
from typing import List, Optional
import os
import time
import logging

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)

logger = logging.getLogger(__name__)

from database import SessionLocal, engine, Base
from models import Node, NodeCreate, NodeResponse, NodeStatus
from worker_integration import router as worker_router
from central.routes import router as central_router

# DB 연결 재시도 함수
def wait_for_db(max_retries=30):
    """데이터베이스 연결이 준비될 때까지 대기"""
    for i in range(max_retries):
        try:
            conn = engine.connect()
            conn.close()
            logger.info("Database connected successfully!")
            return True
        except OperationalError:
            logger.info(f"Waiting for database... ({i+1}/{max_retries})")
            time.sleep(2)
    raise Exception("Could not connect to database after 30 attempts")

# DB 연결 대기
wait_for_db()

# 데이터베이스 초기화
Base.metadata.create_all(bind=engine)
logger.info("Database tables created")

# 마이그레이션: vpn_ip UNIQUE 제약조건 제거
try:
    from sqlalchemy import text, inspect
    with engine.connect() as conn:
        # 인덱스 정보 확인
        inspector = inspect(engine)
        indexes = inspector.get_indexes('nodes')

        # ix_nodes_vpn_ip가 UNIQUE인지 확인
        vpn_ip_index = next((idx for idx in indexes if idx['name'] == 'ix_nodes_vpn_ip'), None)

        if vpn_ip_index and vpn_ip_index.get('unique', False):
            logger.info("Removing UNIQUE constraint from vpn_ip column...")

            # UNIQUE 인덱스 삭제
            conn.execute(text("DROP INDEX IF EXISTS ix_nodes_vpn_ip"))
            conn.commit()

            # 일반 인덱스로 재생성
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_nodes_vpn_ip ON nodes(vpn_ip)"))
            conn.commit()

            logger.info("✓ Migration completed: vpn_ip UNIQUE constraint removed")
        else:
            logger.info("vpn_ip column already configured correctly (no UNIQUE constraint)")
except Exception as e:
    logger.warning(f"Migration check failed (this is normal on first run): {e}")

app = FastAPI(
    title="Worker Manager API",
    description="워커 노드 환경 설정 및 컨테이너 배포 시스템",
    version="1.0.0"
)

# Worker Integration 라우터 포함
app.include_router(worker_router, tags=["worker-integration"])

# Central Server 라우터 포함
app.include_router(central_router, tags=["central-server"])

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 보안
security = HTTPBearer()
API_TOKEN = os.getenv("API_TOKEN", "test-token-123")

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """API 토큰 검증"""
    if credentials.credentials != API_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token"
        )
    return credentials.credentials

def get_db():
    """데이터베이스 세션 생성"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/")
async def root():
    """루트 엔드포인트"""
    return {
        "message": "Worker Manager API",
        "version": "1.0.0",
        "docs": "/docs"
    }

@app.get("/health")
async def health_check():
    """헬스 체크"""
    return {"status": "healthy"}

# ==================== 노드 관리 ====================

@app.post("/nodes", response_model=NodeResponse)
async def create_node(
    node: NodeCreate,
    db: Session = Depends(get_db),
    token: str = Depends(verify_token)
):
    """새 워커 노드 등록"""
    try:
        db_node = Node(
            name=node.name,
            description=node.description,
            status=NodeStatus.PENDING
        )
        db.add(db_node)
        db.commit()
        db.refresh(db_node)
        logger.info(f"Node created: {db_node.id} - {db_node.name}")
        return db_node
    except Exception as e:
        logger.error(f"Failed to create node: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/nodes", response_model=List[NodeResponse])
async def list_nodes(
    db: Session = Depends(get_db),
    token: str = Depends(verify_token)
):
    """모든 노드 목록 조회"""
    nodes = db.query(Node).all()
    return nodes

@app.get("/nodes/{node_id}", response_model=NodeResponse)
async def get_node(
    node_id: str,
    db: Session = Depends(get_db),
    token: str = Depends(verify_token)
):
    """특정 노드 상세 정보"""
    node = db.query(Node).filter(Node.id == node_id).first()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    return node

@app.put("/nodes/{node_id}", response_model=NodeResponse)
async def update_node(
    node_id: str,
    node_update: NodeCreate,
    db: Session = Depends(get_db),
    token: str = Depends(verify_token)
):
    """노드 정보 업데이트"""
    node = db.query(Node).filter(Node.id == node_id).first()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")

    node.name = node_update.name
    node.description = node_update.description
    db.commit()
    db.refresh(node)
    return node

@app.delete("/nodes/{node_id}")
async def delete_node(
    node_id: str,
    db: Session = Depends(get_db),
    token: str = Depends(verify_token)
):
    """노드 삭제"""
    node = db.query(Node).filter(Node.id == node_id).first()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")

    db.delete(node)
    db.commit()
    return {"message": "Node deleted successfully"}

@app.post("/nodes/{node_id}/status")
async def update_node_status(
    node_id: str,
    status_update: dict,
    db: Session = Depends(get_db),
    token: str = Depends(verify_token)
):
    """노드 상태 업데이트"""
    node = db.query(Node).filter(Node.id == node_id).first()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")

    new_status = status_update.get("status")
    if new_status:
        try:
            node.status = NodeStatus(new_status)
            db.commit()
            db.refresh(node)
            logger.info(f"Node {node_id} status updated to {new_status}")
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid status value")

    return node

# ==================== 워커 설정 및 배포 ====================
# 워커 설정 관련 엔드포인트는 web-dashboard와 gui 모듈에서 처리

@app.get("/stats")
async def get_stats(
    db: Session = Depends(get_db),
    token: str = Depends(verify_token)
):
    """시스템 통계"""
    total_nodes = db.query(Node).count()
    active_nodes = db.query(Node).filter(Node.status == NodeStatus.ACTIVE).count()
    pending_nodes = db.query(Node).filter(Node.status == NodeStatus.PENDING).count()
    failed_nodes = db.query(Node).filter(Node.status == NodeStatus.FAILED).count()

    return {
        "total_nodes": total_nodes,
        "active_nodes": active_nodes,
        "pending_nodes": pending_nodes,
        "failed_nodes": failed_nodes
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8090)
