#!/usr/bin/env python3
"""
Auto Migration Manager
서버 시작 시 자동으로 마이그레이션 실행
이미 적용된 마이그레이션은 건너뜀
"""

import os
import sys
from pathlib import Path
from datetime import datetime

# 상위 디렉토리를 Python 경로에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from database import engine
from sqlalchemy import text
import logging

logger = logging.getLogger(__name__)

# 마이그레이션 목록 (순서대로 실행)
MIGRATIONS = [
    {
        "name": "001_remove_vpn_ip_unique",
        "description": "Remove UNIQUE constraint from vpn_ip column",
        "sql_file": "remove_vpn_ip_unique.sql"
    },
    {
        "name": "002_add_owner_id",
        "description": "Add owner_id column to nodes table",
        "sql_file": "add_owner_id.sql"
    },
]


def ensure_migration_table(conn):
    """마이그레이션 히스토리 테이블 생성"""
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS _migrations (
            id SERIAL PRIMARY KEY,
            name VARCHAR(255) UNIQUE NOT NULL,
            description TEXT,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """))
    conn.commit()


def is_migration_applied(conn, name: str) -> bool:
    """마이그레이션이 이미 적용되었는지 확인"""
    result = conn.execute(
        text("SELECT 1 FROM _migrations WHERE name = :name"),
        {"name": name}
    )
    return result.fetchone() is not None


def mark_migration_applied(conn, name: str, description: str):
    """마이그레이션 적용 완료 기록"""
    conn.execute(
        text("INSERT INTO _migrations (name, description) VALUES (:name, :desc)"),
        {"name": name, "desc": description}
    )
    conn.commit()


def execute_sql_file(conn, sql_file: Path):
    """SQL 파일 실행"""
    with open(sql_file, 'r', encoding='utf-8') as f:
        sql_content = f.read()

    # PostgreSQL DO 블록 처리
    sql_commands = []

    if 'DO $$' in sql_content:
        parts = sql_content.split('DO $$')
        for i, part in enumerate(parts):
            if i == 0:
                cmds = [cmd.strip() for cmd in part.split(';') if cmd.strip() and not cmd.strip().startswith('--')]
                sql_commands.extend(cmds)
            else:
                if '$$;' in part:
                    do_block, rest = part.split('$$;', 1)
                    sql_commands.append(f"DO $${do_block}$$")
                    cmds = [cmd.strip() for cmd in rest.split(';') if cmd.strip() and not cmd.strip().startswith('--')]
                    sql_commands.extend(cmds)
    else:
        sql_commands = [cmd.strip() for cmd in sql_content.split(';') if cmd.strip() and not cmd.strip().startswith('--')]

    for cmd in sql_commands:
        if cmd:
            try:
                conn.execute(text(cmd))
                conn.commit()
            except Exception as e:
                # 일부 명령어 실패는 무시 (예: 이미 존재하는 인덱스 삭제 시도)
                logger.warning(f"SQL command warning: {e}")
                conn.rollback()


def run_auto_migrations(verbose: bool = True):
    """모든 마이그레이션 자동 실행"""
    migrations_dir = Path(__file__).parent

    if verbose:
        print("=" * 60)
        print("Auto Migration Manager")
        print("=" * 60)
        print()

    try:
        with engine.connect() as conn:
            # 마이그레이션 테이블 생성
            ensure_migration_table(conn)

            applied_count = 0
            skipped_count = 0

            for migration in MIGRATIONS:
                name = migration["name"]
                description = migration["description"]
                sql_file = migrations_dir / migration["sql_file"]

                if is_migration_applied(conn, name):
                    if verbose:
                        print(f"[SKIP] {name}: Already applied")
                    skipped_count += 1
                    continue

                if not sql_file.exists():
                    if verbose:
                        print(f"[WARN] {name}: SQL file not found ({sql_file})")
                    continue

                if verbose:
                    print(f"[RUN]  {name}: {description}")

                try:
                    execute_sql_file(conn, sql_file)
                    mark_migration_applied(conn, name, description)
                    applied_count += 1
                    if verbose:
                        print(f"       -> Applied successfully")
                except Exception as e:
                    logger.error(f"Migration {name} failed: {e}")
                    if verbose:
                        print(f"       -> FAILED: {e}")
                    raise

            if verbose:
                print()
                print("=" * 60)
                print(f"Migrations complete: {applied_count} applied, {skipped_count} skipped")
                print("=" * 60)

            return applied_count, skipped_count

    except Exception as e:
        logger.error(f"Auto migration failed: {e}")
        if verbose:
            print(f"Migration error: {e}")
        raise


def check_and_apply_owner_id():
    """owner_id 컬럼만 확인하고 추가하는 간단한 함수 (SQLite 호환)"""
    try:
        with engine.connect() as conn:
            # 컬럼 존재 여부 확인 (PostgreSQL)
            result = conn.execute(text("""
                SELECT column_name FROM information_schema.columns
                WHERE table_name = 'nodes' AND column_name = 'owner_id'
            """))

            if result.fetchone() is None:
                # 컬럼 추가
                conn.execute(text("ALTER TABLE nodes ADD COLUMN owner_id VARCHAR(255)"))
                conn.commit()
                logger.info("Added owner_id column to nodes table")
                return True
            else:
                logger.info("owner_id column already exists")
                return False

    except Exception as e:
        logger.error(f"Failed to add owner_id column: {e}")
        return False


if __name__ == "__main__":
    run_auto_migrations(verbose=True)
