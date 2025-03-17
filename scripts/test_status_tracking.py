#!/usr/bin/env python3
"""Test script for job status tracking functionality."""

import os
import sys
from datetime import datetime
from pathlib import Path

# Add project root to Python path
project_root = str(Path(__file__).resolve().parent.parent)
sys.path.insert(0, project_root)

from workday_scraper.db_manager import DatabaseManager

def test_status_tracking(db_file='data/test_jobs.db'):
    """Test job status tracking functionality."""
    print("\nTesting job status tracking...")
    
    # Create test database
    if os.path.exists(db_file):
        os.remove(db_file)
        print(f"Removed existing test database: {db_file}")
    
    try:
        # Initialize database
        print("Initializing database...")
        db = DatabaseManager(db_file)
        if not db.status_manager:
            raise RuntimeError("Failed to initialize JobStatusManager")
    except Exception as e:
        print(f"Error initializing database: {e}")
        sys.exit(1)
    
    # Test company data
    company_data = {
        'name': 'Test Company',
        'url': 'https://test.company.com'
    }
    
    # Create test jobs
    test_jobs = [
        {
            'job_id': 'JOB001',
            'title': 'Software Engineer',
            'description': 'Test job 1',
            'date_posted': datetime.now().isoformat(),
            'company': company_data['name'],
            'company_url': company_data['url'],
            'url': 'https://test.company.com/jobs/001'
        },
        {
            'job_id': 'JOB002',
            'title': 'Product Manager',
            'description': 'Test job 2',
            'date_posted': datetime.now().isoformat(),
            'company': company_data['name'],
            'company_url': company_data['url'],
            'url': 'https://test.company.com/jobs/002'
        }
    ]
    
    # Test scenario 1: Initial job creation
    print("\nScenario 1: Creating initial jobs")
    saved, failed = db.save_jobs(test_jobs)
    print(f"Saved: {saved}, Failed: {failed}")
    
    # Get active jobs
    active_jobs = db.status_manager.get_jobs_by_status('active')
    print(f"Active jobs: {len(active_jobs)}")
    assert len(active_jobs) == 2, "Expected 2 active jobs"
    
    # Test scenario 2: Job goes missing
    print("\nScenario 2: One job goes missing")
    # Second scrape with one job missing
    db.save_jobs([test_jobs[0]])  # Only save first job
    
    # Check job status after first scrape
    try:
        active_jobs = db.status_manager.get_jobs_by_status('active')
        print(f"Active jobs after first miss: {len(active_jobs)}")
    except Exception as e:
        print(f"Error checking job status: {e}")
        sys.exit(1)
    
    # Test scenario 3: Job still missing
    print("\nScenario 3: Job missing for second scrape")
    # Third scrape with same job still missing
    db.save_jobs([test_jobs[0]])  # Only save first job again
    
    # Check job statuses
    active_jobs = db.status_manager.get_jobs_by_status('active')
    closed_jobs = db.status_manager.get_jobs_by_status('closed')
    print(f"Active jobs: {len(active_jobs)}")
    print(f"Closed jobs: {len(closed_jobs)}")
    assert len(active_jobs) == 1, "Expected 1 active job"
    assert len(closed_jobs) == 1, "Expected 1 closed job"
    
    # Test scenario 4: Job reappears
    print("\nScenario 4: Closed job reappears")
    db.save_jobs(test_jobs)  # Save both jobs again
    
    # Check job statuses
    active_jobs = db.status_manager.get_jobs_by_status('active')
    closed_jobs = db.status_manager.get_jobs_by_status('closed')
    print(f"Active jobs after reappearance: {len(active_jobs)}")
    print(f"Closed jobs after reappearance: {len(closed_jobs)}")
    assert len(active_jobs) == 2, "Expected 2 active jobs after reappearance"
    assert len(closed_jobs) == 0, "Expected 0 closed jobs after reappearance"
    
    # Test scenario 5: Check status history
    print("\nScenario 5: Checking status history")
    history = db.status_manager.get_job_status_history(2)  # Get history for second job
    print(f"Status changes for job 2: {len(history)}")
    for change in history:
        print(f"  {change['changed_at']}: {change['status']} - {change['reason']}")
    
    print("\nAll tests completed successfully!")
    
    # Cleanup
    db.close()
    os.remove(db_file)

if __name__ == '__main__':
    # Create data directory if it doesn't exist
    os.makedirs('data', exist_ok=True)
    
    try:
        test_status_tracking()
    except AssertionError as e:
        print(f"Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)