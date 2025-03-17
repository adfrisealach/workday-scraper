# Cleanup Recommendations

This document provides recommendations for cleaning up the project structure to make it more maintainable and easier to share with others.

## Files and Directories That Can Be Safely Removed

The following files and directories are no longer necessary and can be safely removed:

### Root Directory Files

- `dockerhub-deploy.sh` - Removed (Docker Hub deployment can be done with standard Docker commands)
- `.env.docker` - Moved to `config/` directory
- `.env.sample` - Moved to `config/` directory
- `.env.test` - Moved to `config/` directory
- `docker-compose.portainer.yml` - Moved to `docker/` directory
- `docker-compose.pull.yml` - Moved to `docker/` directory
- `docker-compose.yml` - Moved to `docker/` directory
- `docker-setup.sh` - Moved to `docker/` directory
- `Dockerfile` - Moved to `docker/` directory
- `entrypoint.sh` - Moved to `docker/` directory
- `DOCKER-DIRECTORY-STRUCTURE.md` - Content merged into `docs/DOCKER.md`
- `DOCKER-README.md` - Renamed to `docs/DOCKER.md`
- `PORTAINER-DEPLOYMENT.md` - Moved to `docs/` directory
- `future_improvements.md` - Content can be merged into `docs/README.md`
- `implementation_considerations.md` - Content merged into `docs/IMPLEMENTATION.md`
- `implementation_details.md` - Content merged into `docs/IMPLEMENTATION.md`
- `implementation_plan.md` - Content merged into `docs/IMPLEMENTATION.md`
- `export_to_csv.py` - Moved to `scripts/` directory
- `run_telegram_bot.py` - Moved to `scripts/` directory
- `setup_environment.sh` - Moved to `scripts/` directory
- `test_bot.sh` - Moved to `scripts/` directory
- `test_telegram_bot.py` - Moved to `scripts/` directory

### Archive Directory

The `archive/` directory contains old code that is no longer used. It can be safely removed if you don't need to reference it anymore:

- `archive/location_transformation.py`
- `archive/simple_test.py`

## Temporary Files

The following files are temporary and can be safely removed:

- Any `.pyc` files or `__pycache__` directories
- Any `.log` files in the root directory (logs should be stored in the `logs/` directory)
- Any `.db-journal` files
- Any `.bak` files

## Database Files

The database file `data/workday_jobs.db` should be kept if it contains important data. If you're sharing the project with others, you might want to provide an empty database or a script to initialize the database.

## Next Steps

After cleaning up the project, consider:

1. Updating the README.md file to reflect the new project structure
2. Creating a comprehensive documentation in the docs/ directory
3. Adding more examples and usage instructions
4. Setting up a proper CI/CD pipeline for automated testing and deployment