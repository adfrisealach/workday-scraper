#!/usr/bin/env python3
import os
import sqlite3
import logging
from datetime import datetime
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def get_db_path():
    """Get database path from environment or use default"""
    db_path = os.environ.get('DB_FILE', 'data/workday_jobs.db')
    return os.path.abspath(db_path)

def backup_database(db_path):
    """Create a backup of the database before migration"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = f"{db_path}.backup_{timestamp}"
    
    try:
        import shutil
        shutil.copy2(db_path, backup_path)
        logger.info(f"Created database backup at {backup_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to create backup: {e}")
        return False

def column_exists(cursor, table, column):
    """Check if a column exists in a table"""
    cursor.execute(f"PRAGMA table_info({table})")
    columns = [info[1] for info in cursor.fetchall()]
    return column in columns

def table_exists(cursor, table):
    """Check if a table exists in the database"""
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
    return cursor.fetchone() is not None

def index_exists(cursor, index_name):
    """Check if an index exists in the database"""
    cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name=?", (index_name,))
    return cursor.fetchone() is not None

def run_migration_001(db_path):
    """Run the 001_add_job_status migration with column existence checks"""
    try:
        # Connect to database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Start transaction
        cursor.execute('BEGIN')

        try:
            # 1. Add status column if it doesn't exist
            if not column_exists(cursor, 'jobs', 'status'):
                cursor.execute("ALTER TABLE jobs ADD COLUMN status TEXT DEFAULT 'active'")
                logger.info("Added status column to jobs table")
            else:
                logger.info("Status column already exists in jobs table")

            # 2. Add last_seen column if it doesn't exist
            if not column_exists(cursor, 'jobs', 'last_seen'):
                cursor.execute("ALTER TABLE jobs ADD COLUMN last_seen TEXT")
                logger.info("Added last_seen column to jobs table")
            else:
                logger.info("last_seen column already exists in jobs table")

            # 3. Add missed_scrapes column if it doesn't exist
            if not column_exists(cursor, 'jobs', 'missed_scrapes'):
                cursor.execute("ALTER TABLE jobs ADD COLUMN missed_scrapes INTEGER DEFAULT 0")
                logger.info("Added missed_scrapes column to jobs table")
            else:
                logger.info("missed_scrapes column already exists in jobs table")

            # 4. Create job_status_history table if it doesn't exist
            if not table_exists(cursor, 'job_status_history'):
                cursor.execute("""
                CREATE TABLE job_status_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id INTEGER,
                    status TEXT NOT NULL,
                    changed_at TEXT NOT NULL,
                    reason TEXT,
                    FOREIGN KEY (job_id) REFERENCES jobs (id)
                )
                """)
                logger.info("Created job_status_history table")
            else:
                logger.info("job_status_history table already exists")

            # 5. Create index on job_id in status history table if it doesn't exist
            if not index_exists(cursor, 'idx_status_history_job_id'):
                cursor.execute("CREATE INDEX idx_status_history_job_id ON job_status_history (job_id)")
                logger.info("Created index on job_id in job_status_history table")
            else:
                logger.info("Index on job_id in job_status_history table already exists")

            # 6. Create index on status in jobs table if it doesn't exist
            if not index_exists(cursor, 'idx_jobs_status'):
                cursor.execute("CREATE INDEX idx_jobs_status ON jobs (status)")
                logger.info("Created index on status in jobs table")
            else:
                logger.info("Index on status in jobs table already exists")

            # 7. Initialize last_seen for existing jobs if needed
            cursor.execute("UPDATE jobs SET last_seen = created_at WHERE last_seen IS NULL")
            logger.info("Initialized last_seen for existing jobs")

            # 8. Add entries to status history for existing jobs that don't have entries yet
            cursor.execute("""
            INSERT INTO job_status_history (job_id, status, changed_at, reason)
            SELECT id, 'active', created_at, 'Initial migration'
            FROM jobs
            WHERE id NOT IN (SELECT job_id FROM job_status_history WHERE job_id IS NOT NULL)
            """)
            logger.info("Added status history entries for existing jobs")

            # Commit transaction
            conn.commit()
            logger.info("Migration completed successfully")
            return True

        except Exception as e:
            # Rollback on error
            conn.rollback()
            logger.error(f"Migration failed: {e}")
            return False

        finally:
            conn.close()

    except Exception as e:
        logger.error(f"Error during migration: {e}")
        return False

def main():
    # Get database path
    db_path = get_db_path()
    if not os.path.exists(db_path):
        logger.error(f"Database file not found: {db_path}")
        return False

    # Create backup
    if not backup_database(db_path):
        logger.error("Migration aborted due to backup failure")
        return False

    # Run migration
    if run_migration_001(db_path):
        logger.info("Migration completed successfully")
        return True
    else:
        logger.error("Migration failed")
        return False

if __name__ == '__main__':
    success = main()
    exit(0 if success else 1)