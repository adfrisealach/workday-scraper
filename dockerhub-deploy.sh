#!/bin/bash
# Script for building and pushing the Workday Scraper Docker image to DockerHub

# Define colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}Workday Scraper DockerHub Deployment Helper${NC}"
echo "This script will help you build and push the Docker image to DockerHub."
echo

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Error: Docker is not installed.${NC}"
    echo "Please install Docker before continuing."
    exit 1
fi

# Ask for DockerHub username
read -p "Enter your DockerHub username: " dockerhub_username

# Set image name with username
image_name="${dockerhub_username}/workday-scraper"

# Ask for image tag
read -p "Enter image tag (default: latest): " image_tag
image_tag=${image_tag:-latest}

# Build the image
echo -e "${GREEN}Building Docker image...${NC}"
docker build -t ${image_name}:${image_tag} .

# Check if build was successful
if [ $? -ne 0 ]; then
    echo -e "${RED}Error: Docker build failed.${NC}"
    exit 1
fi

echo -e "${GREEN}Docker image built successfully: ${image_name}:${image_tag}${NC}"

# Ask if user wants to push to DockerHub
read -p "Do you want to push this image to DockerHub? (y/n): " push_choice

if [ "$push_choice" = "y" ] || [ "$push_choice" = "Y" ]; then
    # Check if user is logged in to Docker
    docker_login_status=$(docker info 2>/dev/null | grep -c "Username")
    
    # If not logged in, prompt for login
    if [ "$docker_login_status" -eq 0 ]; then
        echo "You need to log in to DockerHub first."
        docker login
        
        # Check if login was successful
        if [ $? -ne 0 ]; then
            echo -e "${RED}Error: Failed to log in to DockerHub.${NC}"
            exit 1
        fi
    fi
    
    # Push the image to DockerHub
    echo -e "${GREEN}Pushing image to DockerHub...${NC}"
    docker push ${image_name}:${image_tag}
    
    # Check if push was successful
    if [ $? -ne 0 ]; then
        echo -e "${RED}Error: Failed to push image to DockerHub.${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}Image successfully pushed to DockerHub!${NC}"
    echo "You can now pull this image on your Ubuntu server with:"
    echo -e "${YELLOW}docker pull ${image_name}:${image_tag}${NC}"
    
    # Create a docker-compose file for pulling from DockerHub
    cat > docker-compose.pull.yml << EOL
version: '3.8'

services:
  workday-scraper:
    image: ${image_name}:${image_tag}
    container_name: workday-scraper
    restart: unless-stopped
    environment:
      - TELEGRAM_BOT_TOKEN=\${TELEGRAM_BOT_TOKEN}
      - TELEGRAM_CHAT_ID=\${TELEGRAM_CHAT_ID}
      - DB_FILE=/app/data/workday_jobs.db
      - LOG_FILE=/app/logs/workday_scraper.log
      - LOG_LEVEL=INFO
      - CONFIG_FILE=autodesk.txt  # Default config file to use for scheduled runs
      - TZ=America/Los_Angeles    # Set your timezone here
    volumes:
      - ./data:/app/data        # Database storage
      - ./configs:/app/configs  # Configuration files
      - ./logs:/app/logs        # Log files
    networks:
      - workday-net
    healthcheck:
      test: ["CMD", "python", "-c", "import os; exit(0 if os.path.exists('/app/data/workday_jobs.db') else 1)"]
      interval: 1m
      timeout: 10s
      retries: 3
      start_period: 30s

networks:
  workday-net:
    driver: bridge
EOL
    
    echo -e "${GREEN}Created docker-compose.pull.yml file for pulling from DockerHub.${NC}"
    echo "On your Ubuntu server, you can use this file to run the container:"
    echo -e "${YELLOW}docker-compose -f docker-compose.pull.yml up -d${NC}"
    
else
    echo -e "${YELLOW}Image not pushed to DockerHub.${NC}"
fi

echo
echo -e "${GREEN}Next steps for deployment on your Ubuntu server:${NC}"
echo "1. Make sure Docker and Docker Compose are installed"
echo "2. Create the required directories: data, configs, logs"
echo "3. Add your configuration files to the configs directory"
echo "4. Create a .env file with your Telegram bot token and chat ID"
echo "5. Pull and run the container using docker-compose.pull.yml"

exit 0