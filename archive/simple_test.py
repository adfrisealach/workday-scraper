#!/usr/bin/env python
"""
Simple test script for the Workday Scraper Telegram bot.

This script tests the basic functionality of the Telegram bot without
actually running the scraper or making API calls.
"""

import os
import asyncio
import sqlite3
from datetime import datetime


def test_db_exists():
    """Test if the database exists and has jobs."""
    db_file = "workday_jobs.db"
    
    print(f"Checking if database {db_file} exists...")
    if not os.path.exists(db_file):
        print(f"❌ Database file {db_file} not found.")
        return False
    
    print(f"✅ Database file {db_file} exists.")
    
    try:
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM jobs")
        job_count = cursor.fetchone()[0]
        print(f"✅ Database contains {job_count} jobs.")
        
        cursor.execute("SELECT COUNT(*) FROM companies")
        company_count = cursor.fetchone()[0]
        print(f"✅ Database contains {company_count} companies.")
        
        conn.close()
        return True
    except Exception as e:
        print(f"❌ Error accessing database: {e}")
        return False


def test_config_exists():
    """Test if config files exist."""
    configs_dir = "configs"
    
    print(f"Checking if configs directory exists...")
    if not os.path.exists(configs_dir):
        print(f"❌ Configs directory {configs_dir} not found.")
        return False
    
    print(f"✅ Configs directory {configs_dir} exists.")
    
    config_files = [f for f in os.listdir(configs_dir) if f.endswith(".txt")]
    if not config_files:
        print("❌ No config files found.")
        return False
    
    print(f"✅ Found {len(config_files)} config files: {', '.join(config_files)}")
    return True


def test_env_vars():
    """Test if environment variables for Telegram bot are set."""
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    
    print("Checking environment variables...")
    
    if not token:
        print("❌ TELEGRAM_BOT_TOKEN is not set.")
        print("  Run: export TELEGRAM_BOT_TOKEN=your_token_here")
    else:
        print(f"✅ TELEGRAM_BOT_TOKEN is set: {token[:4]}...{token[-4:]}")
    
    if not chat_id:
        print("❌ TELEGRAM_CHAT_ID is not set.")
        print("  Run: export TELEGRAM_CHAT_ID=your_chat_id_here")
    else:
        print(f"✅ TELEGRAM_CHAT_ID is set: {chat_id}")
    
    return token is not None and chat_id is not None


def test_imports():
    """Test if required modules can be imported."""
    print("Testing imports...")
    
    try:
        import telegram
        print(f"✅ python-telegram-bot is installed (version: {telegram.__version__})")
    except ImportError:
        print("❌ python-telegram-bot is not installed.")
        print("  Run: pip install python-telegram-bot")
        return False
    
    try:
        import matplotlib
        print(f"✅ matplotlib is installed (version: {matplotlib.__version__})")
    except ImportError:
        print("❌ matplotlib is not installed.")
        print("  Run: pip install matplotlib")
        return False
    
    return True


if __name__ == "__main__":
    print("=== Workday Scraper Telegram Bot Test ===")
    print(f"Time: {datetime.now().isoformat()}")
    print()
    
    # Run tests
    db_ok = test_db_exists()
    config_ok = test_config_exists()
    env_ok = test_env_vars()
    imports_ok = test_imports()
    
    # Print summary
    print("\n=== Test Summary ===")
    print(f"Database Test: {'✅ PASSED' if db_ok else '❌ FAILED'}")
    print(f"Config Test: {'✅ PASSED' if config_ok else '❌ FAILED'}")
    print(f"Environment Variables: {'✅ PASSED' if env_ok else '❌ FAILED'}")
    print(f"Required Imports: {'✅ PASSED' if imports_ok else '❌ FAILED'}")
    
    if db_ok and config_ok and env_ok and imports_ok:
        print("\n🚀 All tests passed! You should be able to run the Telegram bot.")
        print("  1. Run the standalone bot: python run_telegram_bot.py")
        print("  2. Or run a scrape with notifications: python -m workday_scraper -f <config_file>")
    else:
        print("\n⚠️ Some tests failed. Please fix the issues before running the bot.")