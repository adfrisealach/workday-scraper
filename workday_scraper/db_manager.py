"""
Database manager for the Workday Scraper.

This module provides functions to manage the SQLite database for storing
job postings scraped from Workday sites.
"""

import os
import pwd
import grp
import shutil
import sqlite3
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from .status_tracking import JobStatusManager
from pathlib import Path

from .logging_utils import get_logger

logger = get_logger()


class DatabaseManager:
    """Manager for SQLite database operations."""
    
    def __init__(self, db_file=None):
        """Initialize the DatabaseManager.
        
        Args:
            db_file (str, optional): Path to the SQLite database file.
                If not provided, will use DB_FILE environment variable
                or fallback to "workday_jobs.db"
        """
        self.db_file = db_file or os.environ.get("DB_FILE", "workday_jobs.db")
        self.backup_file = f"{self.db_file}.bak"
        self.conn = None
        self.cursor = None
        self.status_manager = None
        
        logger.info(f"Initializing DatabaseManager with file: {self.db_file}")
        self._initialize_db()
        self.status_manager = JobStatusManager(self)

    def _check_file_permissions(self):
        """Check and log file permissions and ownership."""
        try:
            if os.path.exists(self.db_file):
                stat_info = os.stat(self.db_file)
                user = pwd.getpwuid(stat_info.st_uid).pw_name
                group = grp.getgrgid(stat_info.st_gid).gr_name
                logger.info(f"Database file: {self.db_file}")
                logger.info(f"Size: {stat_info.st_size} bytes")
                logger.info(f"Owner: {user}:{group}")
                logger.info(f"Permissions: {oct(stat_info.st_mode)[-3:]}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error checking permissions: {e}")
            return False

    def _setup_connection(self):
        """Set up the database connection with proper settings."""
        self.conn = sqlite3.connect(
            self.db_file,
            timeout=20,
            isolation_level=None
        )
        self.conn.execute('PRAGMA journal_mode=WAL')
        self.conn.execute('PRAGMA busy_timeout=5000')
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
        logger.info("Database connection established")
    def _check_db_integrity(self):
        """Check database integrity and create backup if needed."""
        try:
            # Try to open a separate connection for verification
            verify_conn = sqlite3.connect(self.db_file)
            verify_conn.row_factory = sqlite3.Row
            verify_cur = verify_conn.cursor()
            
            logger.info("Running database diagnostics...")
            
            # Run integrity check
            verify_cur.execute("PRAGMA integrity_check")
            result = verify_cur.fetchone()
            
            if result and result[0] == "ok":
                # Try a test query
                try:
                    verify_cur.execute("SELECT COUNT(*) as count, MIN(created_at) as earliest, MAX(created_at) as latest FROM jobs")
                    job_stats = verify_cur.fetchone()
                    if job_stats:
                        logger.info(f"Database verification - Total jobs: {job_stats['count']}")
                        logger.info(f"Database verification - Date range: {job_stats['earliest']} to {job_stats['latest']}")
                except sqlite3.Error as e:
                    logger.error(f"Test query failed: {str(e)}")
                    return False
                    
                logger.info("Database integrity check passed")
                verify_conn.close()
                return True
            else:
                logger.error("Database integrity check failed")
                verify_conn.close()
                return False
                
        except sqlite3.Error as e:
            logger.error(f"SQLite error during integrity check: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Error during integrity check: {str(e)}")
            return False

    def _backup_database(self):
        """Create a backup of the database file."""
        try:
            import shutil
            shutil.copy2(self.db_file, self.backup_file)
            logger.info(f"Created backup at {self.backup_file}")
            return True
        except Exception as e:
            logger.error(f"Failed to create backup: {str(e)}")
            return False

    def _restore_from_backup(self):
        """Restore database from backup file."""
        try:
            import shutil
            if os.path.exists(self.backup_file):
                shutil.copy2(self.backup_file, self.db_file)
                logger.info(f"Restored from backup {self.backup_file}")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to restore from backup: {str(e)}")
            return False

    def _initialize_db(self):
        """Initialize the database connection and create tables if they don't exist."""
        try:
            # Setup directory
            db_dir = os.path.dirname(self.db_file)
            if db_dir and not os.path.exists(db_dir):
                os.makedirs(db_dir)
                logger.info(f"Created directory: {db_dir}")

            # Check file permissions if exists
            if os.path.exists(self.db_file):
                stat_info = os.stat(self.db_file)
                try:
                    user = pwd.getpwuid(stat_info.st_uid).pw_name
                    group = grp.getgrgid(stat_info.st_gid).gr_name
                    current_user = pwd.getpwuid(os.getuid()).pw_name
                    logger.info(f"File: {self.db_file} ({stat_info.st_size} bytes)")
                    logger.info(f"Owner: {user}:{group}, Current user: {current_user}")
                    logger.info(f"Permissions: {oct(stat_info.st_mode)[-3:]}")
                except (KeyError, ImportError):
                    logger.info(f"File: {self.db_file} (UID: {stat_info.st_uid}, GID: {stat_info.st_gid})")

            # Check database file accessibility before connecting
            if os.path.exists(self.db_file):
                if not os.access(self.db_file, os.R_OK | os.W_OK):
                    logger.error(f"Insufficient permissions on {self.db_file}")
                    logger.error(f"Current process user: {pwd.getpwuid(os.getuid()).pw_name}")
                    logger.error(f"File owner: {pwd.getpwuid(os.stat(self.db_file).st_uid).pw_name}")
                    raise PermissionError(f"Cannot read/write database file: {self.db_file}")
            else:
                logger.info(f"Database file will be created: {self.db_file}")
                # Try to create an empty file to test permissions
                try:
                    with open(self.db_file, 'a'):
                        pass
                except IOError as e:
                    logger.error(f"Cannot create database file: {e}")
                    raise

            # Connect to database with optimized settings
            logger.info("Establishing database connection...")
            self.conn = sqlite3.connect(
                self.db_file,
                timeout=60.0,
                isolation_level='IMMEDIATE'
            )
            self.conn.row_factory = sqlite3.Row
            self.cursor = self.conn.cursor()

            # Configure for reliability and concurrency
            pragmas = [
                ('journal_mode', 'WAL'),
                ('synchronous', 'NORMAL'),
                ('busy_timeout', '60000'),
                ('cache_size', '10000'),
                ('temp_store', 'MEMORY'),
                ('locking_mode', 'NORMAL'),
                ('foreign_keys', 'ON')
            ]
            
            for pragma, value in pragmas:
                try:
                    self.cursor.execute(f'PRAGMA {pragma} = {value}')
                    result = self.cursor.execute(f'PRAGMA {pragma}').fetchone()
                    logger.info(f"PRAGMA {pragma} = {result[0]}")
                except sqlite3.Error as e:
                    logger.warning(f"Failed to set PRAGMA {pragma}: {e}")
            
            # Check existing tables
            self.cursor.execute("""
                SELECT COUNT(*) FROM sqlite_master
                WHERE type='table' AND name IN ('jobs', 'companies')
            """)
            table_count = self.cursor.fetchone()[0]
            
            if table_count == 2:
                try:
                    self.cursor.execute("SELECT COUNT(*) FROM jobs")
                    job_count = self.cursor.fetchone()[0]
                    self.cursor.execute("SELECT COUNT(*) FROM companies")
                    company_count = self.cursor.fetchone()[0]
                    
                    logger.info(f"Found {job_count} jobs and {company_count} companies")
                    if job_count > 0 or company_count > 0:
                        self._backup_database()
                except sqlite3.Error as e:
                    logger.warning(f"Error checking tables: {e}, recreating...")
                    self._create_tables()
            else:
                logger.info("Creating new tables")
                self._create_tables()

        except sqlite3.Error as e:
            logger.error(f"Database error: {e}")
            if self.conn:
                self.conn.close()
                self.conn = None
            raise
        except Exception as e:
            logger.error(f"Error: {e}")
            if self.conn:
                self.conn.close()
                self.conn = None
            raise
    
    def _create_tables(self):
        """Create the necessary tables if they don't exist."""
        try:
            # Create companies table
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS companies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    url TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
            """)
            
            # Create jobs table
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS jobs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT,
                    date_posted TEXT,
                    employment_type TEXT,
                    location TEXT,
                    company_id INTEGER NOT NULL,
                    url TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    status TEXT DEFAULT 'active',
                    last_seen TEXT,
                    missed_scrapes INTEGER DEFAULT 0,
                    FOREIGN KEY (company_id) REFERENCES companies (id),
                    UNIQUE (job_id, company_id)
                )
            """)
            
            # Create job status history table
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS job_status_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id INTEGER,
                    status TEXT NOT NULL,
                    changed_at TEXT NOT NULL,
                    reason TEXT,
                    FOREIGN KEY (job_id) REFERENCES jobs (id)
                )
            """)
            
            # Create indexes for jobs table
            self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_job_id ON jobs (job_id)")
            self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_company_id ON jobs (company_id)")
            self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_status ON jobs (status)")
            self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_last_seen ON jobs (last_seen)")
            
            # Create indexes for status history table
            self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_history_job_id ON job_status_history (job_id)")
            self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_history_status ON job_status_history (status)")
            self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_history_changed_at ON job_status_history (changed_at)")
            
            self.conn.commit()
            logger.info("Database tables created successfully")
        except Exception as e:
            logger.error(f"Error creating database tables: {str(e)}")
            raise
    
    def close(self):
        """Close the database connection."""
        if self.conn:
            self.conn.close()
            logger.info("Database connection closed")
    
    def get_or_create_company(self, name: str, url: str) -> int:
        """Get or create a company record.
        
        Args:
            name (str): Company name.
            url (str): Company URL.
            
        Returns:
            int: Company ID.
        """
        try:
            # Check if the company already exists
            self.cursor.execute(
                "SELECT id FROM companies WHERE name = ?",
                (name,)
            )
            result = self.cursor.fetchone()
            
            if result:
                return result['id']
            
            # Create a new company record
            now = datetime.now().isoformat()
            self.cursor.execute(
                "INSERT INTO companies (name, url, created_at) VALUES (?, ?, ?)",
                (name, url, now)
            )
            self.conn.commit()
            
            return self.cursor.lastrowid
        except Exception as e:
            logger.error(f"Error getting or creating company {name}: {str(e)}")
            self.conn.rollback()
            raise
    
    def save_job(self, job_data: Dict[str, Any], company_id: int) -> bool:
        """Save a job to the database and handle its status.
        
        Args:
            job_data (dict): Job data dictionary.
            company_id (int): Company ID.
            
        Returns:
            bool: True if the job was saved successfully, False otherwise.
        """
        try:
            job_id = job_data.get('job_id', '')
            if not job_id:
                logger.warning("Job data missing job_id, skipping")
                return False
            
            now = datetime.now().isoformat()
            
            # Check if the job exists and get its status
            self.cursor.execute("""
                SELECT id, status
                FROM jobs
                WHERE job_id = ? AND company_id = ?
            """, (job_id, company_id))
            result = self.cursor.fetchone()
            
            if result:
                job_db_id = result['id']
                current_status = result['status']
                
                # If job was closed but is now active again, reactivate it
                if current_status == 'closed':
                    self.status_manager.reactivate_job(job_db_id)
                    logger.info(f"Reactivated job {job_id}")
                
                # Update last seen timestamp
                self.status_manager.update_job_last_seen(job_id, company_id)
                logger.debug(f"Updated last seen for job {job_id}")
                return True
            
            # Insert new job
            self.cursor.execute("""
                INSERT INTO jobs (
                    job_id, title, description, date_posted, employment_type,
                    location, company_id, url, timestamp, created_at,
                    status, last_seen, missed_scrapes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                job_id,
                job_data.get('title', ''),
                job_data.get('description', ''),
                job_data.get('date_posted', ''),
                job_data.get('employment_type', ''),
                job_data.get('location', ''),
                company_id,
                job_data.get('url', ''),
                job_data.get('timestamp', now),
                now,
                'active',  # Initial status
                now,      # Initial last_seen
                0        # Initial missed_scrapes
            ))
            self.conn.commit()
            
            # Add initial status history entry
            job_db_id = self.cursor.lastrowid
            self.status_manager.update_job_status(
                job_db_id,
                'active',
                'Initial posting'
            )
            
            logger.debug(f"Saved new job {job_id} to database")
            return True
            
        except Exception as e:
            logger.error(f"Error saving job {job_data.get('job_id', 'unknown')}: {str(e)}")
            self.conn.rollback()
            return False
    
    def save_jobs(self, jobs: List[Dict[str, Any]]) -> Tuple[int, int]:
        """Save multiple jobs to the database and update their status.
        
        Args:
            jobs (list): List of job data dictionaries.
            
        Returns:
            tuple: (number of jobs saved, number of jobs failed)
        """
        saved = 0
        failed = 0
        
        # Group jobs by company
        jobs_by_company = {}
        for job in jobs:
            company_name = job.get('company', '')
            if not company_name:
                logger.warning("Job data missing company name, skipping")
                failed += 1
                continue
            if company_name not in jobs_by_company:
                jobs_by_company[company_name] = []
            jobs_by_company[company_name].append(job)
        
        # Process each company's jobs
        for company_name, company_jobs in jobs_by_company.items():
            try:
                # Get or create the company
                company_id = self.get_or_create_company(
                    name=company_name,
                    url=company_jobs[0].get('company_url', '')
                )
                
                # Mark all active jobs as missed for this company
                self.status_manager.mark_company_jobs_as_missed(company_id)
                
                # Save each job
                for job in company_jobs:
                    try:
                        result = self.save_job(job, company_id)
                        if result:
                            saved += 1
                            job_id = job['job_id']
                            # Update last seen timestamp for existing jobs
                            self.status_manager.update_job_last_seen(job_id, company_id)
                            logger.info(f"Updated job {job_id} status and last seen timestamp")
                        else:
                            failed += 1
                            logger.warning(f"Failed to save/update job {job.get('job_id', 'unknown')}")
                    except Exception as e:
                        logger.error(f"Error saving job for company {company_name}: {str(e)}")
                        failed += 1
                
                # Mark jobs that weren't seen as closed
                self.status_manager.mark_stale_jobs_as_closed(company_id)
                
            except Exception as e:
                logger.error(f"Error processing jobs for company {company_name}: {str(e)}")
                failed += len(company_jobs)
        
        logger.info(f"Saved {saved} jobs to database, {failed} failed")
        return saved, failed
    
    def get_job_ids_by_company(self) -> Dict[str, List[str]]:
        """Get all job IDs grouped by company.
        
        Returns:
            dict: Dictionary mapping company names to lists of job IDs.
        """
        try:
            self.cursor.execute("""
                SELECT c.name as company_name, j.job_id
                FROM jobs j
                JOIN companies c ON j.company_id = c.id
            """)
            
            results = self.cursor.fetchall()
            
            job_ids_dict = {}
            for row in results:
                company_name = row['company_name']
                job_id = row['job_id']
                
                if company_name not in job_ids_dict:
                    job_ids_dict[company_name] = []
                
                job_ids_dict[company_name].append(job_id)
            
            return job_ids_dict
        except Exception as e:
            logger.error(f"Error getting job IDs by company: {str(e)}")
            return {}
    
    def get_all_jobs(self) -> List[Dict[str, Any]]:
        """Get all jobs from the database.
        
        Returns:
            list: List of job dictionaries.
        """
        try:
            # First check if tables exist and have data
            self.cursor.execute("""
                SELECT COUNT(*) as count FROM jobs
            """)
            job_count = self.cursor.fetchone()['count']
            logger.info(f"Found {job_count} jobs in database at {self.db_file}")

            self.cursor.execute("""
                SELECT j.*, c.name as company_name, c.url as company_url
                FROM jobs j
                JOIN companies c ON j.company_id = c.id
                ORDER BY j.created_at DESC
            """)
            
            results = self.cursor.fetchall()
            
            # Convert rows to dictionaries
            jobs = []
            for row in results:
                job = dict(row)
                job['company'] = job.pop('company_name')
                jobs.append(job)
            
            logger.info(f"Returning {len(jobs)} jobs with company data")
            return jobs
        except Exception as e:
            logger.error(f"Error getting all jobs: {str(e)}")
            return []
    
    def get_jobs_by_company(self, company_name: str) -> List[Dict[str, Any]]:
        """Get jobs for a specific company.
        
        Args:
            company_name (str): Company name.
            
        Returns:
            list: List of job dictionaries.
        """
        try:
            self.cursor.execute("""
                SELECT j.*, c.name as company_name, c.url as company_url
                FROM jobs j
                JOIN companies c ON j.company_id = c.id
                WHERE c.name = ?
                ORDER BY j.created_at DESC
            """, (company_name,))
            
            results = self.cursor.fetchall()
            
            # Convert rows to dictionaries
            jobs = []
            for row in results:
                job = dict(row)
                job['company'] = job.pop('company_name')
                jobs.append(job)
            
            return jobs
        except Exception as e:
            logger.error(f"Error getting jobs for company {company_name}: {str(e)}")
            return []
    def get_jobs_by_date_range(self, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        """Get jobs within a date range.
        
        Args:
            start_date (str): Start date in ISO format (YYYY-MM-DD).
            end_date (str): End date in ISO format (YYYY-MM-DD).
            
        Returns:
            list: List of job dictionaries.
        """
        try:
            self.cursor.execute("""
                SELECT j.*, c.name as company_name, c.url as company_url
                FROM jobs j
                JOIN companies c ON j.company_id = c.id
                WHERE j.date_posted BETWEEN ? AND ?
                ORDER BY j.date_posted DESC
            """, (start_date, end_date))
            
            results = self.cursor.fetchall()
            
            # Convert rows to dictionaries
            jobs = []
            for row in results:
                job = dict(row)
                job['company'] = job.pop('company_name')
                jobs.append(job)
            
            return jobs
        except Exception as e:
            logger.error(f"Error getting jobs for date range {start_date} to {end_date}: {str(e)}")
            return []
    
    def get_jobs_by_location(self) -> Dict[str, Dict[str, int]]:
        """Get jobs grouped by location.
        
        Returns:
            dict: A dictionary mapping locations to job counts.
        """
        try:
            self.cursor.execute("""
                SELECT location, COUNT(*) as count
                FROM jobs
                GROUP BY location
                ORDER BY count DESC
            """)
            
            results = self.cursor.fetchall()
            
            location_counts = {}
            for row in results:
                location = row['location'] or "Unknown"
                count = row['count']
                location_counts[location] = count
            
            return location_counts
        except Exception as e:
            logger.error(f"Error getting jobs by location: {str(e)}")
            return {}
    
    def get_top_job_titles(self, limit: int = 10) -> List[Tuple[str, int]]:
        """Get the top job titles by count.
        
        Args:
            limit (int): The maximum number of job titles to return.
            
        Returns:
            list: A list of (title, count) tuples.
        """
        try:
            self.cursor.execute("""
                SELECT title, COUNT(*) as count
                FROM jobs
                GROUP BY title
                ORDER BY count DESC
                LIMIT ?
            """, (limit,))
            
            results = self.cursor.fetchall()
            
            # Convert rows to tuples
            top_titles = [(row['title'], row['count']) for row in results]
            
            return top_titles
        except Exception as e:
            logger.error(f"Error getting top job titles: {str(e)}")
            return []
    
    def get_jobs_count_by_company(self) -> Dict[str, int]:
        """Get the number of jobs for each company.
        
        Returns:
            dict: A dictionary mapping company names to job counts.
        """
        try:
            self.cursor.execute("""
                SELECT c.name as company_name, COUNT(*) as count
                FROM jobs j
                JOIN companies c ON j.company_id = c.id
                GROUP BY c.name
                ORDER BY count DESC
            """)
            
            results = self.cursor.fetchall()
            
            # Convert rows to dictionary
            company_counts = {row['company_name']: row['count'] for row in results}
            
            return company_counts
        except Exception as e:
            logger.error(f"Error getting jobs count by company: {str(e)}")
            return {}
    
    def search_job_titles_by_keyword(self, keyword: str) -> List[Tuple[str, int]]:
        """Search for job titles containing a keyword.
        
        Args:
            keyword (str): The keyword to search for.
            
        Returns:
            list: A list of (title, count) tuples.
        """
        try:
            # Use LIKE for case-insensitive search
            self.cursor.execute("""
                SELECT title, COUNT(*) as count
                FROM jobs
                WHERE LOWER(title) LIKE LOWER(?)
                GROUP BY title
                ORDER BY count DESC
            """, (f"%{keyword}%",))
            
            results = self.cursor.fetchall()
            
            # Convert rows to tuples
            matching_titles = [(row['title'], row['count']) for row in results]
            
            return matching_titles
        except Exception as e:
            logger.error(f"Error searching job titles by keyword '{keyword}': {str(e)}")
            return []
    
    def search_jobs_with_details(self, keyword: str) -> Dict[str, Any]:
        """Search for jobs containing a keyword in the title with full details including posting dates.
        
        Args:
            keyword (str): The keyword to search for.
            
        Returns:
            dict: A dictionary with 'jobs_by_title' mapping job titles to lists of job details dictionaries,
                  and 'title_recency' mapping job titles to their most recent posting age (in days).
        """
        try:
            # Use LIKE for case-insensitive search - prioritize jobs with date_posted
            self.cursor.execute("""
                SELECT j.id, j.job_id, j.title, j.date_posted, j.location,
                       c.name as company, j.url
                FROM jobs j
                JOIN companies c ON j.company_id = c.id
                WHERE LOWER(j.title) LIKE LOWER(?)
                ORDER BY
                    CASE WHEN j.date_posted IS NULL THEN 1 ELSE 0 END,
                    j.date_posted DESC,
                    j.title
            """, (f"%{keyword}%",))
            
            results = self.cursor.fetchall()
            
            # Group by title
            jobs_by_title = {}
            # Track the most recent job for each title
            title_recency = {}
            
            for row in results:
                job_dict = dict(row)
                title = job_dict['title']
                
                # Calculate days since posting if date_posted is available
                if job_dict.get('date_posted'):
                    try:
                        date_posted = datetime.fromisoformat(job_dict['date_posted'])
                        days_ago = (datetime.now() - date_posted).days
                        job_dict['days_ago'] = days_ago
                        
                        # Update most recent posting for this title
                        if title not in title_recency or days_ago < title_recency[title]:
                            title_recency[title] = days_ago
                    except (ValueError, TypeError):
                        job_dict['days_ago'] = 'unknown'
                        # Use a large number for unknown dates for sorting
                        if title not in title_recency:
                            title_recency[title] = 10000  # Very old
                else:
                    job_dict['days_ago'] = 'unknown'
                    # Use a large number for unknown dates for sorting
                    if title not in title_recency:
                        title_recency[title] = 10000  # Very old
                
                if title not in jobs_by_title:
                    jobs_by_title[title] = []
                
                jobs_by_title[title].append(job_dict)
            
            # Sort jobs within each title by recency
            for title in jobs_by_title:
                jobs_by_title[title] = sorted(
                    jobs_by_title[title],
                    key=lambda x: 10000 if x['days_ago'] == 'unknown' else x['days_ago']
                )
            
            return {
                'jobs_by_title': jobs_by_title,
                'title_recency': title_recency
            }
        except Exception as e:
            logger.error(f"Error searching jobs with details by keyword '{keyword}': {str(e)}")
            return {}
    
    def get_jobs_by_specific_location(self, location: str) -> List[Dict[str, Any]]:
        """Get all jobs for a specific location.
        
        Args:
            location (str): The location to filter by. Partial matching is supported.
            
        Returns:
            list: A list of job dictionaries for the specified location.
        """
        try:
            # Use LIKE for partial matching, making it more user-friendly
            search_term = f"%{location}%"
            
            self.cursor.execute("""
                SELECT j.*, c.name as company_name, c.url as company_url
                FROM jobs j
                JOIN companies c ON j.company_id = c.id
                WHERE j.location LIKE ?
                ORDER BY j.created_at DESC
            """, (search_term,))
            
            results = self.cursor.fetchall()
            
            # Convert rows to dictionaries
            jobs = []
            for row in results:
                job = dict(row)
                job['company'] = job.pop('company_name')
                jobs.append(job)
            
            return jobs
        except Exception as e:
            logger.error(f"Error getting jobs for location '{location}': {str(e)}")
            return []
    
    def get_locations_for_job_title(self, job_title: str) -> List[Tuple[str, int, List[Dict[str, Any]]]]:
        """Get locations where a specific job title is posted.
        
        Args:
            job_title (str): The job title to search for.
            
        Returns:
            list: A list of (location, count, jobs) tuples where jobs is a list of job dictionaries.
        """
        try:
            # First get the locations and counts
            self.cursor.execute("""
                SELECT location, COUNT(*) as count
                FROM jobs
                WHERE title = ?
                GROUP BY location
                ORDER BY count DESC
            """, (job_title,))
            
            location_results = self.cursor.fetchall()
            
            # For each location, get the job details including date_posted
            locations_with_jobs = []
            for row in location_results:
                location = row['location'] or "Unknown"
                count = row['count']
                
                # Get job details for this location and title
                self.cursor.execute("""
                    SELECT j.id, j.job_id, j.title, j.date_posted, j.location,
                           c.name as company, j.url
                    FROM jobs j
                    JOIN companies c ON j.company_id = c.id
                    WHERE j.title = ? AND (j.location = ? OR (j.location IS NULL AND ? = 'Unknown'))
                    ORDER BY j.date_posted DESC
                """, (job_title, location, location))
                
                job_details = []
                for job in self.cursor.fetchall():
                    job_dict = dict(job)
                    # Calculate days since posting if date_posted is available
                    if job_dict.get('date_posted'):
                        try:
                            date_posted = datetime.fromisoformat(job_dict['date_posted'])
                            days_ago = (datetime.now() - date_posted).days
                            job_dict['days_ago'] = days_ago
                        except (ValueError, TypeError):
                            job_dict['days_ago'] = 'unknown'
                    else:
                        job_dict['days_ago'] = 'unknown'
                    
                    job_details.append(job_dict)
                
                locations_with_jobs.append((location, count, job_details))
            
            return locations_with_jobs
        except Exception as e:
            logger.error(f"Error getting locations for job title '{job_title}': {str(e)}")
            return []