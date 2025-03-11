# Docker Setup for Workday Scraper

This document provides instructions for deploying Workday Scraper using Docker on a headless Ubuntu server.

## Overview

The Docker setup for Workday Scraper:
- Packages both the scraper and Telegram bot in a single container
- Runs the Telegram bot continuously as a service
- Schedules the scraper to run nightly at midnight using cron
- Allows for configuration files to be added or modified after deployment
- Persists data across container restarts using volume mounts

## Prerequisites

- Docker installed on your server
- Docker Compose installed on your server
- Git (to clone the repository)

To install Docker and Docker Compose on Ubuntu:

```bash
# Update packages
sudo apt update

# Install prerequisites
sudo apt install -y apt-transport-https ca-certificates curl software-properties-common

# Add Docker GPG key
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -

# Add Docker repository
sudo add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable"

# Update packages again
sudo apt update

# Install Docker
sudo apt install -y docker-ce

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.18.1/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Add your user to the docker group (optional, for running docker without sudo)
sudo usermod -aG docker $USER
```

## Getting Started

### 1. First-time Setup

1. Clone the repository and navigate to the project directory:
   ```bash
   git clone https://github.com/yourusername/workday-scraper.git
   cd workday-scraper
   ```

2. Create the required directories for volume mounting:
   ```bash
   mkdir -p data configs logs
   ```

3. Copy the sample environment file:
   ```bash
   cp .env.docker .env
   ```

4. Edit the `.env` file with your Telegram bot token and chat ID:
   ```bash
   nano .env
   ```

5. Add your configuration files to the `configs` directory:
   ```bash
   cp your_config_file.txt configs/
   ```

### 2. Building and Running the Container

1. Build the Docker image:
   ```bash
   docker-compose build
   ```

2. Start the container:
   ```bash
   docker-compose up -d
   ```

3. Check the container logs:
   ```bash
   docker-compose logs -f
   ```

4. To stop the container:
   ```bash
   docker-compose down
   ```

## Configuration Management

### Telegram Bot Configuration

The Telegram bot requires two environment variables to function:
- `TELEGRAM_BOT_TOKEN`: Your Telegram bot token from BotFather
- `TELEGRAM_CHAT_ID`: Your Telegram chat ID

These are set in the `.env` file.

### Scraper Configuration Files

The scraper uses configuration files in the `configs/` directory to determine which Workday sites to scrape. You can add, remove, or modify these files after the container is running.

1. To add a new configuration file:
   ```bash
   echo "company_name,https://company.wd1.myworkdayjobs.com/en-US/External" > configs/company.txt
   ```

2. To modify which config file is used for the nightly run, edit the `CONFIG_FILE` variable in the `.env` file and restart the container:
   ```bash
   docker-compose down
   docker-compose up -d
   ```

## Data and Logs

### Data Persistence

The SQLite database is stored in the `data/` directory on your host, which is mounted as a volume in the container. This ensures that your data persists even if the container is stopped or removed.

### Logs

All logs are stored in the `logs/` directory:
- `workday_scraper.log`: Main application logs
- `telegram_bot.log`: Telegram bot logs
- `scraper_cron.log`: Logs from the scheduled cron job

## Scheduled Jobs

The scraper is configured to run nightly at midnight (server time) using cron. The job will use the configuration file specified by the `CONFIG_FILE` environment variable.

## Updating the Application

To update the application with a new version:

1. Pull the latest changes from Git:
   ```bash
   git pull
   ```

2. Rebuild and restart the container:
   ```bash
   docker-compose down
   docker-compose build
   docker-compose up -d
   ```

## Troubleshooting

### Container doesn't start

Check the logs for errors:
```bash
docker-compose logs
```

### The Telegram bot isn't responding

Ensure your Telegram bot token and chat ID are correctly set in the `.env` file:
```bash
cat .env
```

### Cron job isn't running

Check the cron logs:
```bash
docker exec workday-scraper cat /var/log/cron.log
```

### Manual scraper run

You can manually trigger a scraper run with:
```bash
docker exec workday-scraper python -m workday_scraper -f configs/your_config.txt
```

## Advanced Configuration

### Changing the Schedule

To change when the scraper runs, you need to modify the crontab entry in `entrypoint.sh` and rebuild the container.

For example, to run at 2 AM instead of midnight, change:
```
0 0 * * * cd /app && python -m workday_scraper -f $CONFIG_FILE >> /app/logs/scraper_cron.log 2>&1
```

to:
```
0 2 * * * cd /app && python -m workday_scraper -f $CONFIG_FILE >> /app/logs/scraper_cron.log 2>&1
```

### Multiple Scheduled Jobs

To schedule multiple scraper runs with different configurations, you can modify the entrypoint.sh script to add additional cron jobs.

## Security Considerations

The Docker container is designed to run with minimal privileges. However, for production environments, consider the following security measures:

1. Use Docker Secrets for sensitive information like API tokens
2. Set up a firewall to restrict access to your server
3. Keep your Docker installation up to date
4. Use non-root users in the container (modify the Dockerfile as needed)