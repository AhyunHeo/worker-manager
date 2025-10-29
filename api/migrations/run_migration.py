#!/usr/bin/env python3
"""
Database Migration Script
vpn_ip 컬럼의 UNIQUE 제약조건 제거
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

    migration_file = Path(__file__).parent / "remove_vpn_ip_unique.sql"

    print("=" * 60)
    print("Database Migration: Remove vpn_ip UNIQUE constraint")
    print("=" * 60)
    print()

    # SQL 파일 읽기
    with open(migration_file, 'r', encoding='utf-8') as f:
        sql_content = f.read()

    # SQL 명령어 분리 (세미콜론 기준)
    sql_commands = [cmd.strip() for cmd in sql_content.split(';') if cmd.strip() and not cmd.strip().startswith('--')]

    try:
        with engine.connect() as conn:
            print("Executing migration...")
            print()

            for i, cmd in enumerate(sql_commands, 1):
                if cmd:
                    print(f"[{i}/{len(sql_commands)}] Executing:")
                    print(f"  {cmd[:80]}..." if len(cmd) > 80 else f"  {cmd}")

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
                            print("  (no results)")
                    else:
                        print("  ✓ Success")
                    print()

        print("=" * 60)
        print("✅ Migration completed successfully!")
        print("=" * 60)
        print()
        print("The vpn_ip column no longer has UNIQUE constraint.")
        print("Multiple nodes can now have the same LAN IP address.")

    except Exception as e:
        print("=" * 60)
        print("❌ Migration failed!")
        print("=" * 60)
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    run_migration()
