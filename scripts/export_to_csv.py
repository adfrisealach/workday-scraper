#!/usr/bin/env python3
"""
CSV Export Utility for Workday Scraper.

This script provides a command-line interface to export job data from the
SQLite database to CSV format for data analysis.

Usage:
    python export_to_csv.py [options]

Options:
    -db, --db-file      Path to the SQLite database file (default: workday_jobs.db)
    -o, --output        Path to the output CSV file (default: job_export.csv)
    -c, --company       Filter by company name
    -sd, --start-date   Filter by start date (YYYY-MM-DD)
    -ed, --end-date     Filter by end date (YYYY-MM-DD)
"""

from workday_scraper.export_utils import main

if __name__ == "__main__":
    main()