-- Remove UNIQUE constraint from vpn_ip column
-- 여러 워커 노드가 같은 LAN IP를 가질 수 있도록 UNIQUE 제약조건 제거

-- UNIQUE 인덱스 삭제
DROP INDEX IF EXISTS ix_nodes_vpn_ip;

-- 일반 인덱스로 재생성 (UNIQUE 없이)
CREATE INDEX IF NOT EXISTS ix_nodes_vpn_ip ON nodes(vpn_ip);

-- 확인
SELECT indexname, indexdef
FROM pg_indexes
WHERE tablename = 'nodes' AND indexname = 'ix_nodes_vpn_ip';
