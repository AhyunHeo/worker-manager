#!/usr/bin/env python3
"""
Database Migration Script
nodes 테이블에 owner_id 컬럼 추가
"""

import os
import sys
from pathlib import Path

# 상위 디렉토리를 Python 경로에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from database import engine
from sqlalchemy import text

def run_migration():
    """마이그레이션 실행"""

    migration_file = Path(__file__).parent / "add_owner_id.sql"

    print("=" * 60)
    print("Database Migration: Add owner_id column to nodes table")
    print("=" * 60)
    print()

    # SQL 파일 읽기
    with open(migration_file, 'r', encoding='utf-8') as f:
        sql_content = f.read()

    # SQL 명령어 분리 (세미콜론 기준, DO $$ 블록은 통째로)
    # PostgreSQL DO 블록 처리
    sql_commands = []

    # DO $$ ... $$ 블록 찾기
    if 'DO $$' in sql_content:
        parts = sql_content.split('DO $$')
        for i, part in enumerate(parts):
            if i == 0:
                # DO $$ 이전 부분
                cmds = [cmd.strip() for cmd in part.split(';') if cmd.strip() and not cmd.strip().startswith('--')]
                sql_commands.extend(cmds)
            else:
                # DO $$ 블록 처리
                if '$$;' in part:
                    do_block, rest = part.split('$$;', 1)
                    sql_commands.append(f"DO $${do_block}$$")
                    # 나머지 부분 처리
                    cmds = [cmd.strip() for cmd in rest.split(';') if cmd.strip() and not cmd.strip().startswith('--')]
                    sql_commands.extend(cmds)
    else:
        sql_commands = [cmd.strip() for cmd in sql_content.split(';') if cmd.strip() and not cmd.strip().startswith('--')]

    try:
        with engine.connect() as conn:
            print("Executing migration...")
            print()

            for i, cmd in enumerate(sql_commands, 1):
                if cmd:
                    print(f"[{i}/{len(sql_commands)}] Executing:")
                    display_cmd = cmd[:100] + "..." if len(cmd) > 100 else cmd
                    print(f"  {display_cmd}")

                    result = conn.execute(text(cmd))
                    conn.commit()

                    # SELECT 결과 출력
                    if cmd.strip().upper().startswith('SELECT'):
                        rows = result.fetchall()
                        if rows:
                            print("  Result:")
                            for row in rows:
                                print(f"    {row}")
                        else:
                            print("  (no results - column may not exist yet)")
                    else:
                        print("  Done")
                    print()

        print("=" * 60)
        print("Migration completed successfully!")
        print("=" * 60)
        print()
        print("The owner_id column has been added to the nodes table.")

    except Exception as e:
        print("=" * 60)
        print("Migration failed!")
        print("=" * 60)
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    run_migration()
