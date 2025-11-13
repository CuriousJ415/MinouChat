"""
Consolidation migration: Add missing fields from chat.py models
to canonical database models.

This migration adds columns that were in api/models/chat.py but missing
from database/models.py, ensuring backward compatibility.

Run with: python src/miachat/database/migrations/consolidate_models.py
"""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from sqlalchemy import text, inspect, create_engine
from pathlib import Path
import os

# Determine database path
# This file is at: src/miachat/database/migrations/consolidate_models.py
# Project root is 4 levels up, then down to data/
script_path = Path(__file__).resolve()
project_root = script_path.parent.parent.parent.parent.parent  # Go up to MiaChat/
db_path = project_root / "data" / "memories.db"

# Create engine directly with local path
database_url = f"sqlite:///{db_path}"
engine = create_engine(
    database_url,
    connect_args={"check_same_thread": False}
)

print(f"📂 Using database: {db_path}")
print(f"   Exists: {db_path.exists()}")
print()

def check_column_exists(connection, table_name: str, column_name: str) -> bool:
    """Check if a column exists in a table."""
    result = connection.execute(text(f"""
        SELECT COUNT(*) as count
        FROM pragma_table_info('{table_name}')
        WHERE name = '{column_name}'
    """))
    return result.fetchone()[0] > 0

def upgrade():
    """Add missing columns to conversations and messages tables."""
    print("=" * 60)
    print("MiaChat Database Consolidation Migration")
    print("=" * 60)
    print()

    changes_made = []

    with engine.connect() as conn:
        # Transaction for safety
        with conn.begin():
            print("📊 Checking conversations table...")

            # Add title column
            if not check_column_exists(conn, 'conversations', 'title'):
                print("  ➕ Adding 'title' column...")
                conn.execute(text("""
                    ALTER TABLE conversations
                    ADD COLUMN title VARCHAR
                """))
                changes_made.append("Added 'title' column to conversations")
            else:
                print("  ✓ 'title' column already exists")

            # Add created_at column
            if not check_column_exists(conn, 'conversations', 'created_at'):
                print("  ➕ Adding 'created_at' column...")
                conn.execute(text("""
                    ALTER TABLE conversations
                    ADD COLUMN created_at DATETIME
                """))

                # Set created_at to started_at for existing rows
                print("  🔄 Populating created_at from started_at...")
                conn.execute(text("""
                    UPDATE conversations
                    SET created_at = started_at
                    WHERE created_at IS NULL
                """))
                changes_made.append("Added 'created_at' column to conversations")
            else:
                print("  ✓ 'created_at' column already exists")

            # Add updated_at column
            if not check_column_exists(conn, 'conversations', 'updated_at'):
                print("  ➕ Adding 'updated_at' column...")
                conn.execute(text("""
                    ALTER TABLE conversations
                    ADD COLUMN updated_at DATETIME
                """))

                # Set updated_at to started_at for existing rows
                print("  🔄 Populating updated_at from started_at...")
                conn.execute(text("""
                    UPDATE conversations
                    SET updated_at = started_at
                    WHERE updated_at IS NULL
                """))
                changes_made.append("Added 'updated_at' column to conversations")
            else:
                print("  ✓ 'updated_at' column already exists")

            print()
            print("📊 Checking messages table...")

            # Add file_attachments column
            if not check_column_exists(conn, 'messages', 'file_attachments'):
                print("  ➕ Adding 'file_attachments' column...")
                conn.execute(text("""
                    ALTER TABLE messages
                    ADD COLUMN file_attachments JSON
                """))
                changes_made.append("Added 'file_attachments' column to messages")
            else:
                print("  ✓ 'file_attachments' column already exists")

    print()
    print("=" * 60)
    if changes_made:
        print("✅ Migration completed successfully!")
        print()
        print("Changes made:")
        for change in changes_made:
            print(f"  • {change}")
    else:
        print("✅ No changes needed - database already up to date!")
    print("=" * 60)

def downgrade():
    """Remove added columns (optional - use with caution!)."""
    print("⚠️  DOWNGRADE WARNING")
    print("=" * 60)
    print("SQLite doesn't support DROP COLUMN easily.")
    print("To downgrade, restore from backup:")
    print()
    print("  cp data/memories.db.backup-YYYYMMDD data/memories.db")
    print()
    print("=" * 60)

def verify():
    """Verify migration succeeded."""
    print()
    print("=" * 60)
    print("Verifying Database Schema")
    print("=" * 60)

    inspector = inspect(engine)

    print()
    print("📊 Conversations table columns:")
    columns = inspector.get_columns('conversations')
    for col in sorted(columns, key=lambda x: x['name']):
        nullable = "NULL" if col['nullable'] else "NOT NULL"
        print(f"  • {col['name']:20s} {str(col['type']):15s} {nullable}")

    print()
    print("📊 Messages table columns:")
    columns = inspector.get_columns('messages')
    for col in sorted(columns, key=lambda x: x['name']):
        nullable = "NULL" if col['nullable'] else "NOT NULL"
        print(f"  • {col['name']:20s} {str(col['type']):15s} {nullable}")

    print()
    print("=" * 60)
    print("✅ Verification complete!")
    print("=" * 60)

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Database consolidation migration')
    parser.add_argument('--verify', action='store_true', help='Verify schema after migration')
    parser.add_argument('--downgrade', action='store_true', help='Show downgrade instructions')

    args = parser.parse_args()

    if args.downgrade:
        downgrade()
    else:
        try:
            upgrade()
            if args.verify:
                verify()
            else:
                print()
                print("💡 Tip: Run with --verify flag to see final schema")
        except Exception as e:
            print()
            print(f"❌ Migration failed: {e}")
            print()
            print("To restore from backup:")
            print("  cp data/memories.db.backup-$(date +%Y%m%d) data/memories.db")
            sys.exit(1)
