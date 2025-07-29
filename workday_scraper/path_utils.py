"""
Path utilities for the Workday Scraper.

This module provides utilities for determining project paths regardless
of the current working directory.
"""

import os
from pathlib import Path

def get_project_root() -> str:
    """
    Get the project root directory.
    
    This function determines the project root by finding the directory
    containing the workday_scraper package, regardless of the current
    working directory.
    
    Returns:
        str: Absolute path to the project root directory
    """
    # Get the directory containing this file (workday_scraper package)
    package_dir = Path(__file__).parent.absolute()
    
    # The project root is the parent of the workday_scraper package
    project_root = package_dir.parent.absolute()
    
    return str(project_root)

def get_base_dir() -> str:
    """
    Get the base directory for the application.
    
    Returns:
        str: Base directory (/app for Docker, project root otherwise)
    """
    # Check if running in Docker
    in_docker = os.path.exists("/.dockerenv")
    
    if in_docker:
        return "/app"
    else:
        return get_project_root()

def get_data_dir() -> str:
    """
    Get the data directory path.
    
    Returns:
        str: Absolute path to the data directory
    """
    base_dir = get_base_dir()
    return os.path.join(base_dir, "data")

def get_logs_dir() -> str:
    """
    Get the logs directory path.
    
    Returns:
        str: Absolute path to the logs directory
    """
    base_dir = get_base_dir()
    return os.path.join(base_dir, "logs")

def get_configs_dir() -> str:
    """
    Get the configs directory path.
    
    Returns:
        str: Absolute path to the configs directory
    """
    base_dir = get_base_dir()
    return os.path.join(base_dir, "configs") 