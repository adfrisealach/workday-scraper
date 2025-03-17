"""
Job status tracking functionality for the Workday Scraper.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime


class JobStatusManager:
    """Handles job status tracking operations."""

    def __init__(self, db_manager):
        """Initialize with a DatabaseManager instance."""
        if not db_manager:
            raise ValueError("DatabaseManager instance is required")
            
        if not hasattr(db_manager, 'cursor') or not db_manager.cursor:
            raise ValueError("DatabaseManager has no valid cursor")
            
        if not hasattr(db_manager, 'conn') or not db_manager.conn:
            raise ValueError("DatabaseManager has no valid connection")
            
        self.db = db_manager
        self.cursor = db_manager.cursor
        self.conn = db_manager.conn
        
        # Verify required tables exist
        try:
            self.cursor.execute("""
                SELECT COUNT(*) FROM sqlite_master
                WHERE type='table' AND name IN ('jobs', 'job_status_history')
            """)
            count = self.cursor.fetchone()[0]
            if count != 2:
                raise RuntimeError("Required tables not found. Run database migration first.")
        except Exception as e:
            raise RuntimeError(f"Error verifying database schema: {e}")

    def mark_company_jobs_as_missed(self, company_id: int) -> None:
        """Increment missed_scrapes counter for all active jobs of a company."""
        try:
            self.cursor.execute("""
                UPDATE jobs
                SET missed_scrapes = missed_scrapes + 1
                WHERE company_id = ? AND status = 'active'
            """, (company_id,))
            self.conn.commit()
        except Exception as e:
            self.conn.rollback()
            raise e

    def update_job_last_seen(self, job_id: str, company_id: int) -> None:
        """Update last_seen timestamp and reset missed_scrapes counter."""
        now = datetime.now().isoformat()
        try:
            self.cursor.execute("""
                UPDATE jobs
                SET last_seen = ?, missed_scrapes = 0
                WHERE job_id = ? AND company_id = ?
            """, (now, job_id, company_id))
            self.conn.commit()
        except Exception as e:
            self.conn.rollback()
            raise e

    def update_job_status(self, job_id: int, status: str, reason: str) -> None:
        """Update job status and record in history table."""
        now = datetime.now().isoformat()
        try:
            # Update status in jobs table
            self.cursor.execute("""
                UPDATE jobs
                SET status = ?, last_seen = ?
                WHERE id = ?
            """, (status, now, job_id))

            # Record in history table
            self.cursor.execute("""
                INSERT INTO job_status_history (job_id, status, changed_at, reason)
                VALUES (?, ?, ?, ?)
            """, (job_id, status, now, reason))

            self.conn.commit()
        except Exception as e:
            self.conn.rollback()
            raise e

    def reactivate_job(self, job_id: int) -> None:
        """Reactivate a previously closed job."""
        self.update_job_status(
            job_id,
            'active',
            'Job reappeared in listings'
        )

    def mark_stale_jobs_as_closed(self, company_id: int) -> None:
        """Mark jobs with missed_scrapes >= 2 as closed."""
        try:
            # Get jobs to close
            self.cursor.execute("""
                SELECT id 
                FROM jobs 
                WHERE company_id = ? 
                AND status = 'active' 
                AND missed_scrapes >= 2
            """, (company_id,))
            
            stale_jobs = self.cursor.fetchall()
            
            # Update each job's status
            for row in stale_jobs:
                self.update_job_status(
                    row['id'],
                    'closed',
                    'Not found in 2 consecutive scrapes'
                )
        except Exception as e:
            self.conn.rollback()
            raise e

    def get_jobs_by_status(self, status: str) -> List[Dict[str, Any]]:
        """Get all jobs with a specific status."""
        try:
            self.cursor.execute("""
                SELECT
                    j.id, j.job_id, j.title, j.description, j.date_posted,
                    j.employment_type, j.location, j.url, j.timestamp,
                    j.created_at, j.status, j.last_seen, j.missed_scrapes,
                    c.name as company_name, c.url as company_url
                FROM jobs j
                JOIN companies c ON j.company_id = c.id
                WHERE j.status = ?
                ORDER BY j.last_seen DESC NULLS LAST
            """, (status,))
            
            results = self.cursor.fetchall()
            
            jobs = []
            for row in results:
                job = dict(row)
                job['company'] = job.pop('company_name')
                jobs.append(job)
            
            return jobs
        except Exception as e:
            raise e

    def get_job_status_history(self, job_id: int) -> List[Dict[str, Any]]:
        """Get the status history for a specific job."""
        try:
            self.cursor.execute("""
                SELECT *
                FROM job_status_history
                WHERE job_id = ?
                ORDER BY changed_at DESC
            """, (job_id,))
            
            return [dict(row) for row in self.cursor.fetchall()]
        except Exception as e:
            raise e