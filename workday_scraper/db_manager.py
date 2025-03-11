"""
Database manager for the Workday Scraper.

This module provides functions to manage the SQLite database for storing
job postings scraped from Workday sites.
"""

import os
import sqlite3
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

from .logging_utils import get_logger

logger = get_logger()


class DatabaseManager:
    """Manager for SQLite database operations."""
    
    def __init__(self, db_file="workday_jobs.db"):
        """Initialize the DatabaseManager.
        
        Args:
            db_file (str): Path to the SQLite database file.
        """
        self.db_file = db_file
        self.conn = None
        self.cursor = None
        
        # Initialize the database
        self._initialize_db()
    
    def _initialize_db(self):
        """Initialize the database connection and create tables if they don't exist."""
        try:
            # Create the database directory if it doesn't exist
            db_dir = os.path.dirname(self.db_file)
            if db_dir and not os.path.exists(db_dir):
                os.makedirs(db_dir)
            
            # Connect to the database
            self.conn = sqlite3.connect(self.db_file)
            self.conn.row_factory = sqlite3.Row  # Return rows as dictionaries
            self.cursor = self.conn.cursor()
            
            # Create tables if they don't exist
            self._create_tables()
            
            logger.info(f"Initialized database connection to {self.db_file}")
        except Exception as e:
            logger.error(f"Error initializing database: {str(e)}")
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
                    FOREIGN KEY (company_id) REFERENCES companies (id),
                    UNIQUE (job_id, company_id)
                )
            """)
            
            # Create index on job_id for faster lookups
            self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_job_id ON jobs (job_id)")
            
            # Create index on company_id for faster joins
            self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_company_id ON jobs (company_id)")
            
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
        """Save a job to the database.
        
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
            
            # Check if the job already exists
            self.cursor.execute(
                "SELECT id FROM jobs WHERE job_id = ? AND company_id = ?",
                (job_id, company_id)
            )
            result = self.cursor.fetchone()
            
            if result:
                logger.debug(f"Job {job_id} already exists in the database")
                return True
            
            # Insert the job
            now = datetime.now().isoformat()
            self.cursor.execute("""
                INSERT INTO jobs (
                    job_id, title, description, date_posted, employment_type,
                    location, company_id, url, timestamp, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                now
            ))
            self.conn.commit()
            
            logger.debug(f"Saved job {job_id} to database")
            return True
        except Exception as e:
            logger.error(f"Error saving job {job_data.get('job_id', 'unknown')}: {str(e)}")
            self.conn.rollback()
            return False
    
    def save_jobs(self, jobs: List[Dict[str, Any]]) -> Tuple[int, int]:
        """Save multiple jobs to the database.
        
        Args:
            jobs (list): List of job data dictionaries.
            
        Returns:
            tuple: (number of jobs saved, number of jobs failed)
        """
        saved = 0
        failed = 0
        
        for job in jobs:
            company_name = job.get('company', '')
            if not company_name:
                logger.warning("Job data missing company name, skipping")
                failed += 1
                continue
            
            try:
                # Get or create the company
                company_id = self.get_or_create_company(
                    name=company_name,
                    url=job.get('company_url', '')
                )
                
                # Save the job
                if self.save_job(job, company_id):
                    saved += 1
                else:
                    failed += 1
            except Exception as e:
                logger.error(f"Error saving job for company {company_name}: {str(e)}")
                failed += 1
        
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