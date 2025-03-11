# Docker Directory Structure

This document explains how the Docker configuration works with the existing Workday Scraper directory structure.

## Overview

The Docker configuration we've designed works with the existing project structure but uses dedicated directories for persistent data. These directories are mounted as volumes in the Docker container.

## Directory Structure

### Existing Project Structure

Your project already has the following structure:
```
workday-scraper/
├── configs/              # Existing directory for configuration files
├── workday_scraper/      # Existing directory for application code
├── requirements.txt      # Python dependencies
├── run_telegram_bot.py   # Telegram bot script
└── [other project files]
```

### Added Directories for Docker

We've added these directories for volume mounts:
```
workday-scraper/
├── data/                 # [NEW] For database storage
├── logs/                 # [NEW] For log files
```

### Inside the Docker Container

Inside the container, the application will be structured as:
```
/app/                     # Working directory inside the container
├── configs/              # Mounted from host's configs/ directory
├── data/                 # Mounted from host's data/ directory
├── logs/                 # Mounted from host's logs/ directory
├── workday_scraper/      # Application code copied during build
├── requirements.txt
└── [other project files]
```

## What You Need to Know

1. **No Code Changes Required**: The Docker setup uses environment variables to redirect database and log files to the appropriate locations. You don't need to modify any application code.

2. **Data Persistence**:
   - The SQLite database will be stored in the `data/` directory
   - All logs will be saved to the `logs/` directory
   - Configuration files remain in the existing `configs/` directory

3. **First Run**:
   - On the first run, the database will be created in the `data/` directory
   - If you already have a database file in the project root, you might want to move it to the `data/` directory before starting the container

4. **Environment Variables**:
   - We've configured environment variables in docker-compose.yml to point to the correct locations:
     - `DB_FILE=/app/data/workday_jobs.db`
     - `LOG_FILE=/app/logs/workday_scraper.log`

## Migrating Existing Data

If you have existing data that you want to migrate to the Docker setup:

1. **Database**:
   - If you already have a `workday_jobs.db` file in your project root, move it to the `data/` directory:
     ```bash
     mv workday_jobs.db data/
     ```

2. **Logs**:
   - If you want to keep existing log files, move them to the `logs/` directory:
     ```bash
     mv *.log logs/
     ```

## Summary

The Docker configuration is designed to work with your existing code structure while providing proper isolation and persistence for data files. The directory structure ensures that:

1. Application code is containerized
2. Data is persisted across container restarts
3. Configuration files can be easily modified
4. Logs are properly organized and accessible

The setup is meant to be non-invasive to your existing code while providing all the benefits of containerization.