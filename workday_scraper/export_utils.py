"""
Export utilities for the Workday Scraper.

This module provides functions to export job data from the SQLite database
to CSV format for data analysis.
"""

import os
import csv
import argparse
import sqlite3
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple

from .logging_utils import get_logger
from .db_manager import DatabaseManager

logger = get_logger()


def export_to_csv(db_file: str, output_file: str, company: Optional[str] = None,
                 start_date: Optional[str] = None, end_date: Optional[str] = None) -> Tuple[int, str]:
    """Export job data from the database to a CSV file.
    
    Args:
        db_file (str): Path to the SQLite database file.
        output_file (str): Path to the output CSV file.
        company (str, optional): Filter by company name.
        start_date (str, optional): Filter by start date (YYYY-MM-DD).
        end_date (str, optional): Filter by end date (YYYY-MM-DD).
        
    Returns:
        tuple: (Number of records exported, Path to the output file)
    """
    try:
        # Initialize database manager
        db_manager = DatabaseManager(db_file=db_file)
        
        # Get jobs based on filters
        if company:
            logger.info(f"Exporting jobs for company: {company}")
            jobs = db_manager.get_jobs_by_company(company)
        elif start_date and end_date:
            logger.info(f"Exporting jobs from {start_date} to {end_date}")
            jobs = db_manager.get_jobs_by_date_range(start_date, end_date)
        else:
            logger.info("Exporting all jobs")
            jobs = db_manager.get_all_jobs()
        
        if not jobs:
            logger.warning("No jobs found matching the criteria")
            return 0, output_file
        
        # Create the output directory if it doesn't exist
        output_dir = os.path.dirname(output_file)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        # Define CSV fields
        fields = [
            'job_id', 'title', 'company', 'location', 'date_posted',
            'employment_type', 'url', 'timestamp'
        ]
        
        # Write to CSV
        with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fields)
            writer.writeheader()
            
            for job in jobs:
                # Create a new dict with only the fields we want
                row = {field: job.get(field, '') for field in fields}
                writer.writerow(row)
        
        logger.info(f"Exported {len(jobs)} jobs to {output_file}")
        
        # Close database connection
        db_manager.close()
        
        return len(jobs), output_file
    
    except Exception as e:
        logger.error(f"Error exporting to CSV: {str(e)}")
        return 0, output_file


def export_to_pandas(db_file: str, company: Optional[str] = None,
                    start_date: Optional[str] = None, end_date: Optional[str] = None) -> Any:
    """Export job data from the database to a pandas DataFrame.
    
    This function is intended for use in Jupyter notebooks.
    
    Args:
        db_file (str): Path to the SQLite database file.
        company (str, optional): Filter by company name.
        start_date (str, optional): Filter by start date (YYYY-MM-DD).
        end_date (str, optional): Filter by end date (YYYY-MM-DD).
        
    Returns:
        pandas.DataFrame: DataFrame containing the job data.
    """
    try:
        # Import pandas here to avoid making it a required dependency
        import pandas as pd
        
        # Initialize database manager
        db_manager = DatabaseManager(db_file=db_file)
        
        # Get jobs based on filters
        if company:
            logger.info(f"Exporting jobs for company: {company}")
            jobs = db_manager.get_jobs_by_company(company)
        elif start_date and end_date:
            logger.info(f"Exporting jobs from {start_date} to {end_date}")
            jobs = db_manager.get_jobs_by_date_range(start_date, end_date)
        else:
            logger.info("Exporting all jobs")
            jobs = db_manager.get_all_jobs()
        
        if not jobs:
            logger.warning("No jobs found matching the criteria")
            return pd.DataFrame()
        
        # Convert to DataFrame
        df = pd.DataFrame(jobs)
        
        # Close database connection
        db_manager.close()
        
        return df
    
    except ImportError:
        logger.error("pandas is required for this function. Install it with 'pip install pandas'")
        return None
    except Exception as e:
        logger.error(f"Error exporting to pandas: {str(e)}")
        return None


def parse_export_args():
    """Parse command-line arguments for the export utility.
    
    Returns:
        dict: Parsed arguments.
    """
    parser = argparse.ArgumentParser(description="Workday Scraper - CSV Export Utility")
    
    # Required arguments
    parser.add_argument("-db", "--db-file", dest="db_file", type=str,
                      default="workday_jobs.db",
                      help="Path to the SQLite database file (default: workday_jobs.db)")
    
    parser.add_argument("-o", "--output", dest="output_file", type=str,
                      default="job_export.csv",
                      help="Path to the output CSV file (default: job_export.csv)")
    
    # Filter options
    parser.add_argument("-c", "--company", dest="company", type=str,
                      help="Filter by company name")
    
    parser.add_argument("-sd", "--start-date", dest="start_date", type=str,
                      help="Filter by start date (YYYY-MM-DD)")
    
    parser.add_argument("-ed", "--end-date", dest="end_date", type=str,
                      help="Filter by end date (YYYY-MM-DD)")
    
    # Parse arguments
    args = vars(parser.parse_args())
    
    # Validate date format if provided
    if args.get("start_date"):
        try:
            datetime.strptime(args["start_date"], "%Y-%m-%d")
        except ValueError:
            parser.error("Start date must be in YYYY-MM-DD format")
    
    if args.get("end_date"):
        try:
            datetime.strptime(args["end_date"], "%Y-%m-%d")
        except ValueError:
            parser.error("End date must be in YYYY-MM-DD format")
    
    # If start_date is provided, end_date is required and vice versa
    if (args.get("start_date") and not args.get("end_date")) or \
       (args.get("end_date") and not args.get("start_date")):
        parser.error("Both start-date and end-date must be provided together")
    
    return args


def main():
    """Main entry point for the CSV export utility."""
    args = parse_export_args()
    
    count, output_file = export_to_csv(
        db_file=args["db_file"],
        output_file=args["output_file"],
        company=args.get("company"),
        start_date=args.get("start_date"),
        end_date=args.get("end_date")
    )
    
    if count > 0:
        print(f"Successfully exported {count} jobs to {output_file}")
    else:
        print("No jobs were exported. Check the log for details.")


if __name__ == "__main__":
    main()