cd # Repository Cleanup Recommendations

## Core Components (Keep)

### Main Application
- `workday_scraper/` directory and all its contents
- `requirements.txt`
- Core configuration files:
  - `.env.sample`
  - `.gitignore`
  - `LICENSE`
  - `README.md`

### Essential Scripts
- `export_to_csv.py`
- `run_telegram_bot.py`
- `setup_environment.sh`
- `test_telegram_bot.py`

### Configuration
- `configs/` directory for user configs

## Cleanup Recommendations

### 1. Docker-Related Files (Consider Consolidating)
Current situation:
- Multiple Docker files and documentation spread across repository
- Some appear to be variations or older versions

Recommendation:
- Keep only the primary Docker files:
  - `Dockerfile`
  - `docker-compose.yml`
  - `.env.docker`
- Consider consolidating Docker documentation into a single `DOCKER.md` file
- Remove:
  - `docker-compose.portainer.yml`
  - `docker-compose.pull.yml`
  - `DOCKER-DIRECTORY-STRUCTURE.md`
  - `DOCKER-README.md`
  - `docker-setup.sh`
  - `dockerhub-deploy.sh`
  - `PORTAINER-DEPLOYMENT.md`

### 2. Archive Directory
Current situation:
- Contains older versions of files that have been superseded
- `simple_test.py` functionality is now covered by `test_telegram_bot.py`
- `location_transformation.py` is replaced by `location_field_parsing.py`

Recommendation:
- Remove the entire `archive/` directory as its contents are obsolete and better implementations exist in the main codebase

### 3. Documentation Cleanup
Current situation:
- Multiple implementation-related markdown files with overlapping content:
  - `implementation_considerations.md`
  - `implementation_details.md`
  - `implementation_plan.md`
  - `future_improvements.md`

Recommendation:
- Consolidate into two files:
  - `IMPLEMENTATION.md` - For current implementation details
  - `ROADMAP.md` - For future improvements and plans

### 4. Data Directory
Current situation:
- Contains backup files (`data/workday_jobs.db.bak`)

Recommendation:
- Keep the `data/` directory but remove `.bak` files
- Add `.bak` extension to `.gitignore`

## Implementation Plan

1. **Backup Phase**
   - Create a backup branch before making any changes
   - Push all current changes to remote repository

2. **Documentation Consolidation**
   ```mermaid
   graph TD
     A[Multiple Implementation Docs] --> B[IMPLEMENTATION.md]
     C[Multiple Docker Docs] --> D[DOCKER.md]
     E[Future Improvements] --> F[ROADMAP.md]
   ```

3. **Docker Cleanup**
   - Create comprehensive `DOCKER.md`
   - Remove redundant Docker files
   - Update main Docker configuration files if needed

4. **Archive Removal**
   - Verify all archived functionality is properly implemented in main codebase
   - Remove archive directory

5. **Data Directory Cleanup**
   - Update `.gitignore` with `.bak` extension
   - Remove backup files
   - Maintain empty data directory structure

6. **Testing**
   - Run test suite to verify functionality
   - Test Docker setup with new configuration
   - Verify documentation links still work

## Safety Measures

1. **Before Cleanup**
   - Create a new branch: `git checkout -b cleanup-march-2024`
   - Commit current state: `git commit -am "Pre-cleanup commit"`

2. **During Cleanup**
   - Commit changes in logical groups
   - Keep detailed commit messages
   - Test functionality after each significant change

3. **After Cleanup**
   - Run all tests
   - Verify Docker builds
   - Create pull request for review

## Files to Remove

```plaintext
./archive/
./DOCKER-DIRECTORY-STRUCTURE.md
./DOCKER-README.md
./PORTAINER-DEPLOYMENT.md
./docker-compose.portainer.yml
./docker-compose.pull.yml
./docker-setup.sh
./dockerhub-deploy.sh
./implementation_considerations.md
./implementation_details.md
./implementation_plan.md
./future_improvements.md
./data/*.bak
```

## Files to Create

```plaintext
./DOCKER.md
./IMPLEMENTATION.md
./ROADMAP.md