# Deploying Workday Scraper with Portainer

This guide provides detailed instructions for deploying the Workday Scraper application using Portainer stacks.

## What is Portainer?

Portainer is a web-based container management tool that simplifies deploying and managing Docker containers through a user-friendly interface. It's particularly useful for managing containers on headless servers without needing to use the command line.

## Prerequisites

1. Docker installed on your Ubuntu server
2. Portainer installed and accessible
3. DockerHub account (if using a private image)

## Deployment Steps

### 1. Prepare Docker Image

Ensure your Docker image is available either:
- Publicly on DockerHub
- In a private DockerHub repository you have access to
- In a local registry accessible to your Portainer instance

You can build and push the image using the provided `dockerhub-deploy.sh` script:
```bash
./dockerhub-deploy.sh
```

### 2. Prepare Host Directories

Before deploying via Portainer, create the necessary directories on your host system:

```bash
# Create directories for persistent data
mkdir -p /portainer/workday-scraper/data
mkdir -p /portainer/workday-scraper/configs
mkdir -p /portainer/workday-scraper/logs

# Add your configuration files
cp your_config.txt /portainer/workday-scraper/configs/
```

### 3. Deploy Stack in Portainer

1. Log in to your Portainer instance
2. Navigate to Stacks → Add stack
3. Give your stack a name (e.g., "workday-scraper")
4. In the "Web editor" tab, paste the contents of `docker-compose.portainer.yml`
5. Configure environment variables in the "Environment variables" section:

   **Required variables:**
   - `TELEGRAM_BOT_TOKEN`: Your Telegram bot token
   - `TELEGRAM_CHAT_ID`: Your Telegram chat ID
   - `DOCKER_USERNAME`: Your DockerHub username

   **Optional variables:**
   - `TAG`: Docker image tag (default: latest)
   - `CONFIG_FILE`: Name of config file to use (default: autodesk.txt)
   - `TZ`: Your timezone (default: America/Los_Angeles)
   - `LOG_LEVEL`: Logging level (default: INFO)
   - `DATA_PATH`: Custom path for data directory
   - `CONFIGS_PATH`: Custom path for configs directory
   - `LOGS_PATH`: Custom path for logs directory

6. Click "Deploy the stack"

## Managing Your Stack

### Viewing Container Logs

1. Navigate to Stacks → your-stack-name
2. Click on the container name
3. Go to the "Logs" tab to view container logs

### Accessing Data Files

Your files are stored in the mounted volumes:
- Database: `/portainer/workday-scraper/data/`
- Logs: `/portainer/workday-scraper/logs/`
- Config files: `/portainer/workday-scraper/configs/`

### Modifying Configuration Files

You can modify configuration files in the `/portainer/workday-scraper/configs/` directory on your host. Changes will be immediately available to the container.

### Updating the Stack

To update your stack (e.g., with a new image):

1. Navigate to Stacks → your-stack-name
2. Click "Editor"
3. Update the image tag or make other changes
4. Click "Update the stack"

## Monitoring and Maintenance

### Health Checks

The container includes a health check that verifies the database file exists. You can view the health status in the Portainer UI.

### Resource Usage

You can monitor resource usage in the Portainer dashboard. The stack is configured with the following resource limits:
- CPU: 0.5 cores (50% of a CPU core)
- Memory: 512MB maximum, 128MB reserved

You can adjust these values in the `docker-compose.portainer.yml` file before deployment or update them later.

### Backup Strategy

For backup, consider periodically copying the contents of the data directory:

```bash
# Example backup script
tar -czf workday-scraper-backup-$(date +%Y%m%d).tar.gz /portainer/workday-scraper/data
```

## Troubleshooting

### Container won't start

1. Check the container logs in Portainer
2. Verify environment variables are set correctly
3. Ensure all required directories exist and have correct permissions

### Telegram Bot not responding

1. Verify `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` are set correctly
2. Check container logs for any error messages
3. Restart the container to reinitialize the bot

### Cron jobs not running

1. Check the logs directory for `scraper_cron.log`
2. Ensure the config file specified in `CONFIG_FILE` exists
3. Verify the container's timezone is set correctly

For additional assistance, refer to the general documentation in `DOCKER-README.md`.