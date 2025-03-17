# Docker Implementation Guide

## Overview

The Workday Scraper can be run in a Docker container for consistent deployment across environments. This guide covers all aspects of Docker deployment, from basic usage to advanced configurations.

## Quick Start

1. Build the image:
```bash
docker build -t workday-scraper .
```

2. Run the scraper:
```bash
docker run -v $(pwd)/data:/app/data \
          -v $(pwd)/configs:/app/configs \
          -v $(pwd)/logs:/app/logs \
          workday-scraper -f your_config.txt
```

## Directory Structure

```
.
├── /app                    # Application root in container
│   ├── /data              # Database and output files
│   ├── /configs           # Configuration files
│   └── /logs              # Log files
```

## Volume Mounts

The container uses three main volume mounts:
- `/app/data`: Persistent storage for database and output files
- `/app/configs`: Configuration files
- `/app/logs`: Log files

## Environment Variables

### Required Variables
- `DB_FILE`: Database file path (default: `/app/data/workday_jobs.db`)
- `CONFIG_DIR`: Config directory (default: `/app/configs`)
- `LOG_DIR`: Log directory (default: `/app/logs`)

### Optional Variables
- `LOG_LEVEL`: Logging verbosity (default: `INFO`)
- `MAX_WORKERS`: Concurrent workers (default: `5`)
- `SCHEDULE_HOUR`: Daily run hour (default: `0`)
- `SCHEDULE_MINUTE`: Daily run minute (default: `0`)
- `SCHEDULE_TIMEZONE`: Schedule timezone (default: `UTC`)

### Telegram Bot Variables
- `TELEGRAM_BOT_TOKEN`: Bot authentication token
- `TELEGRAM_CHAT_ID`: Chat ID for notifications

## Docker Compose

### Basic Setup
```yaml
version: '3.8'
services:
  scraper:
    build: .
    volumes:
      - ./data:/app/data
      - ./configs:/app/configs
      - ./logs:/app/logs
    environment:
      - DB_FILE=/app/data/workday_jobs.db
      - LOG_LEVEL=INFO
```

### With Telegram Bot
```yaml
version: '3.8'
services:
  scraper:
    build: .
    volumes:
      - ./data:/app/data
      - ./configs:/app/configs
      - ./logs:/app/logs
    environment:
      - DB_FILE=/app/data/workday_jobs.db
      - TELEGRAM_BOT_TOKEN=your_bot_token
      - TELEGRAM_CHAT_ID=your_chat_id
```

### With Scheduling
```yaml
version: '3.8'
services:
  scraper:
    build: .
    volumes:
      - ./data:/app/data
      - ./configs:/app/configs
      - ./logs:/app/logs
    environment:
      - DB_FILE=/app/data/workday_jobs.db
      - SCHEDULE_HOUR=0
      - SCHEDULE_MINUTE=0
      - SCHEDULE_TIMEZONE=UTC
```

## Container Resources

### Recommended Limits
```yaml
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 1G
        reservations:
          cpus: '0.5'
          memory: 512M
```

## Data Persistence

### Database Volume
```yaml
volumes:
  db_data:
    driver: local
```

### Using Named Volumes
```yaml
services:
  scraper:
    volumes:
      - db_data:/app/data
volumes:
  db_data:
```

## Health Checks

```yaml
    healthcheck:
      test: ["CMD", "python", "-c", "import sqlite3; sqlite3.connect('/app/data/workday_jobs.db')"]
      interval: 30s
      timeout: 10s
      retries: 3
```

## Networking

### External Access
```yaml
    ports:
      - "8080:8080"  # For web interface
```

### Internal Network
```yaml
    networks:
      - scraper_net
networks:
  scraper_net:
    driver: bridge
```

## Security Considerations

1. **Run as Non-Root**
```dockerfile
RUN useradd -r -u 1001 -g scraper scraper
USER scraper
```

2. **Read-Only Root Filesystem**
```yaml
    read_only: true
    tmpfs:
      - /tmp
      - /var/run
```

3. **Minimal Base Image**
```dockerfile
FROM python:3.10-slim
```

## Monitoring

### Log Collection
```yaml
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

## Updates and Maintenance

1. Update Strategy
```yaml
    deploy:
      update_config:
        parallelism: 1
        delay: 10s
        order: start-first
```

2. Restart Policy
```yaml
    restart: unless-stopped
```

## Troubleshooting

### Common Issues

1. **Permission Denied**
- Ensure volume mount permissions are correct
- Check container user permissions
- Verify file ownership

2. **Database Locked**
- Check for multiple container instances
- Verify proper volume mounting
- Consider using WAL journal mode

3. **Memory Issues**
- Adjust container memory limits
- Monitor memory usage
- Consider cleanup intervals

### Debug Mode
```yaml
    environment:
      - LOG_LEVEL=DEBUG
```

## Best Practices

1. Use multi-stage builds for smaller images
2. Implement proper logging
3. Use Docker secrets for sensitive data
4. Implement health checks
5. Use resource limits
6. Regular backup procedures
7. Monitor container health

## Example Production Setup

```yaml
version: '3.8'
services:
  scraper:
    build: .
    image: workday-scraper:latest
    volumes:
      - db_data:/app/data
      - config_data:/app/configs
      - log_data:/app/logs
    environment:
      - DB_FILE=/app/data/workday_jobs.db
      - LOG_LEVEL=INFO
      - TELEGRAM_BOT_TOKEN_FILE=/run/secrets/bot_token
      - TELEGRAM_CHAT_ID_FILE=/run/secrets/chat_id
    secrets:
      - bot_token
      - chat_id
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 1G
      restart_policy:
        condition: unless-stopped
    healthcheck:
      test: ["CMD", "python", "-c", "import sqlite3; sqlite3.connect('/app/data/workday_jobs.db')"]
      interval: 30s
      timeout: 10s
      retries: 3
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

volumes:
  db_data:
  config_data:
  log_data:

secrets:
  bot_token:
    file: ./secrets/bot_token.txt
  chat_id:
    file: ./secrets/chat_id.txt