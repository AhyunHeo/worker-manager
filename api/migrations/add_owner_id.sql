-- Add owner_id column to nodes table
-- 노드 소유자 ID를 저장하기 위한 컬럼 추가

-- PostgreSQL: owner_id 컬럼 추가 (이미 존재하면 무시)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'nodes' AND column_name = 'owner_id'
    ) THEN
        ALTER TABLE nodes ADD COLUMN owner_id VARCHAR(255);
        RAISE NOTICE 'owner_id column added successfully';
    ELSE
        RAISE NOTICE 'owner_id column already exists, skipping';
    END IF;
END $$;

-- 확인
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'nodes' AND column_name = 'owner_id';
