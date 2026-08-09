#!/usr/bin/env python3
"""Database Performance Optimization Script"""

import sqlite3
import time
from pathlib import Path

DB_PATH = "data/climber.db"

def analyze_database():
    """Analyze current database structure and create optimized indexes"""
    print("="*80)
    print("DATABASE OPTIMIZATION SCRIPT")
    print("="*80)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Get existing tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [row[0] for row in cursor.fetchall()]
    print(f"\nFound {len(tables)} tables: {tables}")

    # Analyze existing indexes
    print("\n--- Existing Indexes ---")
    for table in tables[:10]:  # Limit to first 10 tables
        try:
            cursor.execute(f"PRAGMA index_list({table});")
            indexes = cursor.fetchall()
            if indexes:
                print(f"\nTable '{table}':")
                for idx in indexes:
                    print(f"  - {idx[1]} ({'unique' if idx[2] else 'regular'})")

            # Get column info for common columns
            cursor.execute(f"PRAGMA index_info({table}_id);")
            cols = cursor.fetchall()
            if not cols and f"{table}_idx" in [i[1] for i in indexes]:
                pass
        except Exception as e:
            print(f"Error analyzing {table}: {e}")

    # Create optimization indexes
    print("\n--- Creating Optimization Indexes ---")

    optimization_indexes = [
        # Agent/Session related
        ("CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id)", "Sessions by user"),
        ("CREATE INDEX IF NOT EXISTS idx_sessions_agent_id ON sessions(agent_id)", "Sessions by agent"),
        ("CREATE INDEX IF NOT EXISTS idx_sessions_status ON sessions(status)", "Sessions by status"),
        ("CREATE INDEX IF NOT EXISTS idx_agents_user_id ON agents(user_id)", "Agents by user"),
        ("CREATE INDEX IF NOT EXISTS idx_agents_is_active ON agents(is_active)", "Active agents"),

        # Tasks related
        ("CREATE INDEX IF NOT EXISTS idx_tasks_user_id ON tasks(user_id)", "Tasks by user"),
        ("CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status)", "Tasks by status"),
        ("CREATE INDEX IF NOT EXISTS idx_tasks_created_at ON tasks(created_at)", "Tasks by date"),

        # Crews related
        ("CREATE INDEX IF NOT EXISTS idx_crews_user_id ON crews(user_id)", "Crews by user"),
        ("CREATE INDEX IF NOT EXISTS idx_crews_is_active ON crews(is_active)", "Active crews"),

        # Settings and cache
        ("CREATE INDEX IF NOT EXISTS idx_settings_key ON settings(key)", "Settings by key"),
        ("CREATE INDEX IF NOT EXISTS idx_cache_key ON cache_items(key)", "Cache by key"),
        ("CREATE INDEX IF NOT EXISTS idx_cache_expires ON cache_items(expires_at)", "Cache expiration"),
    ]

    created_count = 0
    for sql, description in optimization_indexes:
        try:
            cursor.execute(sql)
            conn.commit()
            print(f"  ✓ Created: {description}")
            created_count += 1
        except Exception:
            print(f"  ⚠ Skipped (may exist): {description}")

    # Run VACUUM for optimization
    print("\n--- Optimizing Database ---")
    start = time.time()
    cursor.execute("VACUUM;")
    conn.commit()
    duration = time.time() - start
    print(f"  ✓ VACUUM completed in {duration:.2f}s")

    # Run ANALYZE for query planner optimization
    print("\n--- Running Query Planner Analysis ---")
    start = time.time()
    cursor.execute("ANALYZE;")
    conn.commit()
    duration = time.time() - start
    print(f"  ✓ ANALYZE completed in {duration:.2f}s")

    # Check database size
    file_size = Path(DB_PATH).stat().st_size
    print("\n--- Database Statistics ---")
    print(f"  File Size: {file_size / 1024 / 1024:.2f} MB")
    print(f"  Tables: {len(tables)}")
    print(f"  Indexes Created/Updated: {created_count}")

    conn.close()

    return created_count

if __name__ == "__main__":
    create_count = analyze_database()
    print(f"\n✓ Database optimization complete! Created {create_count} indexes.")
